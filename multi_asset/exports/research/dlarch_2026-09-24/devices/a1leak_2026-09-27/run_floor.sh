#!/bin/bash
# run_floor.sh -- executor (protocol 10-f) of lead's two L4c questions (06:0xZ): four A0 m0-recipe noise models (all-shuffle, seeds
# 20260927..20260930; seed 20260927 = the same permuted labels as the A1 L4c arm), then dlarch_a1leak_floor.py.
# Terminal line (line start): 'FLOOR_DONE rc=<n>' ; 'FLOOR_STOP <why>'. Traceback anywhere = failure.
set -u
W=/workspace/dlarch_2026-09-24; A=$W/a1leak_2026-09-27; LOG=$A/floor.log; PY=/workspace/venv/bin/python; R=$W/receipts
mkdir "$W/CHAIN/.claim_FLOOR" 2>/dev/null || { echo "FLOOR_STOP claim exists or cannot be created" >> "$LOG"; exit 4; }
echo "pgid=$(ps -o pgid= -p $$ | tr -d ' ') pid=$$ owner=dlarch job=a1leak_floor started=$(date -u +%FT%TZ)" | tee "$W/CHAIN/.claim_FLOOR/owner" > "$A/floor.pgid"
say(){ echo "$(date -u +%FT%TZ) $*" >> "$LOG"; }
ENV="env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C"
say "FLOOR_START floor=$(sha256sum $A/dlarch_a1leak_floor.py | cut -c1-16) train=$(sha256sum $A/dlarch_a1leak_train.py | cut -c1-16)"
rm -f $A/logs/FAIL_A0N*
train(){ # <seed>
  local T=A0N_$1
  if [ -s $A/arms/$T/KING_OOF.npz ] && grep -q KING_DONE $A/logs/train_$T.log 2>/dev/null; then return 0; fi
  rm -rf $A/arms/$T
  ( cd $A && $ENV nice -n 12 $PY -B dlarch_a1leak_train.py --out $A/arms/$T --arm A0 --rs 0 --label y4s --shuffle all --shuffle-seed $1 > $A/logs/train_$T.log 2>&1 )
  grep -q KING_DONE $A/logs/train_$T.log || { echo "FAIL $T" > $A/logs/FAIL_$T; return 1; }
}
for S in 20260927 20260928 20260929 20260930; do train $S & done
wait
RC=0
ls $A/logs/FAIL_A0N* > /dev/null 2>&1 && { RC=1; say "training failed: $(cat $A/logs/FAIL_A0N* | tr '\n' ' ')"; }
if [ $RC -eq 0 ]; then
  say "A0 noise trainings KING_DONE x4"
  ( cd $A && $ENV OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 nice -n 12 $PY -B dlarch_a1leak_floor.py PATH,HOME,LC_CTYPE $R/A1LEAK_FLOOR_2026-09-27.json \
      $A/arms/ALL $A/arms/A0N_20260927 $A/arms/A0N_20260928 $A/arms/A0N_20260929 $A/arms/A0N_20260930 >> "$LOG" 2>&1 ) || RC=1
fi
grep -q Traceback "$LOG" $A/logs/train_A0N_*.log && RC=1
echo "FLOOR_DONE rc=$RC" >> "$LOG"; rm -rf "$W/CHAIN/.claim_FLOOR"
