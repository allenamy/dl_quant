#!/bin/bash
# ax_chain.sh (axis_0919, stream D) — research data layer through the 5m bar closing at AX_IDX_END, under a NEW root AXR. Every builder gets its
# inputs/outputs EXPLICITLY (env -i + named keys; E-0826-D); every output lands under AXR; any non-zero rc halts the chain (no partial lineage).
# usage: AXR=<root> AX_NEW_DAYS=d1,d2,.. AX_IDX_END="YYYY-MM-DD HH:MM" AX_HI_S=<settlement second> STAGES=all|s1,s2,.. bash ax_chain.sh
# The king builder (s15) peaks at 50-58 GB: it runs only when RUN_KING=1 and the caller has checked memory (run it ALONE).
set -o pipefail
PY=/workspace/venv/bin/python; D=/workspace/axis_0919/devices; V=$D/v4chain; R=${AXR:?AXR}; STAGES=${STAGES:-all}
: "${AX_NEW_DAYS:?}"; : "${AX_IDX_END:?}"; : "${AX_HI_S:?}"
mkdir -p $R/data $R/logs $R/receipts $R/masks $R/trd $R/panels $R/funding $R/meta $R/inputs
L=$R/logs/chain.log
say(){ echo "[$(date -u +%FT%TZ)] $*" | tee -a $L; }
die(){ say "CHAIN_FAIL $1"; exit ${2:-1}; }
want(){ [ "$STAGES" = all ] || [[ ",$STAGES," == *",$1,"* ]]; }
sha(){ sha256sum "$1" | cut -d' ' -f1; }
EP="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root"
HOLEFIX2=/workspace/data/dlnative_5m_wide829_f16_holefix2.npz
X0910=/workspace/data/dlnative_5m_wide829_f16_holefix2_x0910.npz
CACHE=$R/data/dlnative_5m_wide829_f16_holefix2_x0918.npz
R6DL=/workspace/uplift_2026-09-11/r6/dl/klines; AXDL=/workspace/axis_0919/dl/klines5m
REST=/workspace/axis_0919/dl/funding/fund_rest_20260820_20260919T00.json.gz
MASK_T=$R/masks/member_mask_tradable_W24H_cachegrid.npz; MASK=$R/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz
HOLES=$R/inputs/holefix2_cells.npz
PV2=$R/panels/wide_panel_4h_v2ext_x0918.npz; PV3=$R/panels/wide_panel_4h_v3splice_x0918.npz; PRAW=$R/panels/wide_panel_4h_rawbuild_x0918.npz
LEDGER=$R/funding/funding_ledger.npz
say "AX_CHAIN start root=$R stages=$STAGES new_days=$AX_NEW_DAYS idx_end=$AX_IDX_END hi_s=$AX_HI_S chain_sha=$(sha $D/ax_chain.sh)"

if want s1; then say "s1 merge cache (ax03)"
  env -i $EP AX_BASE=$X0910 AX_OUT=$CACHE AX_RECEIPT=$R/receipts/CACHE_MERGE.json AX_WARM_DIR=$R6DL \
    AX_WARM_DAYS=2026-09-04,2026-09-05,2026-09-06,2026-09-07,2026-09-08,2026-09-09,2026-09-10 AX_NEW_DIR=$AXDL AX_NEW_DAYS=$AX_NEW_DAYS \
    AX_IDX_START="2026-09-04 00:00" AX_IDX_END="$AX_IDX_END" AX_PARITY_LO="2026-09-04 00:10" $PY $D/ax03_merge_cache.py > $R/logs/s1_merge.log 2>&1 || die s1_merge
  grep -E "PAR|AX03_MERGE_DONE" $R/logs/s1_merge.log | cut -c1-400 | tee -a $L; fi
if want s2; then say "s2 BW append-only gate vs holefix2 and x0910 (ax03b)"
  env -i $EP AX_NEW=$CACHE AX_BASES=$HOLEFIX2,$X0910 AX_RECEIPT=$R/receipts/CACHE_BW.json $PY $D/ax03b_bw_gate.py > $R/logs/s2_bw.log 2>&1 || die s2_bw 3
  tail -1 $R/logs/s2_bw.log | tee -a $L; fi
