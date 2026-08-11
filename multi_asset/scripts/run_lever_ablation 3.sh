#!/bin/bash
# LEVER ABLATION on weak 2025-08: isolate which lever-pair breaks the weak fold in the unified.
# A noMH (FiLM+bias+MoE): if recovers ~0.0845 -> multi-horizon conflicts. B noMoE: MoE-contribution baseline.
cd /mnt/storage/private/work_hsy/quant_research_multi_asset
PY=/root/miniconda3/envs/hsy_v5push/bin/python; export PYTHONPATH=.
exec > /tmp/ablation_dl.log 2>&1
echo "=== LEVER-ABLATION $(date) ==="
wait_clear () { while pgrep -f "train_v2arch.py|train_dual_lob.py" >/dev/null 2>&1 || [ "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null|grep -c .)" != "0" ]; do sleep 20; done; }
run_job () { local cfg=$1 out=$2 label=$3; wait_clear; echo "=== LAUNCH ${label} $(date) ==="
  $PY -u multi_asset/train/train_v2arch.py --config "configs/npzv4_dual/${cfg}.json" --start-fold 0 --max-folds 1 --seed 42 > /tmp/abl_${label}.log 2>&1 < /dev/null
  local pf="experiments/npzv4_dual/${out}/fold_0/test_preds.npz"; echo "=== EVAL ${label} (vs MoE-alone 0.0845, corrected-base 0.0725, unified 0.039) $(date) ==="
  [ -f "$pf" ] && $PY multi_asset/eval/eval_caliber.py --preds "$pf" --ema 2>&1 || { echo "MISSING ${label}"; tail -8 /tmp/abl_${label}.log; }
  echo "=== DONE ${label} $(date) ==="; }
run_job ablate_noMH_2025_08 ablate_noMH_2025_08 noMH
run_job ablate_noMoE_2025_08 ablate_noMoE_2025_08 noMoE
echo "=== LEVER-ABLATION COMPLETE $(date) ==="
