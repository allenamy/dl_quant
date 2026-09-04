R=/workspace/review_scratch/combo_recheck
PY=/workspace/venv/bin/python; export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
COMMON="LOOK=900 WRULE=msharpe SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy"
run() {  # $1 = dev dir, $2 = OUT_TAG, rest = arm env
  local d=$1 tag=$2; shift 2
  cd $R/$d
  echo "CMD[$tag] (cwd=$R/$d): env $COMMON $* OUT_TAG=$tag $PY ../w10_universe_recheck.py" >> $R/$d/logs/commands.txt
  ( env $COMMON "$@" OUT_TAG=$tag $PY ../w10_universe_recheck.py > $R/$d/logs/$tag.log 2>&1 && echo "${tag}_OK" || echo "${tag}_FAIL" ) &
}
# batch 1: canon form, original meta (Σ-simple y4), CAL=log
run dev A_callog          LEGS=111 PHI=0    FSEED=42   CAL=log    REF_SKIP=1
run dev B_callog          LEGS=101 PHI=0    FSEED=42   CAL=log
run dev C_callog_s42      LEGS=111 PHI=0.45 FSEED=42   CAL=log    REF_SKIP=1
run dev C_callog_s2027    LEGS=111 PHI=0.45 FSEED=2027 CAL=log    REF_SKIP=1
wait
# batch 2: canon form, CAL=simple (expm1 of Σ-simple y4)
run dev A_calsimple       LEGS=111 PHI=0    FSEED=42   CAL=simple REF_SKIP=1
run dev B_calsimple       LEGS=101 PHI=0    FSEED=42   CAL=simple
run dev C_calsimple_s42   LEGS=111 PHI=0.45 FSEED=42   CAL=simple REF_SKIP=1
run dev C_calsimple_s2027 LEGS=111 PHI=0.45 FSEED=2027 CAL=simple REF_SKIP=1
wait
# batch 3: D s2027 canon both calibers + alt-target A,B
run dev D_callog_s2027    LEGS=101 PHI=0.45 FSEED=2027 CAL=log
run dev D_calsimple_s2027 LEGS=101 PHI=0.45 FSEED=2027 CAL=simple
run dev_alt A_prod        LEGS=111 PHI=0    FSEED=42   CAL=log    REF_SKIP=1
run dev_alt B_prod        LEGS=101 PHI=0    FSEED=42   CAL=log
wait
# batch 4: alt-target (compounded holding-window y4, CAL=log = no transform) C,D both seeds
run dev_alt C_prod_s42    LEGS=111 PHI=0.45 FSEED=42   CAL=log    REF_SKIP=1
run dev_alt D_prod_s42    LEGS=101 PHI=0.45 FSEED=42   CAL=log
run dev_alt C_prod_s2027  LEGS=111 PHI=0.45 FSEED=2027 CAL=log    REF_SKIP=1
run dev_alt D_prod_s2027  LEGS=101 PHI=0.45 FSEED=2027 CAL=log
wait
echo "ALL_ARMS_FINISHED $(date -u +%FT%TZ)"
echo "=====CONFIG lines====="
for d in dev dev_alt; do for f in $R/$d/logs/*.log; do echo "$(basename $f): $(grep -E '^CONFIG' $f | head -1)"; done; done
echo "=====RECEIPT_EX d30====="
for d in dev dev_alt; do for f in $R/$d/logs/*.log; do echo "$d/$(basename $f .log): $(grep -E 'RECEIPT_EX d30' $f)"; done; done
echo "=====F10 source lines====="
grep -H "F10 leg source\|F10 OOS preds aligned\|SLOW override" $R/dev/logs/C_callog_s42.log $R/dev/logs/C_callog_s2027.log $R/dev_alt/logs/D_prod_s42.log
echo "=====errors====="; grep -l "Traceback\|Error" $R/dev/logs/*.log $R/dev_alt/logs/*.log || echo "no tracebacks"
