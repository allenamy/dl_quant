#!/bin/bash
# SNAPSHOT-SKIP target-window walk-forward (2025-08..2026-05). Same rolling protocol as run_wf_target.sh,
# but model.use_snapshot_skip=True to recover the snapshot-linear edge the conformer loses.
# Generates per-month snap configs on the fly. Idempotent/resumable. Log: /tmp/wf_snap.log
cd /mnt/storage/private/work_hsy/quant_research_multi_asset
PY=/root/miniconda3/envs/hsy_v5push/bin/python; export PYTHONPATH=.
exec > /tmp/wf_snap.log 2>&1
echo "=== WF-SNAP runner $(date) ==="
wait_clear () { while pgrep -f "train_v2arch.py|train_dual_lob.py" >/dev/null 2>&1 || [ "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null|grep -c .)" != "0" ]; do sleep 20; done; }
MONTHS="2025-08 2025-09 2025-10 2025-11 2025-12 2026-01 2026-02 2026-03 2026-04 2026-05"
for M in $MONTHS; do
  Y=${M%-*}; MO=${M#*-}
  $PY multi_asset/scripts/gen_wf_snapskip.py "$M" >/dev/null 2>&1
  cfg="configs/wf_snap/wfsnap_${Y}_${MO}.json"; out="experiments/wf_snap/wfsnap_${Y}_${MO}"
  if [ "$M" \> "2025-09" ]; then trainer=train_dual_lob; else trainer=train_v2arch; fi
  if [ -f "$out/fold_0/test_preds.npz" ]; then echo "=== SKIP $M (done) ==="; \
    $PY multi_asset/eval/eval_caliber.py --preds "$out/fold_0/test_preds.npz" --ema 2>&1; continue; fi
  wait_clear
  echo "=== WFSNAP TRAIN $M ($trainer) $(date) ==="
  $PY -u multi_asset/train/${trainer}.py --config "$cfg" --start-fold 0 --max-folds 1 --seed 42 > /tmp/wfsnap_${Y}_${MO}.log 2>&1 < /dev/null
  echo "=== WFSNAP METRICS $M $(date) ==="
  if [ -f "$out/fold_0/test_preds.npz" ]; then $PY multi_asset/eval/eval_caliber.py --preds "$out/fold_0/test_preds.npz" --ema 2>&1; else echo "WFSNAP MISSING $M"; tail -6 /tmp/wfsnap_${Y}_${MO}.log; fi
  echo "=== WFSNAP DONE $M $(date) ==="
done
echo "=== WF-SNAP ALL MONTHS COMPLETE $(date) ==="
touch /tmp/wf_snap.DONE
