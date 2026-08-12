#!/bin/bash
# OI-ROUTER-MoE (user core idea): K=2 MoE routed by 14-wide price+positioning regime_prior.
# Disk-safe: build OI cache for the fold range -> run -> eval -> DELETE. Waits for MoE EXPAND COMPLETE.
cd /mnt/storage/private/work_hsy/quant_research_multi_asset
PY=/root/miniconda3/envs/hsy_v5push/bin/python; export PYTHONPATH=.
exec > /tmp/oimoe_dl.log 2>&1
echo "=== OI-ROUTER-MoE runner $(date) ==="
wait_clear () { while pgrep -f "train_v2arch.py|train_dual_lob.py" >/dev/null 2>&1 || [ "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null|grep -c .)" != "0" ]; do sleep 20; done; }
echo "=== wait for MoE EXPAND COMPLETE ==="
while ! grep -q "MoE EXPAND COMPLETE" /tmp/moe_expand.log 2>/dev/null; do sleep 60; done
# 2025-08 weak fold: build OI cache (train700 ending ~2025-08 -> 2023-06..2025-09), run OI-router-MoE, eval, delete
echo "=== build npzv4_dual_oi for 2025-08 fold (2023-06-01..2025-09-15) $(date) ==="
CUDA_VISIBLE_DEVICES="" $PY multi_asset/data/add_oi_regime_prior.py --src npzv4_dual --dst npzv4_dual_oi --start 2023-06-01 --end 2025-09-15 --apply 2>&1 | tail -3
wait_clear
echo "=== LAUNCH oimoe_2025_08 (OI-router MoE) $(date) ==="
$PY -u multi_asset/train/train_v2arch.py --config configs/npzv4_dual/perp_dp32_a02_oimoe_2025_08.json --start-fold 0 --max-folds 1 --seed 42 > /tmp/oimoe_2025_08.log 2>&1 < /dev/null
pf="experiments/npzv4_dual/perp_dp32_a02_oimoe_2025_08/fold_0/test_preds.npz"
echo "=== EVAL oimoe_2025_08 (vs price-router MoE 0.0845, adaptive 0.0450) $(date) ==="
[ -f "$pf" ] && $PY multi_asset/eval/eval_caliber.py --preds "$pf" --ema 2>&1 || { echo "MISSING oimoe_2025_08"; tail -8 /tmp/oimoe_2025_08.log; }
echo "=== cleanup OI cache ==="; rm -rf data/npzv4_dual_oi
echo "=== OI-ROUTER-MoE COMPLETE $(date) ==="
