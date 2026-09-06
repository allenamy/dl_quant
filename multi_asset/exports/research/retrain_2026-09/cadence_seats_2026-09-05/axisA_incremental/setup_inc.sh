#!/bin/bash
# setup_inc.sh — axisA_incremental (PREREG_incremental_retrain_2026-09-06 §2): reproduce axisA's dev/ and dev_alt/ layouts (same symlink targets) and copy axisA's book device verbatim; record df/du. Read-only on sources.
set -e
ROOT=/workspace/review_scratch/cadence_seats/axisA_incremental; AXA=/workspace/review_scratch/cadence_seats/axisA
mkdir -p $ROOT/logs $ROOT/results
cd $ROOT
echo "--- df/du at start $(date -u +%FT%TZ)"; df -h /workspace | tail -1; du -sh /workspace/review_scratch 2>/dev/null | tail -1; nproc; uptime
cp $AXA/w10_universe_recheck.py $ROOT/w10_universe_recheck.py
echo "--- sha256 (my device copy / axisA device / port original)"; sha256sum $ROOT/w10_universe_recheck.py $AXA/w10_universe_recheck.py /workspace/port_w10/w10_universe.py
for v in dev dev_alt; do
  d=$ROOT/$v; mkdir -p $d/pod_backup_2026-08-21 $d/probe_artifacts $d/logs
  for f in nets_histv2_0_0_0.npy nets_histv2_-30_2_42.npy slow_pred_hist_oos.npy wide_panel_4h_hist_v2.npz wide_fea_hist_meta.npz; do ln -sfn $(readlink -f $AXA/$v/pod_backup_2026-08-21/$f) $d/pod_backup_2026-08-21/$f; done
  ln -sfn $(readlink -f $AXA/$v/f8_2026-08-22) $d/f8_2026-08-22; ln -sfn $(readlink -f $AXA/$v/dlw_2026-08-22) $d/dlw_2026-08-22
done
echo "--- resolved targets vs axisA (must all be SAME)"
for v in dev dev_alt; do
  for f in nets_histv2_0_0_0.npy nets_histv2_-30_2_42.npy slow_pred_hist_oos.npy wide_fea_hist_meta.npz wide_panel_4h_hist_v2.npz; do a=$(readlink -f $ROOT/$v/pod_backup_2026-08-21/$f); b=$(readlink -f $AXA/$v/pod_backup_2026-08-21/$f); [ "$a" = "$b" ] && echo "SAME $v/$f -> $a" || echo "DIFF $v/$f mine=$a axisA=$b"; done
  for f in f8_2026-08-22 dlw_2026-08-22; do a=$(readlink -f $ROOT/$v/$f); b=$(readlink -f $AXA/$v/$f); [ "$a" = "$b" ] && echo "SAME $v/$f -> $a" || echo "DIFF $v/$f mine=$a axisA=$b"; done
done
echo "--- input sha256"; sha256sum $AXA/models_d1/fold000_202401.txt /workspace/review_scratch/rolling_king/slow_pred_rollm.npy $AXA/folds_d1.json /workspace/data/wide_fea_v2ext.npy /workspace/data/wide_fea_v2ext_meta.npz /workspace/live_pins.json /workspace/shadow_bundle_v3/slow_pred_pinned.npy
echo "SETUP_DONE $(date -u +%FT%TZ)"
