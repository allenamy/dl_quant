#!/bin/bash
# R6 EXTEND chain. Every step runs the ORIGINAL builder unmodified where one exists, with env passed EXPLICITLY
# (E-0826-D: never rely on a default). Any non-zero rc halts the chain (no partial lineage, PREREG §6.3).
set -o pipefail
PY=/workspace/venv/bin/python
R6=/workspace/uplift_2026-09-11/r6
OUT=$R6/out; LOG=$R6/logs
mkdir -p $OUT $LOG
CACHE_X=/workspace/data/dlnative_5m_wide829_f16_holefix2_x0910.npz
say(){ echo "[$(date -u +%H:%M:%SZ)] $*" | tee -a $LOG/chain.log; }
die(){ say "CHAIN_FAIL $1"; exit ${2:-1}; }

# ---- frozen effective env (PREREG §7.1) ----
export CAL=log MEMBERS_TOPN=829 LEGS=101 PHI=0.45 LOOK=900 WRULE=msharpe
say "R6_CHAIN_START"

say "S3 GATE BW-1 (bitwise, re-read from the written file)"
R6_OUT=$CACHE_X $PY $R6/r6_bw1_gate.py > $LOG/s3_bw1.log 2>&1; rc=$?
tail -30 $LOG/s3_bw1.log | tee -a $LOG/chain.log
[ $rc -eq 0 ] || die s3_bw1_RED 3

say "S4 4h panel raw build on the extended cache (pod_panel_ext.py UNMODIFIED; X3 parity self-check inside)"
CACHE_IN=$CACHE_X PANEL_OUT=$OUT/wide_panel_4h_rawbuild_x0910.npz \
  $PY /workspace/pod_panel_ext.py > $LOG/s4_panel.log 2>&1 || die s4_panel
grep -E "^parity |PANEL_EXT_DONE|PANEL_EXT_PARITY_FAIL" $LOG/s4_panel.log | tee -a $LOG/chain.log

say "S5a panel splice -> v2ext_x0910 (king feature panel)"
R6_BASE_PANEL=/workspace/data/wide_panel_4h_v2ext.npz R6_RAWBUILD=$OUT/wide_panel_4h_rawbuild_x0910.npz \
 R6_PANEL_OUT=$OUT/wide_panel_4h_v2ext_x0910.npz EMA_STATE_JSON=$OUT/fund_state_canoncont_v2ext_x0910.json \
  $PY $R6/r6_panel_splice.py > $LOG/s5a_splice_v2ext.log 2>&1 || die s5a_splice
tail -6 $LOG/s5a_splice_v2ext.log | tee -a $LOG/chain.log

say "S5b panel splice -> v3splice_x0910 (DL targets + legs panel)"
R6_BASE_PANEL=/workspace/data/wide_panel_4h_v3splice.npz R6_RAWBUILD=$OUT/wide_panel_4h_rawbuild_x0910.npz \
 R6_PANEL_OUT=$OUT/wide_panel_4h_v3splice_x0910.npz EMA_STATE_JSON=$OUT/fund_state_canoncont_v3splice_x0910.json \
  $PY $R6/r6_panel_splice.py > $LOG/s5b_splice_v3.log 2>&1 || die s5b_splice
tail -6 $LOG/s5b_splice_v3.log | tee -a $LOG/chain.log

say "S6 king v4 features (pod_fea_ext_clamp.py UNMODIFIED, PANEL_IN=v2ext_x0910 — NOT pod_fea_ext.py, E-0909-A)"
CACHE_IN=$CACHE_X PANEL_IN=$OUT/wide_panel_4h_v2ext_x0910.npz \
 FEA_OUT=$OUT/wide_fea_v4_x0910.npy META_OUT=$OUT/wide_fea_v4_meta_x0910.npz \
  $PY /workspace/review_scratch/pod_fea_ext_clamp.py > $LOG/s6_king_fea.log 2>&1 || die s6_king_fea
grep -E "anchors |NF = |FEA_EXT_DONE" $LOG/s6_king_fea.log | tee -a $LOG/chain.log

say "S7 extend the E-0908-B raw-return patch onto the new rows"
R6_OUT=$CACHE_X R6_RAW_PATCH=$OUT/raw_patch_x0910.npz $PY $R6/r6_raw_patch_ext.py > $LOG/s7_rawpatch.log 2>&1 || die s7_rawpatch
tail -3 $LOG/s7_rawpatch.log | tee -a $LOG/chain.log

