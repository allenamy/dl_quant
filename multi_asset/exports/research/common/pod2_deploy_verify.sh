#!/bin/bash
# pod2_deploy_verify.sh <remote dir> <local dir[:local dir...]> [<remote name>=<repo path> ...] -- three-way deploy check (fresh2 2026-09-27; class fix of
# the stale pod2 copy of durable_write.py news2 found: copied once into /workspace/king_oct_2026-09-27/devices, never compared again).
# For EVERY regular file in the remote dir (derived from the remote dir itself, not from a hand list):
#   source = <local dir>/<name>, or the repo path given by a <name>=<path> mapping (vendored copies, e.g. durable_write.py=.../common/...)
#   PASS for the file  <=>  sha(git HEAD blob of source) == sha(working-tree source) == sha(remote file)
#   a remote file with no source is UNKNOWN (reported, counted as a failure unless its name ends in a declared archive suffix)
# Archive copies kept on purpose are named <name>.<sha8>_used_by_* or *.bak_* and are listed, not compared.
# Prints one line per file and a final line "DEPLOY_VERIFY PASS=True|False n=<files> ..."; rc 0 only on PASS.
set -uo pipefail
RD=$1; LDS=$2; shift 2   # several local dirs (first one holding the name wins): a deploy dir may mix devices of several owners
REPO=$(git -C "${LDS%%:*}" rev-parse --show-toplevel)
inlocal() { local d; local IFS=:; for d in $LDS; do [ -f "$d/$1" ] && { echo "$(cd "$d" && pwd)/$1"; return 0; }; done; return 1; }
MAPS=("$@")   # runs on the Mac (bash 3.2: no associative arrays) -> linear lookup
mapped() { local m; for m in ${MAPS[@]+"${MAPS[@]}"}; do [ "${m%%=*}" = "$1" ] && { echo "${m#*=}"; return 0; }; done; return 1; }
n=0; bad=0; arch=0
while IFS= read -r line; do
  rsha=${line%% *}; name=${line##* }; name=${name##*/}
  case $name in *_used_by_*|*.bak_*) echo "ARCHIVE  $name $rsha"; arch=$((arch + 1)); continue;; esac
  n=$((n + 1))
  src=$(mapped "$name") || src=$(inlocal "$name") || src=/nonexistent/$name; [ "${src#/}" = "$src" ] && src=$REPO/$src
  if [ ! -f "$src" ]; then echo "UNKNOWN  $name remote=$rsha (no local source)"; bad=$((bad + 1)); continue; fi
  rel=$(python3 -c "import os,sys;print(os.path.relpath(os.path.realpath(sys.argv[1]),os.path.realpath(sys.argv[2])))" "$src" "$REPO")
  wsha=$(shasum -a 256 "$src" | cut -c1-64)
  hsha=$(git -C "$REPO" show "HEAD:$rel" 2>/dev/null | shasum -a 256 | cut -c1-64)
  git -C "$REPO" cat-file -e "HEAD:$rel" 2>/dev/null || hsha=NOT_IN_HEAD
  if [ "$hsha" = "$wsha" ] && [ "$wsha" = "$rsha" ]; then echo "OK       $name $rsha"
  else echo "MISMATCH $name head=${hsha:0:12} worktree=${wsha:0:12} remote=${rsha:0:12} src=$rel"; bad=$((bad + 1)); fi
done < <(ssh -o BatchMode=yes pod2 "find $RD -maxdepth 1 -type f -exec sha256sum {} +" | sort -k2)
[ $n -gt 0 ] || { echo "DEPLOY_VERIFY PASS=False n=0 (empty remote dir or ssh failed: 0/0 is not a pass)"; exit 1; }
echo "DEPLOY_VERIFY PASS=$([ $bad -eq 0 ] && echo True || echo False) n=$n bad=$bad archived=$arch remote=$RD"
[ $bad -eq 0 ]
