#!/bin/bash
# DECISIVE ablation on 2025-11: is PATIENCE or WINDOW the real sigma-collapse fix? (fix11 confounded both.)
#   A) 450d + patience10 + epochs32  -> isolate PATIENCE (does patience alone fix it at 450d?)
#   B) 550d + patience5  + epochs25  -> isolate WINDOW   (does window alone fix it with old patience?)
# Baselines on record: 450d/pat5 = COLLAPSED (b2.16 s0.01); fix11 550d/pat10 = HEALTHY (b0.83 s0.057 by ep7).
# Waits for GPU to clear. Log: /tmp/abl11.log
cd /mnt/storage/private/work_hsy/quant_research_multi_asset
PY=/root/miniconda3/envs/hsy_v5push/bin/python; export PYTHONPATH=.
exec > /tmp/abl11.log 2>&1
echo "=== ABL11 runner $(date) ==="
wait_clear () { while pgrep -f "train_v2arch.py|train_dual_lob.py" >/dev/null 2>&1 || [ "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null|grep -c .)" != "0" ]; do sleep 30; done; }
run_arm () {
  local cfg=$1 tag=$2 out=$3
  if [ -f "$out/fold_0/test_preds.npz" ]; then echo "=== SKIP $tag (done) ==="; $PY multi_asset/eval/eval_caliber.py --preds "$out/fold_0/test_preds.npz" --ema 2>&1; return; fi
  wait_clear
  echo "=== ABL11 TRAIN $tag $(date) ==="
  $PY -u multi_asset/train/train_dual_lob.py --config "$cfg" --start-fold 0 --max-folds 1 --seed 42 > /tmp/abl11_${tag}.log 2>&1 < /dev/null
  echo "=== ABL11 $tag SIGMA TRAJECTORY ==="
  grep "^Epoch" /tmp/abl11_${tag}.log 2>/dev/null | sed -E "s/.*(Epoch +[0-9]+).*sigR=([0-9.]+) b=([+-][0-9.]+).*P=([+-][0-9.]+).*EMA P=([+-][0-9.]+).*/\1 sigR=\2 b=\3 valP=\4 emaP=\5/"
  echo "=== ABL11 $tag METRICS ==="
  if [ -f "$out/fold_0/test_preds.npz" ]; then $PY multi_asset/eval/eval_caliber.py --preds "$out/fold_0/test_preds.npz" --ema 2>&1; else echo "$tag MISSING"; tail -6 /tmp/abl11_${tag}.log; fi
}
run_arm configs/abl11/A_450_pat10.json A_450_pat10 experiments/abl11/A_450_pat10
run_arm configs/abl11/B_550_pat5.json  B_550_pat5  experiments/abl11/B_550_pat5
echo "=== ABL11 COMPLETE $(date) ==="
touch /tmp/abl11.DONE
