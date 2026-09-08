#!/bin/bash
# PREREG §3 steps 2-5, gated by AMENDMENT 1's stricter panel regression gate. Panel from the STEP1 run is reused.
cd /workspace
C=/workspace/data/dlnative_5m_wide829_f16_holefix.npz
P=/workspace/data/wide_panel_4h_v2holefix.npz
L=/workspace/review_scratch/holefix_chain2.log
: > $L
say(){ echo "[$(date -u +%FT%TZ)] $*" >> $L; }
say "CHAIN2_START"
say "GATE panel regression (AMENDMENT 1)"
/workspace/venv/bin/python /workspace/review_scratch/panel_regression_gate.py $P >> $L 2>&1 || { say "GATE_FAIL"; exit 1; }
say "STEP2 king features"
CACHE_IN=$C PANEL_IN=$P FEA_OUT=/workspace/data/wide_fea_v2holefix.npy META_OUT=/workspace/data/wide_fea_v2holefix_meta.npz /workspace/venv/bin/python pod_fea_ext.py >> $L 2>&1 || { say "STEP2_FAIL"; exit 1; }
say "STEP3 dlw targets"
DLWT_CACHE=$C DLWT_PANEL=$P DLWT_OUT=/workspace/dlw_holefix /workspace/venv/bin/python pod_dlw_targets_ext.py >> $L 2>&1 || { say "STEP3_FAIL"; exit 1; }
say "STEP4 dlw fea82"
F171_CACHE=$C F171_PANEL=$P F171_OUT=/workspace/dlw_holefix /workspace/venv/bin/python pod_dlw_features_ext.py >> $L 2>&1 || { say "STEP4_FAIL"; exit 1; }
say "STEP5 f8 fea89"
F8_DLW=/workspace/dlw_holefix F8_CACHE=$C F8_OUT=/workspace/f8_holefix /workspace/venv/bin/python pod_f8_build_ext.py build >> $L 2>&1 || { say "STEP5_FAIL"; exit 1; }
say "CHAIN2_DONE"
