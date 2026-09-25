#!/usr/bin/env bash
# pnoise_run.sh <random_state> -- one perturbed chain, King -> legs -> F10 s42 -> combo -> adapter -> engine(base) .
#
# Pre-registration: docs/PREREG_perturbation_noise_run_2026-09-24.md (41e5e8776).
# Every step opens with news2_env_gate.py --check <step> INSIDE that step's own environment (running the
# gate outside the step's env is what made it print REFUSED when I first tried it by hand).
# Any non-zero rc stops the chain: lead 2026-09-24 "如果中途任一次失败,就停下报告,不自动重试".
set -euo pipefail

R="${1:?usage: pnoise_run.sh <random_state>}"
EXP=/dev/shm/pnoise_2026-09-24
SRC=/dev/shm/news2_2026-09-23
NC=/dev/shm/nc_2026-09-23
D=$EXP/devices; E=$EXP/engine; L=$EXP/logs; W=$EXP
PV=/workspace/venv/bin/python
P314=/root/news_2026-09-23_env/venv314/bin/python
GATE=$D/news2_env_gate.py
NPY="X86_V4 AVX512_ICL AVX512_SPR"
TAG="PNOISE_r$R"
say() { echo "$(date -u +%H:%M:%S) [$TAG] $*" | tee -a $L/pnoise_$R.log; }

export PNOISE_W=$EXP

say "START random_state=$R"
say "shm_free_gib=$(df -k /dev/shm | tail -1 | awk '{printf "%.2f", $4/1048576}')"

