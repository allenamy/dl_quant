#!/bin/bash
# GAP#6: same harness as refute_C6_2/run_alt.sh (port w10_universe.py, symlinked inputs), variants base/shiftsum/shiftprod × {w3fix, dyn}
set -e
ROOT=/workspace/review_scratch/gap_6/altrun; mkdir -p $ROOT; cd $ROOT
cp /workspace/port_w10/w10_universe.py $ROOT/w10_universe.py; sha256sum $ROOT/w10_universe.py /workspace/port_w10/w10_universe.py /workspace/review_scratch/refute_C6_2/altrun/w10_universe.py
/workspace/venv/bin/python /workspace/review_scratch/gap_6/build_shift_meta.py 2>&1 | tee $ROOT/build_shift_meta.out
for v in base shiftsum shiftprod; do
  d=$ROOT/$v; mkdir -p $d/pod_backup_2026-08-21 $d/probe_artifacts
  ln -sfn $ROOT/w10_universe.py $d/w10_universe.py
  if [ $v = base ]; then ln -sfn /workspace/data/wide_fea_v2ext_meta.npz $d/pod_backup_2026-08-21/wide_fea_hist_meta.npz; else ln -sfn $ROOT/meta_$v.npz $d/pod_backup_2026-08-21/wide_fea_hist_meta.npz; fi
  ln -sfn /workspace/data/wide_panel_4h_v2ext.npz $d/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz
  ln -sfn /workspace/shadow_bundle_v3/slow_pred_pinned.npy $d/pod_backup_2026-08-21/slow_pred_hist_oos.npy
  ln -sfn /workspace/port_w10/pod_backup_2026-08-21/nets_histv2_0_0_0.npy $d/pod_backup_2026-08-21/nets_histv2_0_0_0.npy
  ln -sfn /workspace/port_w10/pod_backup_2026-08-21/nets_histv2_-30_2_42.npy $d/pod_backup_2026-08-21/nets_histv2_-30_2_42.npy
  ln -sfn /workspace/port_w10/f8_2026-08-22 $d/f8_2026-08-22
  ln -sfn /workspace/port_w10/dlw_2026-08-22 $d/dlw_2026-08-22
done
COMMON="LEGS=101 LOOK=900 WRULE=msharpe SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy FSEED=42 CAL=log"
LIVE="MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero"
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
for v in base shiftsum shiftprod; do
  cd $ROOT/$v
  echo "CMD: cd $ROOT/$v && env $COMMON $LIVE W3FIX=0.21,0,0.79 OUT_TAG=alt_${v}_w3fix /workspace/venv/bin/python w10_universe.py"
  env $COMMON $LIVE W3FIX=0.21,0,0.79 OUT_TAG=alt_${v}_w3fix /workspace/venv/bin/python w10_universe.py > $ROOT/alt_${v}_w3fix.log 2>&1 &
  echo "CMD: cd $ROOT/$v && env $COMMON $LIVE OUT_TAG=alt_${v}_dyn /workspace/venv/bin/python w10_universe.py"
  env $COMMON $LIVE OUT_TAG=alt_${v}_dyn /workspace/venv/bin/python w10_universe.py > $ROOT/alt_${v}_dyn.log 2>&1 &
done
wait
echo ALT_RUNS_DONE $(date -u +%FT%TZ); grep -H -E "RECEIPT_EX d30|CONFIG|SLOW override|F10 OOS|^DONE" $ROOT/alt_*.log | cut -c1-400
