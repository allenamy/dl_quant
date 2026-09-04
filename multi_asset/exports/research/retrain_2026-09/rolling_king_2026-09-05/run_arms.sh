#!/bin/bash
# run_arms.sh <king>   king ∈ pinned|rollm|rollq — STEP 3 arms (PREREG_rolling_king_monthly_2026-09-05 §2), both calibers.
#   L-fix : MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 LEGS=101 FSEED=42
#   L-dyn : MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero LEGS=101 (no W3FIX), FSEED=42 and FSEED=2027
#   C-dyn : canon (no MEMBERS_TOPN/TRADE_TOPN/FTRIM), LEGS=101, FSEED=42
#   caliber log  -> cwd dev/     (meta = /workspace/data/wide_fea_v2ext_meta.npz, raw Σ-simple y4, CAL=log = no transform)
#   caliber prod -> cwd dev_alt/ (meta y4 swapped for refute_C6_2/altrun/meta_newprod.npz = Π(1+r5)-1 over [E+1,E+48], CAL=log)
# Every command is appended verbatim to logs/commands.txt. Read-only inputs; writes only under rolling_king/.
set -e
KING=$1; [ -n "$KING" ] || { echo "usage: run_arms.sh <pinned|rollm|rollq>"; exit 2; }
ROOT=/workspace/review_scratch/rolling_king
PY=/workspace/venv/bin/python
case $KING in
  pinned) SLOW=/workspace/shadow_bundle_v3/slow_pred_pinned.npy ;;
  rollm)  SLOW=$ROOT/slow_pred_rollm.npy ;;
  rollq)  SLOW=$ROOT/slow_pred_rollq.npy ;;
  *) echo "bad king $KING"; exit 2 ;;
esac
[ -f "$SLOW" ] || { echo "missing $SLOW"; exit 3; }
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
COMMON="LEGS=101 LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=$SLOW"
LIVE="MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero"
run() {  # $1 = cal (log|prod), $2 = OUT_TAG, rest = extra env
  local cal=$1; local tag=$2; shift 2
  local d=$ROOT/dev; [ $cal = prod ] && d=$ROOT/dev_alt
  echo "CMD[$tag] (cwd=$d): env $COMMON $* OUT_TAG=$tag $PY ../w10_universe_recheck.py" | tee -a $ROOT/logs/commands.txt
  (cd $d && env $COMMON "$@" OUT_TAG=$tag $PY ../w10_universe_recheck.py > $d/logs/$tag.log 2>&1) &
}
for cal in log prod; do
  run $cal Lfix_${KING}_${cal}_s42   FSEED=42   $LIVE W3FIX=0.21,0,0.79
  run $cal Ldyn_${KING}_${cal}_s42   FSEED=42   $LIVE
  run $cal Ldyn_${KING}_${cal}_s2027 FSEED=2027 $LIVE
  run $cal Cdyn_${KING}_${cal}_s42   FSEED=42
done
wait
echo "ARMS_DONE king=$KING $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a $ROOT/logs/commands.txt
for cal in log prod; do d=$ROOT/dev; [ $cal = prod ] && d=$ROOT/dev_alt
  for tag in Lfix_${KING}_${cal}_s42 Ldyn_${KING}_${cal}_s42 Ldyn_${KING}_${cal}_s2027 Cdyn_${KING}_${cal}_s42; do
    echo "== $tag"; grep -E "^(CONFIG|SLOW override|F10 OOS|MEMBERS_TOPN|RECEIPT_EX d30|DONE|Traceback|AssertionError)" $d/logs/$tag.log | cut -c1-600
  done
done
