#!/bin/bash
# Choppy adaptive train700 caliber-fix. Chains after OI-FILMDL COMPLETE (reordered: OI before this low-pri caliber-fix). f16-fix enables train700 on heavy cache.
cd /mnt/storage/private/work_hsy/quant_research_multi_asset
PY=/root/miniconda3/envs/hsy_v5push/bin/python; export PYTHONPATH=.
exec > /tmp/choppy700_dl.log 2>&1
echo "=== CHOPPY-TRAIN700 runner $(date) ==="
wait_clear () { while pgrep -f "train_v2arch.py|train_dual_lob.py" >/dev/null 2>&1 || [ "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null|grep -c .)" != "0" ]; do sleep 20; done; }
echo "=== wait for OI-FILMDL COMPLETE (reordered after OI) ==="
while ! grep -q "OI-FILMDL COMPLETE" /tmp/oi_filmdl.log 2>/dev/null; do sleep 60; done
wait_clear
echo "=== LAUNCH choppy-train700 $(date) ==="
$PY -u multi_asset/train/train_dual_lob.py --config configs/v2arch/dp32_adaptive_train700_2026_05.json --start-fold 0 --max-folds 1 --seed 42 > /tmp/choppy700.log 2>&1 < /dev/null
pf="experiments/v2arch_dp32/dp32_adaptive_train700_2026_05/fold_0/test_preds.npz"
echo "=== EVAL choppy-train700 (dual-caliber vs adaptive train300 choppy 0.040) $(date) ==="
[ -f "$pf" ] && $PY multi_asset/eval/eval_caliber.py --preds "$pf" --ema 2>&1 || { echo "MISSING"; tail -8 /tmp/choppy700.log; }
echo "=== CHOPPY-TRAIN700 COMPLETE $(date) ==="
