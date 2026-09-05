#!/bin/bash
# stage 08 setup: dev/ (caliber log = raw Σ-simple meta) and dev_alt/ (caliber prod = meta y4 := Π(1+r5)-1) layouts for the verbatim
# w10_universe_recheck.py (combo_recheck copy, sha 5424aceb…), following rolling_king/setup_dev.sh. Reference nets = stage-6 rebuilt files.
# Adapters: make_pinned_on_hist.py (pinned king re-indexed to the hist anchor grid), build_alt_meta_hist.py (prod-caliber meta).
source /workspace/review_scratch/jpline_rebuild/lib.sh
cd $ROOT
cp src/w10_universe_recheck.py $ROOT/w10_universe_recheck.py
sha256sum $ROOT/w10_universe_recheck.py src/w10_universe_recheck.py /workspace/review_scratch/combo_recheck/w10_universe_recheck.py
echo "--- diff vs port original (expected: REF_SKIP guard only)"; diff /workspace/port_w10/w10_universe.py $ROOT/w10_universe_recheck.py || true
sha256sum gates/make_pinned_on_hist.py gates/build_alt_meta_hist.py
run $PY gates/make_pinned_on_hist.py
run $PY gates/build_alt_meta_hist.py
for v in dev dev_alt; do
  d=$ROOT/$v; mkdir -p $d/pod_backup_2026-08-21 $d/probe_artifacts $d/logs
  ln -sfn $ROOT/data/nets_histv2_0_0_0.npy $d/pod_backup_2026-08-21/nets_histv2_0_0_0.npy
  ln -sfn $ROOT/data/nets_histv2_-30_2_42.npy $d/pod_backup_2026-08-21/nets_histv2_-30_2_42.npy
  ln -sfn $ROOT/data/slow_pred_hist_oos_rebuilt.npy $d/pod_backup_2026-08-21/slow_pred_hist_oos.npy
  ln -sfn $ROOT/data/wide_panel_4h_hist_v2_rebuilt.npz $d/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz
  if [ $v = dev ]; then ln -sfn $ROOT/data/wide_fea_hist_meta_rebuilt.npz $d/pod_backup_2026-08-21/wide_fea_hist_meta.npz
  else ln -sfn $ROOT/data/meta_hist_newprod.npz $d/pod_backup_2026-08-21/wide_fea_hist_meta.npz; fi
  ln -sfn /workspace/port_w10/f8_2026-08-22 $d/f8_2026-08-22      # F10 V2MAIN OOS preds s42/s2027 (read-only, the files the recheck device already uses)
  ln -sfn /workspace/port_w10/dlw_2026-08-22 $d/dlw_2026-08-22    # dlw_targets.npz used only for F10 anchor/symbol alignment (read-only)
done
echo "--- layout"; for v in dev dev_alt; do for f in $ROOT/$v/pod_backup_2026-08-21/* $ROOT/$v/f8_2026-08-22 $ROOT/$v/dlw_2026-08-22; do echo "$f -> $(readlink -f $f)"; done; done
sha256sum /workspace/f8_2026-08-22/preds/f10_V2MAIN_s42.npy /workspace/f8_2026-08-22/preds/f10_V2MAIN_s2027.npy /workspace/data/dlw_targets.npz /workspace/shadow_bundle_v3/slow_pred_pinned.npy
