#!/bin/bash
# FAST 3-month snapshot-skip test: 2025-08 (snapshot-linear), 2025-09 (nonlinear), 2025-10 (strong).
# Verifies snapshot-skip DL captures BOTH signals in one model. Log: /tmp/wf_snap3.log
cd /mnt/storage/private/work_hsy/quant_research_multi_asset
PY=/root/miniconda3/envs/hsy_v5push/bin/python; export PYTHONPATH=.
exec > /tmp/wf_snap3.log 2>&1
echo "=== WF-SNAP3 runner $(date) ==="
wait_clear () { while pgrep -f "train_v2arch.py|train_dual_lob.py" >/dev/null 2>&1 || [ "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null|grep -c .)" != "0" ]; do sleep 20; done; }
MONTHS="2025-08 2025-09 2025-10"
for M in $MONTHS; do
  Y=${M%-*}; MO=${M#*-}
  $PY multi_asset/scripts/gen_wf_snapskip.py "$M" >/dev/null 2>&1
  cfg="configs/wf_snap/wfsnap_${Y}_${MO}.json"; out="experiments/wf_snap/wfsnap_${Y}_${MO}"
  if [ "$M" \> "2025-09" ]; then trainer=train_dual_lob; else trainer=train_v2arch; fi
  if [ -f "$out/fold_0/test_preds.npz" ]; then echo "=== SKIP $M (done) ==="; \
    $PY multi_asset/eval/eval_caliber.py --preds "$out/fold_0/test_preds.npz" --ema 2>&1; continue; fi
  wait_clear
  echo "=== SNAP3 TRAIN $M ($trainer) $(date) ==="
  $PY -u multi_asset/train/${trainer}.py --config "$cfg" --start-fold 0 --max-folds 1 --seed 42 > /tmp/snap3_${Y}_${MO}.log 2>&1 < /dev/null
  echo "=== SNAP3 METRICS $M $(date) ==="
  if [ -f "$out/fold_0/test_preds.npz" ]; then $PY multi_asset/eval/eval_caliber.py --preds "$out/fold_0/test_preds.npz" --ema 2>&1; else echo "SNAP3 MISSING $M"; tail -6 /tmp/snap3_${Y}_${MO}.log; fi
  echo "=== SNAP3 DONE $M $(date) ==="
done
echo "=== WF-SNAP3 ALL COMPLETE $(date) ==="
touch /tmp/wf_snap3.DONE
