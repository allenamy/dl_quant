#!/bin/sh
set -u
W=/workspace/dlarch_2026-09-24
LOG=$W/CHAIN/f10full_verdict.log
mkdir "$W/CHAIN/.claim_F10FULL_VERDICT" 2>/dev/null || { echo "claimed elsewhere" >> "$LOG"; exit 4; }
echo "pgid=$(ps -o pgid= -p $$ | tr -d ' ') pid=$$ owner=dlarch job=f10full_verdict started=$(date -u +%FT%TZ)" | tee "$W/CHAIN/.claim_F10FULL_VERDICT/owner" > "$W/CHAIN/f10full_verdict.pgid"
cd "$W" && env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C /workspace/venv/bin/python -B dlarch_f10full_verdict.py \
   PATH,HOME,LC_CTYPE "$W" "$W/receipts/F10FULL_VERDICT_2026-09-26.json" >> "$LOG" 2>&1
RC=$?
rm -rf "$W/CHAIN/.claim_F10FULL_VERDICT"
if [ $RC -ne 0 ] || grep -q Traceback "$LOG"; then echo "VERDICT_RUN_DONE rc=1" >> "$LOG"; exit 1; fi
echo "VERDICT_RUN_DONE rc=0" >> "$LOG"