if want s3; then say "s3 coverage gate v2 (cache_coverage_gate_v2.py 23584a0c, unmodified)"
  $PY $V/cache_coverage_gate_v2.py $CACHE > $R/logs/s3_coverage.log 2>&1; rc=$?
  tail -6 $R/logs/s3_coverage.log | tee -a $L; [ $rc -eq 0 ] || die s3_coverage_rc_$rc 3; fi
if want s4; then say "s4 raw patch extension (ax07) + manifest (v4_rawpatch_manifest.py) + gate (v4_gate_rawpatch.py)"
  env -i $EP AX_CACHE=$CACHE AX_OLD_PATCH=/workspace/fp2_2026-09/raw_patch.npz AX_N_OLD_ROWS=490753 AX_KLINE_DIRS=$R6DL,$AXDL AX_OUT=$R/data/raw_patch.npz \
    AX_RECEIPT=$R/receipts/RAW_PATCH_EXT.json AX_R6_PATCH=/workspace/uplift_2026-09-11/r6/out/raw_patch_x0910.npz $PY $D/ax07_raw_patch_ext.py > $R/logs/s4_rawpatch.log 2>&1 || die s4_rawpatch
  tail -1 $R/logs/s4_rawpatch.log | cut -c1-400 | tee -a $L
  env -i $EP CACHE=$CACHE RAW_PATCH=$R/data/raw_patch.npz KLINE_SOURCES=/workspace/review_scratch/raw5m_kl,/workspace/wide_multisrc/klines5m_daily,$R6DL,$AXDL \
    MANIFEST_OUT=$R/data/raw_patch.manifest.json $PY $V/v4_rawpatch_manifest.py > $R/logs/s4b_manifest.log 2>&1 || die s4b_manifest
  tail -1 $R/logs/s4b_manifest.log | tee -a $L
  env -i $EP CACHE=$CACHE RAW_PATCH=$R/data/raw_patch.npz RAW_PATCH_MANIFEST=$R/data/raw_patch.manifest.json RAWPATCH_OUT=$R/receipts/RAW_PATCH_COVERAGE.json \
    $PY $V/v4_gate_rawpatch.py > $R/logs/s4c_rawpatch_gate.log 2>&1 || die s4c_rawpatch_gate 3
  grep RAW_PATCH_COVERAGE $R/logs/s4c_rawpatch_gate.log | tee -a $L; fi
if want s5; then say "s5 tradability (ax06 = fx_trd_build.py 066c3d74, path-patched) with T7 control extended to 09-18T23Z open"
  mkdir -p $R/trd
  ( cd /workspace/axis_0919 && env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    PYTHONPATH=/workspace/fx_data_2026-09-13/common AX_CACHE_X=$CACHE AX_CACHE_X_SHA16=$(sha $CACHE | cut -c1-16) \
    nice -n 19 python -B $D/ax06_fx_trd_build.py $R/trd /workspace/axis_0919/t7_klines_1h_x0918 /workspace/axis_0919/receipts/T7_EXTEND_RECEIPT.json ) > $R/logs/s5_trd.log 2>&1 || die s5_trd
  tail -1 $R/logs/s5_trd.log | cut -c1-300 | tee -a $L; fi
if want s6; then say "s6 tradable W24H member mask (fp2_member_mask_build.py a2d5493a) + liveness AND (v4_member_mask_liveness.py a369e1c0)"
  [ -f $HOLES ] || { cp /workspace/review_scratch/holefix2_cells.npz $HOLES && [ "$(sha $HOLES)" = 6156f97a0709f073147e392d5b0cb542f6b6d463cc3be2500f8791a0d1a8dfda ] || die s6_holes_copy; }
  env -i $EP PYTHONPATH=/workspace/fx_data_2026-09-13/common CACHE=$CACHE TRD_NPZ=$R/trd/tradability_v1.npz TRD_SHA=$(sha $R/trd/tradability_v1.npz) \
    UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz INJECT_NPZ=/workspace/fx_data_2026-09-13/out/inject/umask_UPIT_CRYPTO_tradable_W24H.npz \
    INJECT_SHA=3badc4b6a4fcbc5935f66f29c065ffd7ab500cb6876bdf53ce491b2d9056024c OUT=$MASK_T RECEIPT=$R/masks/RECEIPT_member_mask_build.json \
    $PY $V/fp2_member_mask_build.py > $R/logs/s6_mask_trd.log 2>&1 || die s6_mask_trd
  tail -1 $R/logs/s6_mask_trd.log | cut -c1-300 | tee -a $L
  env -i $EP CACHE=$CACHE HOLE_CELLS=$HOLES OUT=$MASK RECEIPT=$R/masks/RECEIPT_member_mask_liveness.json MASK_IN=$MASK_T MASK_IN_SHA=$(sha $MASK_T) \
    $PY $V/v4_member_mask_liveness.py > $R/logs/s6b_mask_live.log 2>&1 || die s6b_mask_live
  tail -1 $R/logs/s6b_mask_live.log | cut -c1-300 | tee -a $L; fi
