#!/bin/bash
# setup_dev.sh — reproduce rolling_king's dev/ and dev_alt/ input layouts under review_scratch/health_check/
# (copied from cadence_seats/axisA/setup_dev.sh; ROOT changed; device copied from rolling_king = sha 5424aceb…).
# Read-only on all sources; writes only under /workspace/review_scratch/health_check/.
set -e
ROOT=/workspace/review_scratch/health_check
mkdir -p $ROOT/logs $ROOT/results $ROOT/masks
cd $ROOT
cp /workspace/review_scratch/rolling_king/w10_universe_recheck.py $ROOT/w10_universe_recheck.py
echo "--- sha256 (my copy / rolling_king / axisA / combo_recheck / port original)"
sha256sum $ROOT/w10_universe_recheck.py /workspace/review_scratch/rolling_king/w10_universe_recheck.py /workspace/review_scratch/cadence_seats/axisA/w10_universe_recheck.py /workspace/review_scratch/combo_recheck/w10_universe_recheck.py /workspace/port_w10/w10_universe.py
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
echo "--- resolved targets vs cadence_seats/axisB (must all be SAME)"
for v in dev dev_alt; do
  for f in nets_histv2_0_0_0.npy nets_histv2_-30_2_42.npy slow_pred_hist_oos.npy wide_fea_hist_meta.npz wide_panel_4h_hist_v2.npz; do
    a=$(readlink -f $ROOT/$v/pod_backup_2026-08-21/$f); b=$(readlink -f /workspace/review_scratch/cadence_seats/axisB/$v/pod_backup_2026-08-21/$f)
    [ "$a" = "$b" ] && echo "SAME $v/$f -> $a" || echo "DIFF $v/$f mine=$a axisB=$b"
  done
  for f in f8_2026-08-22 dlw_2026-08-22; do
    a=$(readlink -f $ROOT/$v/$f); b=$(readlink -f /workspace/review_scratch/cadence_seats/axisB/$v/$f)
    [ "$a" = "$b" ] && echo "SAME $v/$f -> $a" || echo "DIFF $v/$f mine=$a axisB=$b"
  done
done
echo "--- input sha256"
sha256sum /workspace/data/wide_fea_v2ext_meta.npz /workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz /workspace/shadow_bundle_v3/slow_pred_pinned.npy /workspace/data/wide_panel_4h_v2ext.npz /workspace/f8_2026-08-22/preds/f10_V2MAIN_s42.npy /workspace/f8_2026-08-22/preds/f10_V2MAIN_s2027.npy /workspace/port_w10/dlw_2026-08-22/data/dlw_targets.npz
echo "SETUP_DONE $(date -u +%FT%TZ)"
