#!/bin/bash
# Non-network regression sweep: every suite run_acceptance.sh lists that lives under live/ or ops/,
# EXCEPT tests_entrypoint_wiring (it drives a DRY_RUN run_anchor, which makes a public fapi GET and
# is therefore battery-window work). One tree per invocation.
set -u
TREE=$1; TAG=$2
PY=/usr/bin/python3
OUT=/Users/haosiyu/cc_tmp/fx_w6c_probes/sweep_$TAG
mkdir -p "$OUT"
: > "$OUT/SUMMARY.txt"
grep -oE '"[A-Za-z0-9_]+:[$]_SELF/[A-Za-z0-9_/]+[.]py"' "$TREE/run_acceptance.sh" | tr -d '"' | while IFS=: read -r name path; do
  f="${path/\$_SELF/$TREE}"
  [ -f "$f" ] || { printf "%-40s MISSING\n" "$name" >> "$OUT/SUMMARY.txt"; continue; }
  case "$name" in tests_entrypoint_wiring) printf "%-40s SKIPPED_NETWORK\n" "$name" >> "$OUT/SUMMARY.txt"; continue;; esac
  env -u LIVE_MODE ACCEPTANCE_INNER=1 $PY "$f" > "$OUT/$name.log" 2>&1
  printf "%-40s rc=%s\n" "$name" "$?" >> "$OUT/SUMMARY.txt"
done
echo "SWEEP_DONE $TAG $(grep -c 'rc=0' $OUT/SUMMARY.txt) green / $(grep -c 'rc=' $OUT/SUMMARY.txt) run" >> "$OUT/SUMMARY.txt"
