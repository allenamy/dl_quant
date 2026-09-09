#!/bin/bash
cd /workspace/review_scratch; /workspace/venv/bin/python patch_targets_raw_inplace.py || exit 1
mkdir -p /workspace/dlw_raw32/data /workspace/dlw_raw32/results; : > gate_r2_r3_32.log
cd /workspace && DLWT_CACHE=/workspace/data/dlnative_5m_wide829_f16_holefix.npz DLWT_PANEL=/workspace/data/wide_panel_4h_v3splice.npz DLWT_OUT=/workspace/dlw_raw32 DLWT_RET_CH=0 DLWT_RAW_PATCH=/workspace/review_scratch/raw_patch.npz /workspace/venv/bin/python /workspace/review_scratch/pod_dlw_targets_raw.py > /workspace/review_scratch/targets_raw32.log 2>&1; echo "targets rc=$?"
grep -E "raw patch|TARGETS_DONE|Traceback" /workspace/review_scratch/targets_raw32.log | cut -c1-200
cd /workspace/review_scratch; sed -i 's#for i in $(seq 1 120); do grep -q PIPE_RAW32_END gate_r2_r3_32.log 2>/dev/null && break; sleep 30; done#test -f /workspace/dlw_raw32/data/dlw_targets.npz || { echo NO_RAW32 >> pipeD.log; exit 1; }#' pipeD.sh
grep -c "dlw_raw32/data/dlw_targets.npz" pipeD.sh
(setsid nohup bash pipeD.sh > /dev/null 2>&1 < /dev/null &); echo "pipeD relaunched"
