#!/bin/bash
# run_w7b_round3_control.sh — W7b 2026-09-13, PREREG_v4_gates_monthly AMENDMENT 2 (researcher F-R3): re-run of the month-generic STEP2 gate on the SEPTEMBER
# contract paths after the new-tail MEMBER INDEX validity rule. CPU only, isolated /workspace/w7b_round3_2026-09-13/, /workspace/review_scratch READ-ONLY.
# THIS FILE IS THE TRANSCRIPT. ONE VARIABLE: the device dir is W7's r2 copy verbatim (same v4_gate_common f8f4fc0e, same contract, same September env);
# only v4_gate_step2_m.py is replaced (0fe5ec55 -> the round-3 build) and chain_lib.sh (3cd82956 -> round 3, used only to load the contract).
# PRE-REGISTERED EXPECTATION (written before this ran; the point is that the structural rule must NOT reject real data):
#   1. STEP2 PASS rc 0, exactly as r2 — the 6 September tail anchors carry ~400 members each and those indices must be valid symbol indices.
#   2. tail_quality gains ONE field, member_index_ok = true; every other tail_quality value byte-equal to r2
#      (n_tail_anchors 6, member_finite_frac_min 0.9756, median 0.9756, n_members_min 400, floor 0.9, ok true); NO member_index_bad field.
#   3. compare_gate_receipts vs the r2 receipt: exactly 1 differing verdict field (tail_quality, because of the added member_index_ok), PASS=true both sides.
#   If member_index_ok comes back false, the September meta carries an index my rule calls illegal and the RULE is wrong, not the data — report it, do not adjust.
W=/workspace/w7b_round3_2026-09-13; DEV=$W/device; ROOT=$W/root
mkdir -p "$ROOT/v4_gates" || exit 1
T=$ROOT/w7b_commands.txt
log(){ echo "[$(date -u +%FT%TZ)] $*" | tee -a "$T"; }
log "W7b round 3 control start (this script: $(sha256sum "$0" | cut -c1-64))"
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader > "$ROOT/nvidia_before.txt"; ps -o pid,stat,etime -p 333197,339489 > "$ROOT/paused_pids_before.txt"
log "gpu before: $(cat "$ROOT/nvidia_before.txt") | paused pids: $(tail -n +2 "$ROOT/paused_pids_before.txt" | tr '\n' ' ')"
ls -la --time-style=full-iso /workspace/review_scratch/v4_commands.txt /workspace/review_scratch/v4_gates/step1.json /workspace/review_scratch/v4_gates/step2.json > "$ROOT/review_scratch_before_ls.txt" 2>&1
cd "$DEV" || exit 1
sha256sum v4_gate_step2_m.py v4_gate_step1_m.py v4_gate_common.py ELIGIBILITY_CONTRACT.json v4_month_2026-09.env chain_lib.sh pod_fea_ext_clamp.py > "$ROOT/device_sha256_w7b.txt"
for want in "f8f4fc0e6ca3a02f9c51383b72f553b5f8614b3be5f496f510bae9d43fe0df12  v4_gate_common.py" \
            "1188267adf420c0b3a39a4b20a8a131ee80ae5d667b5056006465dbaba50a732  ELIGIBILITY_CONTRACT.json" \
            "b9f9c72816241715fc4b767950420e74f50adbbbcfc4ea77b362407ab5efa4ac  pod_fea_ext_clamp.py" \
            "79950786271e690a24c72bc189b20e65eab6271164c1e582dff72b799db00163  v4_gate_step1_m.py" \
            "563efdef86993ac37364b735f4492023c8e69846c5a9e763427fa30601da8ad4  v4_month_2026-09.env"; do
  grep -qF "$want" "$ROOT/device_sha256_w7b.txt" || { log "FAIL_device_sha_mismatch: $want"; exit 2; }
done
log "unchanged device files verified (5 pinned: only v4_gate_step2_m.py and chain_lib.sh differ from W7 r2)"
export L=$ROOT/chain_lib_say.txt CHAIN_DEVICE_DIR=$DEV
. "$DEV/chain_lib.sh"
load_month_env "$DEV/v4_month_2026-09.env" >> "$T" || { log "FAIL_load_month_env (round-3 loader on the September contract)"; exit 4; }
L=$ROOT/chain_lib_say.txt   # load_month_env points L at $R/v4_commands.txt (September review_scratch): re-point — nothing is written there
log "round-3 load_month_env on the shipped September contract: rc 0; R=$R D=$D KING_FEA=$KING_FEA KING_META=$KING_META PREV_META=$PREV_META PREV_KING_FEA=$PREV_KING_FEA PREV_KING_FEA_UNCLAMPED=$PREV_KING_FEA_UNCLAMPED"
run_gate STEP2 v4_gate_step2_m.py "$ROOT/gate_step2_m.log" STEP2_OUT="$ROOT/v4_gates/step2.json"; rc2=$?
log "gate ran: STEP2 rc=$rc2 (expected 0)"
S2=$(gate_sha "$DEV/v4_gate_step2_m.py"); log "runtime self sha: STEP2_m $S2"
"$PY" -c "import json,sys;r=json.load(open(sys.argv[1]));print('PASS',r['PASS']);print('tail_quality',json.dumps(r.get('tail_quality'),sort_keys=True))" "$ROOT/v4_gates/step2.json" | tee -a "$T"
"$PY" "$DEV/compare_gate_receipts.py" "$ROOT/step2_r2_ARCHIVED_reference.json" "$ROOT/v4_gates/step2.json" "$ROOT/parity_STEP2_round3_vs_r2.json" > "$ROOT/parity_STEP2_round3_vs_r2.txt" 2>&1
log "parity vs W7 r2 receipt: $(cut -c1-200 "$ROOT/parity_STEP2_round3_vs_r2.txt")"
"$PY" "$DEV/v4_gate_common.py" require "$ROOT/v4_gates/step2.json" gate=STEP2 self_sha=$S2 wide_fea_v4=$KING_FEA wide_fea_v4_meta=$KING_META > "$ROOT/require_real_step2.txt" 2>&1; log "require REAL contract STEP2 rc=$? $(cut -c1-160 "$ROOT/require_real_step2.txt")"
sha256sum "$DEV/ELIGIBILITY_CONTRACT.json" > "$ROOT/contract_sha_after.txt"; log "contract sha after (must still be 1188267a…): $(cut -c1-12 "$ROOT/contract_sha_after.txt")"
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader > "$ROOT/nvidia_after.txt"; ps -o pid,stat,etime -p 333197,339489 > "$ROOT/paused_pids_after.txt"
log "gpu after: $(cat "$ROOT/nvidia_after.txt") | paused pids: $(tail -n +2 "$ROOT/paused_pids_after.txt" | tr '\n' ' ')"
ls -la --time-style=full-iso /workspace/review_scratch/v4_commands.txt /workspace/review_scratch/v4_gates/step1.json /workspace/review_scratch/v4_gates/step2.json > "$ROOT/review_scratch_after_ls.txt" 2>&1
cmp -s "$ROOT/review_scratch_before_ls.txt" "$ROOT/review_scratch_after_ls.txt" && log "review_scratch untouched (ls before == after)" || log "WARN review_scratch ls changed"
log "W7b round 3 control end: STEP2 rc=$rc2 receipt $ROOT/v4_gates/step2.json"
exit 0
