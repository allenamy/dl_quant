#!/bin/bash
# setup_dev.sh — reproduce rolling_king's dev/ and dev_alt/ input layouts under cadence_seats/axisA/ (copied from rolling_king/setup_dev.sh; ROOT changed).
# Read-only on all sources; writes only under /workspace/review_scratch/cadence_seats/axisA/.
set -e
ROOT=/workspace/review_scratch/cadence_seats/axisA
cd $ROOT
cp /workspace/review_scratch/rolling_king/w10_universe_recheck.py $ROOT/w10_universe_recheck.py
echo "--- sha256 (my copy / rolling_king copy / combo_recheck copy / port original)"
sha256sum $ROOT/w10_universe_recheck.py /workspace/review_scratch/rolling_king/w10_universe_recheck.py /workspace/review_scratch/combo_recheck/w10_universe_recheck.py /workspace/port_w10/w10_universe.py
echo "--- diff port original vs my copy (expected: REF_SKIP guard only)"
diff /workspace/port_w10/w10_universe.py $ROOT/w10_universe_recheck.py || true
for v in dev dev_alt; do
  d=$ROOT/$v; mkdir -p $d/pod_backup_2026-08-21 $d/probe_artifacts $d/logs
  for f in nets_histv2_0_0_0.npy nets_histv2_-30_2_42.npy slow_pred_hist_oos.npy wide_panel_4h_hist_v2.npz; do
    ln -sfn /workspace/port_w10/pod_backup_2026-08-21/$f $d/pod_backup_2026-08-21/$f
  done
  if [ $v = dev ]; then
    ln -sfn /workspace/port_w10/pod_backup_2026-08-21/wide_fea_hist_meta.npz $d/pod_backup_2026-08-21/wide_fea_hist_meta.npz
  else
    ln -sfn /workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz $d/pod_backup_2026-08-21/wide_fea_hist_meta.npz
  fi
  ln -sfn /workspace/port_w10/f8_2026-08-22 $d/f8_2026-08-22
  ln -sfn /workspace/port_w10/dlw_2026-08-22 $d/dlw_2026-08-22
done
echo "--- resolved targets"
for v in dev dev_alt; do for f in $ROOT/$v/pod_backup_2026-08-21/*; do echo "$f -> $(readlink -f $f)"; done; done
echo "--- meta_newprod sha256 + refuters' parity receipt"
sha256sum /workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz
grep -E "PARITY" /workspace/review_scratch/refute_C6_2/altrun/build_alt_meta.out
