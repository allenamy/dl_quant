#!/bin/bash
# The control for "are these suites really offline?": the same sweep with every HTTP(S) request
# pointed at a dead local address. No real request can leave the machine, so this is safe outside
# the battery window — and any suite whose rc CHANGES is one whose behaviour depends on reaching
# the network, which is the question.
set -u
TREE=$1; TAG=$2
PY=/usr/bin/python3
OUT=/Users/haosiyu/cc_tmp/fx_w6c_probes/sweep_$TAG
mkdir -p "$OUT"; : > "$OUT/SUMMARY.txt"
export http_proxy=http://127.0.0.1:9 https_proxy=http://127.0.0.1:9 HTTP_PROXY=http://127.0.0.1:9 HTTPS_PROXY=http://127.0.0.1:9 no_proxy= NO_PROXY=
grep -oE '"[A-Za-z0-9_]+:[$]_SELF/[A-Za-z0-9_/]+[.]py"' "$TREE/run_acceptance.sh" | tr -d '"' | while IFS=: read -r name path; do
  f="${path/\$_SELF/$TREE}"
  [ -f "$f" ] || { printf "%-40s MISSING\n" "$name" >> "$OUT/SUMMARY.txt"; continue; }
  case "$name" in tests_entrypoint_wiring) printf "%-40s SKIPPED_NETWORK\n" "$name" >> "$OUT/SUMMARY.txt"; continue;; esac
  env -u LIVE_MODE ACCEPTANCE_INNER=1 $PY "$f" > "$OUT/$name.log" 2>&1
  printf "%-40s rc=%s\n" "$name" "$?" >> "$OUT/SUMMARY.txt"
done
echo "SWEEP_DONE $TAG" >> "$OUT/SUMMARY.txt"
