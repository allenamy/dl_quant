#!/bin/bash
# kf_train_family.sh <ARM...>  -- process executor (§10-f) of the King improvement family's training (fresh2 2026-09-27; rule 4158f1521).
# ARM in {A1, KN}: 8 members rs 0..7 + one duplicate of m0 (revision 1: scores must be bitwise equal, else STOP). KN needs the pinned
# T_NET (TNET_PIN.json: path + sha, written by fresh2 only after dlarch's identity control PASS). 3 trainings in parallel (8 threads each).
# Per member: KING_IDENTITY.json (model-text shas + score shas). A1_m0 / A1_m1 scores must also equal their run-3 scores (receipted
# 3498659b / 7e1d2f01; the same determinism property across runs) else STOP. End: MANIFEST.json + "KF_TRAIN_DONE" (the IC device binds it).
# Registered log: logs/kingfam.log, terminal ^\S+ (STOP|KF_TRAIN_DONE).
set -uo pipefail
K=/workspace/kingfam_2026-09-27; D=$K/devices; PV=/workspace/venv/bin/python; MG=/dev/shm/mretrain_2026-09-26/devices/mr_gates.py
LG=$K/logs/kingfam.log; mkdir -p $K/arms $K/logs
say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a $LG; }
stop() { say "STOP: $*"; exit 1; }
PG=$(ps -o pgid= -p $$ | tr -d ' ')
echo "{\"what\":\"kf_train_family2.sh $*\",\"pgid\":\"$PG\",\"started_utc\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" > $K/logs/PGID_train_$(echo $* | tr " " "_").json
say "KF_TRAIN_START pgid=$PG arms=$*"
declare -A RUN3=([A1_m0]=3498659b09520ca9 [A1_m1]=7e1d2f012505d8ca)
train() {   # <LBL> <ARM> <RS>
  local LBL=$1 ARM=$2 RS=$3 W=$K/arms/$1 EXTRA=""
  if [ "$ARM" = KN ]; then
    local TP TS; TP=$(python3 -c "import json;print(json.load(open('$K/TNET_PIN.json'))['path'])"); TS=$(python3 -c "import json;print(json.load(open('$K/TNET_PIN.json'))['sha256'])")
    EXTRA="--arm A0 --label tnet --tnet $TP --tnet-sha $TS"
  else EXTRA="--arm $ARM --label y4s"; fi
  if [ ! -s $W/KING_OOF.npz ]; then
    rm -rf $W; (cd $D && nice -n 12 $PV -B kf_train_king.py --out $W --rs $RS $EXTRA > $K/logs/train_$LBL.log 2>&1)
    grep -q "KING_DONE" $K/logs/train_$LBL.log || { echo "FAIL $LBL" > $K/logs/FAIL_$LBL; return 1; }
  fi
  $PV -B $MG --identity $W/KING_OOF.npz $W/KING_IDENTITY.json > $K/logs/identity_$LBL.log 2>&1 || { echo "FAIL identity $LBL" > $K/logs/FAIL_$LBL; return 1; }
}
[ " $* " == *" KN "* ] && { [ -s $K/TNET_PIN.json ] || stop "KN requested but TNET_PIN.json absent"; }
JOBS=()
for ARM in "$@"; do for m in 0 1 2 3 4 5 6 7; do JOBS+=("${ARM}_m$m $ARM $m"); done; JOBS+=("${ARM}_m0_dup $ARM 0"); done
rm -f $K/logs/FAIL_*
for j in "${JOBS[@]}"; do
  while [ "$(jobs -rp | wc -l)" -ge 3 ]; do sleep 10; done
  ls $K/logs/FAIL_* > /dev/null 2>&1 && break
  train $j & say "train launched $j"
done
wait
ls $K/logs/FAIL_* > /dev/null 2>&1 && stop "training failed: $(cat $K/logs/FAIL_* | tr '\n' ' ')"
for ARM in "$@"; do
  $PV -B $MG --dup $K/arms/${ARM}_m0/KING_OOF.npz $K/arms/${ARM}_m0_dup/KING_OOF.npz $K/arms/${ARM}_m0_dup/DUP_CHECK.json > $K/logs/dup_$ARM.log 2>&1
  grep -q "^MR_DUP PASS=True" $K/logs/dup_$ARM.log || stop "revision-1 duplicate check ${ARM}_m0: scores not bitwise equal"
  say "dup ${ARM}_m0 $(head -c 160 $K/logs/dup_$ARM.log)"
done
for L in "${!RUN3[@]}"; do
  [ -s $K/arms/$L/KING_IDENTITY.json ] || continue
  grep -q "\"P\": \"${RUN3[$L]}" $K/arms/$L/KING_IDENTITY.json || stop "$L scores differ from their run-3 scores ${RUN3[$L]}"
  say "$L scores == run-3 ${RUN3[$L]}"
done
$PV - $K "$@" <<'PY' || stop "manifest"
import sys, json, hashlib, os
K, arms = sys.argv[1], sys.argv[2:]
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
man = {}
for a in arms:
    for l in [f"{a}_m{m}" for m in range(8)] + [f"{a}_m0_dup"]:
        W = f"{K}/arms/{l}"; idn = json.load(open(f"{W}/KING_IDENTITY.json")); rec = json.load(open(f"{W}/TRAIN_RECEIPT.json"))
        man[l] = {"oof": f"{W}/KING_OOF.npz", "oof_sha256": sha(f"{W}/KING_OOF.npz"), "P_sha256": idn["array_sha256"]["P"],
                  "receipt_sha256": sha(f"{W}/TRAIN_RECEIPT.json"), "arm_folds": rec["arm"], "label": rec["label_switch"], "random_state": rec["random_state"],
                  "role": "duplicate (determinism only; not a member)" if l.endswith("_dup") else "member"}
p = f"{K}/MANIFEST_{'_'.join(arms)}.json"; json.dump(man, open(p + ".tmp", "w"), indent=1); os.replace(p + ".tmp", p)
print(p, sha(p))
PY
say "KF_TRAIN_DONE arms=$* manifest=$(ls $K/MANIFEST_$(echo $* | tr ' ' '_').json) sha=$(sha256sum $K/MANIFEST_$(echo $* | tr ' ' '_').json | cut -c1-16)"
