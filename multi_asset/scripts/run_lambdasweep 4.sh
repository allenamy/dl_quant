#!/bin/bash
# 2b lambda_quantile SWEET-SPOT sweep: find lambda where DENSE Pearson lifts AND beta~1.
# Known: 2025-09 lambda0.1 -> P+0.050 b0.69 | lambda0.5 -> P+0.070 b1.59 (beta overshot). Test 0.2, 0.3 (bracket).
# 2025-09 (fast train_v2arch) first for the curve, then 2025-10 (strong) to confirm. Reports lambda->(P,beta,sigma).
# Waits for GPU. Log: /tmp/lambdasweep.log
cd /mnt/storage/private/work_hsy/quant_research_multi_asset
PY=/root/miniconda3/envs/hsy_v5push/bin/python; export PYTHONPATH=.
exec > /tmp/lambdasweep.log 2>&1
echo "=== LAMBDASWEEP runner $(date) ==="
wait_clear () { while pgrep -f "train_v2arch.py|train_dual_lob.py" >/dev/null 2>&1 || [ "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null|grep -c .)" != "0" ]; do sleep 30; done; }
run () {
  local cfg=$1 tag=$2 out=$3 trainer=$4
  [ -f "$out/fold_0/test_preds.npz" ] && { echo "SKIP $tag"; } || {
    wait_clear
    echo "=== LSWEEP TRAIN $tag $(date) ==="
    $PY -u multi_asset/train/${trainer}.py --config "$cfg" --start-fold 0 --max-folds 1 --seed 42 > /tmp/lsweep_${tag}.log 2>&1 < /dev/null
  }
  echo "=== LSWEEP $tag (DENSE) ==="
  [ -f "$out/fold_0/test_preds.npz" ] && $PY multi_asset/eval/eval_caliber.py --preds "$out/fold_0/test_preds.npz" 2>&1|grep DENSE:|head -1 || { echo "$tag MISSING"; tail -4 /tmp/lsweep_${tag}.log; }
}
run configs/lossab/2025_09_Q02.json 2025_09_Q02 experiments/lossab/2025_09_Q02 train_v2arch
run configs/lossab/2025_09_Q03.json 2025_09_Q03 experiments/lossab/2025_09_Q03 train_v2arch
echo "=== 2025-09 lambda->(P,beta,sigma) CURVE (DENSE) ==="
for t in 2025_09_Q02:0.2 2025_09_Q03:0.3 2025_09_Q05:0.5; do
  tag=${t%:*}; lq=${t#*:}; f=experiments/lossab/$tag/fold_0/test_preds.npz
  [ -f "$f" ] && echo "lambda=$lq : $($PY multi_asset/eval/eval_caliber.py --preds $f 2>&1|grep DENSE:|head -1)"
done
echo "(baseline lambda=0.1 : DENSE +0.050 b0.69 s0.072)"
# confirm best on 2025-10 (strong) -- run Q03 (likely sweet spot)
run configs/lossab/2025_10_Q03.json 2025_10_Q03 experiments/lossab/2025_10_Q03 train_dual_lob
echo "=== LAMBDASWEEP COMPLETE $(date) ==="
touch /tmp/lambdasweep.DONE
