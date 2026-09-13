#!/bin/bash
# run_x3_round4_control.sh — X3 2026-09-13, round 4 (REVIEW_round3_code_and_research_2026-09-13 §4 R3-D2 / R3-D3). CPU only, isolated /workspace/x3_round4_2026-09-13/,
# /workspace/review_scratch READ-ONLY. THIS FILE IS THE TRANSCRIPT. Device = the W7b round-3 pod2 device verbatim (/workspace/w7b_round3_2026-09-13/device: common f8f4fc0e,
# contract 1188267a, clamp builder b9f9c728, STEP1_m 79950786, September contract 563efdef, compare_gate_receipts fbf69781), with EXACTLY two files replaced:
#   v4_gate_step2_m.py b2f9cfd4 -> d99a9109 (AMENDMENT 3: member index dtype must be a signed/unsigned integer KIND) and chain_lib.sh a331f035 -> 4ee217e1 (round-4 parser).
# PRE-REGISTERED EXPECTATIONS (written before this ran):
#   E1 the round-4 load_month_env (Python data-grammar parser, pod2 bash 5.1 + /workspace/venv/bin/python) loads the shipped September contract rc 0, and the FULL exported
#      environment after it is IDENTICAL to the round-3 loader's (a331f035, same parent env) — every variable, the 46 keys included.
#   E2 direct read-only measurement of the persisted member index of the 6 September new-tail anchors (the gate's own tail definition): every one has dtype KIND 'i' or 'u',
#      ndim 1, 400 entries, all in [0, 829), unique. If any tail anchor is NOT an integer kind, the new rule would refuse real data: then the RULE is wrong for this data —
#      report it, do not adjust. (Axis-wide element dtype kinds are also counted, informational.)
#   E3 STEP2_m d99a9109 PASS rc 0; tail_quality byte-equal to the round-3 receipt (n_tail_anchors 6, member_index_ok true, member_finite_frac_min = median = 0.975609756097561,
#      n_members_min 400, floor 0.9, ok true), no member_index_bad.
#   E4 compare_gate_receipts vs the round-3 receipt (10eaadce…): PARITY OK — 38 verdict fields equal, 0 differ.
#   E5 require on the REAL contract: REQUIRE_FAIL, d99a9109 is not an APPROVED source (approval = the user's word); contract sha after still 1188267a.
#   E6 GPU 0 %, 2 MiB before and after; PIDs 333197 / 339489 state Tl before and after (never signalled); review_scratch ls before == after.
W=/workspace/x3_round4_2026-09-13; DEV=$W/device; ROOT=$W/root; W7B=/workspace/w7b_round3_2026-09-13
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
mkdir -p "$ROOT/v4_gates" || exit 1
T=$ROOT/x3_commands.txt
log(){ echo "[$(date -u +%FT%TZ)] $*" | tee -a "$T"; }
log "X3 round 4 control start (this script: $(sha256sum "$0" | cut -c1-64))"
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader > "$ROOT/nvidia_before.txt"; ps -o pid,stat,etime -p 333197,339489 > "$ROOT/paused_pids_before.txt"
log "gpu before: $(cat "$ROOT/nvidia_before.txt") | paused pids: $(tail -n +2 "$ROOT/paused_pids_before.txt" | tr '\n' ' ') | load: $(cut -d' ' -f1-3 /proc/loadavg) nproc $(nproc)"
ls -la --time-style=full-iso /workspace/review_scratch/v4_commands.txt /workspace/review_scratch/v4_gates/step1.json /workspace/review_scratch/v4_gates/step2.json > "$ROOT/review_scratch_before_ls.txt" 2>&1
cd "$DEV" || exit 1
sha256sum v4_gate_step2_m.py chain_lib.sh chain_lib.r2_a331f035.sh v4_gate_step1_m.py v4_gate_common.py ELIGIBILITY_CONTRACT.json v4_month_2026-09.env pod_fea_ext_clamp.py compare_gate_receipts.py > "$ROOT/device_sha256_x3.txt"
for want in "d99a910951e070f70ae3eede1533013e009a62fa617eda55dff546290864329d  v4_gate_step2_m.py" \
            "4ee217e1d761fa13abf34d16222f1dede79ceade3d44547e171aa7477a30288d  chain_lib.sh" \
            "a331f0351b3eca9ac2e64636e94a906045deb209f25888f38a8ab07e4d715a40  chain_lib.r2_a331f035.sh" \
            "f8f4fc0e6ca3a02f9c51383b72f553b5f8614b3be5f496f510bae9d43fe0df12  v4_gate_common.py" \
            "1188267adf420c0b3a39a4b20a8a131ee80ae5d667b5056006465dbaba50a732  ELIGIBILITY_CONTRACT.json" \
            "b9f9c72816241715fc4b767950420e74f50adbbbcfc4ea77b362407ab5efa4ac  pod_fea_ext_clamp.py" \
            "79950786271e690a24c72bc189b20e65eab6271164c1e582dff72b799db00163  v4_gate_step1_m.py" \
            "563efdef86993ac37364b735f4492023c8e69846c5a9e763427fa30601da8ad4  v4_month_2026-09.env" \
            "fbf69781b3df5600c089a87e47a49f96ff52ad116d8f381aedebc0f59ab8e8c1  compare_gate_receipts.py"; do
  grep -qF "$want" "$ROOT/device_sha256_x3.txt" || { log "FAIL_device_sha_mismatch: $want"; exit 2; }
