#!/bin/bash
# Rich-regime FiLM (6->14 descriptors) on strong + choppy, dual-caliber. nw0/preload.
cd /mnt/storage/private/work_hsy/quant_research_multi_asset
PY=/root/miniconda3/envs/hsy_v5push/bin/python; export PYTHONPATH=.
exec > /tmp/richreg_dl.log 2>&1
echo "=== RICH-REGIME runner $(date) ==="
wait_clear () { while pgrep -f "train_v2arch.py|train_dual_lob.py" >/dev/null 2>&1 || [ "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null|grep -c .)" != "0" ]; do sleep 20; done; }
run_job () {
  local trainer=$1 cfg=$2 out=$3 label=$4
  wait_clear
  echo "=== LAUNCH ${label} $(date) ==="
  $PY -u multi_asset/train/${trainer}.py --config "${cfg}" --start-fold 0 --max-folds 1 --seed 42 > /tmp/rr_${label}.log 2>&1 < /dev/null
  local pf="${out}/fold_0/test_preds.npz"
  echo "=== EVAL ${label} (dual-caliber vs adaptive strong .075/.105, choppy .040) $(date) ==="
  if [ -f "$pf" ]; then $PY multi_asset/eval/eval_caliber.py --preds "$pf" --ema 2>&1; else echo "MISSING ${label}"; tail -6 /tmp/rr_${label}.log; fi
  echo "=== DONE ${label} $(date) ==="
}
echo "=== wait for ADAPTIVE MULTI-FOLD COMPLETE ==="
while ! grep -q "ADAPTIVE MULTI-FOLD COMPLETE" /tmp/adaptmf_dl.log 2>/dev/null; do sleep 60; done
echo "=== multifold done, starting rich-regime $(date) ==="
run_job train_v2arch  configs/npzv4_dual/perp_dp32_a02_richreg_2025_04.json experiments/npzv4_dual/perp_dp32_a02_richreg_2025_04 richreg_strong
run_job train_dual_lob configs/v2arch/dp32_richreg_2026_05.json experiments/v2arch_dp32/dp32_richreg_2026_05 richreg_choppy
echo "=== RICH-REGIME COMPLETE $(date) ==="
