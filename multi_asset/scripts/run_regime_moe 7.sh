#!/bin/bash
# Regime-MoE (K=2, routed by regime_prior) -- 4 folds: strong anchor 2025-04 + 2025-08 + 2025-12 + 2026-02.
# Chains after CHOPPY-TRAIN700 COMPLETE. Eval vs adaptive baselines per fold. nw0/preload, clean shared caches.
cd /mnt/storage/private/work_hsy/quant_research_multi_asset
PY=/root/miniconda3/envs/hsy_v5push/bin/python; export PYTHONPATH=.
exec > /tmp/moe_dl.log 2>&1
echo "=== REGIME-MoE runner $(date) ==="
wait_clear () { while pgrep -f "train_v2arch.py|train_dual_lob.py" >/dev/null 2>&1 || [ "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null|grep -c .)" != "0" ]; do sleep 20; done; }
run_job () {
  local trainer=$1 cfg=$2 out=$3 label=$4
  wait_clear
  echo "=== LAUNCH ${label} $(date) ==="
  $PY -u multi_asset/train/${trainer}.py --config "${cfg}" --start-fold 0 --max-folds 1 --seed 42 > /tmp/moe_${label}.log 2>&1 < /dev/null
  local pf="${out}/fold_0/test_preds.npz"
  echo "=== EVAL ${label} (dual-caliber vs adaptive baseline) $(date) ==="
  if [ -f "$pf" ]; then $PY multi_asset/eval/eval_caliber.py --preds "$pf" --ema 2>&1; else echo "MISSING ${label}"; tail -6 /tmp/moe_${label}.log; fi
  echo "=== DONE ${label} $(date) ==="
}
echo "=== wait for RICH-REGIME COMPLETE (reordered: MoE is now the priority main direction) ==="
while ! grep -q "RICH-REGIME COMPLETE" /tmp/richreg_dl.log 2>/dev/null; do sleep 60; done
echo "=== prior chain done, starting regime-MoE $(date) ==="
run_job train_v2arch  configs/npzv4_dual/perp_dp32_a02_moe_2025_04.json experiments/npzv4_dual/perp_dp32_a02_moe_2025_04 moe_strong_2025_04
run_job train_v2arch  configs/npzv4_dual/perp_dp32_a02_moe_2025_08.json experiments/npzv4_dual/perp_dp32_a02_moe_2025_08 moe_2025_08
run_job train_dual_lob configs/v2arch/dp32_moe_2025_12.json experiments/v2arch_dp32/dp32_moe_2025_12 moe_2025_12
run_job train_dual_lob configs/v2arch/dp32_moe_2026_02.json experiments/v2arch_dp32/dp32_moe_2026_02 moe_2026_02
echo "=== REGIME-MoE COMPLETE $(date) ==="
