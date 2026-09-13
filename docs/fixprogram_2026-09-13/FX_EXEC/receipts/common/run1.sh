#!/bin/bash
# run1.sh <tree> <suite-relpath> <logfile> — one suite, the battery's interpreter + pyenv, foreground, rc recorded
set -uo pipefail
TREE="$1"; SUITE="$2"; LOG="$3"
cd "$TREE" || exit 99
. "$TREE/ops/pyenv.sh"
PY="${ACCEPT_PY:-/usr/bin/python3}"
{
  echo "# run1 tree=$TREE suite=$SUITE head=$(git -C "$TREE" rev-parse HEAD) dirty=$(git -C "$TREE" status --porcelain --untracked-files=no -- live ops scheduler signal run_acceptance.sh | wc -l | tr -d ' ') start=$(date -u +%Y-%m-%dT%H:%M:%SZ) py=$($PY --version 2>&1)"
  echo "# suite_sha256=$(shasum -a 256 "$TREE/$SUITE" | cut -d' ' -f1)"
} > "$LOG"
"$PY" "$TREE/$SUITE" >> "$LOG" 2>&1
RC=$?
echo "# end=$(date -u +%Y-%m-%dT%H:%M:%SZ) rc=$RC" >> "$LOG"
exit $RC