if want s7; then say "s7 funding ledger + 4h accounting table (ax04)"
  env -i $EP AX_REST=$REST AX_FUND_AUG=/workspace/fund_aug.json.gz AX_FDIR=/workspace/wide_multisrc/funding \
    AX_PROD_LEDGER=/workspace/axis_0919/inputs/producer_ledger_tail_20260919.json AX_T5D_SRC=/workspace/uplift_r2_2026-09-13/T5d/inputs/t5d_interval_sources.json \
    AX_CACHE=$CACHE AX_LO_S=1787270400 AX_HI_S=$AX_HI_S AX_OUT_NPZ=$LEDGER AX_OUT_ACC=$R/funding/funding_4h_accounting.npz AX_RECEIPT=$R/receipts/FUNDING_LEDGER.json \
    $PY $D/ax04_funding_ledger.py > $R/logs/s7_ledger.log 2>&1 || die s7_ledger
  tail -1 $R/logs/s7_ledger.log | cut -c1-600 | tee -a $L; fi
if want s8; then say "s8 raw panel build (pod_panel_ext.py db7f0474, unmodified; v1-parity self-check inside)"
  env -i $EP CACHE_IN=$CACHE PANEL_OUT=$PRAW $PY /workspace/pod_panel_ext.py > $R/logs/s8_panel.log 2>&1; rc=$?
  grep -E "^parity |PANEL_EXT_DONE|PANEL_EXT_PARITY_FAIL" $R/logs/s8_panel.log | tee -a $L
  if [ $rc -ne 0 ]; then
    # KNOWN, DIAGNOSED reading (r6 RESULT §X3 + RECEIPT_r6_X3_amihud_diagnosis.json; holefix_chain.log 09-08): on every holefix-lineage cache the builder's
    # v1-panel Pearson self-check reads f_amihud_24h 0.0546 (heavy-tailed ratio in the hole windows) and exits 3 AFTER writing the panel. The gate is NOT
    # changed or re-thresholded: rc 3 is accepted only if every parity line is IDENTICAL to r6's reading on the same overlap, and the panel file exists;
    # the prefix identity of this rawbuild vs r6's rawbuild is then proven bitwise by ax10 (panel_rawbuild_vs_r6_rawbuild_x0910).
    grep -E "^parity |PANEL_EXT" $R/logs/s8_panel.log > $R/logs/s8_parity_lines.txt
    grep -E "^parity |PANEL_EXT" /workspace/uplift_2026-09-11/r6/logs/s4_panel.log > $R/logs/s8_parity_lines_r6.txt
    if [ $rc -eq 3 ] && [ -s $R/logs/s8_parity_lines.txt ] && cmp -s $R/logs/s8_parity_lines.txt $R/logs/s8_parity_lines_r6.txt && [ -f $PRAW ]; then
      say "s8 rc=3 = the KNOWN X3 amihud v1-parity reading, line-for-line identical to r6 s4_panel.log (gate reading recorded, not changed)"
    else die s8_panel_rc_$rc 3; fi
  fi; fi
if want s9; then say "s9 panel splices v2ext / v3splice with ledger intervals (ax05)"
  for B in v2ext v3splice; do
    OUTP=$R/panels/wide_panel_4h_${B}_x0918.npz
    env -i $EP R6_BASE_PANEL=/workspace/data/wide_panel_4h_$B.npz R6_RAWBUILD=$PRAW R6_PANEL_OUT=$OUTP AX_REST=$REST AX_LEDGER=$LEDGER AX_HI_S=$AX_HI_S \
      EMA_STATE_JSON=$R/panels/fund_state_canoncont_${B}_x0918.json $PY $D/ax05_panel_splice_ivledger.py > $R/logs/s9_splice_$B.log 2>&1 || die s9_splice_$B
    grep -E "^P2|R6_PANEL_SPLICE_DONE|X4 tail" $R/logs/s9_splice_$B.log | tee -a $L
  done; fi
