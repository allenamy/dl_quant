#!/bin/bash
# run_a1leak.sh -- executor (protocol 10-f) of the A1 leakage audit (lead 2026-09-27 05:1xZ; descriptive, A1 verdict d585e1792 not reopened).
# 1. static audit (L1 fold boundaries, L2 shared features, L3 offset spectrum, L5 model age) -- read-only, runs beside step 2;
# 2. three A1 rs=0 retrains with dlarch_a1leak_train.py: future (all folds), pastlast (folds 202301,202506,202608), all (all folds);
# 3. shuffle reading (L4a/b/c) once all three trainings wrote KING_DONE.
# Terminal line (line start): 'A1LEAK_DONE rc=<n>' ; 'A1LEAK_STOP <why>'. Traceback anywhere in the log = failure (rc 1).
set -u
W=/workspace/dlarch_2026-09-24; A=$W/a1leak_2026-09-27; LOG=$A/a1leak.log; PY=/workspace/venv/bin/python; R=$W/receipts
mkdir -p $A/arms $A/logs
mkdir "$W/CHAIN/.claim_A1LEAK" 2>/dev/null || { echo "A1LEAK_STOP claim exists or cannot be created" >> "$LOG"; exit 4; }
echo "pgid=$(ps -o pgid= -p $$ | tr -d ' ') pid=$$ owner=dlarch job=a1leak started=$(date -u +%FT%TZ)" | tee "$W/CHAIN/.claim_A1LEAK/owner" > "$A/a1leak.pgid"
say(){ echo "$(date -u +%FT%TZ) $*" >> "$LOG"; }
stop(){ echo "A1LEAK_STOP $1" >> "$LOG"; rm -rf "$W/CHAIN/.claim_A1LEAK"; exit 1; }
ENV="env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C"
say "A1LEAK_START devices audit=$(sha256sum $A/dlarch_a1leak_audit.py | cut -c1-16) train=$(sha256sum $A/dlarch_a1leak_train.py | cut -c1-16)"
( cd $A && $ENV OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 nice -n 12 $PY -B dlarch_a1leak_audit.py PATH,HOME,LC_CTYPE static $R/A1LEAK_STATIC_2026-09-27.json > $A/logs/static.log 2>&1 ) &
PS=$!
train(){ # <tag> <mode> [folds]
  local F=""; [ -n "${3:-}" ] && F="--folds $3"
  ( cd $A && $ENV nice -n 12 $PY -B dlarch_a1leak_train.py --out $A/arms/$1 --arm A1 --rs 0 --label y4s --shuffle $2 $F > $A/logs/train_$1.log 2>&1 )
  grep -q KING_DONE $A/logs/train_$1.log || { echo "FAIL $1" > $A/logs/FAIL_$1; return 1; }
}
rm -f $A/logs/FAIL_*
train FUT future & P1=$!; train PAS pastlast 202301,202506,202608 & P2=$!; train ALL all & P3=$!
say "launched static pid=$PS trains pids=$P1,$P2,$P3"
wait $PS; RS=$?; cat $A/logs/static.log >> "$LOG"; say "static rc=$RS"
wait $P1 $P2 $P3
ls $A/logs/FAIL_* > /dev/null 2>&1 && { RC=1; say "training failed: $(cat $A/logs/FAIL_* | tr '\n' ' ')"; } || RC=0
[ $RS -ne 0 ] && RC=1
if [ $RC -eq 0 ]; then
  say "trainings KING_DONE x3"
  ( cd $A && $ENV OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 nice -n 12 $PY -B dlarch_a1leak_audit.py PATH,HOME,LC_CTYPE shuffle $R/A1LEAK_SHUFFLE_2026-09-27.json \
      $A/arms/FUT $A/arms/PAS $A/arms/ALL >> "$LOG" 2>&1 ) || RC=1
fi
grep -q Traceback "$LOG" $A/logs/*.log && RC=1
echo "A1LEAK_DONE rc=$RC" >> "$LOG"; rm -rf "$W/CHAIN/.claim_A1LEAK"