done
log "device verified: 9 pinned shas (the two replaced files + the round-3 loader kept as chain_lib.r2_a331f035.sh + the 6 unchanged W7b files)"
sha256sum "$W7B/root/v4_gates/step2.json" | grep -q '^10eaadce8045c678cf82b8f1c69487321eb2d26e6e3a116a5639739e622ddeb7 ' || { log "FAIL_round3_reference_sha"; exit 2; }
cp "$W7B/root/v4_gates/step2.json" "$ROOT/step2_round3_ARCHIVED_reference.json" || exit 2
# E1: the two loaders under the same parent environment; `env` dumped after each (separate processes, nothing written outside ROOT)
for LIBV in chain_lib.r2_a331f035.sh chain_lib.sh; do
  env L="$ROOT/loader_say_${LIBV}.txt" CHAIN_DEVICE_DIR="$DEV" bash -c 'set -o pipefail; . "$1"; load_month_env "$2" > "$3.ok" || exit 4; env | LC_ALL=C sort > "$3"' u "$DEV/$LIBV" "$DEV/v4_month_2026-09.env" "$ROOT/env_after_${LIBV}.txt"
  log "E1 loader $LIBV rc=$? $(cut -c1-160 "$ROOT/env_after_${LIBV}.txt.ok")"
done
if cmp -s "$ROOT/env_after_chain_lib.r2_a331f035.sh.txt" "$ROOT/env_after_chain_lib.sh.txt"; then log "E1 exported environment IDENTICAL ($(wc -l < "$ROOT/env_after_chain_lib.sh.txt") variables; MONTH_ENV_OK lines identical: $(cmp -s "$ROOT/env_after_chain_lib.r2_a331f035.sh.txt.ok" "$ROOT/env_after_chain_lib.sh.txt.ok" && echo yes || echo NO))"
else log "E1 exported environment DIFFERS:"; diff "$ROOT/env_after_chain_lib.r2_a331f035.sh.txt" "$ROOT/env_after_chain_lib.sh.txt" | head -20 | tee -a "$T"; fi
export L=$ROOT/chain_lib_say.txt CHAIN_DEVICE_DIR=$DEV
. "$DEV/chain_lib.sh"
load_month_env "$DEV/v4_month_2026-09.env" >> "$T" || { log "FAIL_load_month_env (round-4 parser on the September contract)"; exit 4; }
L=$ROOT/chain_lib_say.txt   # load_month_env points L at $R/v4_commands.txt (September review_scratch): re-point — nothing is written there
log "round-4 load_month_env on the shipped September contract: rc 0; R=$R D=$D KING_META=$KING_META PREV_META=$PREV_META PREV_KING_FEA_UNCLAMPED=$PREV_KING_FEA_UNCLAMPED"
# E2: read-only dtype measurement of the persisted member index (the gate's tail definition verbatim: only-in-new AND after the reference axis end)
nice -n 10 "$PY" - "$ROOT/tail_member_dtype.json" <<'PYEOF' | tee -a "$T"
import json, os, sys, collections
import numpy as np
M4 = np.load(os.environ["KING_META"], allow_pickle=True); ME = np.load(os.environ["PREV_META"], allow_pickle=True)
E4 = M4["E_ts"].astype(np.int64); EE = ME["E_ts"].astype(np.int64); mem = M4["members"]
x4 = np.setdiff1d(E4, EE); tail = np.searchsorted(E4, x4[x4 > int(EE.max())])
rows = []
for i in tail:
    a = np.asarray(mem[i])
    rows.append({"i": int(i), "E_ts": int(E4[i]), "dtype": str(a.dtype), "kind": a.dtype.kind, "ndim": int(a.ndim), "size": int(a.size),
                 "min": int(a.min()) if a.size and a.dtype.kind in "iu" else None, "max": int(a.max()) if a.size and a.dtype.kind in "iu" else None, "n_unique": int(np.unique(a).size)})
