#!/bin/bash
# ax_chain_r.sh (axis_0919, variant x0918r) — downstream rebuild on the corrected cache (08-31 from the official daily archives, ax13) and the corrected
# hole-cell list. Root RR=/workspace/axis_0919/x0918r; x0918 files (root /workspace/axis_0919) are READ ONLY. Every builder = the same file (sha) the x0918
# chain used, same explicit env; heavy builders start only through ax_memguard.py (lead rule 2026-09-19, shared pod memory). Any non-zero rc halts.
# Panels are NOT rebuilt: stage r6 proves the panel builder's output on x0918r is array-identical to x0918's rawbuild, and the splice reads nothing else
# from the cache; the x0918 v2ext/v3splice panels are then the x0918r panels (paths recorded).
set -o pipefail
PY=/workspace/venv/bin/python; D=/workspace/axis_0919/devices; V=$D/v4chain; X=/workspace/axis_0919; RR=$X/x0918r; STAGES=${STAGES:-all}
mkdir -p $RR/data $RR/logs $RR/receipts $RR/masks $RR/trd $RR/panels $RR/meta $RR/inputs
L=$RR/logs/chain_r.log
say(){ echo "[$(date -u +%FT%TZ)] $*" | tee -a $L; }
die(){ say "CHAIN_R_FAIL $1"; exit ${2:-1}; }
want(){ [ "$STAGES" = all ] || [[ ",$STAGES," == *",$1,"* ]]; }
sha(){ sha256sum "$1" | cut -d' ' -f1; }
EP="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root"
MG="$PY $D/ax_memguard.py"
CACHE=$RR/data/dlnative_5m_wide829_f16_holefix2_x0918r.npz; HOLES=$RR/inputs/holefix2r_cells_x0918r.npz
MASK_T=$RR/masks/member_mask_tradable_W24H_cachegrid.npz; MASK=$RR/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz
PV2=$X/panels/wide_panel_4h_v2ext_x0918.npz; PV3=$X/panels/wide_panel_4h_v3splice_x0918.npz
[ -f $CACHE ] && [ -f $HOLES ] || die "r1_outputs_missing (run ax13 first)"
say "AX_CHAIN_R start stages=$STAGES chain_sha=$(sha $D/ax_chain_r.sh) cache=$(sha $CACHE | cut -c1-16) holes=$(sha $HOLES | cut -c1-16)"

if want r2; then say "r2 coverage gate v2 on x0918r (unmodified)"
  $PY $V/cache_coverage_gate_v2.py $CACHE > $RR/logs/r2_coverage.log 2>&1; rc=$?; tail -3 $RR/logs/r2_coverage.log | tee -a $L; [ $rc -eq 0 ] || die r2_coverage 3; fi
if want r3; then say "r3 raw patch: x0918 patch rows (959, byte copy) + manifest bound to the x0918r cache + coverage gate"
  cp $X/data/raw_patch.npz $RR/data/raw_patch.npz && cmp -s $X/data/raw_patch.npz $RR/data/raw_patch.npz || die r3_copy
  env -i $EP CACHE=$CACHE RAW_PATCH=$RR/data/raw_patch.npz KLINE_SOURCES=/workspace/review_scratch/raw5m_kl,/workspace/wide_multisrc/klines5m_daily,/workspace/uplift_2026-09-11/r6/dl/klines,$X/dl/klines5m \
    MANIFEST_OUT=$RR/data/raw_patch.manifest.json $PY $V/v4_rawpatch_manifest.py > $RR/logs/r3_manifest.log 2>&1 || die r3_manifest
  tail -1 $RR/logs/r3_manifest.log | tee -a $L
  env -i $EP CACHE=$CACHE RAW_PATCH=$RR/data/raw_patch.npz RAW_PATCH_MANIFEST=$RR/data/raw_patch.manifest.json RAWPATCH_OUT=$RR/receipts/RAW_PATCH_COVERAGE.json \
    $PY $V/v4_gate_rawpatch.py > $RR/logs/r3_gate.log 2>&1 || die r3_gate 3
  grep "RAW_PATCH_COVERAGE" $RR/logs/r3_gate.log | head -1 | tee -a $L; fi
