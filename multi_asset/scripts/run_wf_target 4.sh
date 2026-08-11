#!/bin/bash
# TARGET-WINDOW honest base-adaptive walk-forward (2025-08..2026-05), RAM-SAFE + VERIFY-BEFORE-ADVANCE.
# Uniform train_days=450 (650-700d preload OOMs at 203GB>196GB). If a month OOM-fails (no test_preds), RETRY at
# a smaller window (350d, then 250d) before advancing -- NEVER silently skip. Idempotent/resumable. Log: /tmp/wf_target.log
cd /mnt/storage/private/work_hsy/quant_research_multi_asset
PY=/root/miniconda3/envs/hsy_v5push/bin/python; export PYTHONPATH=.
exec > /tmp/wf_target.log 2>&1
echo "=== WF-TARGET runner (RAM-safe/verify) $(date) ==="
wait_clear () { while pgrep -f "train_v2arch.py|train_dual_lob.py" >/dev/null 2>&1 || [ "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null|grep -c .)" != "0" ]; do sleep 20; done; }
MONTHS="2025-08 2025-09 2025-10 2025-11 2025-12 2026-01 2026-02 2026-03 2026-04 2026-05"
for M in $MONTHS; do
  Y=${M%-*}; MO=${M#*-}; cfg="configs/walkforward/wf_${Y}_${MO}.json"; out="experiments/walkforward/wf_${Y}_${MO}"
  if [ "$M" \> "2025-09" ]; then trainer=train_dual_lob; else trainer=train_v2arch; fi
  if [ -f "$out/fold_0/test_preds.npz" ]; then echo "=== SKIP $M (done) ==="; \
    $PY multi_asset/eval/eval_caliber.py --preds "$out/fold_0/test_preds.npz" --ema 2>&1; continue; fi
  # train; retry at smaller train_days on OOM-fail (VERIFY test_preds written before advancing)
  ok=0
  for TD in 450 350 250; do
    wait_clear
    tcfg="/tmp/wfcfg_${Y}_${MO}_td${TD}.json"
    $PY -c "import json; d=json.load(open('$cfg')); d['training']['train_days']=$TD; json.dump(d,open('$tcfg','w'))"
    echo "=== WFT TRAIN $M ($trainer, train_days=$TD) $(date) ==="
    $PY -u multi_asset/train/${trainer}.py --config "$tcfg" --start-fold 0 --max-folds 1 --seed 42 > /tmp/wft_${Y}_${MO}.log 2>&1 < /dev/null
    if [ -f "$out/fold_0/test_preds.npz" ]; then
      echo "=== WFT METRICS $M (train_days=$TD) $(date) ==="
      $PY multi_asset/eval/eval_caliber.py --preds "$out/fold_0/test_preds.npz" --ema 2>&1
      ok=1; break
    else
      echo "=== WFT OOM/FAIL $M at train_days=$TD -> retry smaller (tail:) ==="; tail -4 /tmp/wft_${Y}_${MO}.log
    fi
  done
  [ "$ok" = 0 ] && echo "=== WFT GAVE-UP $M (failed even at 250d) ==="
  echo "=== WFT DONE $M $(date) ==="
done
echo "=== WF-TARGET ALL MONTHS COMPLETE $(date) ==="
touch /tmp/wf_target.DONE
