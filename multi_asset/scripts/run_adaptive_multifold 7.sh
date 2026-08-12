#!/bin/bash
# Adaptive multi-fold robustness: 4 added folds, each train+eval, per-fold dual-caliber.
# npzv4_dual folds via train_v2arch; v2arch folds via train_dual_lob. nw0/preload (reliable).
cd /mnt/storage/private/work_hsy/quant_research_multi_asset
PY=/root/miniconda3/envs/hsy_v5push/bin/python; export PYTHONPATH=.
exec > /tmp/adaptmf_dl.log 2>&1
echo "=== ADAPTIVE MULTI-FOLD runner $(date) ==="
wait_clear () { while pgrep -f "train_v2arch.py|train_dual_lob.py" >/dev/null 2>&1 || [ "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null|grep -c .)" != "0" ]; do sleep 20; done; }
run_job () {
  local trainer=$1 cfg=$2 out=$3 label=$4
  wait_clear
  echo "=== LAUNCH ${label} $(date) ==="
  $PY -u multi_asset/train/${trainer}.py --config "${cfg}" --start-fold 0 --max-folds 1 --seed 42 > /tmp/amf_${label}.log 2>&1 < /dev/null
  local pf="${out}/fold_0/test_preds.npz"
  echo "=== EVAL ${label} (dual-caliber) $(date) ==="
  if [ -f "$pf" ]; then $PY multi_asset/eval/eval_caliber.py --preds "$pf" --ema 2>&1; else echo "MISSING ${label}"; tail -6 /tmp/amf_${label}.log; fi
  echo "=== DONE ${label} $(date) ==="
}
# wait for the current final runner (dp48->mh180) to finish first
echo "=== wait for FINAL DL COMPLETE (dp48+mh180) ==="
while ! grep -q "FINAL DL COMPLETE" /tmp/final_dl.log 2>/dev/null; do sleep 60; done
echo "=== final done, starting adaptive multi-fold $(date) ==="
run_job train_v2arch  configs/npzv4_dual/perp_dp32_a02_adaptive_2024_10.json experiments/npzv4_dual/perp_dp32_a02_adaptive_2024_10 adapt_2024_10
run_job train_v2arch  configs/npzv4_dual/perp_dp32_a02_adaptive_2025_08.json experiments/npzv4_dual/perp_dp32_a02_adaptive_2025_08 adapt_2025_08
run_job train_dual_lob configs/v2arch/dp32_adaptive_2025_12.json experiments/v2arch_dp32/dp32_adaptive_2025_12 adapt_2025_12
run_job train_dual_lob configs/v2arch/dp32_adaptive_2026_02.json experiments/v2arch_dp32/dp32_adaptive_2026_02 adapt_2026_02
echo "=== ADAPTIVE MULTI-FOLD COMPLETE $(date) ==="
