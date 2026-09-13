#!/bin/bash
# FX-TRAIN TRN-02 real-data controls S1-S5 (pod2, CPU, nice 19). Writes ONLY under /workspace/fx_train_2026-09-13/. September artifacts are read-only; shas before/after.
set -o pipefail
W=/workspace/fx_train_2026-09-13; DEV=$W/trn02_dev; ISO=$W/trn02_iso; PY=/workspace/venv/bin/python; LOG=$W/receipts/trn02_real
mkdir -p $LOG
C09=/workspace/data/dlnative_5m_wide829_f16_holefix2.npz; CX=/workspace/data/dlnative_5m_wide829_f16_holefix2_x0910.npz
P09=/workspace/review_scratch/raw_patch.npz; PX=/workspace/uplift_2026-09-11/r6/out/raw_patch_x0910.npz
KL=/workspace/review_scratch/raw5m_kl; DLX=/workspace/uplift_2026-09-11/r6/dl/klines
PROT="$C09 $P09 $PX /workspace/review_scratch/holefix2_cells.npz /workspace/dlw_v4raw/data/dlw_targets.npz /workspace/uplift_2026-09-11/r6/out/dlw_targets_x0910.npz"
echo "START $(date -u +%FT%TZ)"
nice -n 19 sha256sum $PROT > $LOG/protected_sha_before.txt; stat -c "%n %s %Y" $CX > $LOG/protected_stat_before.txt
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader > $LOG/gpu_before.txt
for d in sept x0910 sept_on_x0910; do rm -rf $ISO/$d; mkdir -p $ISO/$d; done
cp $P09 $ISO/sept/raw_patch.npz; cp $PX $ISO/x0910/raw_patch.npz; cp $P09 $ISO/sept_on_x0910/raw_patch.npz
sha256sum $ISO/*/raw_patch.npz | tee $LOG/iso_patch_sha.txt
run(){ lab=$1; shift; echo "== $lab"; nice -n 19 env -i PATH=/usr/bin:/bin HOME=/root "$@" > $LOG/$lab.log 2>&1; rc=$?; echo "$lab rc=$rc"; tail -3 $LOG/$lab.log; }
run S3_manifest_sept     CACHE=$C09 RAW_PATCH=$ISO/sept/raw_patch.npz          KLINE_SOURCES=$KL        MANIFEST_OUT=$ISO/sept/raw_patch.manifest.json $PY $DEV/v4_rawpatch_manifest.py
run S3_manifest_x0910    CACHE=$CX  RAW_PATCH=$ISO/x0910/raw_patch.npz         KLINE_SOURCES=$KL,$DLX   MANIFEST_OUT=$ISO/x0910/raw_patch.manifest.json $PY $DEV/v4_rawpatch_manifest.py
run S3_manifest_sept_on_x0910 CACHE=$CX RAW_PATCH=$ISO/sept_on_x0910/raw_patch.npz KLINE_SOURCES=$KL,$DLX MANIFEST_OUT=$ISO/sept_on_x0910/raw_patch.manifest.json $PY $DEV/v4_rawpatch_manifest.py
run S4_gate_sept          CACHE=$C09 RAW_PATCH=$ISO/sept/raw_patch.npz RAW_PATCH_MANIFEST=$ISO/sept/raw_patch.manifest.json RAWPATCH_OUT=$LOG/S4_gate_sept.json $PY $DEV/v4_gate_rawpatch.py
run S4_gate_x0910         CACHE=$CX RAW_PATCH=$ISO/x0910/raw_patch.npz RAW_PATCH_MANIFEST=$ISO/x0910/raw_patch.manifest.json RAWPATCH_OUT=$LOG/S4_gate_x0910.json $PY $DEV/v4_gate_rawpatch.py
run S4_gate_sept_on_x0910 CACHE=$CX RAW_PATCH=$ISO/sept_on_x0910/raw_patch.npz RAW_PATCH_MANIFEST=$ISO/sept_on_x0910/raw_patch.manifest.json RAWPATCH_OUT=$LOG/S4_gate_sept_on_x0910.json $PY $DEV/v4_gate_rawpatch.py
run S5_builder_fixed_sept_on_x0910 DLWT_CACHE=$CX DLWT_PANEL=/workspace/uplift_2026-09-11/r6/out/wide_panel_4h_v3splice_x0910.npz DLWT_OUT=$ISO/tg_red_sept_on_x0910 DLWT_RET_CH=0 DLWT_RAW_PATCH=$ISO/sept_on_x0910/raw_patch.npz $PY $DEV/pod_dlw_targets_raw.py
ls -la $ISO/tg_red_sept_on_x0910/data $ISO/tg_red_sept_on_x0910/results 2>&1 | tee $LOG/S5_outputs.txt
nice -n 19 sha256sum $PROT > $LOG/protected_sha_after.txt; stat -c "%n %s %Y" $CX > $LOG/protected_stat_after.txt
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader > $LOG/gpu_after.txt
cmp -s $LOG/protected_sha_before.txt $LOG/protected_sha_after.txt && cmp -s $LOG/protected_stat_before.txt $LOG/protected_stat_after.txt && echo SEPT_ARTIFACTS_UNCHANGED || echo SEPT_ARTIFACTS_CHANGED
echo "END $(date -u +%FT%TZ)"
