#!/bin/bash
# UNIFIED single model 2-fold quick-read: strong 2025-04 (vs mh180 0.1165 / adaptive 0.1054) + weak 2025-08
# (vs corrected-baseline 0.0725 / MoE 0.0845). ONE model, all levers. patience 6.
cd /mnt/storage/private/work_hsy/quant_research_multi_asset
PY=/root/miniconda3/envs/hsy_v5push/bin/python; export PYTHONPATH=.
exec > /tmp/unified_qr.log 2>&1
echo "=== UNIFIED QUICK-READ runner $(date) ==="
wait_clear () { while pgrep -f "train_v2arch.py|train_dual_lob.py" >/dev/null 2>&1 || [ "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null|grep -c .)" != "0" ]; do sleep 20; done; }
run_job () { local cfg=$1 out=$2 label=$3; wait_clear; echo "=== LAUNCH ${label} $(date) ==="
  $PY -u multi_asset/train/train_v2arch.py --config "configs/npzv4_dual/${cfg}.json" --start-fold 0 --max-folds 1 --seed 42 > /tmp/uni_${label}.log 2>&1 < /dev/null
  local pf="experiments/npzv4_dual/${out}/fold_0/test_preds.npz"; echo "=== EVAL ${label} (dual-caliber, y600 primary) $(date) ==="
  [ -f "$pf" ] && $PY multi_asset/eval/eval_caliber.py --preds "$pf" --ema 2>&1 || { echo "MISSING ${label}"; tail -8 /tmp/uni_${label}.log; }
  echo "=== DONE ${label} $(date) ==="; }
run_job unified_2025_04 unified_2025_04 unified_strong_2025_04
run_job unified_2025_08 unified_2025_08 unified_weak_2025_08
echo "=== UNIFIED QUICK-READ COMPLETE $(date) ==="
