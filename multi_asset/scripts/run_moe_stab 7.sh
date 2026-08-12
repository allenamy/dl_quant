#!/bin/bash
# SIGMA-STABILIZED MoE on 2026-02 (signal EXISTS at Ridge 0.046 but MoE regressed). Heavier wd+load-balance.
# Goal: degrade gracefully (no neg) + recover toward the floor. Waits for CORRECTED-BASELINE COMPLETE.
cd /mnt/storage/private/work_hsy/quant_research_multi_asset
PY=/root/miniconda3/envs/hsy_v5push/bin/python; export PYTHONPATH=.
exec > /tmp/moestab_dl.log 2>&1
echo "=== MoE-STAB runner $(date) ==="
wait_clear () { while pgrep -f "train_v2arch.py|train_dual_lob.py" >/dev/null 2>&1 || [ "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null|grep -c .)" != "0" ]; do sleep 20; done; }
while ! grep -q "CORRECTED-BASELINE COMPLETE" /tmp/corrbase_dl.log 2>/dev/null; do sleep 60; done
wait_clear
echo "=== LAUNCH moe_stab_2026_02 (heavier wd+lb) $(date) ==="
$PY -u multi_asset/train/train_dual_lob.py --config configs/v2arch/dp32_moe_stab_2026_02.json --start-fold 0 --max-folds 1 --seed 42 > /tmp/moestab_2026_02.log 2>&1 < /dev/null
pf="experiments/v2arch_dp32/dp32_moe_stab_2026_02/fold_0/test_preds.npz"
echo "=== EVAL moe_stab_2026_02 (vs adaptive 2026-02 0.0172, MoE-plain regressed -0.029, Ridge floor 0.046) $(date) ==="
[ -f "$pf" ] && $PY multi_asset/eval/eval_caliber.py --preds "$pf" --ema 2>&1 || { echo "MISSING"; tail -8 /tmp/moestab_2026_02.log; }
echo "=== MoE-STAB COMPLETE $(date) ==="
