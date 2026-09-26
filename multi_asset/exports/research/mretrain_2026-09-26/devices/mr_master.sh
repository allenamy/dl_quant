#!/bin/bash
# mr_master.sh -- the single pod2 executor of the family (§10-f): gates -> (prep queue || engine queue) -> MASTER_DONE.
# Every step below has THIS process as its executor; the only session-driven step is the reading device (named in the plan).
set -uo pipefail
R=/dev/shm/mretrain_2026-09-26; D=$R/devices; PV=/workspace/venv/bin/python; L=$R/logs; mkdir -p $L $R/gate
say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a $L/master.log; }
say "MASTER_START pgid=$(ps -o pgid= -p $$ | tr -d ' ')"
# ---- stage G: A0 m0 chain + an independent second training of A0 m0 (determinism) + gate device
bash $D/mr_prep.sh A0 0 train > $L/prep_A0_m0.out 2>&1 &
P1=$!
if [ ! -s $R/gate/A0_m0_dup/KING_OOF.npz ]; then
  rm -rf $R/gate/A0_m0_dup
  (cd $D && nice -n 12 $PV -B mr_train_king.py --out $R/gate/A0_m0_dup --arm A0 --rs 0 > $L/king_dup.log 2>&1)
fi
wait $P1 || { say "STOP: A0_m0 prep failed"; exit 1; }
grep -q "^Traceback" $L/king_dup.log && { say "STOP: dup king traceback"; exit 1; }
$PV -B $D/mr_gates.py $R/gate/MR_GATES.json > $L/gates.log 2>&1
say "$(tail -1 $L/gates.log)"
grep -q "ALL_PASS=True" $L/gates.log || { say "STOP: device gates FAILED -> whole family stops (rule section 0)"; exit 1; }
touch $R/GATES_PASS
# ---- stage F: prep queue (3 concurrent) and engine queue (1 at a time), both started now
bash $D/mr_engine_queue.sh $D/ORDER.txt > $L/engine_queue.out 2>&1 &
PE=$!
running=0; stopped=0
while read -r ARM M MODE; do
  [ -z "$ARM" ] && continue
  [ -e $R/ENGINE_QUEUE_STOPPED ] && { stopped=1; break; }
  while [ "$(jobs -rp | grep -v "^$PE$" | wc -l)" -ge 3 ]; do sleep 30; done
  for f in $R/arms/*/FAILED; do [ -e "$f" ] && { stopped=1; break 2; }; done
  bash $D/mr_prep.sh $ARM $M $MODE > $L/prep_${ARM}_m${M}_${MODE}.out 2>&1 &
  say "prep launched $ARM m$M $MODE"
done < $D/PREP_LIST.txt
while [ "$(jobs -rp | grep -v "^$PE$" | wc -l)" -gt 0 ]; do sleep 30; done
for f in $R/arms/*/FAILED; do [ -e "$f" ] && stopped=1; done
if [ $stopped -eq 1 ]; then touch $R/PREP_QUEUE_STOPPED; say "PREP_QUEUE_STOPPED"; else touch $R/PREP_QUEUE_DONE; say "PREP_QUEUE_DONE"; fi
wait $PE; rc=$?
say "engine queue rc=$rc"
[ $rc -eq 0 ] && say "MASTER_DONE" || say "MASTER_STOPPED"
