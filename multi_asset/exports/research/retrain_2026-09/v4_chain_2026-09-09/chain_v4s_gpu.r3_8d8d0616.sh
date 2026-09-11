#!/bin/bash
# chain_v4s_gpu.sh — PREREG_fea89_stable_trend G3: RAW x {42,2027} on f8_v4s (stable trend fea89), legs v4b, FIX7 20 folds; then merge.
# HARDENED 2026-09-09 (review b0a573a1 P1-PIPE): dispatches ONLY on a fresh PASS receipt of the G2 stable closure gate (input shas verified);
# every shard is waited on by PID and any non-zero rc aborts before merge; merge rc + MERGE_DONE marker checked; DONE only on success.
set -o pipefail; R=/workspace/review_scratch; . $R/chain_lib.sh; cd $R || exit 2; export MWF_ROOT=mwf_v4s
SH0=202501,202505,202509,202601,202605; SH1=202502,202506,202510,202602,202606; SH2=202503,202507,202511,202603,202607; SH3=202504,202508,202512,202604,202608
require_gate $R/v4_gates/G2_closure_stable.json fea_A=/workspace/f8_v4s/data/f8_fea89.npz fea_B=/workspace/f8_hf2s/data/f8_fea89.npz targets_A=/workspace/dlw_hf3/data/dlw_targets.npz targets_B=/workspace/dlw_hf2/data/dlw_targets.npz
for TS in "RAW 42" "RAW 2027"; do set -- $TS; T=$1; SD=$2
  say "F10 chain $T s$SD start (v4s: stable trend fea89, legs v4b)"
  run_shards launch_mwf_v4s.sh $T $SD || die "shards_${T}_s${SD}_rc_[$RCS]" 1
  $PY merge_mwf_v4s.py $T $SD > /workspace/f8_v4s/logs/merge_v4b_${T}_s${SD}.log 2>&1; rc=$?; say "merge v4s $T s$SD rc=$rc $(tail -1 /workspace/f8_v4s/logs/merge_v4b_${T}_s${SD}.log | cut -c1-80)"
  [ $rc -eq 0 ] || die "merge_${T}_s${SD}_rc_$rc" 1; check_marker /workspace/f8_v4s/logs/merge_v4b_${T}_s${SD}.log "MERGE_DONE"
done
say "CHAIN_V4S_GPU_DONE (all shards rc=0, merges rc=0 + MERGE_DONE)"
