#!/bin/bash
# run_w7_positive_control.sh — W7 2026-09-12, PREREG_v4_gates_monthly_2026-09-12 §5 G1/G4 on pod2. THIS FILE IS THE TRANSCRIPT (复跑命令逐字).
# Runs the month-generic gates v4_gate_step1_m.py / v4_gate_step2_m.py on the SEPTEMBER contract paths (the existing September artefacts, read-only)
# through the driver's own calling convention (chain_lib.sh load_month_env + run_gate), in the isolated dir /workspace/w7_gates_2026-09-12/.
# CPU only (numpy). ZERO writes outside $W: chain_lib's say/die log L is re-pointed at $ROOT before AND after load_month_env (which sets L=$R/v4_commands.txt,
# R = /workspace/review_scratch = September). Expected: STEP1 FAIL rc 3 (AMENDMENT 3 trend_288, as archived), STEP2 PASS rc 0; require under the REAL contract
# refuses both ("not an APPROVED source" — approval is the user's word); under a SIMULATION COPY of the contract STEP2 -> REQUIRE_OK, STEP1 -> PASS=False.
W=/workspace/w7_gates_2026-09-12; DEV=$W/device; ROOT=$W/root; SIM=$W/device_sim
mkdir -p "$ROOT/v4_gates" "$SIM" || exit 1
T=$ROOT/w7_commands.txt
log(){ echo "[$(date -u +%FT%TZ)] $*" | tee -a "$T"; }
log "W7 positive control start (this script: $(sha256sum "$0" | cut -c1-64))"; date -u +%FT%TZ > "$ROOT/started_utc.txt"
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader > "$ROOT/nvidia_before.txt"; ps -o pid,stat,etime -p 333197,339489 > "$ROOT/paused_pids_before.txt"
log "gpu before: $(cat "$ROOT/nvidia_before.txt") | paused pids: $(tail -n +2 "$ROOT/paused_pids_before.txt" | tr '\n' ' ')"
ls -la --time-style=full-iso /workspace/review_scratch/v4_commands.txt /workspace/review_scratch/v4_gates/step1.json /workspace/review_scratch/v4_gates/step2.json > "$ROOT/review_scratch_before_ls.txt" 2>&1
cd "$DEV" || exit 1
sha256sum v4_gate_step1_m.py v4_gate_step2_m.py v4_gate_common.py ELIGIBILITY_CONTRACT.json compare_gate_receipts.py v4_month_2026-09.env chain_lib.sh > "$ROOT/device_sha256_w7.txt"
# the device copy must be the git single source (shas measured locally by shasum -a 256 before upload)
for want in "79950786271e690a24c72bc189b20e65eab6271164c1e582dff72b799db00163  v4_gate_step1_m.py" \
            "455e3df4c19545aa45f1042228501627938c9b0387053e4cc97a812d9e018ca5  v4_gate_step2_m.py" \
            "f8f4fc0e6ca3a02f9c51383b72f553b5f8614b3be5f496f510bae9d43fe0df12  v4_gate_common.py" \
            "1188267adf420c0b3a39a4b20a8a131ee80ae5d667b5056006465dbaba50a732  ELIGIBILITY_CONTRACT.json"; do
  grep -qF "$want" "$ROOT/device_sha256_w7.txt" || { log "FAIL_device_sha_mismatch: $want"; exit 2; }
