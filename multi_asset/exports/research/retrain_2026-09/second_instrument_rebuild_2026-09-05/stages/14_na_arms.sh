#!/bin/bash
# stage 14: NOT-ADMITTED hist-king arms (条件性诊断: G4b(iii) 3/15 格失败) in separate directories dev_na/ dev_alt_na/; judge on a root that
# combines the main pinned artifacts with these; output tables go to na_root/results (appendix only, never the main table).
source /workspace/review_scratch/jpline_rebuild/lib.sh
cd $ROOT
for v in dev_na dev_alt_na; do d=$ROOT/$v; mkdir -p $d/pod_backup_2026-08-21 $d/probe_artifacts $d/logs
  ln -sfn $ROOT/data/nets_histv2_0_0_0.npy $d/pod_backup_2026-08-21/nets_histv2_0_0_0.npy; ln -sfn $ROOT/data/nets_histv2_-30_2_42.npy $d/pod_backup_2026-08-21/nets_histv2_-30_2_42.npy
  ln -sfn $ROOT/data/slow_pred_hist_oos_rebuilt.npy $d/pod_backup_2026-08-21/slow_pred_hist_oos.npy; ln -sfn $ROOT/data/wide_panel_4h_hist_v2_rebuilt.npz $d/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz
  if [ $v = dev_na ]; then ln -sfn $ROOT/data/wide_fea_hist_meta_rebuilt.npz $d/pod_backup_2026-08-21/wide_fea_hist_meta.npz; else ln -sfn $ROOT/data/meta_hist_newprod.npz $d/pod_backup_2026-08-21/wide_fea_hist_meta.npz; fi
  ln -sfn /workspace/port_w10/f8_2026-08-22 $d/f8_2026-08-22; ln -sfn /workspace/port_w10/dlw_2026-08-22 $d/dlw_2026-08-22
done
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
SLOW=$ROOT/data/slow_pred_hist_oos_rebuilt.npy; LIVE="MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero"; MAXJ=6; njobs=0
launch() { local cal=$1; local tag=$2; shift 2; local d=$ROOT/dev_na; [ $cal = prod ] && d=$ROOT/dev_alt_na
  echo "CMD[$STAGE] (cwd=$d) $(date -u +%FT%TZ): env LOOK=900 WRULE=msharpe CAL=log $* OUT_TAG=$tag $PY ../w10_universe_recheck.py" >> $CMDLOG
  (cd $d && env LOOK=900 WRULE=msharpe CAL=log "$@" OUT_TAG=$tag $PY ../w10_universe_recheck.py > $d/logs/$tag.log 2>&1) &
  njobs=$((njobs+1)); if [ $njobs -ge $MAXJ ]; then wait -n; njobs=$((njobs-1)); fi; }
launch prod F1_hist_prod SLOW_NPY=$SLOW LEGS=111 PHI=0 FSEED=42
for cal in log prod; do for seed in 42 2027; do
  launch $cal F2_hist_${cal}_s$seed SLOW_NPY=$SLOW LEGS=101 PHI=0.45 FSEED=$seed $LIVE W3FIX=0.21,0,0.79
  launch $cal F3_hist_${cal}_s$seed SLOW_NPY=$SLOW LEGS=101 PHI=0.45 FSEED=$seed $LIVE
done; done; wait
fail=0; for f in $ROOT/dev_na/logs/*.log $ROOT/dev_alt_na/logs/*.log; do echo "== $f"; grep -E "^(CONFIG|RECEIPT_EX d30|DONE|Traceback|AssertionError)" $f | cut -c1-400; grep -q "^DONE" $f || fail=1; done; [ $fail = 0 ] || exit 3
run bash gates/make_na_root.sh
run env JR_ROOT=$ROOT/na_root JR_DATA_ROOT=$ROOT $PY gates/judge_rebuild.py
cp $ROOT/na_root/results/REPORT_tables.md $ROOT/results/REPORT_tables_NOT_ADMITTED.md; cp $ROOT/na_root/results/judge_rebuild.json $ROOT/results/judge_rebuild_NOT_ADMITTED.json
run sha256sum results/REPORT_tables_NOT_ADMITTED.md results/judge_rebuild_NOT_ADMITTED.json
