#!/bin/bash
# CONTINUOUS MONTHLY WALK-FORWARD of adaptive (production sim). 24 months 2024-06..2026-05, rolling-retrain
# 700d before each month, test the month, roll forward. Streams per-month metrics. nw0/preload (f16-fix).
cd /mnt/storage/private/work_hsy/quant_research_multi_asset
PY=/root/miniconda3/envs/hsy_v5push/bin/python; export PYTHONPATH=.
exec > /tmp/walkforward.log 2>&1
echo "=== WALK-FORWARD runner $(date) ==="
wait_clear () { while pgrep -f "train_v2arch.py|train_dual_lob.py" >/dev/null 2>&1 || [ "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null|grep -c .)" != "0" ]; do sleep 20; done; }
MONTHS="2024-06 2024-07 2024-08 2024-09 2024-10 2024-11 2024-12 2025-01 2025-02 2025-03 2025-04 2025-05 2025-06 2025-07 2025-08 2025-09 2025-10 2025-11 2025-12 2026-01 2026-02 2026-03 2026-04 2026-05"
for M in $MONTHS; do
  Y=${M%-*}; MO=${M#*-}; cfg="configs/walkforward/wf_${Y}_${MO}.json"; out="experiments/walkforward/wf_${Y}_${MO}"
  if [ "$M" \> "2025-09" ]; then trainer=train_dual_lob; else trainer=train_v2arch; fi
  # skip if already done (idempotent / resumable across flaps)
  if [ -f "$out/fold_0/test_preds.npz" ]; then echo "=== SKIP $M (done) ==="; continue; fi
  wait_clear
  echo "=== WF TRAIN $M ($trainer) $(date) ==="
  $PY -u multi_asset/train/${trainer}.py --config "$cfg" --start-fold 0 --max-folds 1 --seed 42 > /tmp/wf_${Y}_${MO}.log 2>&1 < /dev/null
  echo "=== WF METRICS $M $(date) ==="
  if [ -f "$out/fold_0/test_preds.npz" ]; then $PY multi_asset/eval/eval_caliber.py --preds "$out/fold_0/test_preds.npz" --ema 2>&1; else echo "WF MISSING $M"; tail -4 /tmp/wf_${Y}_${MO}.log; fi
  echo "=== WF DONE $M $(date) ==="
done
echo "=== WALK-FORWARD ALL MONTHS COMPLETE $(date) ==="
