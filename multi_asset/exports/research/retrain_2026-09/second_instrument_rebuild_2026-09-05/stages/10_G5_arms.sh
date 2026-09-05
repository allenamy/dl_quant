#!/bin/bash
# stage 10: G5 arms (prereg §2 G5). Panel/meta fixed = rebuilt hist; king in {pinned (re-indexed), hist (only if G4 verdict admits)};
# F1 = LEGS=111 PHI=0 dynamic msharpe; F2 = LEGS=101 PHI=0.45 W3FIX=0.21,0,0.79 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero;
# F3 = F2 without W3FIX; caliber log -> dev/, prod -> dev_alt/ (meta y4 := Π(1+r5)-1); F2/F3 seeds 42 and 2027. REF_SKIP unset.
source /workspace/review_scratch/jpline_rebuild/lib.sh
cd $ROOT
ADMIT=$($PY -c "import json;print(int(json.load(open('results/G4_verdict.json'))['hist_king_admitted']))")
echo "hist king admitted to G5: $ADMIT"
KINGS="pinned"; [ "$ADMIT" = "1" ] && KINGS="hist pinned"
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
LIVE="MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero"
MAXJ=6; njobs=0
launch() {  # $1 cal, $2 tag, rest env
  local cal=$1; local tag=$2; shift 2
  local d=$ROOT/dev; [ $cal = prod ] && d=$ROOT/dev_alt
  if [ -f $d/probe_artifacts/w10_ablation_series_$tag.npz ] && grep -q "^DONE" $d/logs/$tag.log 2>/dev/null; then echo "skip $tag (exists)"; return; fi
  echo "CMD[$STAGE] (cwd=$d) $(date -u +%FT%TZ): env LOOK=900 WRULE=msharpe CAL=log $* OUT_TAG=$tag $PY ../w10_universe_recheck.py" >> $CMDLOG
  (cd $d && env LOOK=900 WRULE=msharpe CAL=log "$@" OUT_TAG=$tag $PY ../w10_universe_recheck.py > $d/logs/$tag.log 2>&1) &
  njobs=$((njobs+1)); if [ $njobs -ge $MAXJ ]; then wait -n; njobs=$((njobs-1)); fi
}
for king in $KINGS; do
  [ $king = hist ] && SLOW=$ROOT/data/slow_pred_hist_oos_rebuilt.npy || SLOW=$ROOT/data/slow_pred_pinned_on_hist.npy
  for cal in log prod; do
    launch $cal F1_${king}_${cal}        SLOW_NPY=$SLOW LEGS=111 PHI=0 FSEED=42
    for seed in 42 2027; do
      launch $cal F2_${king}_${cal}_s$seed SLOW_NPY=$SLOW LEGS=101 PHI=0.45 FSEED=$seed $LIVE W3FIX=0.21,0,0.79
      launch $cal F3_${king}_${cal}_s$seed SLOW_NPY=$SLOW LEGS=101 PHI=0.45 FSEED=$seed $LIVE
    done
  done
done
wait
echo "G5_ARMS_DONE $(date -u +%FT%TZ)" | tee -a $CMDLOG
fail=0
for king in $KINGS; do for cal in log prod; do d=$ROOT/dev; [ $cal = prod ] && d=$ROOT/dev_alt
  for tag in F1_${king}_${cal} F2_${king}_${cal}_s42 F2_${king}_${cal}_s2027 F3_${king}_${cal}_s42 F3_${king}_${cal}_s2027; do
    echo "== $tag"; grep -E "^(CONFIG|SLOW override|F10 OOS|MEMBERS_TOPN|NOTE|RECEIPT_EX d30|DONE|Traceback|AssertionError)" $d/logs/$tag.log | cut -c1-600
    grep -q "^DONE" $d/logs/$tag.log || fail=1
  done; done; done
[ $fail = 0 ] || exit 3
sha256sum $ROOT/dev/probe_artifacts/*.npz $ROOT/dev_alt/probe_artifacts/*.npz
