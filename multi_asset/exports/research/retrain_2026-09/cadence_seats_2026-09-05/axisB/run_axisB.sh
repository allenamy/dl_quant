#!/bin/bash
# run_axisB.sh <rule> <king> <cal> <seed> — one axis-B arm (PREREG_retrain_cadence_and_seat_rule_2026-09-05 §2), L-dyn form:
#   MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero LEGS=101 CAL=log (no W3FIX); rule ∈ R0..R5; king ∈ pinned(K0)|rollm(K1); cal ∈ log|prod; seed ∈ 42|2027
#   R0 WRULE=msharpe LOOK=900 (baseline) | R1 msharpe LOOK=300 | R2 msharpe_net LOOK=900 | R3 shrink LOOK=900 | R4 meanvar LOOK=900 | R5 regime LOOK=900
#   caliber log  -> cwd dev/     (meta = /workspace/data/wide_fea_v2ext_meta.npz, raw Σ-simple y4, CAL=log = no transform)
#   caliber prod -> cwd dev_alt/ (meta y4 swapped for refute_C6_2/altrun/meta_newprod.npz = Π(1+r5)-1 over [E+1,E+48], CAL=log)
# Every command is appended verbatim to logs/commands.txt. Read-only inputs; writes only under cadence_seats/axisB/.
RULE=$1; KING=$2; CAL=$3; SEED=$4
[ -n "$SEED" ] || { echo "usage: run_axisB.sh <R0..R5> <pinned|rollm> <log|prod> <42|2027>"; exit 2; }
ROOT=/workspace/review_scratch/cadence_seats/axisB; PY=/workspace/venv/bin/python
case $KING in
  pinned) SLOW=/workspace/shadow_bundle_v3/slow_pred_pinned.npy ;;
  rollm)  SLOW=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy ;;
  *) echo "bad king $KING"; exit 2 ;;
esac
case $RULE in
  R0) RENV="WRULE=msharpe LOOK=900" ;;
  R1) RENV="WRULE=msharpe LOOK=300" ;;
  R2) RENV="WRULE=msharpe_net LOOK=900" ;;
  R3) RENV="WRULE=shrink LOOK=900" ;;
  R4) RENV="WRULE=meanvar LOOK=900" ;;
  R5) RENV="WRULE=regime LOOK=900" ;;
  *) echo "bad rule $RULE"; exit 2 ;;
esac
case $CAL in log) d=$ROOT/dev ;; prod) d=$ROOT/dev_alt ;; *) echo "bad cal $CAL"; exit 2 ;; esac
[ -f "$SLOW" ] || { echo "missing $SLOW"; exit 3; }
TAG=${RULE}_${KING}_${CAL}_s${SEED}
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
CMD="env LEGS=101 CAL=log SLOW_NPY=$SLOW $RENV FSEED=$SEED MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=$TAG $PY ../w10_universe_seats.py"
echo "CMD[$TAG] (cwd=$d) $(date -u +%FT%TZ): $CMD" >> $ROOT/logs/commands.txt
cd $d && $CMD > $d/logs/$TAG.log 2>&1; rc=$?
echo "END[$TAG] rc=$rc $(date -u +%FT%TZ)" >> $ROOT/logs/commands.txt
grep -E "^(CONFIG|SLOW override|F10 OOS|MEMBERS_TOPN|AXISB|RECEIPT_EX d30|DONE|Traceback|AssertionError)" $d/logs/$TAG.log | cut -c1-400
exit $rc
