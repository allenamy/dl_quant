#!/bin/bash
# MoE 2-fold QUICK-READ: strong anchor 2025-04 (already running standalone) + weak 2025-08 (patience 6).
# Decision gate: if MoE per-fold >= adaptive baseline (strong held + weak lifted) -> run remaining folds.
cd /mnt/storage/private/work_hsy/quant_research_multi_asset
PY=/root/miniconda3/envs/hsy_v5push/bin/python; export PYTHONPATH=.
exec > /tmp/moe_quickread.log 2>&1
echo "=== MoE QUICK-READ runner $(date) ==="
wait_clear () { while pgrep -f "train_v2arch.py|train_dual_lob.py" >/dev/null 2>&1 || [ "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null|grep -c .)" != "0" ]; do sleep 20; done; }
# 1) the strong-anchor fold is ALREADY running standalone -> wait for its test_preds, then eval
echo "=== wait for moe_strong_2025_04 test_preds (already running) ==="
SP=experiments/npzv4_dual/perp_dp32_a02_moe_2025_04/fold_0/test_preds.npz
while [ ! -f "$SP" ]; do sleep 30; done
echo "=== EVAL moe_strong_2025_04 (vs adaptive 0.0747/0.1054) $(date) ==="
$PY multi_asset/eval/eval_caliber.py --preds "$SP" --ema 2>&1
echo "=== DONE moe_strong_2025_04 $(date) ==="
# 2) weak fold 2025-08 (patience 6)
wait_clear
echo "=== LAUNCH moe_2025_08 (weak fold, patience 6) $(date) ==="
$PY -u multi_asset/train/train_v2arch.py --config configs/npzv4_dual/perp_dp32_a02_moe_2025_08.json --start-fold 0 --max-folds 1 --seed 42 > /tmp/moe_moe_2025_08.log 2>&1 < /dev/null
WP=experiments/npzv4_dual/perp_dp32_a02_moe_2025_08/fold_0/test_preds.npz
echo "=== EVAL moe_2025_08 (vs adaptive 2025-08 0.0237/0.0450) $(date) ==="
[ -f "$WP" ] && $PY multi_asset/eval/eval_caliber.py --preds "$WP" --ema 2>&1 || { echo "MISSING moe_2025_08"; tail -6 /tmp/moe_moe_2025_08.log; }
echo "=== MoE QUICK-READ COMPLETE (strong-anchor + weak-2025-08) $(date) ==="