# ---- 0. clear this run's outputs (previous run's artifacts are freed by the caller) ----
rm -rf $EXP/runs/* $EXP/work/king $EXP/work/legs.npz $EXP/work/NC_LEGS_RECEIPT.json $EXP/work/f10_s42 \
       $EXP/work/combo_s42 $EXP/targets/* $EXP/configs/* $EXP/receipts/P3_LEGS.json

# ---- 1. King ----
say "king"
cd $D
NPY_DISABLE_CPU_FEATURES="$NPY" PNOISE_RANDOM_STATE=$R $PV -B $GATE --check king $EXP/receipts/ENV_GATE_king_r$R.json >> $L/pnoise_$R.log 2>&1
NPY_DISABLE_CPU_FEATURES="$NPY" PNOISE_RANDOM_STATE=$R nice -n 10 $PV -u news2_train_king.py > $L/king_r$R.log 2>&1
say "king done"

# ---- 2. legs ----
# NC_W must be the NC workspace: legs reads work/axes.npz and ws/ caches from there (read-only).
say "legs"
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NPY_DISABLE_CPU_FEATURES="$NPY" \
  NC_W=$NC NC_TREE=$NC/tree NC_WS=$NC/ws NC_CFG=$SRC/inputs/bundle_config.json \
  nice -n 10 $P314 -u nc_legs.py $EXP/work/NEWS_FEATURES.npz $EXP/work/king/KING_OOF.npz $EXP/work/legs.npz \
  > $L/legs_r$R.log 2>&1
cp -a $EXP/work/NC_LEGS_RECEIPT.json $EXP/receipts/P3_LEGS.json
say "legs done"

# ---- 3. F10 s42 (GPU) ----
# lead / user rule: the GPU is only used when nobody else is on it.
BUSY=$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | wc -l)
if [ "$BUSY" -ne 0 ]; then say "GPU BUSY ($BUSY procs) -- STOP, not waiting silently"; exit 7; fi
say "f10 s42 (GPU free)"
cd $D
env -u NPY_DISABLE_CPU_FEATURES OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
  $PV -B $GATE --check f10 $EXP/receipts/ENV_GATE_f10_r$R.json >> $L/pnoise_$R.log 2>&1
env -u NPY_DISABLE_CPU_FEATURES OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
  nice -n 10 $PV -u news2_train_f10.py --seed 42 > $L/f10_r$R.log 2>&1
say "f10 done"

# ---- 4. combo s42 ----
say "combo"
NPY_DISABLE_CPU_FEATURES="$NPY" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  $P314 -B $GATE --check combo $EXP/receipts/ENV_GATE_combo_r$R.json >> $L/pnoise_$R.log 2>&1
NPY_DISABLE_CPU_FEATURES="$NPY" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  nice -n 10 $P314 -u news2_combo.py --seed 42 > $L/combo_r$R.log 2>&1
say "combo done"

# ---- 5. adapter (specs + targets) ----
say "adapter"
env -i PATH=/usr/bin:/bin HOME=/root $PV -B $D/news2_adapter_specs.py PATH,HOME,LC_CTYPE $W > $L/adapter_specs_r$R.log 2>&1
cd $E
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $PV -B ovn_adapter.py PATH,HOME,LC_CTYPE \
  $W/configs/ADAPTER_SPEC_NEWS2_s42.json $W/targets/TARGETS_NEWS2_s42.npz $W/targets/TARGETS_NEWS2_s42.json \
  > $L/adapter_r$R.log 2>&1
say "adapter done TARGET_SHA=$(sha256sum $W/targets/TARGETS_NEWS2_s42.npz | cut -d' ' -f1)"

# ---- 6. run config: derived from the archived s42 config, BASE CELL ONLY ----
# Derivation, each change recorded in the receipt: pod_root -> the experiment root; runs -> [runs[0]]
# (the base cell; lead approved "runs only base" for the attribution design and the same trade-off
# applies here); the targets npz path + sha -> this run's; arm/tag -> PNOISE_r<R> so outputs never
# collide with the archived NC cells.
say "config"
$PV - <<'PY' >> $L/pnoise_$R.log 2>&1
import json, hashlib
SRC="/dev/shm/news2_2026-09-23"; EXP="/dev/shm/pnoise_2026-09-24"
src=json.load(open(f"{SRC}/configs/RUN_CONFIG_NEWS2_s42_2026-09-23.json"))
npz=f"{EXP}/targets/TARGETS_NEWS2_s42.npz"
h=hashlib.sha256(open(npz,"rb").read()).hexdigest()
base=src["runs"][0]
assert base["tag"]=="NEWS2_s42|scaled|rule|raw|UAFE", base["tag"]
# Change ONLY the target location+sha and pod_root. arm/tag stay as archived: the engine validates
# run arm == the targets receipt arm (renaming them gave arm_mismatch), and the experiment root plus
# clearing runs/ between perturbations already keeps outputs from colliding.
# The receipt key is "receipt"/"receipt_sha256" (NOT "json"): bt_objb_targets.load_source L54-58
# shas the receipt against its pin AND cross-checks receipt["targets_npz_sha256"] == the npz sha.
# Leaving "receipt" on the archived file is what made run 1 die with npz_sha_mismatch_vs_receipt.
rj=npz.replace(".npz",".json")
rh=hashlib.sha256(open(rj,"rb").read()).hexdigest()
for x in base["targets"]["sources"]:
    x["npz"]=npz; x["npz_sha256"]=h
    x["receipt"]=rj; x["receipt_sha256"]=rh
src["runs"]=[base]; src["paths"]["pod_root"]=EXP; src["config"]="RUN_CONFIG_PNOISE"
src["status"]=("DERIVED from RUN_CONFIG_NEWS2_s42_2026-09-23; changed ONLY: paths.pod_root, "
               "runs=[base cell only], targets npz path + sha.")
json.dump(src,open(f"{EXP}/configs/RUN_CONFIG_PNOISE.json","w"),indent=1)
print("config ok target_sha", h[:16], "receipt_sha", rh[:16])
PY
say "config done"

# ---- 7. engine, base cell only ----
say "engine"
env -i PATH=/usr/bin:/bin HOME=/root $PV -B $GATE --check engine $EXP/receipts/ENV_GATE_engine_r$R.json >> $L/pnoise_$R.log 2>&1
cd $E
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $PV -B bt_launch.py PATH,HOME,LC_CTYPE \
  $W/configs/RUN_CONFIG_PNOISE.json --resume pnoise_r$R > $L/engine_r$R.log 2>&1
say "engine done"
say "shm_free_gib=$(df -k /dev/shm | tail -1 | awk '{printf "%.2f", $4/1048576}')"
say "CHAIN_DONE random_state=$R"
