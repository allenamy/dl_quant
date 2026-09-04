#!/bin/bash
set -e
SC=/workspace/review_scratch/gap_2; DEV=$SC/dev; mkdir -p $DEV/pod_backup_2026-08-21 $DEV/probe_artifacts $DEV/f8_2026-08-22 $DEV/dlw_2026-08-22/data $DEV/logs
cd $DEV
cp /workspace/port_w10/w10_universe.py $DEV/w10_universe.py
ln -sfn /workspace/data/wide_panel_4h_v2ext.npz pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz
ln -sfn /workspace/data/wide_fea_v2ext_meta.npz pod_backup_2026-08-21/wide_fea_hist_meta.npz
ln -sfn /workspace/shadow_bundle_v3/slow_pred_pinned.npy pod_backup_2026-08-21/slow_pred_hist_oos.npy
ln -sfn /workspace/port_w10/pod_backup_2026-08-21/nets_histv2_-30_2_42.npy pod_backup_2026-08-21/nets_histv2_-30_2_42.npy
ln -sfn /workspace/port_w10/pod_backup_2026-08-21/nets_histv2_0_0_0.npy pod_backup_2026-08-21/nets_histv2_0_0_0.npy
ln -sfn /workspace/f8_2026-08-22/preds f8_2026-08-22/preds
ln -sfn /workspace/data/dlw_targets.npz dlw_2026-08-22/data/dlw_targets.npz
sha256sum w10_universe.py /workspace/port_w10/w10_universe.py
ls -la /workspace/probe_artifacts/umask_F_M7.npz /workspace/port_w10/probe_artifacts/umask_F_M7.npz 2>&1 | head -2 || true
find /workspace -name 'umask_*.npz' -not -path '*/venv/*' 2>/dev/null | head -5 || true
for C in simple log; do
  TAG=gap2_armB_cal$C
  echo "CMD[$TAG]: env LOOK=900 WRULE=msharpe CAL=$C LEGS=101 PHI=0.45 FSEED=42 FPRED=f10_V2MAIN_s42.npy MEMBERS_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy OUT_TAG=$TAG /workspace/venv/bin/python w10_universe.py" >> logs/commands.txt
  ( env OMP_NUM_THREADS=4 LOOK=900 WRULE=msharpe CAL=$C LEGS=101 PHI=0.45 FSEED=42 FPRED=f10_V2MAIN_s42.npy MEMBERS_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy OUT_TAG=$TAG /workspace/venv/bin/python w10_universe.py > logs/$TAG.log 2>&1 ) &
done
wait
for C in simple log; do grep -H "RECEIPT_EX d30_n2_c42" logs/gap2_armB_cal$C.log | cut -c1-400; done
echo ARMB_DONE $(date -u +%FT%TZ)
