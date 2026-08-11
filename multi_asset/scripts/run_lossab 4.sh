#!/bin/bash
# 2b A/B: does raising lambda_quantile (pinball L1 amplitude anchor, anti-#20-safe) LIFT Pearson w/o sigma-collapse?
# Rank-dominated loss (lq0.1 vs rank/dir 1.0) suppresses q50 amplitude -> Pearson low. Test lq 0.5 (Q05) and 1.0 (Q10).
# Months: 2025-09 (FAST train_v2arch) first for a quick read, then 2025-10 (dual-path). vs baseline DENSE:
#   2025-09 base DENSE +0.050 b0.69 s0.072 | 2025-10 base DENSE +0.045 b0.81 s0.056.
# Measure DENSE Pearson + sigma + beta (HEADLINE caliber, NOT cross-day CLEAN). Waits for GPU. Log: /tmp/lossab.log
cd /mnt/storage/private/work_hsy/quant_research_multi_asset
PY=/root/miniconda3/envs/hsy_v5push/bin/python; export PYTHONPATH=.
exec > /tmp/lossab.log 2>&1
echo "=== LOSSAB 2b runner $(date) ==="
wait_clear () { while pgrep -f "train_v2arch.py|train_dual_lob.py" >/dev/null 2>&1 || [ "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null|grep -c .)" != "0" ]; do sleep 30; done; }
run () {
  local cfg=$1 tag=$2 out=$3 trainer=$4
  [ -f "$out/fold_0/test_preds.npz" ] && { echo "SKIP $tag"; return; }
  wait_clear
  echo "=== LOSSAB TRAIN $tag $(date) ==="
  $PY -u multi_asset/train/${trainer}.py --config "$cfg" --start-fold 0 --max-folds 1 --seed 42 > /tmp/lossab_${tag}.log 2>&1 < /dev/null
  echo "=== LOSSAB $tag RESULT (DENSE = honest caliber) ==="
  if [ -f "$out/fold_0/test_preds.npz" ]; then
    echo "-- BEST --"; $PY multi_asset/eval/eval_caliber.py --preds "$out/fold_0/test_preds.npz" 2>&1 | grep DENSE: | head -1
    echo "-- EMA  --"; $PY multi_asset/eval/eval_caliber.py --preds "$out/fold_0/ema_test_preds.npz" 2>&1 | grep DENSE: | head -1
  else echo "$tag MISSING"; tail -5 /tmp/lossab_${tag}.log; fi
}
# 2025-09 FAST (train_v2arch) -- quick decisive read
run configs/lossab/2025_09_Q05.json 2025_09_Q05 experiments/lossab/2025_09_Q05 train_v2arch
run configs/lossab/2025_09_Q10.json 2025_09_Q10 experiments/lossab/2025_09_Q10 train_v2arch
# 2025-10 (dual-path) confirmation
run configs/lossab/2025_10_Q05.json 2025_10_Q05 experiments/lossab/2025_10_Q05 train_dual_lob
run configs/lossab/2025_10_Q10.json 2025_10_Q10 experiments/lossab/2025_10_Q10 train_dual_lob
echo "=== LOSSAB 2b COMPLETE $(date) ==="
echo "BASELINE DENSE: 2025-09 +0.050 b0.69 s0.072 | 2025-10 +0.045 b0.81 s0.056"
touch /tmp/lossab.DONE
