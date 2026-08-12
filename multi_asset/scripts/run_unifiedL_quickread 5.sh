#!/bin/bash
# UNIFIED-LIGHT quick-read: all levers + LIGHT MoE reg (wd0.01 lb0.01). Tests if lighter reg recovers the
# normal-weak gain (2025-08) the drift-tuned wd0.05 suppressed, WITHOUT hurting strong (2025-04).
cd /mnt/storage/private/work_hsy/quant_research_multi_asset
PY=/root/miniconda3/envs/hsy_v5push/bin/python; export PYTHONPATH=.
exec > /tmp/unifiedL_qr.log 2>&1
echo "=== UNIFIED-LIGHT QUICK-READ $(date) ==="
wait_clear () { while pgrep -f "train_v2arch.py|train_dual_lob.py" >/dev/null 2>&1 || [ "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null|grep -c .)" != "0" ]; do sleep 20; done; }
run_job () { local cfg=$1 out=$2 label=$3; wait_clear; echo "=== LAUNCH ${label} $(date) ==="
  $PY -u multi_asset/train/train_v2arch.py --config "configs/npzv4_dual/${cfg}.json" --start-fold 0 --max-folds 1 --seed 42 > /tmp/uniL_${label}.log 2>&1 < /dev/null
  local pf="experiments/npzv4_dual/${out}/fold_0/test_preds.npz"; echo "=== EVAL ${label} $(date) ==="
  [ -f "$pf" ] && $PY multi_asset/eval/eval_caliber.py --preds "$pf" --ema 2>&1 || { echo "MISSING ${label}"; tail -8 /tmp/uniL_${label}.log; }
  echo "=== DONE ${label} $(date) ==="; }
run_job unifiedL_2025_08 unifiedL_2025_08 unifiedL_weak_2025_08
run_job unifiedL_2025_04 unifiedL_2025_04 unifiedL_strong_2025_04
echo "=== UNIFIED-LIGHT QUICK-READ COMPLETE $(date) ==="
