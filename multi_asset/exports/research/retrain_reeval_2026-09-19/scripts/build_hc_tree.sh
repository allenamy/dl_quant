#!/bin/bash
# build_hc_tree.sh — a private replay tree for stream T that reads EXACTLY the inputs the real-cost A1 arms read
# (/workspace/fp2_2026-09/health_check/dev_v4, BUILD.json 2026-09-17T11:58:34Z), by symlinking the same resolved targets file by file.
# Only logs/, probe_artifacts/ and f8_2026-08-22/preds/ are real directories (the device writes probe_artifacts; run_arm.sh writes logs).
# The device file is a byte copy of /workspace/fp2_2026-09/health_check/w10_health.py (sha256 8684d9a9…, asserted).
set -e
W=/workspace/retrain_reeval_2026-09-19; H=$W/hc; SRC=/workspace/fp2_2026-09/health_check; D=$H/dev_v4
mkdir -p $D/logs $D/probe_artifacts $D/pod_backup_2026-08-21 $D/f8_2026-08-22/preds $H/logs
cp $SRC/w10_health.py $H/w10_health.py
[ "$(sha256sum $H/w10_health.py | cut -c1-64)" = 8684d9a9f43a8d15beaa559cd12bd8f2977a3d088b01b93835f60f2bbf98a53d ] || { echo "device sha mismatch"; exit 3; }
ln -sfn $(readlink -f $SRC/dev_v4/dlw_2026-08-22) $D/dlw_2026-08-22
for f in nets_histv2_-30_2_42.npy nets_histv2_0_0_0.npy wide_panel_4h_hist_v2.npz slow_pred_hist_oos.npy wide_fea_hist_meta.npz; do
  ln -sfn $(readlink -f $SRC/dev_v4/pod_backup_2026-08-21/$f) $D/pod_backup_2026-08-21/$f
done
for s in 42 2027; do ln -sfn $SRC/dev_v4/f8_2026-08-22/preds/f10_v4RAW_s$s.npy $D/f8_2026-08-22/preds/f10_v4RAW_s$s.npy; done
# receipt: every input the device reads, resolved, with sha256 (source tree vs this tree must resolve to the same file)
{
  echo "{\"built_utc\": \"$(date -u +%FT%TZ)\", \"inputs\": {"
  first=1
  for rel in dlw_2026-08-22/data/dlw_targets.npz pod_backup_2026-08-21/nets_histv2_-30_2_42.npy pod_backup_2026-08-21/nets_histv2_0_0_0.npy pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz pod_backup_2026-08-21/slow_pred_hist_oos.npy pod_backup_2026-08-21/wide_fea_hist_meta.npz f8_2026-08-22/preds/f10_v4RAW_s42.npy f8_2026-08-22/preds/f10_v4RAW_s2027.npy; do
    a=$(readlink -f $D/$rel); b=$(readlink -f $SRC/dev_v4/$rel); sa=$(sha256sum $a | cut -c1-64)
    [ "$a" = "$b" ] || { echo "RESOLVE MISMATCH $rel: $a vs $b" >&2; exit 3; }
    [ $first = 1 ] || echo ","; first=0; echo "  \"$rel\": {\"resolved\": \"$a\", \"sha256\": \"$sa\"}"
  done
  echo "}, \"device\": \"$H/w10_health.py\", \"device_sha256\": \"$(sha256sum $H/w10_health.py | cut -c1-64)\"}"
} > $W/receipts/HC_TREE.json
echo HC_TREE_DONE
