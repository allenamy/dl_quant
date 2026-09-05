#!/bin/bash
# setup_phi.sh — PREREG_dl_monthly_gate_and_phi_grid_2026-09-05 §B: φ grid layout under review_scratch/phi_grid/ = a copy of the f10_caliber dev_alt layout
# (label (iii) accounting caliber: meta = refute_C6_2/altrun/meta_newprod.npz = dlw y4s), device / mask / cost tiers byte-identical to health_check.
# Read-only on every source; writes only under /workspace/review_scratch/phi_grid/. Every command is logged verbatim in logs/commands.txt.
set -e
ROOT=/workspace/review_scratch/phi_grid; FC=/workspace/review_scratch/f10_caliber; HC=/workspace/review_scratch/health_check
mkdir -p $ROOT/logs $ROOT/results $ROOT/masks $ROOT/calib
cd $ROOT
echo "CMD[setup_phi] $(date -u +%FT%TZ): bash setup_phi.sh" >> $ROOT/logs/commands.txt
cp $HC/w10_health.py $ROOT/w10_health.py
cp $HC/masks/umask_UPIT.npz $ROOT/masks/umask_UPIT.npz
cp $HC/calib/costb_fee_steady.json $ROOT/calib/costb_fee_steady.json
echo "--- sha256 copies vs health_check originals vs f10_caliber copies (must be identical per row)"
sha256sum $ROOT/w10_health.py $HC/w10_health.py $FC/w10_health.py $ROOT/masks/umask_UPIT.npz $HC/masks/umask_UPIT.npz $FC/masks/umask_UPIT.npz $ROOT/calib/costb_fee_steady.json $HC/calib/costb_fee_steady.json $FC/calib/costb_fee_steady.json
d=$ROOT/dev_alt; mkdir -p $d/pod_backup_2026-08-21 $d/probe_artifacts $d/logs
for f in nets_histv2_0_0_0.npy nets_histv2_-30_2_42.npy slow_pred_hist_oos.npy wide_panel_4h_hist_v2.npz wide_fea_hist_meta.npz; do
  ln -sfn $(readlink -f $FC/dev_alt/pod_backup_2026-08-21/$f) $d/pod_backup_2026-08-21/$f
done
ln -sfn $(readlink -f $FC/dev_alt/f8_2026-08-22) $d/f8_2026-08-22
ln -sfn $(readlink -f $FC/dev_alt/dlw_2026-08-22) $d/dlw_2026-08-22
echo "--- resolved targets vs f10_caliber/dev_alt and health_check/dev_alt (must all be SAME)"
for f in nets_histv2_0_0_0.npy nets_histv2_-30_2_42.npy slow_pred_hist_oos.npy wide_fea_hist_meta.npz wide_panel_4h_hist_v2.npz; do
  a=$(readlink -f $d/pod_backup_2026-08-21/$f); b=$(readlink -f $FC/dev_alt/pod_backup_2026-08-21/$f); c=$(readlink -f $HC/dev_alt/pod_backup_2026-08-21/$f)
  [ "$a" = "$b" ] && [ "$a" = "$c" ] && echo "SAME dev_alt/$f -> $a" || echo "DIFF dev_alt/$f mine=$a f10_caliber=$b hc=$c"
done
for f in f8_2026-08-22 dlw_2026-08-22; do
  a=$(readlink -f $d/$f); b=$(readlink -f $FC/dev_alt/$f); c=$(readlink -f $HC/dev_alt/$f)
  [ "$a" = "$b" ] && [ "$a" = "$c" ] && echo "SAME dev_alt/$f -> $a" || echo "DIFF dev_alt/$f mine=$a f10_caliber=$b hc=$c"
done
echo "--- grid anchors reused from f10_caliber (PHI 0 and PHI 0.45, prod layout) — sha256 (must equal f10_caliber MANIFEST / chain_s2.log)"
sha256sum $FC/dev_alt/probe_artifacts/w10_ablation_series_prod_phi0_s42.npz $FC/dev_alt/probe_artifacts/w10_ablation_series_prod_phi0_s2027.npz $FC/dev_alt/probe_artifacts/w10_ablation_series_prod_phi045_s42.npz $FC/dev_alt/probe_artifacts/w10_ablation_series_prod_phi045_s2027.npz
echo "--- input sha256"
sha256sum /workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz /workspace/shadow_bundle_v3/slow_pred_pinned.npy /workspace/data/wide_panel_4h_v2ext.npz /workspace/port_w10/f8_2026-08-22/preds/f10_V2MAIN_s42.npy /workspace/port_w10/f8_2026-08-22/preds/f10_V2MAIN_s2027.npy /workspace/port_w10/dlw_2026-08-22/data/dlw_targets.npz
echo "SETUP_PHI_DONE $(date -u +%FT%TZ)"
