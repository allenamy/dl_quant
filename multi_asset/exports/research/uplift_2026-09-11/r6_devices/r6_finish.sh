#!/bin/bash
set -o pipefail
PY=/workspace/venv/bin/python
R6=/workspace/uplift_2026-09-11/r6; OUT=$R6/out; LOG=$R6/logs
CACHE_X=/workspace/data/dlnative_5m_wide829_f16_holefix2_x0910.npz
say(){ echo "[$(date -u +%H:%M:%SZ)] $*" | tee -a $LOG/chain.log; }
say "S12 retry: pod_dlw_features_ext.py reads {F171_OUT}/data/dlw_targets.npz (its own dir) -> stage the extended targets there first"
mkdir -p $OUT/dlw_hf3_x0910/data $OUT/dlw_hf3_x0910/results
cp $OUT/dlw_targets_x0910.npz $OUT/dlw_hf3_x0910/data/dlw_targets.npz || exit 1
cmp -s $OUT/dlw_targets_x0910.npz $OUT/dlw_hf3_x0910/data/dlw_targets.npz || exit 1
F171_CACHE=$CACHE_X F171_PANEL=$OUT/wide_panel_4h_v3splice_x0910.npz F171_OUT=$OUT/dlw_hf3_x0910 \
  $PY /workspace/pod_dlw_features_ext.py > $LOG/s12_fea82.log 2>&1 || { say "S12 FAIL"; tail -5 $LOG/s12_fea82.log | tee -a $LOG/chain.log; exit 1; }
tail -3 $LOG/s12_fea82.log | tee -a $LOG/chain.log
say "S13 f8 fea89"
F8_DLW=$OUT/dlw_hf3_x0910 F8_CACHE=$CACHE_X F8_OUT=$OUT/f8_v4_x0910 \
  $PY /workspace/pod_f8_build_ext.py build > $LOG/s13_fea89.log 2>&1 || { say "S13 FAIL"; tail -5 $LOG/s13_fea89.log | tee -a $LOG/chain.log; }
tail -3 $LOG/s13_fea89.log | tee -a $LOG/chain.log
say "S11b legs whitelist repair variant"
REP_SRC=$OUT/f10v2_legs_x0910.npz REP_PANEL=$OUT/wide_panel_4h_v3splice_x0910.npz REP_TG=$OUT/dlw_targets_x0910.npz \
 REP_PRED=$OUT/SLOW_v4_x0910.npy REP_META=$OUT/wide_fea_v4_meta_x0910.npz REP_OUT=$OUT/f10v2_legs_x0910_repair5.npz \
  $PY $R6/r6_legs_repair5.py > $LOG/s11b.log 2>&1 || say "S11b FAIL"
tail -7 $LOG/s11b.log | tee -a $LOG/chain.log
say "S14 extended replay tree"
$PY $R6/r6_dev_tree.py > $LOG/s14.log 2>&1 || say "S14 FAIL"
tail -8 $LOG/s14.log | tee -a $LOG/chain.log
say "S15 manifest"
$PY $R6/r6_manifest.py > $LOG/s15_manifest.log 2>&1 || say "S15 FAIL"
say "R6_FINISH_DONE"
