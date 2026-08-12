#!/bin/bash
# CORRECTED 2025-08 baseline: plain dp32_a02 (NO regime gate, proven beta~1). Establishes the TRUE non-MoE
# baseline to fairly judge the MoE "breakthrough". Waits for OI-ROUTER-MoE COMPLETE.
cd /mnt/storage/private/work_hsy/quant_research_multi_asset
PY=/root/miniconda3/envs/hsy_v5push/bin/python; export PYTHONPATH=.
exec > /tmp/corrbase_dl.log 2>&1
echo "=== CORRECTED BASELINE runner $(date) ==="
wait_clear () { while pgrep -f "train_v2arch.py|train_dual_lob.py" >/dev/null 2>&1 || [ "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null|grep -c .)" != "0" ]; do sleep 20; done; }
while ! grep -q "OI-ROUTER-MoE COMPLETE" /tmp/oimoe_dl.log 2>/dev/null; do sleep 60; done
wait_clear
echo "=== LAUNCH corrected baseline (plain dp32, 2025-08, beta-healthy) $(date) ==="
$PY -u multi_asset/train/train_v2arch.py --config configs/npzv4_dual/perp_dp32_a02_BASE_2025_08.json --start-fold 0 --max-folds 1 --seed 42 > /tmp/corrbase_2025_08.log 2>&1 < /dev/null
pf="experiments/npzv4_dual/perp_dp32_a02_BASE_2025_08/fold_0/test_preds.npz"
echo "=== EVAL corrected-baseline 2025-08 (TRUE non-MoE baseline; MoE was 0.0845/b1.06) $(date) ==="
[ -f "$pf" ] && $PY multi_asset/eval/eval_caliber.py --preds "$pf" --ema 2>&1 || { echo "MISSING"; tail -8 /tmp/corrbase_2025_08.log; }
echo "=== CORRECTED-BASELINE COMPLETE $(date) ==="
