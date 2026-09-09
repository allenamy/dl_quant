#!/bin/bash
# chain_v4_gpu3.sh — AMENDMENT 5 rerun of all four F10 chains with legs v4b (in-service legs policy). MWF_ROOT=mwf_v4b.
# HARDENED 2026-09-09 (review b0a573a1 P1-PIPE): dispatches ONLY on fresh PASS receipts of STEP1 (DL side) and STEP2 (king side) gates with
# verified input shas; shard rcs collected by PID; merge rc + MERGE_DONE marker checked; DONE only on success.
set -o pipefail; R=/workspace/review_scratch; . $R/chain_lib.sh; cd $R || exit 2; export MWF_ROOT=mwf_v4b
SH0=202501,202505,202509,202601,202605; SH1=202502,202506,202510,202602,202606; SH2=202503,202507,202511,202603,202607; SH3=202504,202508,202512,202604,202608
require_gate $R/v4_gates/step1.json dlw_v4raw_targets=/workspace/dlw_v4raw/data/dlw_targets.npz dlw_hf3_targets=/workspace/dlw_hf3/data/dlw_targets.npz fea82_v4raw=/workspace/dlw_v4raw/data/dlw_fea82.npz fea89_f8v4=/workspace/f8_v4/data/f8_fea89.npz
require_gate $R/v4_gates/step2.json wide_fea_v4=/workspace/data/wide_fea_v4.npy wide_fea_v4_meta=/workspace/data/wide_fea_v4_meta.npz
[ -f /workspace/f8_v4/data/f10v2_legs.npz ] || die "legs_v4b_missing" 3
for TS in "RAW 42" "RAW 2027" "CLIP 42" "CLIP 2027"; do set -- $TS; T=$1; SD=$2
  say "F10 chain $T s$SD start (gpu3, legs v4b)"
  run_shards launch_mwf_v4b.sh $T $SD || die "shards_${T}_s${SD}_rc_[$RCS]" 1
  $PY merge_mwf_v4b.py $T $SD > /workspace/f8_v4/logs/merge_v4b_${T}_s${SD}.log 2>&1; rc=$?; say "merge v4b $T s$SD rc=$rc $(tail -1 /workspace/f8_v4/logs/merge_v4b_${T}_s${SD}.log | cut -c1-80)"
  [ $rc -eq 0 ] || die "merge_${T}_s${SD}_rc_$rc" 1; check_marker /workspace/f8_v4/logs/merge_v4b_${T}_s${SD}.log "MERGE_DONE"
done
say "CHAIN_V4_GPU3_DONE (all shards rc=0, merges rc=0 + MERGE_DONE)"
