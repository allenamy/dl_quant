#!/bin/bash
cd /mnt/storage/private/work_hsy/quant_research_multi_asset
PY=/root/miniconda3/envs/hsy_v5push/bin/python; export PYTHONPATH=.
exec > /tmp/noMH_rerun.log 2>&1
wait_clear () { while pgrep -f "train_v2arch.py|train_dual_lob.py" >/dev/null 2>&1 || [ "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null|grep -c .)" != "0" ]; do sleep 20; done; }
while ! grep -q "LEVER-ABLATION COMPLETE" /tmp/ablation_dl.log 2>/dev/null; do sleep 60; done
wait_clear
echo "=== LAUNCH noMH (fixed, single-horizon y600) $(date) ==="
$PY -u multi_asset/train/train_v2arch.py --config configs/npzv4_dual/ablate_noMH_2025_08.json --start-fold 0 --max-folds 1 --seed 42 > /tmp/abl_noMH.log 2>&1 < /dev/null
pf="experiments/npzv4_dual/ablate_noMH_2025_08/fold_0/test_preds.npz"
echo "=== EVAL noMH (FiLM+bias+MoE, no multi-horizon; vs MoE-alone 0.0845, unified 0.039) $(date) ==="
[ -f "$pf" ] && $PY multi_asset/eval/eval_caliber.py --preds "$pf" --ema 2>&1 || { echo "MISSING noMH"; tail -8 /tmp/abl_noMH.log; }
echo "=== noMH-RERUN COMPLETE $(date) ==="