kinds = collections.Counter(np.asarray(m).dtype.str for m in mem)
ok = bool(len(rows) == 6 and all(r["kind"] in "iu" and r["ndim"] == 1 and r["size"] == 400 and 0 <= r["min"] and r["max"] < 829 and r["n_unique"] == r["size"] for r in rows))
res = {"container_dtype": str(mem.dtype), "container_shape": list(mem.shape), "element_type": type(mem[0]).__name__, "tail": rows, "axis_element_dtype_counts": dict(kinds), "E2_expected_holds": ok}
json.dump(res, open(sys.argv[1], "w"), indent=1)
print("E2 container", res["container_dtype"], res["container_shape"], res["element_type"], "| tail dtypes", sorted({r["dtype"] for r in rows}), "sizes", sorted({r["size"] for r in rows}),
      "| axis element dtypes", dict(kinds), "| E2 holds:", ok)
PYEOF
run_gate STEP2 v4_gate_step2_m.py "$ROOT/gate_step2_m.log" STEP2_OUT="$ROOT/v4_gates/step2.json"; rc2=$?
log "E3 gate ran: STEP2 rc=$rc2 (expected 0)"
S2=$(gate_sha "$DEV/v4_gate_step2_m.py"); log "runtime self sha: STEP2_m $S2"
"$PY" -c "import json,sys;r=json.load(open(sys.argv[1]));a=json.load(open(sys.argv[2]));print('E3 PASS',r['PASS'],'| tail_quality',json.dumps(r.get('tail_quality'),sort_keys=True),'| byte-equal to round 3:',r.get('tail_quality')==a.get('tail_quality'))" "$ROOT/v4_gates/step2.json" "$ROOT/step2_round3_ARCHIVED_reference.json" | tee -a "$T"
"$PY" "$DEV/compare_gate_receipts.py" "$ROOT/step2_round3_ARCHIVED_reference.json" "$ROOT/v4_gates/step2.json" "$ROOT/parity_STEP2_round4_vs_round3.json" > "$ROOT/parity_STEP2_round4_vs_round3.txt" 2>&1
log "E4 parity vs round-3 receipt: $(cut -c1-200 "$ROOT/parity_STEP2_round4_vs_round3.txt")"
"$PY" "$DEV/v4_gate_common.py" require "$ROOT/v4_gates/step2.json" gate=STEP2 self_sha=$S2 wide_fea_v4=$KING_FEA wide_fea_v4_meta=$KING_META > "$ROOT/require_real_step2.txt" 2>&1; log "E5 require REAL contract STEP2 rc=$? $(cut -c1-170 "$ROOT/require_real_step2.txt")"
sha256sum "$DEV/ELIGIBILITY_CONTRACT.json" > "$ROOT/contract_sha_after.txt"; log "E5 contract sha after (must still be 1188267a…): $(cut -c1-12 "$ROOT/contract_sha_after.txt")"
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader > "$ROOT/nvidia_after.txt"; ps -o pid,stat,etime -p 333197,339489 > "$ROOT/paused_pids_after.txt"
log "E6 gpu after: $(cat "$ROOT/nvidia_after.txt") | paused pids: $(tail -n +2 "$ROOT/paused_pids_after.txt" | tr '\n' ' ')"
ls -la --time-style=full-iso /workspace/review_scratch/v4_commands.txt /workspace/review_scratch/v4_gates/step1.json /workspace/review_scratch/v4_gates/step2.json > "$ROOT/review_scratch_after_ls.txt" 2>&1
cmp -s "$ROOT/review_scratch_before_ls.txt" "$ROOT/review_scratch_after_ls.txt" && log "E6 review_scratch untouched (ls before == after)" || log "WARN review_scratch ls changed"
log "X3 round 4 control end: STEP2 rc=$rc2 receipt $ROOT/v4_gates/step2.json"
exit 0
