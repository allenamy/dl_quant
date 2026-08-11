#!/bin/bash
# FINAL PRODUCTION VALIDATION: clean from-scratch re-train of ADAPTIVE on all 6 folds + full metrics + CSV.
# npzv4_dual folds via train_v2arch; v2arch folds via train_dual_lob. Cache pre-verified clean (6-wide).
cd /mnt/storage/private/work_hsy/quant_research_multi_asset
PY=/root/miniconda3/envs/hsy_v5push/bin/python; export PYTHONPATH=.
exec > /tmp/prodval.log 2>&1
echo "=== PRODUCTION VALIDATION runner $(date) ==="
wait_clear () { while pgrep -f "train_v2arch.py|train_dual_lob.py" >/dev/null 2>&1 || [ "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null|grep -c .)" != "0" ]; do sleep 20; done; }
run_fold () { local trainer=$1 cfg=$2 out=$3 label=$4; wait_clear; echo "=== TRAIN ${label} $(date) ==="
  $PY -u multi_asset/train/${trainer}.py --config "${cfg}" --start-fold 0 --max-folds 1 --seed 42 > /tmp/pv_${label}.log 2>&1 < /dev/null
  local pf="${out}/fold_0/test_preds.npz"
  echo "=== METRICS ${label} (dual-caliber + mono + DA) $(date) ==="
  [ -f "$pf" ] && $PY multi_asset/eval/eval_caliber.py --preds "$pf" --ema 2>&1 || { echo "MISSING ${label}"; tail -6 /tmp/pv_${label}.log; }
  echo "=== DONE ${label} $(date) ==="; }
# npzv4_dual folds (train_v2arch)
run_fold train_v2arch  configs/npzv4_dual/perp_dp32_a02_adaptive_2024_10.json experiments/npzv4_dual/perp_dp32_a02_adaptive_2024_10 PV_2024_10
run_fold train_v2arch  configs/npzv4_dual/perp_dp32_a02_adaptive_2025_04.json experiments/npzv4_dual/perp_dp32_a02_adaptive_2025_04 PV_2025_04
run_fold train_v2arch  configs/npzv4_dual/perp_dp32_a02_adaptive_2025_08.json experiments/npzv4_dual/perp_dp32_a02_adaptive_2025_08 PV_2025_08
# v2arch folds (train_dual_lob)
run_fold train_dual_lob configs/v2arch/dp32_adaptive_2025_12.json experiments/v2arch_dp32/dp32_adaptive_2025_12 PV_2025_12
run_fold train_dual_lob configs/v2arch/dp32_adaptive_2026_02.json experiments/v2arch_dp32/dp32_adaptive_2026_02 PV_2026_02
run_fold train_dual_lob configs/v2arch/dp32_adaptive_2026_05.json experiments/v2arch_dp32/dp32_adaptive_2026_05 PV_2026_05
echo "=== EXPORT CSV ==="; $PY multi_asset/eval/export_production_csv.py exports/adaptive_production_allfolds.csv 2>&1
echo "=== PRODUCTION VALIDATION COMPLETE $(date) ==="
