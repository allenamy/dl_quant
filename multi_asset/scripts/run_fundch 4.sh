#!/bin/bash
# FUNDING/OI RAW-DL-CHANNEL test (user's ceiling-breaker): add 8 leak-safe funding/OI feats as raw X channels
# (X 88->96) so the Conformer learns the NON-LINEAR book interaction. Test on STRONG (2025-10) + DRIFT (2025-12,
# 2026-02) vs the no-funding wfEMA baseline. patience10 + EMA (same fix as baseline, fair A/B). Per month:
#   1. build fundch cache for [test month + 450d prior] (disk-safe separate cache)
#   2. train fund-channel DL (auto-widens to 96ch)
#   3. eval DENSE + per-day vs baseline; shuffle-null on a follow-up
# Log: /tmp/fundch.log . Sequential, disk-careful (build month range, train, can delete cache after).
cd /mnt/storage/private/work_hsy/quant_research_multi_asset
PY=/root/miniconda3/envs/hsy_v5push/bin/python; export PYTHONPATH=.
exec > /tmp/fundch.log 2>&1
echo "=== FUNDCH runner $(date) ==="
wait_clear () { while pgrep -f "train_v2arch.py|train_dual_lob.py" >/dev/null 2>&1 || [ "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null|grep -c .)" != "0" ]; do sleep 30; done; }
# prior-450d date range helper (approx: test month start minus ~480d to be safe, end = test month start)
run_month () {
  local M=$1   # YYYY-MM
  local Y=${M%-*} MO=${M#*-}
  # build fundch cache for the needed range: ~2024-01-01 .. test-month-end (npz_v2arch starts 2024-01)
  local TEST_END="${M}-28"
  echo "=== FUNDCH BUILD $M (npz_v2arch -> npz_v2arch_fundch, 2024-01-01..$TEST_END) $(date) ==="
  CUDA_VISIBLE_DEVICES="" $PY -u multi_asset/data/add_funding_channels.py --src npz_v2arch --dst npz_v2arch_fundch --start 2024-01-01 --end "$TEST_END" --apply 2>&1 | tail -3
  # config: clone the wf_<m> config, point npz_dir to fundch, patience10/ep32/td450
  local cfg="/tmp/fundch_${Y}_${MO}.json"
  $PY -c "import json; d=json.load(open('configs/walkforward/wf_${Y}_${MO}.json')); d['data']['npz_dir']='data/npz_v2arch_fundch'; d['training']['train_days']=450; d['training']['patience']=10; d['training']['epochs']=32; d['output_dir']='experiments/fundch/wf_${Y}_${MO}'; json.dump(d,open('$cfg','w'))"
  local out="experiments/fundch/wf_${Y}_${MO}"
  if [ -f "$out/fold_0/test_preds.npz" ]; then echo "SKIP $M (done)"; else
    wait_clear
    echo "=== FUNDCH TRAIN $M (fund-channel DL, 96ch) $(date) ==="
    $PY -u multi_asset/train/train_dual_lob.py --config "$cfg" --start-fold 0 --max-folds 1 --seed 42 > /tmp/fundch_train_${Y}_${MO}.log 2>&1 < /dev/null
  fi
  echo "=== FUNDCH RESULT $M (fund-channel; DENSE = headline) $(date) ==="
  if [ -f "$out/fold_0/test_preds.npz" ]; then
    echo "-- fund-channel BEST --"; $PY multi_asset/eval/eval_caliber.py --preds "$out/fold_0/test_preds.npz" 2>&1|grep DENSE:|head -1
    echo "-- fund-channel EMA  --"; $PY multi_asset/eval/eval_caliber.py --preds "$out/fold_0/ema_test_preds.npz" 2>&1|grep DENSE:|head -1
    echo "-- BASELINE (no-funding wfEMA) BEST/EMA --"
    $PY multi_asset/eval/eval_caliber.py --preds "experiments/wfEMA/wf_${Y}_${MO}/fold_0/test_preds.npz" 2>&1|grep DENSE:|head -1
    $PY multi_asset/eval/eval_caliber.py --preds "experiments/wfEMA/wf_${Y}_${MO}/fold_0/ema_test_preds.npz" 2>&1|grep DENSE:|head -1
  else echo "FUNDCH $M MISSING"; tail -6 /tmp/fundch_train_${Y}_${MO}.log; fi
  echo "=== FUNDCH DONE $M $(date) ==="
}
run_month 2025-10   # STRONG
run_month 2025-12   # DRIFT (key)
run_month 2026-02   # DRIFT (key)
echo "=== FUNDCH ALL COMPLETE $(date) ==="
touch /tmp/fundch.DONE
