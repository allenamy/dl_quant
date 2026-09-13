#!/bin/bash
set -o pipefail
W=/workspace/fx_train_2026-09-13; PY=/workspace/venv/bin/python
F="/workspace/data/dlnative_5m_wide829_f16_holefix2.npz /workspace/review_scratch/raw_patch.npz /workspace/uplift_2026-09-11/r6/out/raw_patch_x0910.npz /workspace/review_scratch/holefix2_cells.npz"
echo "START $(date -u +%FT%TZ)"
nice -n 19 sha256sum $F > $W/receipts/trn02_sha_before.txt
stat -c "%n %s %Y" /workspace/data/dlnative_5m_wide829_f16_holefix2_x0910.npz /workspace/data/dlnative_5m_wide829_f16_holefix.npz > $W/receipts/trn02_stat_before.txt
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader > $W/receipts/trn02_gpu_before.txt
nice -n 19 $PY $W/devices/fx_trn02_measure_patch_coverage.py $W/receipts/TRN02_patch_coverage_measure.json \
  sept_holefix2=/workspace/data/dlnative_5m_wide829_f16_holefix2.npz,/workspace/review_scratch/raw_patch.npz \
  r6_x0910=/workspace/data/dlnative_5m_wide829_f16_holefix2_x0910.npz,/workspace/uplift_2026-09-11/r6/out/raw_patch_x0910.npz \
  sept_patch_on_x0910=/workspace/data/dlnative_5m_wide829_f16_holefix2_x0910.npz,/workspace/review_scratch/raw_patch.npz \
  build_cache_holefix=/workspace/data/dlnative_5m_wide829_f16_holefix.npz,/workspace/review_scratch/raw_patch.npz
rc=$?
nice -n 19 sha256sum $F > $W/receipts/trn02_sha_after.txt
stat -c "%n %s %Y" /workspace/data/dlnative_5m_wide829_f16_holefix2_x0910.npz /workspace/data/dlnative_5m_wide829_f16_holefix.npz > $W/receipts/trn02_stat_after.txt
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader > $W/receipts/trn02_gpu_after.txt
cmp -s $W/receipts/trn02_sha_before.txt $W/receipts/trn02_sha_after.txt && cmp -s $W/receipts/trn02_stat_before.txt $W/receipts/trn02_stat_after.txt && echo "SEPT_ARTIFACTS_UNCHANGED" || echo "SEPT_ARTIFACTS_CHANGED"
echo "END rc=$rc $(date -u +%FT%TZ)"
