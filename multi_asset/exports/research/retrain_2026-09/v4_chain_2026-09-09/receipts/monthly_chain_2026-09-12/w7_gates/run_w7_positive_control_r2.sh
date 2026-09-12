#!/bin/bash
# run_w7_positive_control_r2.sh — W7 2026-09-12, PREREG_v4_gates_monthly AMENDMENT 1: re-run of the STEP2 month-generic gate (v4_gate_step2_m.py 0fe5ec55…, B-R4:
# NONE builder identity + new-tail quality) on the SEPTEMBER contract paths, CPU only, isolated /workspace/w7_gates_2026-09-12/ (round 2 root). THIS FILE IS THE TRANSCRIPT.
# Expected (pre-registered): STEP2 PASS rc 0; compare_gate_receipts vs the archive = 31 verdict fields equal + EXACTLY 1 diff (tail_quality missing_in_archived:
# the 6 September anchors after the v2ext axis end now carry the quality record, member finite fraction min ~0.9756 >= 0.90). STEP1_m unchanged (79950786…) — not re-run.
W=/workspace/w7_gates_2026-09-12; DEV=$W/device; ROOT=$W/root_r2; SIM=$W/device_sim_r2
mkdir -p "$ROOT/v4_gates" "$SIM" || exit 1
T=$ROOT/w7_commands.txt
log(){ echo "[$(date -u +%FT%TZ)] $*" | tee -a "$T"; }
log "W7 positive control r2 start (this script: $(sha256sum "$0" | cut -c1-64))"; date -u +%FT%TZ > "$ROOT/started_utc.txt"
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader > "$ROOT/nvidia_before.txt"; ps -o pid,stat,etime -p 333197,339489 > "$ROOT/paused_pids_before.txt"
log "gpu before: $(cat "$ROOT/nvidia_before.txt") | paused pids: $(tail -n +2 "$ROOT/paused_pids_before.txt" | tr '\n' ' ')"
ls -la --time-style=full-iso /workspace/review_scratch/v4_commands.txt /workspace/review_scratch/v4_gates/step1.json /workspace/review_scratch/v4_gates/step2.json > "$ROOT/review_scratch_before_ls.txt" 2>&1
cd "$DEV" || exit 1
sha256sum v4_gate_step2_m.py v4_gate_step1_m.py v4_gate_common.py ELIGIBILITY_CONTRACT.json v4_month_2026-09.env chain_lib.sh pod_fea_ext_clamp.py > "$ROOT/device_sha256_w7_r2.txt"
for want in "0fe5ec5573f346969d9d3448c3e424f2ebc8b7c192cefe4313a05cdf84c09007  v4_gate_step2_m.py" \
            "f8f4fc0e6ca3a02f9c51383b72f553b5f8614b3be5f496f510bae9d43fe0df12  v4_gate_common.py" \
            "1188267adf420c0b3a39a4b20a8a131ee80ae5d667b5056006465dbaba50a732  ELIGIBILITY_CONTRACT.json" \
            "b9f9c72816241715fc4b767950420e74f50adbbbcfc4ea77b362407ab5efa4ac  pod_fea_ext_clamp.py"; do
  grep -qF "$want" "$ROOT/device_sha256_w7_r2.txt" || { log "FAIL_device_sha_mismatch: $want"; exit 2; }
done
log "device shas verified (4 pinned; v4_gate_common here is the frozen f8f4fc0e copy the September gates were verified with) -> $ROOT/device_sha256_w7_r2.txt"
export L=$ROOT/chain_lib_say.txt CHAIN_DEVICE_DIR=$DEV
. "$DEV/chain_lib.sh"
load_month_env "$DEV/v4_month_2026-09.env" >> "$T" || { log "FAIL_load_month_env"; exit 4; }
L=$ROOT/chain_lib_say.txt   # load_month_env set L=$R/v4_commands.txt (September review_scratch): re-point — no write to review_scratch
log "env (46-key contract, incl. the 5 new keys): R=$R D=$D PY=$PY | KING_FEA=$KING_FEA KING_META=$KING_META PREV_META=$PREV_META PREV_KING_FEA=$PREV_KING_FEA PREV_KING_FEA_UNCLAMPED=$PREV_KING_FEA_UNCLAMPED PREV_CLAMP_BUILDER_SHA256=$PREV_CLAMP_BUILDER_SHA256 HOLE_CELLS=$HOLE_CELLS CACHE=$CACHE"
run_gate STEP2 v4_gate_step2_m.py "$ROOT/gate_step2_m.log" STEP2_OUT="$ROOT/v4_gates/step2.json"; rc2=$?
log "gate ran: STEP2 rc=$rc2 (expected 0)"
S2=$(gate_sha "$DEV/v4_gate_step2_m.py"); log "runtime self sha: STEP2_m $S2"
"$PY" "$DEV/v4_gate_common.py" require "$ROOT/v4_gates/step2.json" gate=STEP2 self_sha=$S2 wide_fea_v4=$KING_FEA wide_fea_v4_meta=$KING_META > "$ROOT/require_real_step2.txt" 2>&1; log "require REAL contract STEP2 rc=$? $(cut -c1-160 "$ROOT/require_real_step2.txt")"
cp "$DEV/v4_gate_common.py" "$SIM/v4_gate_common.py"
"$PY" - "$DEV/ELIGIBILITY_CONTRACT.json" "$SIM/ELIGIBILITY_CONTRACT.json" "$S2" <<'PYEOF'
import json, sys
c = json.load(open(sys.argv[1])); c["gates"]["STEP2"]["approved_source_sha256"].append(sys.argv[3])
c["status"] = "SIMULATION COPY (W7 G4 r2 2026-09-12): NOT the frozen contract; STEP2 approved list extended by the runtime sha of v4_gate_step2_m.py (AMENDMENT 1) to show `require` accepts it once the USER approves"
json.dump(c, open(sys.argv[2], "w"), indent=1)
PYEOF
"$PY" "$SIM/v4_gate_common.py" require "$ROOT/v4_gates/step2.json" gate=STEP2 self_sha=$S2 wide_fea_v4=$KING_FEA wide_fea_v4_meta=$KING_META > "$ROOT/require_sim_step2.txt" 2>&1; log "require SIM contract STEP2 rc=$? $(cut -c1-160 "$ROOT/require_sim_step2.txt")"
sha256sum "$DEV/ELIGIBILITY_CONTRACT.json" "$SIM/ELIGIBILITY_CONTRACT.json" > "$ROOT/contract_real_vs_sim_sha.txt"; log "contract shas (real must still be 1188267a…): $(cut -c1-12 "$ROOT/contract_real_vs_sim_sha.txt" | tr '\n' ' ')"
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader > "$ROOT/nvidia_after.txt"; ps -o pid,stat,etime -p 333197,339489 > "$ROOT/paused_pids_after.txt"
log "gpu after: $(cat "$ROOT/nvidia_after.txt") | paused pids: $(tail -n +2 "$ROOT/paused_pids_after.txt" | tr '\n' ' ')"
ls -la --time-style=full-iso /workspace/review_scratch/v4_commands.txt /workspace/review_scratch/v4_gates/step1.json /workspace/review_scratch/v4_gates/step2.json > "$ROOT/review_scratch_after_ls.txt" 2>&1; cmp -s "$ROOT/review_scratch_before_ls.txt" "$ROOT/review_scratch_after_ls.txt" && log "review_scratch untouched (ls before == after)" || log "WARN review_scratch ls changed"
log "W7 positive control r2 end: STEP2 rc=$rc2 receipt $ROOT/v4_gates/step2.json"
exit 0
