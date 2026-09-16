#!/bin/bash
# FX-TRAIN TRN-03 positive control: rebuild the IN-SERVICE f10_live_s42_np.npz arrays from /workspace/f8_ext/models/f10_live_s42.pt
# with pod_f10_np_export_v4.py in LEGACY COMPARE MODE (that checkpoint predates the refit sidecar, FACT_TABLE 03.6) and compare
# every array BITWISE with the deployed file. Legacy mode NEVER writes an npz. READ-ONLY on /workspace/f8_ext and /workspace/dlw_ext;
# writes only under /workspace/fx_train_2026-09-13/. F10_NP_OUT points into my own sandbox, never at the live path.
set -o pipefail
DEV=/workspace/fx_train_2026-09-13/trn03_dev; OUTD=/workspace/fx_train_2026-09-13/receipts/trn03; PY=/workspace/venv/bin/python
mkdir -p $OUTD $DEV/never_written
echo "START $(date -u +%FT%TZ)"
sha256sum $DEV/pod_f10_np_export_v4.py
PROT="/workspace/f8_ext/models/f10_live_s42.pt /workspace/f8_ext/models/f10_live_s42_np.npz"
nice -n 19 sha256sum $PROT | tee $OUTD/protected_sha_before.txt
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader > $OUTD/gpu_before.txt
nice -n 19 env -i PATH=/usr/bin:/bin HOME=/root \
  F10_OUT=/workspace/f8_ext F10_DLW=/workspace/dlw_ext SEED=42 \
  F10_SIDECAR=NONE_LEGACY_ARTIFACT F10_NP_COMPARE=/workspace/f8_ext/models/f10_live_s42_np.npz \
  F10_NP_OUT=$DEV/never_written/must_not_appear.npz F10_NP_RECEIPT=$OUTD/F10_NP_EXPORT_legacy_compare.json \
  F10_GENERATION=legacy_control F10_BEST_EP_RULE=fix7 \
  $PY $DEV/pod_f10_np_export_v4.py 2>&1 | tee $OUTD/legacy_compare.log
echo "EXPORTER rc=${PIPESTATUS[0]}"
ls -la $DEV/never_written/ | tee $OUTD/never_written_listing.txt
nice -n 19 sha256sum $PROT | tee $OUTD/protected_sha_after.txt
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader > $OUTD/gpu_after.txt
echo "END $(date -u +%FT%TZ)"