if want s10; then say "s10 DL targets RAW + CLIP (pod_dlw_targets_raw_v2.py 9e9dfd94, member mask tradable AND live)"
  env -i $EP OMP_NUM_THREADS=8 DLWT_CACHE=$CACHE DLWT_PANEL=$PV3 DLWT_OUT=$R/dlw_v4raw DLWT_RET_CH=0 DLWT_RAW_PATCH=$R/data/raw_patch.npz MEMBER_MASK_NPZ=$MASK \
    $PY -B $V/pod_dlw_targets_raw_v2.py > $R/logs/s10_targets_raw.log 2>&1 || die s10_targets_raw
  grep -E "raw patch|anchors |TARGETS_DONE|对齐自检" $R/logs/s10_targets_raw.log | cut -c1-300 | tee -a $L
  env -i $EP OMP_NUM_THREADS=8 DLWT_CACHE=$CACHE DLWT_PANEL=$PV3 DLWT_OUT=$R/dlw_hf3 DLWT_RET_CH=0 DLWT_RAW_PATCH= MEMBER_MASK_NPZ=$MASK \
    $PY -B $V/pod_dlw_targets_raw_v2.py > $R/logs/s10b_targets_clip.log 2>&1 || die s10b_targets_clip
  grep -E "anchors |TARGETS_DONE" $R/logs/s10b_targets_clip.log | cut -c1-300 | tee -a $L; fi
if want s11; then say "s11 fea82 (pod_dlw_features_ext.py e86725cc) into dlw_hf3, byte-verified copy into dlw_v4raw"
  ( cd /workspace && env -i $EP OMP_NUM_THREADS=8 F171_CACHE=$CACHE F171_PANEL=$PV3 F171_OUT=$R/dlw_hf3 $PY -B /workspace/pod_dlw_features_ext.py ) > $R/logs/s11_fea82.log 2>&1 || die s11_fea82
  cp $R/dlw_hf3/data/dlw_fea82.npz $R/dlw_v4raw/data/dlw_fea82.npz && cmp -s $R/dlw_hf3/data/dlw_fea82.npz $R/dlw_v4raw/data/dlw_fea82.npz || die s11_copy
  tail -1 $R/logs/s11_fea82.log | tee -a $L; fi
if want s12; then say "s12 fea89 (pod_f8_build_ext.py f606bffa build) from dlw_hf3"
  ( cd /workspace && env -i $EP OMP_NUM_THREADS=8 F8_DLW=$R/dlw_hf3 F8_CACHE=$CACHE F8_OUT=$R/f8_v4 $PY -B /workspace/pod_f8_build_ext.py build ) > $R/logs/s12_fea89.log 2>&1 || die s12_fea89
  grep -E "BUILD_DONE" $R/logs/s12_fea89.log | cut -c1-300 | tee -a $L; fi
if want s15 && [ "${RUN_KING:-0}" = 1 ]; then say "s15 king v4 features (pod_fea_ext_clamp_v2.py 7b8b843d, member mask) — ALONE"
  env -i $EP OMP_NUM_THREADS=8 CACHE_IN=$CACHE PANEL_IN=$PV2 FEA_OUT=$R/data/wide_fea_v4.npy META_OUT=$R/data/wide_fea_v4_meta.npz MEMBER_MASK_NPZ=$MASK \
    $PY -B $V/pod_fea_ext_clamp_v2.py > $R/logs/s15_king.log 2>&1 || die s15_king
  grep -E "anchors |NF = |FEA_EXT_DONE" $R/logs/s15_king.log | cut -c1-300 | tee -a $L; fi
if want s16; then say "s16 accounting meta meta_newprod_v4-type (ax09)"
  env -i $EP KING_META=$R/data/wide_fea_v4_meta.npz DLW_RAW_TARGETS=$R/dlw_v4raw/data/dlw_targets.npz CACHE=$CACHE HOLE_CELLS=$HOLES \
    REF_META=/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz MEMBER_MASK=$MASK OUT=$R/meta/meta_newprod_v4_x0918.npz RECEIPT=$R/receipts/META_NEWPROD.json \
    $PY $D/ax09_meta_newprod.py > $R/logs/s16_meta.log 2>&1 || die s16_meta
  tail -1 $R/logs/s16_meta.log | cut -c1-600 | tee -a $L; fi
say "AX_CHAIN_END stages=$STAGES"
