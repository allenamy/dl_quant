#!/bin/bash
cd /workspace; L=/workspace/review_scratch/chain_v4_data.log; : > $L; say(){ echo "[$(date -u +%FT%TZ)] $*" >> $L; }
C=/workspace/data/dlnative_5m_wide829_f16_holefix2.npz; P=/workspace/data/wide_panel_4h_v3splice.npz
mkdir -p /workspace/dlw_v4raw/data /workspace/dlw_v4raw/results /workspace/f8_v4/data /workspace/f8_v4/results /workspace/f8_v4/preds /workspace/f8_v4/models
say "targets RAW on holefix2"; DLWT_CACHE=$C DLWT_PANEL=$P DLWT_OUT=/workspace/dlw_v4raw DLWT_RET_CH=0 DLWT_RAW_PATCH=/workspace/review_scratch/raw_patch.npz /workspace/venv/bin/python /workspace/review_scratch/pod_dlw_targets_raw.py >> $L 2>&1 || { say FAIL_targets_raw; exit 1; }
say "fea82 on holefix2 (into dlw_hf3 = CLIP dir)"; F171_CACHE=$C F171_PANEL=$P F171_OUT=/workspace/dlw_hf3 /workspace/venv/bin/python pod_dlw_features_ext.py >> $L 2>&1 || { say FAIL_fea82; exit 1; }
cp /workspace/dlw_hf3/data/dlw_fea82.npz /workspace/dlw_v4raw/data/dlw_fea82.npz; cp /workspace/dlw_hf3/results/dlw_features_report.json /workspace/dlw_v4raw/results/ 2>/dev/null
say "f8 fea89 on holefix2"; F8_DLW=/workspace/dlw_hf3 F8_CACHE=$C F8_OUT=/workspace/f8_v4 /workspace/venv/bin/python pod_f8_build_ext.py build >> $L 2>&1 || { say FAIL_fea89; exit 1; }
say "king v4 features (clamp) on holefix2"; CACHE_IN=$C PANEL_IN=/workspace/data/wide_panel_4h_v2ext.npz FEA_OUT=/workspace/data/wide_fea_v4.npy META_OUT=/workspace/data/wide_fea_v4_meta.npz /workspace/venv/bin/python /workspace/review_scratch/pod_fea_ext_clamp.py >> $L 2>&1 || { say FAIL_king_fea; exit 1; }
say CHAIN_V4_DATA_DONE
