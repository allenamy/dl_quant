#!/bin/bash
# king_oct_controls.sh -- process executor (§10-f) of king_oct_train.py's device controls (fresh2 2026-09-27). Criteria are in
# king_oct_check.py's docstring (frozen before any run). No research reading: the D10 run is a dry run of the device on line D's
# committed NEWS_FEATURES_D10 (f1cd3fa2, receipt news2_2026-09-23/receipts/d10_2026-09-25/lineD/stage2/), not the October input.
#   R0  red: a wrong --features-sha is refused (non-zero, the assertion text, no output dir created)
#   C1  identity: in-service features 3c886a2b, rs 0 => KING_OOF E_ts/symbols/P bitwise == in-service a10b8725
#   C1s served: C1's fold-2026 model file reloaded reproduces its fold-2026 P bitwise
#   C2  determinism on D10: two rs-0 runs => bitwise equal P;  C2s served on D10;  C3 D10 P differs from in-service in > 0 cells
# Registered log: logs/controls.log; terminal line-start "<ts> (KOC_DONE|KOC_STOP)"; KOC_DONE carries all_pass=True|False.
set -uo pipefail
K=/workspace/king_oct_2026-09-27; D=$K/devices; PV=/workspace/venv/bin/python; LG=$K/logs/controls.log; RN=$K/runs
INS=/dev/shm/news2_2026-09-23/work/NEWS_FEATURES.npz; INS_SHA=3c886a2bc0ff65c10b7e0a621c9468210bbd77ef58c90e625f0a29354d63c4d8
D10=/workspace/d10_lineD_2026-09-26/stage2/NEWS_FEATURES_D10.npz; D10_SHA=f1cd3fa2b48e96ddf202a5098e08b9cc0ebcffda3bfc42c347743b9a5cd7d5fd
REF=/dev/shm/news2_2026-09-23/work/king/KING_OOF.npz; REF_SHA=a10b872506ca60afcd0f69b0e43d17a548cdd7c6956075000aac954b21e3df9a
mkdir -p $K/logs $RN $K/checks
say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a $LG; }
stop() { say "KOC_STOP: $*"; exit 1; }
PG=$(ps -o pgid= -p $$ | tr -d ' ')
echo "{\"what\":\"king_oct_controls.sh\",\"pgid\":\"$PG\",\"started_utc\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" > $K/logs/PGID_controls.json
say "KOC_START pgid=$PG"
[ "$(sha256sum $REF | cut -c1-64)" = "$REF_SHA" ] || stop "in-service KING_OOF is not a10b8725"
for r in R0 C1 C2a C2b; do [ -e $RN/$r ] && stop "run dir $RN/$r exists (fresh controls only; archive it first)"; done
# R0: refused before anything is created
(cd $D && $PV -B king_oct_train.py --out $RN/R0 --rs 0 --features $INS --features-sha 0000000000000000000000000000000000000000000000000000000000000000 > $K/logs/R0.log 2>&1); r0=$?
if [ $r0 -ne 0 ] && grep -q "features sha .* != --features-sha" $K/logs/R0.log && [ ! -e $RN/R0 ]; then say "R0 PASS refused rc=$r0, no output dir"; R0=True
else say "R0 FAIL rc=$r0 dir_exists=$([ -e $RN/R0 ] && echo yes || echo no)"; R0=False; fi
train() { (cd $D && nice -n 12 $PV -B king_oct_train.py --out $RN/$1 --rs 0 --features $2 --features-sha $3 $4 > $K/logs/train_$1.log 2>&1); }
train C1 $INS $INS_SHA --keep-models & p1=$!
train C2a $D10 $D10_SHA --keep-models & p2=$!
train C2b $D10 $D10_SHA "" & p3=$!
say "trainings launched C1 C2a C2b"
for p in $p1 $p2 $p3; do wait $p; done
for r in C1 C2a C2b; do
  grep -q "^Traceback" $K/logs/train_$r.log && stop "$r traceback (see $K/logs/train_$r.log)"
  grep -q "KING_DONE" $K/logs/train_$r.log || stop "$r no KING_DONE"
done
say "trainings done"
all=$R0
chk() { local n=$1; shift; $PV -B $D/king_oct_check.py "$@" $K/checks/$n.json > $K/logs/check_$n.log 2>&1; say "$n $(grep -h '^KOC_CHECK' $K/logs/check_$n.log | cut -c1-300)"
        grep -q "^KOC_CHECK [a-z]* PASS=True" $K/logs/check_$n.log || all=False; }
chk C1_same same $RN/C1/KING_OOF.npz $REF
chk C1_served served $RN/C1 $INS $INS_SHA
chk C2_same same $RN/C2a/KING_OOF.npz $RN/C2b/KING_OOF.npz
chk C2_served served $RN/C2a $D10 $D10_SHA
chk C3_differ differ $RN/C2a/KING_OOF.npz $REF
say "KOC_DONE all_pass=$all"
