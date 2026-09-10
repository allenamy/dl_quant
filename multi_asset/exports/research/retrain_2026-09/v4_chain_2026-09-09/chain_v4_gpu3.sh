#!/bin/bash
# chain_v4_gpu3.sh — AMENDMENT 5 rerun of all four F10 chains with legs v4b (in-service legs policy). MWF_ROOT=mwf_v4b.
# HARDENED 2026-09-09 (review b0a573a1 P1-PIPE): dispatches ONLY on fresh PASS receipts of STEP1 (DL side) and STEP2 (king side) gates with
# verified input shas; shard rcs collected by PID; merge rc + MERGE_DONE marker checked; DONE only on success.
# ROUND 3 (review 31fa3e4e §2, 2026-09-10): receipts are required BY NAME (gate=STEP1 / gate=STEP2); the RAW and CLIP targets both chains read
# are bound through STEP1; pin_deps records trainer / launcher / merge / chain_lib / legs / fea89 / targets / fea82 shas at dispatch.
# ROUND 4 (2026-09-10): receipts are required with self_sha= of $R/v4_gate_step1.py / $R/v4_gate_step2.py computed at run time (gate_sha).
set -o pipefail; R=/workspace/review_scratch; . $R/chain_lib.sh; cd $R || exit 2; export MWF_ROOT=mwf_v4b
SH0=202501,202505,202509,202601,202605; SH1=202502,202506,202510,202602,202606; SH2=202503,202507,202511,202603,202607; SH3=202504,202508,202512,202604,202608
S1_SRC=$(gate_sha $R/v4_gate_step1.py) || die "gate_source_unreadable_v4_gate_step1" 3
S2_SRC=$(gate_sha $R/v4_gate_step2.py) || die "gate_source_unreadable_v4_gate_step2" 3
require_gate $R/v4_gates/step1.json gate=STEP1 self_sha=$S1_SRC dlw_v4raw_targets=/workspace/dlw_v4raw/data/dlw_targets.npz dlw_hf3_targets=/workspace/dlw_hf3/data/dlw_targets.npz fea82_v4raw=/workspace/dlw_v4raw/data/dlw_fea82.npz fea89_f8v4=/workspace/f8_v4/data/f8_fea89.npz
require_gate $R/v4_gates/step2.json gate=STEP2 self_sha=$S2_SRC wide_fea_v4=/workspace/data/wide_fea_v4.npy wide_fea_v4_meta=/workspace/data/wide_fea_v4_meta.npz
[ -f /workspace/f8_v4/data/f10v2_legs.npz ] || die "legs_v4b_missing" 3
pin_deps v4_gpu3 $R/pod_f10_train_monthly_v4.py $R/launch_mwf_v4b.sh $R/merge_mwf_v4b.py $R/chain_lib.sh /workspace/f8_v4/data/f10v2_legs.npz /workspace/f8_v4/data/f8_fea89.npz /workspace/dlw_v4raw/data/dlw_targets.npz /workspace/dlw_hf3/data/dlw_targets.npz /workspace/dlw_v4raw/data/dlw_fea82.npz
for TS in "RAW 42" "RAW 2027" "CLIP 42" "CLIP 2027"; do set -- $TS; T=$1; SD=$2
  say "F10 chain $T s$SD start (gpu3, legs v4b)"
  run_shards launch_mwf_v4b.sh $T $SD || die "shards_${T}_s${SD}_rc_[$RCS]" 1
  $PY merge_mwf_v4b.py $T $SD > /workspace/f8_v4/logs/merge_v4b_${T}_s${SD}.log 2>&1; rc=$?; say "merge v4b $T s$SD rc=$rc $(tail -1 /workspace/f8_v4/logs/merge_v4b_${T}_s${SD}.log | cut -c1-80)"
  [ $rc -eq 0 ] || die "merge_${T}_s${SD}_rc_$rc" 1; check_marker /workspace/f8_v4/logs/merge_v4b_${T}_s${SD}.log "MERGE_DONE"
done
say "CHAIN_V4_GPU3_DONE (all shards rc=0, merges rc=0 + MERGE_DONE; deps pinned in v4_gates/deps_v4_gpu3.json)"
