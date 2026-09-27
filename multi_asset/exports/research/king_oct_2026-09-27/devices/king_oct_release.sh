#!/bin/bash
# king_oct_release.sh -- process executor (§10-f) of the October candidate King (fresh2 2026-09-27; lead: user chose plan (ii),
# runbook 1fa4e3be5). king_oct_train.py (8dd1a0068, controls 5078fd402) on D10 features f1cd3fa2: m0 = rs 0 WITH --keep-models
# (its king_2026.txt is the file to pin), m1..m7 = rs 1..7 OOF (descriptive), m0_dup = rs 0 again (determinism of THIS run).
# Gates (frozen here, before the run): G1 m0 == m0_dup; G2 m0 == controls C2a (same code, same input); G3 m0's served file reproduces
# its fold-2026 P bitwise; every member KING_DONE. Then king_oct_manifest.py writes MANIFEST_RELEASE.json and the release root is
# marked read-only (E-0912-B: the file to pin must not be rewritten in place). pod2 runs as root, which ignores mode bits, so the mark
# is a signal only; the guard is the sha in the manifest, which every consumer must check before use.
# Registered log: logs/release.log; terminal line-start "<ts> (KOR_STOP|KOR_DONE)"; KOR_DONE carries release_ok=True|False.
set -uo pipefail
K=/workspace/king_oct_2026-09-27; D=$K/devices; PV=/workspace/venv/bin/python; LG=$K/logs/release.log; RL=$K/release
D10=/workspace/d10_lineD_2026-09-26/stage2/NEWS_FEATURES_D10.npz; D10_SHA=f1cd3fa2b48e96ddf202a5098e08b9cc0ebcffda3bfc42c347743b9a5cd7d5fd
C2A=$K/runs/C2a/KING_OOF.npz
say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a $LG; }
stop() { say "KOR_STOP: $*"; exit 1; }
mkdir -p $K/logs
PG=$(ps -o pgid= -p $$ | tr -d ' ')
echo "{\"what\":\"king_oct_release.sh\",\"pgid\":\"$PG\",\"started_utc\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" > $K/logs/PGID_release.json
say "KOR_START pgid=$PG"
[ -e $RL ] && stop "release root $RL exists (a release is written once; archive it first)"
[ -s $C2A ] || stop "controls C2a OOF missing (G2 reference)"
mkdir -p $RL/checks
JOBS=("m0 0 --keep-models" "m1 1" "m2 2" "m3 3" "m4 4" "m5 5" "m6 6" "m7 7" "m0_dup 0")
train() { (cd $D && nice -n 12 $PV -B king_oct_train.py --out $RL/$1 --rs $2 --features $D10 --features-sha $D10_SHA ${3:-} > $K/logs/release_train_$1.log 2>&1) \
          || echo "FAIL $1 rc=$?" > $RL/FAIL_$1; }
failed() { ls $RL/FAIL_* > /dev/null 2>&1; }
for j in "${JOBS[@]}"; do
  while [ "$(jobs -rp | wc -l)" -ge 3 ]; do failed && break; sleep 10; done
  failed && break
  set -- $j; failed || { train $1 $2 ${3:-} & }; say "train launched $j"   # failure re-checked on the launch line (mr_stop.sh rule 2)
done
wait
failed && stop "training failed: $(cat $RL/FAIL_* | tr '\n' ' ')"
for j in "${JOBS[@]}"; do set -- $j; grep -q "KING_DONE" $K/logs/release_train_$1.log || stop "$1 no KING_DONE"; done
say "trainings done (9)"
chk() { local n=$1; shift; $PV -B $D/king_oct_check.py "$@" $RL/checks/$n.json > $K/logs/release_check_$n.log 2>&1
        say "$n $(grep -h '^KOC_CHECK' $K/logs/release_check_$n.log | cut -c1-260)"
        grep -q "^KOC_CHECK [a-z]* PASS=True" $K/logs/release_check_$n.log || stop "$n not PASS (see $K/logs/release_check_$n.log)"; }
chk G1_dup same $RL/m0/KING_OOF.npz $RL/m0_dup/KING_OOF.npz
chk G2_cross_run_vs_C2a same $RL/m0/KING_OOF.npz $C2A
chk G3_served served $RL/m0 $D10 $D10_SHA
(cd $D && $PV -B king_oct_manifest.py $RL $D10_SHA > $K/logs/release_manifest.log 2>&1); mrc=$?
say "$(grep -h '^KOR_MANIFEST' $K/logs/release_manifest.log | cut -c1-260)"
[ $mrc -eq 0 ] || stop "manifest rc=$mrc (see $K/logs/release_manifest.log)"
chmod -R a-w $RL && say "release root marked read-only (mode bits; root ignores them -- the manifest sha is the guard)"
say "KOR_DONE release_ok=True served=$(grep -o 'served=[0-9a-f]*' $K/logs/release_manifest.log | cut -c8-)"