say "S8 DL targets RAW (pod_dlw_targets_raw.py UNMODIFIED, y4s = prod(1+r)-1, RET_CH=0 + raw patch)"
DLWT_CACHE=$CACHE_X DLWT_PANEL=$OUT/wide_panel_4h_v3splice_x0910.npz DLWT_OUT=$OUT/dlw_v4raw_x0910 \
 DLWT_RET_CH=0 DLWT_RAW_PATCH=$OUT/raw_patch_x0910.npz \
  $PY /workspace/review_scratch/pod_dlw_targets_raw.py > $LOG/s8_targets.log 2>&1 || die s8_targets
cp $OUT/dlw_v4raw_x0910/data/dlw_targets.npz $OUT/dlw_targets_x0910.npz || die s8_cp
cmp -s $OUT/dlw_v4raw_x0910/data/dlw_targets.npz $OUT/dlw_targets_x0910.npz || die s8_cp_verify
grep -E "anchors |TARGETS_DONE|对齐自检" $LOG/s8_targets.log | tee -a $LOG/chain.log

say "S9 GATES BW-3 / BW-4 / X4 / X5"
$PY $R6/r6_bw345_gate.py > $LOG/s9_bw345.log 2>&1; rc=$?
tail -40 $LOG/s9_bw345.log | tee -a $LOG/chain.log
say "S9 rc=$rc"

say "S10 king predictions forward from the pinned v4 booster"
R6_FEA=$OUT/wide_fea_v4_x0910.npy R6_META=$OUT/wide_fea_v4_meta_x0910.npz \
 R6_PRED_OUT=$OUT/SLOW_v4_x0910.npy $PY $R6/r6_king_pred.py > $LOG/s10_king_pred.log 2>&1 || die s10_king_pred
tail -6 $LOG/s10_king_pred.log | tee -a $LOG/chain.log

say "R6_CHAIN_DONE"

say "S11 legs (r6_legs_x0910.py = pod_legs_v4b.py with 2 input paths moved to env; formulas verbatim)"
LEGS_OLD=/workspace/f8_v4/data/f10v2_legs.npz LEGS_PANEL=$OUT/wide_panel_4h_v3splice_x0910.npz \
 LEGS_TG=$OUT/dlw_targets_x0910.npz LEGS_META=$OUT/wide_fea_v4_meta_x0910.npz \
 LEGS_PRED=$OUT/SLOW_v4_x0910.npy LEGS_OUT=$OUT/f10v2_legs_x0910.npz \
  $PY $R6/r6_legs_x0910.py > $LOG/s11_legs.log 2>&1 || die s11_legs
tail -5 $LOG/s11_legs.log | tee -a $LOG/chain.log

say "S12 dlw fea82 on the extended chain (pod_dlw_features_ext.py UNMODIFIED)"
F171_CACHE=$CACHE_X F171_PANEL=$OUT/wide_panel_4h_v3splice_x0910.npz F171_OUT=$OUT/dlw_hf3_x0910 \
  $PY /workspace/pod_dlw_features_ext.py > $LOG/s12_fea82.log 2>&1 || die s12_fea82
tail -4 $LOG/s12_fea82.log | tee -a $LOG/chain.log

say "S13 f8 fea89 on the extended chain (pod_f8_build_ext.py UNMODIFIED)"
F8_DLW=$OUT/dlw_hf3_x0910 F8_CACHE=$CACHE_X F8_OUT=$OUT/f8_v4_x0910 \
  $PY /workspace/pod_f8_build_ext.py build > $LOG/s13_fea89.log 2>&1 || die s13_fea89
tail -4 $LOG/s13_fea89.log | tee -a $LOG/chain.log

say "R6_CHAIN_FULL_DONE"

say "S11b legs WHITELIST repair variant (5 dead anchors 2026-08-31 04Z..20Z), built BESIDE the verbatim one"
REP_SRC=$OUT/f10v2_legs_x0910.npz REP_PANEL=$OUT/wide_panel_4h_v3splice_x0910.npz REP_TG=$OUT/dlw_targets_x0910.npz \
 REP_PRED=$OUT/SLOW_v4_x0910.npy REP_META=$OUT/wide_fea_v4_meta_x0910.npz REP_OUT=$OUT/f10v2_legs_x0910_repair5.npz \
  $PY $R6/r6_legs_repair5.py > $LOG/s11b_legs_repair.log 2>&1 || echo "S11b FAILED (non-fatal, variant only)" | tee -a $LOG/chain.log
tail -8 $LOG/s11b_legs_repair.log | tee -a $LOG/chain.log

say "S14 extended replay tree dev_v4_x0910 (device-compatible layout; DL FPRED NaN on the new anchors = the visible gap)"
$PY $R6/r6_dev_tree.py > $LOG/s14_devtree.log 2>&1 || echo "S14 FAILED" | tee -a $LOG/chain.log
tail -8 $LOG/s14_devtree.log | tee -a $LOG/chain.log
say "R6_ALL_DONE"
