#!/bin/bash
# run_arms_dyn.sh <king>   king ∈ pinned|rollm|rollm1|rollw1 — AMENDMENT 2 (L-dyn addendum): live dynamic msharpe seat, NO W3FIX,
#   MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero LEGS=101 LOOK=900 WRULE=msharpe CAL=log; FSEED 42 and 2027; calibers log (dev/) and prod (dev_alt/).
# Every command appended verbatim to logs/commands.txt. Read-only inputs; writes only under cadence_seats/axisA/.
set -e
KING=$1; [ -n "$KING" ] || { echo "usage: run_arms_dyn.sh <pinned|rollm|rollm1|rollw1>"; exit 2; }
ROOT=/workspace/review_scratch/cadence_seats/axisA
PY=/workspace/venv/bin/python
case $KING in
  pinned) SLOW=/workspace/shadow_bundle_v3/slow_pred_pinned.npy ;;
  rollm)  SLOW=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy ;;
  rollm1) SLOW=$ROOT/slow_pred_rollm1.npy ;;
  rollw1) SLOW=$ROOT/slow_pred_rollw1.npy ;;
  *) echo "bad king $KING"; exit 2 ;;
esac
[ -f "$SLOW" ] || { echo "missing $SLOW"; exit 3; }
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
COMMON="LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=$SLOW"
LIVE="MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero"
for cal in log prod; do
  d=$ROOT/dev; [ $cal = prod ] && d=$ROOT/dev_alt
  for seed in 42 2027; do
    tag=Ldyn_${KING}_${cal}_s${seed}
    echo "CMD[$tag] (cwd=$d) $(date -u +%Y-%m-%dT%H:%M:%SZ): env $COMMON $LIVE FSEED=$seed OUT_TAG=$tag $PY ../w10_universe_recheck.py" | tee -a $ROOT/logs/commands.txt
    (cd $d && env $COMMON $LIVE FSEED=$seed OUT_TAG=$tag $PY ../w10_universe_recheck.py > $d/logs/$tag.log 2>&1) &
  done
done
wait
echo "ARMS_DYN_DONE king=$KING $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a $ROOT/logs/commands.txt
for cal in log prod; do d=$ROOT/dev; [ $cal = prod ] && d=$ROOT/dev_alt
  for seed in 42 2027; do tag=Ldyn_${KING}_${cal}_s${seed}
    echo "== $tag"; grep -E "^(CONFIG|SLOW override|F10 OOS|RECEIPT_EX d30|DONE|Traceback|AssertionError)" $d/logs/$tag.log | cut -c1-500
  done
done
