#!/usr/bin/env bash
# pnoise_run_from_king.sh <label> -- the pnoise chain from an ALREADY-BUILT King OOF.
#
# Step 2 of docs/PREREG_gap_carrier_ladder_2026-09-25.md (be4a013a8): run refit arms (a) and (b)
# through the full pipeline. Identical to pnoise_run.sh EXCEPT that the King step is replaced by
# "the King OOF is supplied", because these arms are defined by modified King INPUTS (extra rows /
# researcher funding columns), not by a random_state.
#
# The caller must have placed $EXP/work/king/KING_OOF.npz before calling.
# Any non-zero rc stops the chain (lead: 任一次失败就停下报告, 不自动重试).
set -uo pipefail

LBL="${1:?usage: pnoise_run_from_king.sh <label>}"
EXP=/dev/shm/pnoise_2026-09-24
SRC=/dev/shm/news2_2026-09-23
NC=/dev/shm/nc_2026-09-23
D=$EXP/devices; E=$EXP/engine; L=$EXP/logs; W=$EXP
PV=/workspace/venv/bin/python
P314=/root/news_2026-09-23_env/venv314/bin/python
GATE=$D/news2_env_gate.py
NPY="X86_V4 AVX512_ICL AVX512_SPR"
say() { echo "$(date -u +%H:%M:%S) [$LBL] $*" | tee -a $L/step2.log; }

export PNOISE_W=$EXP
say "START (King supplied, not trained)"
[ -s $EXP/work/king/KING_OOF.npz ] || { say "FATAL: no supplied KING_OOF.npz"; exit 2; }
say "king sha=$(sha256sum $EXP/work/king/KING_OOF.npz | cut -c1-16)"

rm -rf $EXP/runs/* $EXP/work/legs.npz $EXP/work/NC_LEGS_RECEIPT.json $EXP/work/f10_s42 \
       $EXP/work/combo_s42 $EXP/targets/* $EXP/receipts/P3_LEGS.json
rm -f $EXP/configs/ADAPTER_SPEC_NEWS2_s42.json $EXP/configs/RUN_CONFIG_PNOISE.json

say "legs"
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NPY_DISABLE_CPU_FEATURES="$NPY" \
  NC_W=$NC NC_TREE=$NC/tree NC_WS=$NC/ws NC_CFG=$SRC/inputs/bundle_config.json \
  nice -n 10 $P314 -u $D/nc_legs.py $EXP/work/NEWS_FEATURES.npz $EXP/work/king/KING_OOF.npz \
  $EXP/work/legs.npz > $L/legs_$LBL.log 2>&1 || { say "LEGS FAILED"; exit 1; }
cp -a $EXP/work/NC_LEGS_RECEIPT.json $EXP/receipts/P3_LEGS.json
say "legs done"

BUSY=$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | wc -l)
if [ "$BUSY" -ne 0 ]; then say "GPU BUSY ($BUSY) -- STOP, not waiting silently"; exit 7; fi
say "f10 s42 (GPU free)"
cd $D
env -u NPY_DISABLE_CPU_FEATURES OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 PNOISE_W=$EXP \
  $PV -B $GATE --check f10 $EXP/receipts/ENV_GATE_f10_$LBL.json >> $L/step2.log 2>&1
env -u NPY_DISABLE_CPU_FEATURES OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 PNOISE_W=$EXP \
  nice -n 10 $PV -u news2_train_f10.py --seed 42 > $L/f10_$LBL.log 2>&1 || { say "F10 FAILED"; exit 1; }
say "f10 done"

say "combo"
NPY_DISABLE_CPU_FEATURES="$NPY" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PNOISE_W=$EXP \
  nice -n 10 $P314 -u news2_combo.py --seed 42 > $L/combo_$LBL.log 2>&1 || { say "COMBO FAILED"; exit 1; }
say "combo done"

say "adapter"
env -i PATH=/usr/bin:/bin HOME=/root $PV -B $D/news2_adapter_specs.py PATH,HOME,LC_CTYPE $W \
  > $L/adapter_specs_$LBL.log 2>&1 || { say "SPECS FAILED"; exit 1; }
cd $E
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $PV -B ovn_adapter.py PATH,HOME,LC_CTYPE \
  $W/configs/ADAPTER_SPEC_NEWS2_s42.json $W/targets/TARGETS_NEWS2_s42.npz \
  $W/targets/TARGETS_NEWS2_s42.json > $L/adapter_$LBL.log 2>&1 || { say "ADAPTER FAILED"; exit 1; }
say "adapter done TARGET_SHA=$(sha256sum $W/targets/TARGETS_NEWS2_s42.npz | cut -d' ' -f1 | cut -c1-16)"

say "config"
$PV - <<'PY' >> $L/step2.log 2>&1
import json, hashlib
SRC="/dev/shm/news2_2026-09-23"; EXP="/dev/shm/pnoise_2026-09-24"
src=json.load(open(f"{SRC}/configs/RUN_CONFIG_NEWS2_s42_2026-09-23.json"))
npz=f"{EXP}/targets/TARGETS_NEWS2_s42.npz"; rj=npz.replace(".npz",".json")
h=hashlib.sha256(open(npz,"rb").read()).hexdigest(); rh=hashlib.sha256(open(rj,"rb").read()).hexdigest()
base=src["runs"][0]
assert base["tag"]=="NEWS2_s42|scaled|rule|raw|UAFE", base["tag"]
for x in base["targets"]["sources"]:
    x["npz"]=npz; x["npz_sha256"]=h; x["receipt"]=rj; x["receipt_sha256"]=rh
src["runs"]=[base]; src["paths"]["pod_root"]=EXP; src["config"]="RUN_CONFIG_PNOISE"
json.dump(src,open(f"{EXP}/configs/RUN_CONFIG_PNOISE.json","w"),indent=1)
print("config ok", h[:16], rh[:16])
PY
say "config done"

say "engine"
cd $E
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $PV -B bt_launch.py PATH,HOME,LC_CTYPE \
  $W/configs/RUN_CONFIG_PNOISE.json --resume $LBL > $L/engine_$LBL.log 2>&1 \
  || { say "ENGINE FAILED"; exit 1; }
say "engine done"
say "CHAIN_DONE"