done
log "device shas verified (4 pinned) -> $ROOT/device_sha256_w7.txt"
export L=$ROOT/chain_lib_say.txt CHAIN_DEVICE_DIR=$DEV
. "$DEV/chain_lib.sh"
load_month_env "$DEV/v4_month_2026-09.env" >> "$T" || { log "FAIL_load_month_env"; exit 4; }
L=$ROOT/chain_lib_say.txt   # load_month_env set L=$R/v4_commands.txt (September review_scratch): re-point — no write to review_scratch
export PREV_DLW_CLIP=/workspace/dlw_hf2 PREV_F8=/workspace/f8_hf2 PREV_KING_FEA=/workspace/data/wide_fea_v2ext_clamp.npy PREV_KING_FEA_UNCLAMPED=/workspace/data/wide_fea_v2ext.npy   # PREREG §2 September values of the 4 new keys
log "env: R=$R D=$D PY=$PY | HOLE_CELLS=$HOLE_CELLS RAW_PATCH=$RAW_PATCH CACHE=$CACHE DLW_RAW=$DLW_RAW DLW_CLIP=$DLW_CLIP F8=$F8 KING_FEA=$KING_FEA KING_META=$KING_META PREV_META=$PREV_META | PREV_DLW_CLIP=$PREV_DLW_CLIP PREV_F8=$PREV_F8 PREV_KING_FEA=$PREV_KING_FEA PREV_KING_FEA_UNCLAMPED=$PREV_KING_FEA_UNCLAMPED"
run_gate STEP1 v4_gate_step1_m.py "$ROOT/gate_step1_m.log" STEP1_OUT="$ROOT/v4_gates/step1.json"; rc1=$?
run_gate STEP2 v4_gate_step2_m.py "$ROOT/gate_step2_m.log" STEP2_OUT="$ROOT/v4_gates/step2.json"; rc2=$?
log "gates ran: STEP1 rc=$rc1 (expected 3: AMENDMENT 3 literal FAIL) STEP2 rc=$rc2 (expected 0)"
S1=$(gate_sha "$DEV/v4_gate_step1_m.py"); S2=$(gate_sha "$DEV/v4_gate_step2_m.py"); log "runtime self shas: STEP1_m $S1 STEP2_m $S2"
# G4 under the REAL contract (expected: REQUIRE_FAIL ... not an APPROVED source — the new gates are not approved yet)
"$PY" "$DEV/v4_gate_common.py" require "$ROOT/v4_gates/step1.json" gate=STEP1 profile=v4 self_sha=$S1 dlw_v4raw_targets=$DLW_RAW/data/dlw_targets.npz dlw_hf3_targets=$DLW_CLIP/data/dlw_targets.npz fea82_v4raw=$DLW_RAW/data/dlw_fea82.npz fea89_f8v4=$F8/data/f8_fea89.npz > "$ROOT/require_real_step1.txt" 2>&1; log "require REAL contract STEP1 rc=$? $(cut -c1-160 "$ROOT/require_real_step1.txt")"
"$PY" "$DEV/v4_gate_common.py" require "$ROOT/v4_gates/step2.json" gate=STEP2 self_sha=$S2 wide_fea_v4=$KING_FEA wide_fea_v4_meta=$KING_META > "$ROOT/require_real_step2.txt" 2>&1; log "require REAL contract STEP2 rc=$? $(cut -c1-160 "$ROOT/require_real_step2.txt")"
# G4 under a SIMULATION COPY of the contract (approved lists + the two runtime shas; the real contract is NOT touched — its sha is re-read below)
cp "$DEV/v4_gate_common.py" "$SIM/v4_gate_common.py"
"$PY" - "$DEV/ELIGIBILITY_CONTRACT.json" "$SIM/ELIGIBILITY_CONTRACT.json" "$S1" "$S2" <<'PYEOF'
import json, sys
c = json.load(open(sys.argv[1])); c["gates"]["STEP1"]["approved_source_sha256"].append(sys.argv[3]); c["gates"]["STEP2"]["approved_source_sha256"].append(sys.argv[4])
c["status"] = "SIMULATION COPY (W7 G4 2026-09-12): NOT the frozen contract; approved lists extended by the runtime shas of v4_gate_step1_m.py / v4_gate_step2_m.py to show `require` accepts them once the USER approves"
json.dump(c, open(sys.argv[2], "w"), indent=1)
PYEOF
"$PY" "$SIM/v4_gate_common.py" require "$ROOT/v4_gates/step1.json" gate=STEP1 profile=v4 self_sha=$S1 dlw_v4raw_targets=$DLW_RAW/data/dlw_targets.npz dlw_hf3_targets=$DLW_CLIP/data/dlw_targets.npz fea82_v4raw=$DLW_RAW/data/dlw_fea82.npz fea89_f8v4=$F8/data/f8_fea89.npz > "$ROOT/require_sim_step1.txt" 2>&1; log "require SIM contract STEP1 rc=$? $(cut -c1-160 "$ROOT/require_sim_step1.txt")"
"$PY" "$SIM/v4_gate_common.py" require "$ROOT/v4_gates/step2.json" gate=STEP2 self_sha=$S2 wide_fea_v4=$KING_FEA wide_fea_v4_meta=$KING_META > "$ROOT/require_sim_step2.txt" 2>&1; log "require SIM contract STEP2 rc=$? $(cut -c1-160 "$ROOT/require_sim_step2.txt")"
sha256sum "$DEV/ELIGIBILITY_CONTRACT.json" "$SIM/ELIGIBILITY_CONTRACT.json" > "$ROOT/contract_real_vs_sim_sha.txt"; log "contract shas (real must still be 1188267a…): $(cut -c1-12 "$ROOT/contract_real_vs_sim_sha.txt" | tr '\n' ' ')"
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader > "$ROOT/nvidia_after.txt"; ps -o pid,stat,etime -p 333197,339489 > "$ROOT/paused_pids_after.txt"
log "gpu after: $(cat "$ROOT/nvidia_after.txt") | paused pids: $(tail -n +2 "$ROOT/paused_pids_after.txt" | tr '\n' ' ')"
ls -la --time-style=full-iso /workspace/review_scratch/v4_commands.txt /workspace/review_scratch/v4_gates/step1.json /workspace/review_scratch/v4_gates/step2.json > "$ROOT/review_scratch_after_ls.txt" 2>&1; cmp -s "$ROOT/review_scratch_before_ls.txt" "$ROOT/review_scratch_after_ls.txt" && log "review_scratch untouched (ls before == after)" || log "WARN review_scratch ls changed"
log "W7 positive control end: STEP1 rc=$rc1 STEP2 rc=$rc2 receipts $ROOT/v4_gates/step{1,2}.json"
exit 0