if want r4; then say "r4 tradability (ax06 5c37ef49) on x0918r"
  ( cd $X && env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    PYTHONPATH=/workspace/fx_data_2026-09-13/common AX_CACHE_X=$CACHE AX_CACHE_X_SHA16=$(sha $CACHE | cut -c1-16) \
    nice -n 19 python -B $D/ax06_fx_trd_build.py $RR/trd $X/t7_klines_1h_x0918 $X/receipts/T7_EXTEND_RECEIPT.json ) > $RR/logs/r4_trd.log 2>&1 || die r4_trd
  tail -1 $RR/logs/r4_trd.log | cut -c1-300 | tee -a $L; fi
if want r5; then say "r5 masks: tradable W24H (fp2_member_mask_build a2d5493a) + liveness AND with the x0918r hole list (v4_member_mask_liveness a369e1c0)"
  env -i $EP PYTHONPATH=/workspace/fx_data_2026-09-13/common CACHE=$CACHE TRD_NPZ=$RR/trd/tradability_v1.npz TRD_SHA=$(sha $RR/trd/tradability_v1.npz) \
    UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz INJECT_NPZ=/workspace/fx_data_2026-09-13/out/inject/umask_UPIT_CRYPTO_tradable_W24H.npz \
    INJECT_SHA=3badc4b6a4fcbc5935f66f29c065ffd7ab500cb6876bdf53ce491b2d9056024c OUT=$MASK_T RECEIPT=$RR/masks/RECEIPT_member_mask_build.json \
    $PY $V/fp2_member_mask_build.py > $RR/logs/r5_mask_trd.log 2>&1 || die r5_mask_trd
  tail -1 $RR/logs/r5_mask_trd.log | cut -c1-200 | tee -a $L
  env -i $EP CACHE=$CACHE HOLE_CELLS=$HOLES OUT=$MASK RECEIPT=$RR/masks/RECEIPT_member_mask_liveness.json MASK_IN=$MASK_T MASK_IN_SHA=$(sha $MASK_T) \
    $PY $V/v4_member_mask_liveness.py > $RR/logs/r5b_mask_live.log 2>&1 || die r5b_mask_live
  tail -1 $RR/logs/r5b_mask_live.log | cut -c1-300 | tee -a $L; fi
if want r6; then say "r6 panel builder on x0918r (pod_panel_ext.py db7f0474) — proof input for reusing the x0918 panels"
  env -i $EP CACHE_IN=$CACHE PANEL_OUT=$RR/panels/wide_panel_4h_rawbuild_x0918r.npz $MG $RR/logs/mem_r6_panel.json 32 -- $PY /workspace/pod_panel_ext.py > $RR/logs/r6_panel.log 2>&1; rc=$?
  grep -E "^parity |PANEL_EXT" $RR/logs/r6_panel.log > $RR/logs/r6_parity_lines.txt
  if [ $rc -eq 3 ] && cmp -s $RR/logs/r6_parity_lines.txt $X/logs/s8_parity_lines.txt; then say "r6 rc=3 = the known X3 amihud reading, identical lines to x0918 s8"; elif [ $rc -ne 0 ]; then die r6_panel_rc_$rc 3; fi; fi
if want r7; then say "r7 DL targets RAW + CLIP (pod_dlw_targets_raw_v2.py 9e9dfd94) with the x0918r member mask"
  env -i $EP OMP_NUM_THREADS=8 DLWT_CACHE=$CACHE DLWT_PANEL=$PV3 DLWT_OUT=$RR/dlw_v4raw DLWT_RET_CH=0 DLWT_RAW_PATCH=$RR/data/raw_patch.npz MEMBER_MASK_NPZ=$MASK \
    $MG $RR/logs/mem_r7_targets_raw.json 28 -- $PY -B $V/pod_dlw_targets_raw_v2.py > $RR/logs/r7_targets_raw.log 2>&1 || die r7_targets_raw
  grep -E "anchors |TARGETS_DONE" $RR/logs/r7_targets_raw.log | cut -c1-250 | tee -a $L
  env -i $EP OMP_NUM_THREADS=8 DLWT_CACHE=$CACHE DLWT_PANEL=$PV3 DLWT_OUT=$RR/dlw_hf3 DLWT_RET_CH=0 DLWT_RAW_PATCH= MEMBER_MASK_NPZ=$MASK \
    $MG $RR/logs/mem_r7_targets_clip.json 28 -- $PY -B $V/pod_dlw_targets_raw_v2.py > $RR/logs/r7b_targets_clip.log 2>&1 || die r7b_targets_clip
  grep -E "anchors |TARGETS_DONE" $RR/logs/r7b_targets_clip.log | cut -c1-250 | tee -a $L; fi
