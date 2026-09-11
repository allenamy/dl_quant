#!/bin/bash
# chain_v4_data.sh — v4 data chain on holefix2: RAW targets -> fea82 (into dlw_hf3) -> copy fea82 to dlw_v4raw -> fea89 -> king v4 features (clamp).
# ROUND 3 (review 31fa3e4e §2, 2026-09-10): every step's rc AND every copy is checked (the two bare `cp` used to be unchecked, so a missing
# fea82 source still produced CHAIN_V4_DATA_DONE); the copied file is verified byte-equal to its source; DATA_DONE is written only after
# every producer and every copy succeeded. Failures write FAIL_<step> to the log and exit non-zero (chain_lib die).
set -o pipefail; R=/workspace/review_scratch; L=$R/chain_v4_data.log; : > $L; . $R/chain_lib.sh; cd /workspace || exit 2
C=/workspace/data/dlnative_5m_wide829_f16_holefix2.npz; P=/workspace/data/wide_panel_4h_v3splice.npz
mkdir -p /workspace/dlw_v4raw/data /workspace/dlw_v4raw/results /workspace/f8_v4/data /workspace/f8_v4/results /workspace/f8_v4/preds /workspace/f8_v4/models || die "mkdir" 1
say "targets RAW on holefix2"; DLWT_CACHE=$C DLWT_PANEL=$P DLWT_OUT=/workspace/dlw_v4raw DLWT_RET_CH=0 DLWT_RAW_PATCH=$R/raw_patch.npz $PY $R/pod_dlw_targets_raw.py >> $L 2>&1 || die "targets_raw" 1
[ -f /workspace/dlw_v4raw/data/dlw_targets.npz ] || die "targets_raw_output_missing" 1
say "fea82 on holefix2 (into dlw_hf3 = CLIP dir)"; F171_CACHE=$C F171_PANEL=$P F171_OUT=/workspace/dlw_hf3 $PY pod_dlw_features_ext.py >> $L 2>&1 || die "fea82" 1
[ -f /workspace/dlw_hf3/data/dlw_fea82.npz ] || die "fea82_output_missing" 1
cp /workspace/dlw_hf3/data/dlw_fea82.npz /workspace/dlw_v4raw/data/dlw_fea82.npz || die "cp_fea82_to_v4raw" 1
cmp -s /workspace/dlw_hf3/data/dlw_fea82.npz /workspace/dlw_v4raw/data/dlw_fea82.npz || die "cp_fea82_verify_mismatch" 1
if [ -f /workspace/dlw_hf3/results/dlw_features_report.json ]; then
  cp /workspace/dlw_hf3/results/dlw_features_report.json /workspace/dlw_v4raw/results/ || die "cp_fea82_report" 1
else
  say "fea82 report absent at /workspace/dlw_hf3/results/dlw_features_report.json (optional artefact, not copied)"
fi
say "f8 fea89 on holefix2"; F8_DLW=/workspace/dlw_hf3 F8_CACHE=$C F8_OUT=/workspace/f8_v4 $PY pod_f8_build_ext.py build >> $L 2>&1 || die "fea89" 1
[ -f /workspace/f8_v4/data/f8_fea89.npz ] || die "fea89_output_missing" 1
say "king v4 features (clamp) on holefix2"; CACHE_IN=$C PANEL_IN=/workspace/data/wide_panel_4h_v2ext.npz FEA_OUT=/workspace/data/wide_fea_v4.npy META_OUT=/workspace/data/wide_fea_v4_meta.npz $PY $R/pod_fea_ext_clamp.py >> $L 2>&1 || die "king_fea" 1
[ -f /workspace/data/wide_fea_v4.npy ] && [ -f /workspace/data/wide_fea_v4_meta.npz ] || die "king_fea_output_missing" 1
say CHAIN_V4_DATA_DONE
