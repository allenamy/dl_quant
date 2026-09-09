#!/bin/bash
# CORRECTED chain (independent review 9954c158 item 3). Panel lineage is now taken from each artifact's own
# provenance, NOT from the script default:
#   DL side  (dlw targets + fea82) : PANEL = wide_panel_4h_v3splice.npz   (dlw_*_report.json panel_sha256 c5d10f6a)
#   king side(pod_fea_ext)         : PANEL = v2 lineage                    (determined by reproduction: 28,587/28,587
#                                    cells finite only in v2ext are finite in wide_fea_v2ext.npy -> v2ext, not v3splice)
# CACHE = holefix everywhere. All outputs are NEW paths.
cd /workspace
C=/workspace/data/dlnative_5m_wide829_f16_holefix.npz
P_DL=/workspace/data/wide_panel_4h_v3splice.npz
P_KING=/workspace/data/wide_panel_4h_v2holefix.npz
L=/workspace/review_scratch/holefix_chain3.log
mkdir -p /workspace/dlw_hf2/data /workspace/dlw_hf2/results /workspace/f8_hf2/data /workspace/f8_hf2/results /workspace/f8_hf2/preds /workspace/f8_hf2/models
: > $L
say(){ echo "[$(date -u +%FT%TZ)] $*" >> $L; }
say "CHAIN3_START  cache=$C  P_DL=$P_DL  P_KING=$P_KING"
sha256sum $C $P_DL $P_KING >> $L 2>&1
say "STEP3 dlw targets (v3splice)"
DLWT_CACHE=$C DLWT_PANEL=$P_DL DLWT_OUT=/workspace/dlw_hf2 /workspace/venv/bin/python pod_dlw_targets_ext.py >> $L 2>&1 || { say "STEP3_FAIL"; exit 1; }
say "STEP4 dlw fea82 (v3splice)"
F171_CACHE=$C F171_PANEL=$P_DL F171_OUT=/workspace/dlw_hf2 /workspace/venv/bin/python pod_dlw_features_ext.py >> $L 2>&1 || { say "STEP4_FAIL"; exit 1; }
say "STEP5 f8 fea89"
F8_DLW=/workspace/dlw_hf2 F8_CACHE=$C F8_OUT=/workspace/f8_hf2 /workspace/venv/bin/python pod_f8_build_ext.py build >> $L 2>&1 || { say "STEP5_FAIL"; exit 1; }
say "CHAIN3_DONE"