if want r8; then say "r8 fea82 (e86725cc) + byte-verified copy; fea89 (f606bffa)"
  ( cd /workspace && env -i $EP OMP_NUM_THREADS=8 F171_CACHE=$CACHE F171_PANEL=$PV3 F171_OUT=$RR/dlw_hf3 $MG $RR/logs/mem_r8_fea82.json 19 -- $PY -B /workspace/pod_dlw_features_ext.py ) > $RR/logs/r8_fea82.log 2>&1 || die r8_fea82
  cp $RR/dlw_hf3/data/dlw_fea82.npz $RR/dlw_v4raw/data/dlw_fea82.npz && cmp -s $RR/dlw_hf3/data/dlw_fea82.npz $RR/dlw_v4raw/data/dlw_fea82.npz || die r8_copy
  tail -1 $RR/logs/r8_fea82.log | tee -a $L
  ( cd /workspace && env -i $EP OMP_NUM_THREADS=8 F8_DLW=$RR/dlw_hf3 F8_CACHE=$CACHE F8_OUT=$RR/f8_v4 $MG $RR/logs/mem_r8_fea89.json 27 -- $PY -B /workspace/pod_f8_build_ext.py build ) > $RR/logs/r8b_fea89.log 2>&1 || die r8b_fea89
  grep BUILD_DONE $RR/logs/r8b_fea89.log | cut -c1-200 | tee -a $L; fi
if want r9; then say "r9 king v4 features (pod_fea_ext_clamp_v2.py 7b8b843d) — memguard: ALONE (peak 50 GiB in a 56.8 GiB cgroup)"
  env -i $EP OMP_NUM_THREADS=8 CACHE_IN=$CACHE PANEL_IN=$PV2 FEA_OUT=$RR/data/wide_fea_v4.npy META_OUT=$RR/data/wide_fea_v4_meta.npz MEMBER_MASK_NPZ=$MASK \
    $MG $RR/logs/mem_r9_king.json 51 -- $PY -B $V/pod_fea_ext_clamp_v2.py > $RR/logs/r9_king.log 2>&1 || die r9_king
  grep -E "anchors |FEA_EXT_DONE" $RR/logs/r9_king.log | cut -c1-250 | tee -a $L; fi
if want r10; then say "r10 accounting meta (ax09) + truncation-aware member rule (ax09b)"
  env -i $EP KING_META=$RR/data/wide_fea_v4_meta.npz DLW_RAW_TARGETS=$RR/dlw_v4raw/data/dlw_targets.npz CACHE=$CACHE HOLE_CELLS=$HOLES \
    REF_META=/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz MEMBER_MASK=$MASK OUT=$RR/meta/meta_newprod_v4_x0918r.npz RECEIPT=$RR/receipts/META_NEWPROD.json \
    $PY $D/ax09_meta_newprod.py > $RR/logs/r10_meta.log 2>&1 || die r10_meta
  tail -1 $RR/logs/r10_meta.log | cut -c1-500 | tee -a $L
  env -i $EP META=$RR/meta/meta_newprod_v4_x0918r.npz REF_META=/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz CACHE=$CACHE HOLE_CELLS=$HOLES MEMBER_MASK=$MASK \
    GATE_LIB_DIR=$V RECEIPT=$RR/receipts/META_MEMBER_RULE.json $PY $D/ax09b_member_rule.py > $RR/logs/r10b_member_rule.log 2>&1 || die r10b_member_rule
  tail -1 $RR/logs/r10b_member_rule.log | cut -c1-500 | tee -a $L; fi
say "AX_CHAIN_R_END stages=$STAGES"
