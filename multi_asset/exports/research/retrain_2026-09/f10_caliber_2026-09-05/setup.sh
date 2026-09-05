#!/bin/bash
# setup.sh — PREREG_f10_caliber_sensitivity_2026-09-05: reproduce the health_check device layout under review_scratch/f10_caliber/
# dev/ (log caliber = meta y4 = label (i) Σ-simple [E,E+47]), dev_alt/ (prod = meta_newprod = label (iii) Π(1+r)−1 [E+1,E+48]),
# dev_alt2/ (sum1 = meta_newsum_f10cal = label (ii) Σ-simple [E+1,E+48], built by s0_build_labels.py).
# Read-only on every source; writes only under /workspace/review_scratch/f10_caliber/. Every command is logged verbatim in logs/commands.txt.
set -e
ROOT=/workspace/review_scratch/f10_caliber; HC=/workspace/review_scratch/health_check
mkdir -p $ROOT/logs $ROOT/results $ROOT/masks $ROOT/calib $ROOT/labels $ROOT/meta
cd $ROOT
echo "CMD[setup] $(date -u +%FT%TZ): bash setup.sh" >> $ROOT/logs/commands.txt
cp $HC/w10_health.py $ROOT/w10_health.py
cp $HC/masks/umask_UPIT.npz $ROOT/masks/umask_UPIT.npz
cp $HC/calib/costb_fee_steady.json $ROOT/calib/costb_fee_steady.json
echo "--- sha256 copies vs health_check originals (must be pairwise identical)"
sha256sum $ROOT/w10_health.py $HC/w10_health.py $ROOT/masks/umask_UPIT.npz $HC/masks/umask_UPIT.npz $ROOT/calib/costb_fee_steady.json $HC/calib/costb_fee_steady.json
for v in dev dev_alt dev_alt2; do
  d=$ROOT/$v; mkdir -p $d/pod_backup_2026-08-21 $d/probe_artifacts $d/logs
  for f in nets_histv2_0_0_0.npy nets_histv2_-30_2_42.npy slow_pred_hist_oos.npy wide_panel_4h_hist_v2.npz; do
    ln -sfn $(readlink -f $HC/dev/pod_backup_2026-08-21/$f) $d/pod_backup_2026-08-21/$f
  done
  case $v in
    dev)      ln -sfn $(readlink -f $HC/dev/pod_backup_2026-08-21/wide_fea_hist_meta.npz) $d/pod_backup_2026-08-21/wide_fea_hist_meta.npz ;;
    dev_alt)  ln -sfn $(readlink -f $HC/dev_alt/pod_backup_2026-08-21/wide_fea_hist_meta.npz) $d/pod_backup_2026-08-21/wide_fea_hist_meta.npz ;;
    dev_alt2) ln -sfn $ROOT/meta/meta_newsum_f10cal.npz $d/pod_backup_2026-08-21/wide_fea_hist_meta.npz ;;
  esac
  ln -sfn $(readlink -f $HC/dev/f8_2026-08-22) $d/f8_2026-08-22
  ln -sfn $(readlink -f $HC/dev/dlw_2026-08-22) $d/dlw_2026-08-22
done
echo "--- resolved targets vs health_check (dev, dev_alt must all be SAME; dev_alt2 meta = my label-(ii) file)"
for v in dev dev_alt; do
  for f in nets_histv2_0_0_0.npy nets_histv2_-30_2_42.npy slow_pred_hist_oos.npy wide_fea_hist_meta.npz wide_panel_4h_hist_v2.npz; do
    a=$(readlink -f $ROOT/$v/pod_backup_2026-08-21/$f); b=$(readlink -f $HC/$v/pod_backup_2026-08-21/$f)
    [ "$a" = "$b" ] && echo "SAME $v/$f -> $a" || echo "DIFF $v/$f mine=$a hc=$b"
  done
  for f in f8_2026-08-22 dlw_2026-08-22; do
    a=$(readlink -f $ROOT/$v/$f); b=$(readlink -f $HC/$v/$f)
    [ "$a" = "$b" ] && echo "SAME $v/$f -> $a" || echo "DIFF $v/$f mine=$a hc=$b"
  done
done
for f in nets_histv2_0_0_0.npy nets_histv2_-30_2_42.npy slow_pred_hist_oos.npy wide_panel_4h_hist_v2.npz wide_fea_hist_meta.npz; do echo "dev_alt2/$f -> $(readlink -f $ROOT/dev_alt2/pod_backup_2026-08-21/$f)"; done
echo "dev_alt2/f8_2026-08-22 -> $(readlink -f $ROOT/dev_alt2/f8_2026-08-22)"; echo "dev_alt2/dlw_2026-08-22 -> $(readlink -f $ROOT/dev_alt2/dlw_2026-08-22)"
echo "--- input sha256"
sha256sum /workspace/data/dlnative_5m_wide829_f16_ext.npz /workspace/data/wide_fea_v2ext_meta.npz /workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz /workspace/review_scratch/refute_C6_2/altrun/meta_newsum.npz /workspace/shadow_bundle_v3/slow_pred_pinned.npy /workspace/data/wide_panel_4h_v2ext.npz /workspace/port_w10/f8_2026-08-22/preds/f10_V2MAIN_s42.npy /workspace/port_w10/f8_2026-08-22/preds/f10_V2MAIN_s2027.npy /workspace/port_w10/dlw_2026-08-22/data/dlw_targets.npz
echo "SETUP_DONE $(date -u +%FT%TZ)"
