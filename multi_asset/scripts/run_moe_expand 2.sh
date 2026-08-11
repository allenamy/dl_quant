#!/bin/bash
# MoE EXPAND: remaining weak folds 2025-12 + 2026-02 (price-router, patience 6). Launched manually after quick-read GO.
cd /mnt/storage/private/work_hsy/quant_research_multi_asset
PY=/root/miniconda3/envs/hsy_v5push/bin/python; export PYTHONPATH=.
exec > /tmp/moe_expand.log 2>&1
echo "=== MoE EXPAND runner $(date) ==="
wait_clear () { while pgrep -f "train_v2arch.py|train_dual_lob.py" >/dev/null 2>&1 || [ "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null|grep -c .)" != "0" ]; do sleep 20; done; }
run_job () { local cfg=$1 out=$2 label=$3; wait_clear; echo "=== LAUNCH ${label} $(date) ==="
  $PY -u multi_asset/train/train_dual_lob.py --config "$cfg" --start-fold 0 --max-folds 1 --seed 42 > /tmp/moe_${label}.log 2>&1 < /dev/null
  local pf="${out}/fold_0/test_preds.npz"; echo "=== EVAL ${label} $(date) ==="
  [ -f "$pf" ] && $PY multi_asset/eval/eval_caliber.py --preds "$pf" --ema 2>&1 || { echo "MISSING ${label}"; tail -6 /tmp/moe_${label}.log; }
  echo "=== DONE ${label} $(date) ==="; }
run_job configs/v2arch/dp32_moe_2025_12.json experiments/v2arch_dp32/dp32_moe_2025_12 moe_2025_12
run_job configs/v2arch/dp32_moe_2026_02.json experiments/v2arch_dp32/dp32_moe_2026_02 moe_2026_02
echo "=== MoE EXPAND COMPLETE $(date) ==="
