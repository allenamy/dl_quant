#!/bin/bash
# run_arms.sh <king>   king ∈ pinned|rollm|rollm1|rollw1|k1rep — PREREG_retrain_cadence_and_seat_rule_2026-09-05 §1 axis A: L-fix arm ONLY, both calibers.
#   L-fix : MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 LEGS=101 LOOK=900 WRULE=msharpe FSEED=42
#   caliber log  -> cwd dev/     (meta = /workspace/data/wide_fea_v2ext_meta.npz, raw Σ-simple y4, CAL=log = no transform)
#   caliber prod -> cwd dev_alt/ (meta y4 swapped for refute_C6_2/altrun/meta_newprod.npz = Π(1+r5)-1 over [E+1,E+48], CAL=log)
# Every command is appended verbatim to logs/commands.txt. Read-only inputs; writes only under cadence_seats/axisA/.
set -e
KING=$1; [ -n "$KING" ] || { echo "usage: run_arms.sh <pinned|rollm|rollm1|rollw1|k1rep>"; exit 2; }
ROOT=/workspace/review_scratch/cadence_seats/axisA
PY=/workspace/venv/bin/python
case $KING in
  pinned) SLOW=/workspace/shadow_bundle_v3/slow_pred_pinned.npy ;;
  rollm)  SLOW=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy ;;
  rollm1) SLOW=$ROOT/slow_pred_rollm1.npy ;;
  rollw1) SLOW=$ROOT/slow_pred_rollw1.npy ;;
  k1rep)  SLOW=$ROOT/slow_pred_d1_testfold.npy ;;   # K1 replicate (D1 retrain, same recipe+seeds, LightGBM bits differ): device noise floor, NOT a selection arm
  *) echo "bad king $KING"; exit 2 ;;
esac
[ -f "$SLOW" ] || { echo "missing $SLOW"; exit 3; }
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
COMMON="LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=$SLOW"
LIVE="MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 FSEED=42"
for cal in log prod; do
  d=$ROOT/dev; [ $cal = prod ] && d=$ROOT/dev_alt
  tag=Lfix_${KING}_${cal}_s42
  echo "CMD[$tag] (cwd=$d) $(date -u +%Y-%m-%dT%H:%M:%SZ): env $COMMON $LIVE OUT_TAG=$tag $PY ../w10_universe_recheck.py" | tee -a $ROOT/logs/commands.txt
  (cd $d && env $COMMON $LIVE OUT_TAG=$tag $PY ../w10_universe_recheck.py > $d/logs/$tag.log 2>&1) &
done
wait
echo "ARMS_DONE king=$KING $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a $ROOT/logs/commands.txt
for cal in log prod; do d=$ROOT/dev; [ $cal = prod ] && d=$ROOT/dev_alt
  tag=Lfix_${KING}_${cal}_s42
  echo "== $tag"; grep -E "^(CONFIG|SLOW override|F10 OOS|MEMBERS_TOPN|RECEIPT_EX d30|DONE|Traceback|AssertionError)" $d/logs/$tag.log | cut -c1-600
done
