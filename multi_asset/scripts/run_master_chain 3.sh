#!/bin/bash
# MASTER autonomous chain (overnight): ablation -> pick fix -> full beta-healthy trajectory -> aggregate.
# 1. Wait for fix11 (the 550d/pat10 reference) + GPU clear.
# 2. Run ablation arm A (450d+pat10, isolate PATIENCE) + arm B (550d+pat5, isolate WINDOW).
# 3. Decide the fix: if A is beta-healthy (sigma>=0.02 & 0.5<=beta<=1.8) -> WIN=450 (patience is it, RAM headroom).
#    else if fix11/B healthy -> WIN=550. patience10 always.
# 4. Run the FULL 10-month trajectory at WINd/patience10/epochs32 (verify-before-advance, OOM-retry).
# 5. honest aggregate.
# Idempotent. Log: /tmp/master_chain.log
cd /mnt/storage/private/work_hsy/quant_research_multi_asset
PY=/root/miniconda3/envs/hsy_v5push/bin/python; export PYTHONPATH=.
exec > /tmp/master_chain.log 2>&1
echo "=== MASTER CHAIN $(date) ==="
wait_clear () { while pgrep -f "train_v2arch.py|train_dual_lob.py" >/dev/null 2>&1 || [ "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null|grep -c .)" != "0" ]; do sleep 30; done; }
healthy () {  # arg: test_preds path -> echo 1 if beta-healthy per eval_caliber BEST
  local p=$1; [ -f "$p" ] || { echo 0; return; }
  $PY - "$p" <<'PYEOF'
import sys,numpy as np
from scipy.stats import pearsonr
z=np.load(sys.argv[1],allow_pickle=True); pr=z["predictions"]; q=(pr[:,1] if pr.ndim==2 else pr).astype(float)
y=z["targets"].astype(float)
b=np.cov(y,q)[0,1]/q.var() if q.var()>1e-12 else 0; sg=q.std()/(y.std()+1e-12)
print(1 if (sg>=0.02 and 0.5<=b<=1.8) else 0)
PYEOF
}
train () {  # cfg tag out td
  local cfg=$1 tag=$2 out=$3 td=$4
  [ -f "$out/fold_0/test_preds.npz" ] && { echo "SKIP $tag done"; return; }
  wait_clear
  tcfg="/tmp/mc_${tag}.json"
  $PY -c "import json;d=json.load(open('$cfg'));d['training']['train_days']=$td;d['training']['patience']=10;d['training']['epochs']=32;d['output_dir']='$out';json.dump(d,open('$tcfg','w'))"
  echo "=== MC TRAIN $tag (td=$td pat10) $(date) ==="
  $PY -u multi_asset/train/train_dual_lob.py --config "$tcfg" --start-fold 0 --max-folds 1 --seed 42 > /tmp/mc_${tag}.log 2>&1 < /dev/null
  [ -f "$out/fold_0/test_preds.npz" ] && $PY multi_asset/eval/eval_caliber.py --preds "$out/fold_0/test_preds.npz" --ema 2>&1 || { echo "$tag FAIL"; tail -4 /tmp/mc_${tag}.log; }
}
# step 2: ablation A (patience-isolation). (B/fix11 = 550d refs; A is the decisive one.)
train configs/abl11/A_450_pat10.json A_450_pat10 experiments/abl11/A_450_pat10 450
AHEALTHY=$(healthy experiments/abl11/A_450_pat10/fold_0/test_preds.npz)
echo "=== ABLATION A (450d+pat10) beta-healthy? = $AHEALTHY ==="
# also run B for completeness (window-isolation, old patience)
[ -f experiments/abl11/B_550_pat5/fold_0/test_preds.npz ] || { wait_clear; $PY -c "import json;d=json.load(open('configs/abl11/B_550_pat5.json'));json.dump(d,open('/tmp/mc_B.json','w'))"; echo "=== MC TRAIN B_550_pat5 $(date) ==="; $PY -u multi_asset/train/train_dual_lob.py --config configs/abl11/B_550_pat5.json --start-fold 0 --max-folds 1 --seed 42 > /tmp/mc_B_550_pat5.log 2>&1 </dev/null; [ -f experiments/abl11/B_550_pat5/fold_0/test_preds.npz ] && $PY multi_asset/eval/eval_caliber.py --preds experiments/abl11/B_550_pat5/fold_0/test_preds.npz --ema 2>&1; }
# step 3: pick winning window
if [ "$AHEALTHY" = "1" ]; then WIN=450; echo "=== VERDICT: PATIENCE is the fix -> WIN=450d (RAM headroom, generalizes) ==="; else WIN=550; echo "=== VERDICT: window matters -> WIN=550d ==="; fi
# step 4: full trajectory at WINd/patience10/epochs32
MONTHS="2025-08 2025-09 2025-10 2025-11 2025-12 2026-01 2026-02 2026-03 2026-04 2026-05"
for M in $MONTHS; do
  Y=${M%-*}; MO=${M#*-}; out="experiments/wfFINAL/wf_${Y}_${MO}"
  base="configs/walkforward/wf_${Y}_${MO}.json"
  for TD in $WIN 450 350; do
    [ -f "$out/fold_0/test_preds.npz" ] && break
    train "$base" "${Y}_${MO}_td${TD}" "$out" "$TD"
  done
done
echo "=== MC FULL TRAJECTORY DONE -> AGGREGATE $(date) ==="
WFFINAL_DIR=experiments/wfFINAL PYTHONPATH=. $PY multi_asset/eval/honest_aggregate_final.py 2>&1
echo "=== MASTER CHAIN COMPLETE $(date) ==="
touch /tmp/master_chain.DONE
