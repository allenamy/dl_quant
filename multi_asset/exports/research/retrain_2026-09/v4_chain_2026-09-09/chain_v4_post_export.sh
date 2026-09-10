#!/bin/bash
# chain_v4_post_export.sh — PREREG_v4 §2.4–2.5 queue: dev_v4 tree -> legs v4b -> (wait for a FRESH STEP1 PASS receipt) -> 4 F10 chains x 4 shards -> merge.
# HARDENED 2026-09-09 (review b0a573a1 P1-PIPE): the old `while [ ! -f STEP1_PASS ]` marker wait is replaced by `require` on step1.json
# (PASS + input shas); export marker checked; legs marker checked; shards waited by PID; merge rc + MERGE_DONE; DONE only on success.
# ROUND 3 (review 31fa3e4e §2, 2026-09-10): the export log must carry BUNDLE_DONE and must NOT carry BUNDLE_FAIL; the STEP1 receipt is
# required BY NAME with all four inputs it hashed (RAW + CLIP targets, fea82, fea89); pin_deps records the dispatch's scripts and data.
# ROUND 4 (2026-09-10): the STEP1 receipt is required (in the wait loop AND at dispatch) with self_sha= of $R/v4_gate_step1.py computed at run time.
set -o pipefail; R=/workspace/review_scratch; . $R/chain_lib.sh; cd $R || exit 2; export MWF_ROOT=${MWF_ROOT:-mwf_v4b}
check_marker $R/export_v4.log "BUNDLE_DONE"; check_no_marker $R/export_v4.log "BUNDLE_FAIL"
say "post_export: build_dev_v4"; $PY build_dev_v4.py > build_dev_v4.log 2>&1 || die "build_dev_v4" 1
say "post_export: legs v4b"; env LEGS_TG=/workspace/dlw_v4raw/data/dlw_targets.npz LEGS_META=/workspace/data/wide_fea_v4_meta.npz LEGS_PRED=/workspace/shadow_bundle_v4/slow_pred_pinned.npy LEGS_OUT=/workspace/f8_v4/data/f10v2_legs.npz $PY pod_legs_v4b.py > legs_v4.log 2>&1 || die "legs_v4b" 1
check_marker legs_v4.log "LEGS_V4B_DONE"
S1_SRC=$(gate_sha $R/v4_gate_step1.py) || die "gate_source_unreadable_v4_gate_step1" 3
STEP1_REQ="$R/v4_gates/step1.json gate=STEP1 self_sha=$S1_SRC dlw_v4raw_targets=/workspace/dlw_v4raw/data/dlw_targets.npz dlw_hf3_targets=/workspace/dlw_hf3/data/dlw_targets.npz fea82_v4raw=/workspace/dlw_v4raw/data/dlw_fea82.npz fea89_f8v4=/workspace/f8_v4/data/f8_fea89.npz"
n=0; until $PY $R/v4_gate_common.py require $STEP1_REQ > /dev/null 2>&1; do
  n=$((n + 1)); [ $n -gt 120 ] && die "step1_receipt_timeout_2h" 3; sleep 60
done; require_gate $STEP1_REQ; say "post_export: STEP1 receipt PASS + fresh, launching F10 chains"
pin_deps v4_post_export $R/pod_f10_train_monthly_v4.py $R/launch_mwf_v4b.sh $R/merge_mwf_v4b.py $R/chain_lib.sh /workspace/f8_v4/data/f10v2_legs.npz /workspace/f8_v4/data/f8_fea89.npz /workspace/dlw_v4raw/data/dlw_targets.npz /workspace/dlw_hf3/data/dlw_targets.npz /workspace/dlw_v4raw/data/dlw_fea82.npz
SH0=202501,202505,202509,202601,202605; SH1=202502,202506,202510,202602,202606; SH2=202503,202507,202511,202603,202607; SH3=202504,202508,202512,202604,202608
for TS in "RAW 42" "RAW 2027" "CLIP 42" "CLIP 2027"; do set -- $TS; T=$1; SD=$2
  say "F10 chain $T s$SD start"
  run_shards launch_mwf_v4b.sh $T $SD || die "shards_${T}_s${SD}_rc_[$RCS]" 1
  $PY merge_mwf_v4b.py $T $SD > /workspace/f8_v4/logs/merge_${T}_s${SD}.log 2>&1; rc=$?; say "merge $T s$SD rc=$rc $(tail -1 /workspace/f8_v4/logs/merge_${T}_s${SD}.log | cut -c1-80)"
  [ $rc -eq 0 ] || die "merge_${T}_s${SD}_rc_$rc" 1; check_marker /workspace/f8_v4/logs/merge_${T}_s${SD}.log "MERGE_DONE"
done
say "CHAIN_V4_POST_EXPORT_DONE (all shards rc=0, merges rc=0 + MERGE_DONE; deps pinned in v4_gates/deps_v4_post_export.json)"
