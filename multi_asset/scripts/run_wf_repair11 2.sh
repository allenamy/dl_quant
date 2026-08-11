#!/bin/bash
# Standalone repair of the OOM'd 2025-11 month. Waits for the main wf-target run's GPU to clear, then trains
# 2025-11 with the repaired config (train_days=450). Idempotent. Log: /tmp/wf_repair11.log
cd /mnt/storage/private/work_hsy/quant_research_multi_asset
PY=/root/miniconda3/envs/hsy_v5push/bin/python; export PYTHONPATH=.
exec > /tmp/wf_repair11.log 2>&1
echo "=== WF-REPAIR11 runner $(date) ==="
out="experiments/walkforward/wf_2025_11"; cfg="configs/walkforward/wf_2025_11.json"
if [ -f "$out/fold_0/test_preds.npz" ]; then echo "already done"; touch /tmp/wf_repair11.DONE; exit 0; fi
# wait for ALL trainers + GPU apps to clear (don't collide with the main run)
while pgrep -f "train_v2arch.py|train_dual_lob.py" >/dev/null 2>&1 || [ "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null|grep -c .)" != "0" ]; do sleep 60; done
echo "=== GPU clear; REPAIR11 TRAIN 2025-11 (train_dual_lob, train_days=450) $(date) ==="
$PY -u multi_asset/train/train_dual_lob.py --config "$cfg" --start-fold 0 --max-folds 1 --seed 42 > /tmp/wft_2025_11.log 2>&1 < /dev/null
echo "=== REPAIR11 METRICS 2025-11 $(date) ==="
if [ -f "$out/fold_0/test_preds.npz" ]; then $PY multi_asset/eval/eval_caliber.py --preds "$out/fold_0/test_preds.npz" --ema 2>&1; else echo "REPAIR11 STILL MISSING"; tail -8 /tmp/wft_2025_11.log; fi
echo "=== REPAIR11 DONE $(date) ==="
touch /tmp/wf_repair11.DONE
