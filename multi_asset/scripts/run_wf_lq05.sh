#!/bin/bash
# DEFINITIVE lambda0.5 trajectory: final-best adaptive config (regime FiLM + zero-init bias + perp residual)
#   + 450d rolling + patience10 + epochs32 + EMA/causal-checkpoint + lambda_quantile=0.5.
# Full rolling 2025-08 -> 2026-05 (10 months), train-on-prior-450d -> test. Headline = absolute Pearson at sigma>=0.02.
# verify-before-advance (EMA preds), OOM-retry 450->350->250. Streams per-month BEST+EMA DENSE/per-day caliber.
# Log: /tmp/wf_lq05.log   Out: experiments/wfEMA_lq05/
cd /mnt/storage/private/work_hsy/quant_research_multi_asset
PY=/root/miniconda3/envs/hsy_v5push/bin/python; export PYTHONPATH=.
exec > /tmp/wf_lq05.log 2>&1
echo "=== WF_LQ05 runner $(date) ==="
wait_clear () { while pgrep -f "train_v2arch.py|train_dual_lob.py" >/dev/null 2>&1 || [ "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null|grep -c .)" != "0" ]; do sleep 30; done; }
MONTHS="2025-08 2025-09 2025-10 2025-11 2025-12 2026-01 2026-02 2026-03 2026-04 2026-05"
# Seed 2025-09 + 2025-10 from the already-trained lambda0.5 runs (lossab) to save 2 runs.
seed_from () { # src_dir dst_month
  local src=$1 yk=$2
  local dst="experiments/wfEMA_lq05/wf_${yk}/fold_0"
  if [ -f "$src/fold_0/ema_test_preds.npz" ] && [ ! -f "$dst/ema_test_preds.npz" ]; then
    mkdir -p "$dst"
    cp "$src/fold_0/ema_test_preds.npz" "$dst/ema_test_preds.npz"
    cp "$src/fold_0/test_preds.npz" "$dst/test_preds.npz" 2>/dev/null
    cp "$src/fold_0/metrics.json" "$dst/metrics.json" 2>/dev/null
    echo "=== SEEDED $yk from $src ==="
  fi
}
seed_from experiments/lossab/2025_09_Q05 2025_09
seed_from experiments/lossab/2025_10_Q05 2025_10
for M in $MONTHS; do
  Y=${M%-*}; MO=${M#*-}; out="experiments/wfEMA_lq05/wf_${Y}_${MO}"; base="configs/walkforward/wf_${Y}_${MO}.json"
  if [ "$M" \> "2025-09" ]; then trainer=train_dual_lob; else trainer=train_v2arch; fi
  if [ -f "$out/fold_0/ema_test_preds.npz" ]; then
    echo "=== WF_LQ05 MONTH $M (already present) $(date) ==="
    echo "--- $M caliber (BEST + EMA) ---"
    $PY multi_asset/eval/eval_caliber.py --preds "$out/fold_0/test_preds.npz" --ema 2>&1
    echo "=== WF_LQ05 DONE $M $(date) ==="; continue
  fi
  ok=0
  for TD in 450 350 250; do
    wait_clear
    tcfg="/tmp/lq05_${Y}_${MO}_td${TD}.json"
    $PY -c "import json;d=json.load(open('$base'));d['training']['train_days']=$TD;d['training']['patience']=10;d['training']['epochs']=32;d['training']['dul_config']['lambda_quantile']=0.5;d['output_dir']='$out';json.dump(d,open('$tcfg','w'))"
    echo "=== WF_LQ05 TRAIN $M ($trainer, td=$TD pat10 lq0.5) $(date) ==="
    $PY -u multi_asset/train/${trainer}.py --config "$tcfg" --start-fold 0 --max-folds 1 --seed 42 > /tmp/lq05_${Y}_${MO}.log 2>&1 < /dev/null
    if [ -f "$out/fold_0/ema_test_preds.npz" ]; then
      echo "=== WF_LQ05 MONTH $M (td=$TD) caliber (BEST + EMA) $(date) ==="
      $PY multi_asset/eval/eval_caliber.py --preds "$out/fold_0/test_preds.npz" --ema 2>&1
      ok=1; break
    else echo "=== WF_LQ05 OOM/FAIL $M td=$TD -> retry smaller ==="; tail -5 /tmp/lq05_${Y}_${MO}.log; fi
  done
  [ "$ok" = 0 ] && echo "=== WF_LQ05 GAVE-UP $M ==="
  echo "=== WF_LQ05 DONE $M $(date) ==="
done
echo "=== WF_LQ05 ALL MONTHS COMPLETE -> CAUSAL AGGREGATE $(date) ==="
$PY multi_asset/eval/honest_aggregate_lq05.py 2>&1
echo "=== WF_LQ05 CHAIN COMPLETE $(date) ==="
touch /tmp/wf_lq05.DONE
