#!/bin/bash
# 550d PRODUCTION walk-forward (2025-08..2026-05) — calibration-healthy window (fix11 confirmed 550d fixes
# the 450d sigma-collapse). train_days=550 patience=10 epochs=32, book-mid, verify-before-advance, RAM-safe
# (89GB confirmed). Idempotent/resumable. Log: /tmp/wf550.log
cd /mnt/storage/private/work_hsy/quant_research_multi_asset
PY=/root/miniconda3/envs/hsy_v5push/bin/python; export PYTHONPATH=.
exec > /tmp/wf550.log 2>&1
echo "=== WF550 runner $(date) ==="
wait_clear () { while pgrep -f "train_v2arch.py|train_dual_lob.py" >/dev/null 2>&1 || [ "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null|grep -c .)" != "0" ]; do sleep 20; done; }
MONTHS="2025-08 2025-09 2025-10 2025-11 2025-12 2026-01 2026-02 2026-03 2026-04 2026-05"
for M in $MONTHS; do
  Y=${M%-*}; MO=${M#*-}; cfg="configs/wf550/wf550_${Y}_${MO}.json"; out="experiments/wf550/wf550_${Y}_${MO}"
  if [ "$M" \> "2025-09" ]; then trainer=train_dual_lob; else trainer=train_v2arch; fi
  if [ -f "$out/fold_0/test_preds.npz" ]; then echo "=== SKIP $M (done) ==="; \
    $PY multi_asset/eval/eval_caliber.py --preds "$out/fold_0/test_preds.npz" --ema 2>&1; continue; fi
  # train; OOM-retry-smaller (550->450->350) with verify-before-advance
  ok=0
  for TD in 550 450 350; do
    wait_clear
    tcfg="/tmp/wf550cfg_${Y}_${MO}_td${TD}.json"
    $PY -c "import json; d=json.load(open('$cfg')); d['training']['train_days']=$TD; json.dump(d,open('$tcfg','w'))"
    echo "=== WF550 TRAIN $M ($trainer, train_days=$TD) $(date) ==="
    $PY -u multi_asset/train/${trainer}.py --config "$tcfg" --start-fold 0 --max-folds 1 --seed 42 > /tmp/wf550_${Y}_${MO}.log 2>&1 < /dev/null
    if [ -f "$out/fold_0/test_preds.npz" ]; then
      echo "=== WF550 METRICS $M (train_days=$TD) $(date) ==="
      $PY multi_asset/eval/eval_caliber.py --preds "$out/fold_0/test_preds.npz" --ema 2>&1
      ok=1; break
    else
      echo "=== WF550 OOM/FAIL $M at train_days=$TD -> retry smaller (tail:) ==="; tail -4 /tmp/wf550_${Y}_${MO}.log
    fi
  done
  [ "$ok" = 0 ] && echo "=== WF550 GAVE-UP $M ==="
  echo "=== WF550 DONE $M $(date) ==="
done
echo "=== WF550 ALL MONTHS COMPLETE $(date) ==="
touch /tmp/wf550.DONE
