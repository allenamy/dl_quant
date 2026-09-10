#!/bin/bash
# chain_v4s_gpu.sh — PREREG_fea89_stable_trend G3: RAW x {42,2027} on f8_v4s (stable trend fea89), legs v4b, FIX7 20 folds; then merge.
# HARDENED 2026-09-09 (review b0a573a1 P1-PIPE): dispatches ONLY on a fresh PASS receipt of the G2 stable closure gate (input shas verified);
# every shard is waited on by PID and any non-zero rc aborts before merge; merge rc + MERGE_DONE marker checked; DONE only on success.
# ROUND 3 (review 31fa3e4e §2, 2026-09-10): the FULL dependency set is bound —
#   · G2 closure receipt: named gate, ALL five hashed inputs incl. hole_cells (was 4, hole_cells omitted);
#   · STEP1 receipt: the RAW targets and fea82 the trainer ACTUALLY reads (/workspace/dlw_v4raw) — the old require passed CLIP targets;
#   · pin_deps: sha256 of trainer / launcher / merge / chain_lib / legs / fea89 / targets / fea82 at dispatch time (provenance receipt).
# ROUND 4 (researcher chain_valid_wrong_gate_source, 2026-09-10): each receipt is required with self_sha= of the gate script THIS archive
#   invokes ($R/v4_gate_closure.py, $R/v4_gate_step1.py), computed here at run time — a receipt written by another program is refused.
set -o pipefail; R=/workspace/review_scratch; . $R/chain_lib.sh; cd $R || exit 2; export MWF_ROOT=mwf_v4s
SH0=202501,202505,202509,202601,202605; SH1=202502,202506,202510,202602,202606; SH2=202503,202507,202511,202603,202607; SH3=202504,202508,202512,202604,202608
G2_SRC=$(gate_sha $R/v4_gate_closure.py) || die "gate_source_unreadable_v4_gate_closure" 3
S1_SRC=$(gate_sha $R/v4_gate_step1.py) || die "gate_source_unreadable_v4_gate_step1" 3
require_gate $R/v4_gates/G2_closure_stable.json gate=G2_closure self_sha=$G2_SRC fea_A=/workspace/f8_v4s/data/f8_fea89.npz fea_B=/workspace/f8_hf2s/data/f8_fea89.npz targets_A=/workspace/dlw_hf3/data/dlw_targets.npz targets_B=/workspace/dlw_hf2/data/dlw_targets.npz hole_cells=$R/holefix2_cells.npz
require_gate $R/v4_gates/step1.json gate=STEP1 self_sha=$S1_SRC dlw_v4raw_targets=/workspace/dlw_v4raw/data/dlw_targets.npz fea82_v4raw=/workspace/dlw_v4raw/data/dlw_fea82.npz
[ -f /workspace/f8_v4s/data/f10v2_legs.npz ] || die "legs_v4s_missing" 3
pin_deps v4s_gpu $R/pod_f10_train_monthly_v4s.py $R/launch_mwf_v4s.sh $R/merge_mwf_v4s.py $R/chain_lib.sh /workspace/f8_v4s/data/f10v2_legs.npz /workspace/f8_v4s/data/f8_fea89.npz /workspace/dlw_v4raw/data/dlw_targets.npz /workspace/dlw_v4raw/data/dlw_fea82.npz
for TS in "RAW 42" "RAW 2027"; do set -- $TS; T=$1; SD=$2
  say "F10 chain $T s$SD start (v4s: stable trend fea89, legs v4b)"
  run_shards launch_mwf_v4s.sh $T $SD || die "shards_${T}_s${SD}_rc_[$RCS]" 1
  $PY merge_mwf_v4s.py $T $SD > /workspace/f8_v4s/logs/merge_v4b_${T}_s${SD}.log 2>&1; rc=$?; say "merge v4s $T s$SD rc=$rc $(tail -1 /workspace/f8_v4s/logs/merge_v4b_${T}_s${SD}.log | cut -c1-80)"
  [ $rc -eq 0 ] || die "merge_${T}_s${SD}_rc_$rc" 1; check_marker /workspace/f8_v4s/logs/merge_v4b_${T}_s${SD}.log "MERGE_DONE"
done
say "CHAIN_V4S_GPU_DONE (all shards rc=0, merges rc=0 + MERGE_DONE; deps pinned in v4_gates/deps_v4s_gpu.json)"
