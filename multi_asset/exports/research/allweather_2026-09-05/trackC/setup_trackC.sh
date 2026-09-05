#!/bin/bash
# setup_trackC.sh — allweather Track C (PREREG_allweather_programme_2026-09-05 §3 Track C): reproduce health_check's dev/ and dev_alt/ input layouts under
# /workspace/review_scratch/allweather_trackC/ (copied from health_check/setup_dev.sh; ROOT changed; device = health_check/w10_health.py sha 8684d9a9… copied verbatim as w10_health_orig.py,
# the patched device w10_agew.py is shipped from the research machine). Read-only on all sources; writes only under ROOT.
set -e
ROOT=/workspace/review_scratch/allweather_trackC; HC=/workspace/review_scratch/health_check
mkdir -p $ROOT/logs $ROOT/results $ROOT/c2 $ROOT/c4
cd $ROOT
cp $HC/w10_health.py $ROOT/w10_health_orig.py
echo "--- sha256 (orig copy / health_check device / patched device)"
sha256sum $ROOT/w10_health_orig.py $HC/w10_health.py $ROOT/w10_agew.py
echo "--- diff orig vs patched"
diff $ROOT/w10_health_orig.py $ROOT/w10_agew.py || true
for v in dev dev_alt; do
  d=$ROOT/$v; mkdir -p $d/pod_backup_2026-08-21 $d/probe_artifacts $d/logs
  for f in nets_histv2_0_0_0.npy nets_histv2_-30_2_42.npy slow_pred_hist_oos.npy wide_panel_4h_hist_v2.npz wide_fea_hist_meta.npz; do
    ln -sfn $(readlink -f $HC/$v/pod_backup_2026-08-21/$f) $d/pod_backup_2026-08-21/$f
  done
  ln -sfn $(readlink -f $HC/$v/f8_2026-08-22) $d/f8_2026-08-22
  ln -sfn $(readlink -f $HC/$v/dlw_2026-08-22) $d/dlw_2026-08-22
done
echo "--- resolved targets vs health_check (must all be SAME)"
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
echo "--- input sha256"
sha256sum $HC/masks/umask_UPIT.npz $HC/calib/costb_fee_steady.json /workspace/shadow_bundle_v3/slow_pred_pinned.npy /workspace/f8_2026-08-22/preds/f10_V2MAIN_s42.npy /workspace/f8_2026-08-22/preds/f10_V2MAIN_s2027.npy /workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz /workspace/data/wide_fea_v2ext_meta.npz
echo "SETUP_DONE $(date -u +%FT%TZ)"
