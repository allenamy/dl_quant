#!/bin/bash
# run_arms_inc.sh — replay arms for kings rollm (K1 reference rerun, bitwise receipt vs axisA), KR, KC: L-dyn (axisA run_arms_dyn.sh env verbatim; 2 calibers × FSEED 42/2027) and
# L-fix (axisA run_arms.sh env verbatim; W3FIX 0.21,0,0.79, FSEED 42, 2 calibers). At most 3 device runs in parallel × 4 threads = 12 threads. Commands appended verbatim to logs/commands.txt.
ROOT=/workspace/review_scratch/cadence_seats/axisA_incremental; PY=/workspace/venv/bin/python; cd $ROOT
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
declare -A SLOW=( [rollm]=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy [KR]=$ROOT/slow_pred_KR.npy [KC]=$ROOT/slow_pred_KC.npy )
COMMON="LEGS=101 LOOK=900 WRULE=msharpe CAL=log"; LIVE="MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero"
jobs_list=()
for king in rollm KR KC; do
  [ -f "${SLOW[$king]}" ] || { echo "missing ${SLOW[$king]}"; exit 3; }
  for cal in log prod; do d=$ROOT/dev; [ $cal = prod ] && d=$ROOT/dev_alt
    for seed in 42 2027; do jobs_list+=("$d|Ldyn_${king}_${cal}_s${seed}|$COMMON SLOW_NPY=${SLOW[$king]} $LIVE FSEED=$seed"); done
    jobs_list+=("$d|Lfix_${king}_${cal}_s42|$COMMON SLOW_NPY=${SLOW[$king]} $LIVE W3FIX=0.21,0,0.79 FSEED=42")
  done
done
n=0
for j in "${jobs_list[@]}"; do
  d=${j%%|*}; rest=${j#*|}; tag=${rest%%|*}; envs=${rest#*|}
  echo "CMD[$tag] (cwd=$d) $(date -u +%FT%TZ): env $envs OUT_TAG=$tag $PY ../w10_universe_recheck.py" >> logs/commands.txt
  (cd $d && env $envs OUT_TAG=$tag $PY ../w10_universe_recheck.py > $d/logs/$tag.log 2>&1; echo "END[$tag] rc=$? $(date -u +%FT%TZ)" >> $ROOT/logs/commands.txt) &
  n=$((n+1)); if [ $((n % 3)) -eq 0 ]; then wait; fi
done; wait
echo "ARMS_INC_DONE $(date -u +%FT%TZ)" >> logs/commands.txt
/workspace/venv/bin/python check_equiv_inc.py > logs/check_equiv_inc.log 2>&1
sha256sum dev/probe_artifacts/w10_ablation_series_*.npz dev_alt/probe_artifacts/w10_ablation_series_*.npz slow_pred_KR.npy slow_pred_KC.npy >> logs/chain_train.log
