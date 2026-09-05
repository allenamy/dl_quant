#!/bin/bash
# stage 08 arms for G2(b)/(c): F1 form (LEGS=111 PHI=0 WRULE=msharpe LOOK=900) with the rebuilt hist king, CAL=log (also the G5 F1/hist/log arm)
# and CAL=simple (G2(c) negative control). REF_SKIP unset => the device's parity gate against the stage-6 nets is live.
source /workspace/review_scratch/jpline_rebuild/lib.sh
cd $ROOT/dev
export OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 MKL_NUM_THREADS=8
KING=$ROOT/data/slow_pred_hist_oos_rebuilt.npy
echo "CMD[$STAGE] (cwd=$PWD) $(date -u +%FT%TZ): env LOOK=900 WRULE=msharpe SLOW_NPY=$KING LEGS=111 PHI=0 FSEED=42 CAL=log OUT_TAG=F1_hist_log $PY ../w10_universe_recheck.py" >> $CMDLOG
env LOOK=900 WRULE=msharpe SLOW_NPY=$KING LEGS=111 PHI=0 FSEED=42 CAL=log OUT_TAG=F1_hist_log $PY ../w10_universe_recheck.py > logs/F1_hist_log.log 2>&1 &
echo "CMD[$STAGE] (cwd=$PWD) $(date -u +%FT%TZ): env LOOK=900 WRULE=msharpe SLOW_NPY=$KING LEGS=111 PHI=0 FSEED=42 CAL=simple OUT_TAG=F1_hist_simple $PY ../w10_universe_recheck.py" >> $CMDLOG
env LOOK=900 WRULE=msharpe SLOW_NPY=$KING LEGS=111 PHI=0 FSEED=42 CAL=simple OUT_TAG=F1_hist_simple $PY ../w10_universe_recheck.py > logs/F1_hist_simple.log 2>&1 &
wait
for t in F1_hist_log F1_hist_simple; do echo "== $t"; grep -E "^(CONFIG|SLOW override|legs done|NOTE|RECEIPT d30|RECEIPT S0|DONE|Traceback|AssertionError)" logs/$t.log | cut -c1-700; echo "RC[$STAGE] $t $(grep -q '^DONE' logs/$t.log && echo 0 || echo FAIL) $(date -u +%FT%TZ)" >> $CMDLOG; done
grep -q "^DONE" logs/F1_hist_log.log || exit 3
grep -q "^DONE" logs/F1_hist_simple.log || exit 3
sha256sum probe_artifacts/w10_ablation_series_F1_hist_log.npz probe_artifacts/w10_ablation_series_F1_hist_simple.npz
