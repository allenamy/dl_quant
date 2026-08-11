#!/bin/bash
# Fill the lambda0.1 trajectory's 3 MISSING months (2026-03/04/05) so the same-checkpoint apples-to-apples
# 2b comparison (lq_apples_compare.py) covers ALL 10 months. Same config as wfEMA: 450d pat10 ep32 EMA lambda0.1.
# Chains AFTER lambda0.5 finishes (waits for GPU). Out: experiments/wfEMA/ (fills gaps). Log: /tmp/wf_l01fill.log
cd /mnt/storage/private/work_hsy/quant_research_multi_asset
PY=/root/miniconda3/envs/hsy_v5push/bin/python; export PYTHONPATH=.
exec > /tmp/wf_l01fill.log 2>&1
echo "=== WF_L01FILL runner $(date) ==="
wait_clear () { while pgrep -f "train_v2arch.py|train_dual_lob.py" >/dev/null 2>&1 || [ "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null|grep -c .)" != "0" ]; do sleep 30; done; }
for M in 2026-03 2026-04 2026-05; do
  Y=${M%-*}; MO=${M#*-}; out="experiments/wfEMA/wf_${Y}_${MO}"; base="configs/walkforward/wf_${Y}_${MO}.json"
  trainer=train_dual_lob   # all 2026 months use npz_v2arch
  if [ -f "$out/fold_0/ema_test_preds.npz" ]; then echo "=== SKIP $M (present) ==="; continue; fi
  ok=0
  for TD in 450 350 250; do
    wait_clear
    tcfg="/tmp/l01fill_${Y}_${MO}_td${TD}.json"
    $PY -c "import json;d=json.load(open('$base'));d['training']['train_days']=$TD;d['training']['patience']=10;d['training']['epochs']=32;d['training']['dul_config']['lambda_quantile']=0.1;d['output_dir']='$out';json.dump(d,open('$tcfg','w'))"
    echo "=== WF_L01FILL TRAIN $M (td=$TD pat10 lq0.1) $(date) ==="
    $PY -u multi_asset/train/${trainer}.py --config "$tcfg" --start-fold 0 --max-folds 1 --seed 42 > /tmp/l01fill_${Y}_${MO}.log 2>&1 < /dev/null
    if [ -f "$out/fold_0/ema_test_preds.npz" ]; then
      echo "=== WF_L01FILL $M caliber (BEST+EMA) ==="
      $PY multi_asset/eval/eval_caliber.py --preds "$out/fold_0/test_preds.npz" --ema 2>&1 | grep -E "DENSE:|CLEAN:"
      ok=1; break
    else echo "=== WF_L01FILL OOM/FAIL $M td=$TD ==="; tail -4 /tmp/l01fill_${Y}_${MO}.log; fi
  done
  [ "$ok" = 0 ] && echo "=== WF_L01FILL GAVE-UP $M ==="
  echo "=== WF_L01FILL DONE $M $(date) ==="
done
echo "=== WF_L01FILL ALL DONE -> FULL 10-MONTH APPLES COMPARE $(date) ==="
$PY multi_asset/eval/lq_apples_compare.py 2>&1
echo "=== WF_L01FILL CHAIN COMPLETE $(date) ==="
touch /tmp/wf_l01fill.DONE
