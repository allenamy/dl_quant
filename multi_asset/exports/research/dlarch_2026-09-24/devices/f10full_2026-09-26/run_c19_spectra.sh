#!/bin/sh
# C1.9 inputs: F10_FULL s2027 / s7 pooled offset spectra via the frozen dlarch_f10full_leak.py (26c9ff6e),
# same invocation shape as the delivered s42 receipt (K=5 default). Sequential. Then the re-judge.
set -u
W=/workspace/dlarch_2026-09-24
PY=/workspace/venv/bin/python
LOG=$W/CHAIN/c19_spectra.log
MYPGID=$(ps -o pgid= -p $$ | tr -d ' ')
mkdir "$W/CHAIN/.claim_C19" 2>/dev/null || { echo "claimed elsewhere" >> "$LOG"; exit 4; }
echo "pgid=$MYPGID pid=$$ owner=dlarch job=c19_spectra started=$(date -u +%FT%TZ)" | tee "$W/CHAIN/.claim_C19/owner" > "$W/CHAIN/c19_spectra.pgid"
cd "$W"
for S in 2027 7; do
  echo "$(date -u +%T) start s$S" >> "$LOG"
  env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C "$PY" -B dlarch_f10full_leak.py PATH,HOME,LC_CTYPE \
     "$W/T3/G1_T0_nomask_frac1/f10_s$S" "$W/receipts/F10FULL_LEAK_s${S}_23folds_2026-09-26.json" >> "$LOG" 2>&1
  RC=$?; echo "$(date -u +%T) s$S rc=$RC" >> "$LOG"
  [ $RC -eq 0 ] || { echo "C19_RUN_DONE rc=1" >> "$LOG"; rm -rf "$W/CHAIN/.claim_C19"; exit 1; }
done
env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C "$PY" -B dlarch_c19_rejudge.py PATH,HOME,LC_CTYPE \
   "$W/receipts/C1_9_REJUDGE_KPOS_2026-09-26.json" \
   "$W/receipts/F10FULL_LEAK_s42_23folds_2026-09-26.json" "$W/receipts/F10FULL_LEAK_s2027_23folds_2026-09-26.json" \
   "$W/receipts/F10FULL_LEAK_s7_23folds_2026-09-26.json" \
   "$W/receipts/LEAK_NC_INSERVICE_s42_2026-09-26.json" "$W/receipts/LEAK_NC_INSERVICE_s2027_2026-09-26.json" >> "$LOG" 2>&1
RC=$?
rm -rf "$W/CHAIN/.claim_C19"
if [ $RC -ne 0 ] || grep -q Traceback "$LOG"; then echo "C19_RUN_DONE rc=1" >> "$LOG"; exit 1; fi
echo "C19_RUN_DONE rc=0" >> "$LOG"
