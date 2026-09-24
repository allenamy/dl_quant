"""fa_b5transform.py — B5 targets by a SINGLE auditable post-adapter transform (lead 2026-09-24).
The shared adapter is NOT modified and NOT bypassed for anything else: the adapter's own output for the ORIGINAL
arm is the input here, so every adapter check (shape, name mapping, axis, holds) has already applied.

The only change: on the gate-failure anchors, scaled_kind 0 -> 2. Those rows are ALREADY empty (verified), so
scaled_off / scaled_idx / scaled_val are untouched, and the lit_* arrays are untouched entirely.

Three assertions the lead required:
  1. the number of changed anchors == the original arm's gate-failure anchor count
  2. every other array is bitwise identical to the adapter's output
  3. loading the result with bt_objb_targets gives written_rows_without_weights == the gate-failure count

NAMED DEVIATION: the adapter would REFUSE this artifact (ovn_adapter.py:78 published_row_without_weight). It is
produced only by this assertion-bound post-processing. The FORMAT and the ENGINE accept it: the reader rejects only
kind==0-with-weights, and both the reader and the window loader carry a dedicated counter for this exact state.
usage: ... fa_b5transform.py WL <arm_root> <seed> <outdir>
"""
import os, sys, json, time, hashlib, shutil
import numpy as np
WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x
ROOT, SEED, OUTD = sys.argv[2], sys.argv[3], sys.argv[4]
sys.path.insert(0, "/dev/shm/fresh_2026-09-23/engine")
import bt_objb_targets as BOT
ARM = "FRESH" if "fresh" in ROOT else "NEWS"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
os.makedirs(OUTD, exist_ok=True)
src_npz = f"{ROOT}/targets/TARGETS_{ARM}_s{SEED}.npz"; src_json = f"{ROOT}/targets/TARGETS_{ARM}_s{SEED}.json"
T = np.load(src_npz); C = np.load(f"{ROOT}/work/combo_s{SEED}/scaled_diagnostic.npz", allow_pickle=True)
A = T["anchor"].astype(np.int64); kind = T["scaled_kind"].copy(); off = T["scaled_off"].astype(np.int64)
ce = C["E_ts"].astype(np.int64); tm = np.asarray(C["trade_mask"]).astype(bool)
rsn = np.array([str(x) for x in C["reason"]])
gf = ce[(~tm) & (rsn != "unready causal legs")]; n_gf = len(gf)
pos = {int(t): i for i, t in enumerate(A)}; ii = np.array([pos[int(t)] for t in gf])
rowlen = np.diff(off)
assert set(kind[ii].tolist()) == {0} and set(rowlen[ii].tolist()) == {0}, "gate-failure rows are not empty holds"
kind[ii] = 2
out = {k: T[k] for k in T.files}; out["scaled_kind"] = kind
p = f"{OUTD}/TARGETS.npz"; np.savez(p + ".tmp.npz", **out); os.replace(p + ".tmp.npz", p)
V = np.load(p)
# assertion 1
n_changed = int((V["scaled_kind"] != T["scaled_kind"]).sum())
# assertion 2
untouched = [k for k in T.files if k != "scaled_kind"]
all_same = all(np.array_equal(V[k], T[k]) for k in untouched)
# receipt regenerated for the transformed npz
R = json.load(open(src_json))
R["targets_npz_sha256"] = sha(p)
R["DIAGNOSTIC_B5"] = {"named_deviation": "the adapter would REFUSE this artifact (ovn_adapter.py:78 "
                                          "published_row_without_weight); it is produced only by an assertion-bound "
                                          "post-processing of the adapter's own output for the ORIGINAL arm",
                      "why_format_and_engine_accept_it": "bt_objb_targets rejects only kind==0-with-weights; both the "
                                                         "reader (L88) and the window loader (L119) carry a dedicated "
                                                         "written_rows_without_weights counter for this exact state",
                      "source_npz": src_npz, "source_npz_sha256": sha(src_npz),
                      "change": "scaled_kind 0 -> 2 on the gate-failure anchors only; scaled_off/idx/val and all lit_* untouched",
                      "n_anchors_changed": n_changed, "gate_failure_anchors": n_gf}
rj = f"{OUTD}/TARGETS.json"; json.dump(R, open(rj, "w"), indent=1)
# assertion 3, through the real reader
A2, k2, off2, idx2, val2, info = BOT.load_source({"npz": p, "npz_sha256": sha(p), "receipt": rj, "receipt_sha256": sha(rj)}, "scaled", R.get("arm", f"{ARM}_s{SEED}"), 829)
w_no_w = int(info["written_rows_without_weights"])
rec = {"device": "fa_b5transform.py", "self_sha256": sha(os.path.abspath(__file__)),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "arm": ARM, "seed": SEED,
       "assert_1_changed_equals_gate_failures": {"changed": n_changed, "gate_failures": n_gf, "PASS": bool(n_changed == n_gf)},
       "assert_2_all_other_arrays_bitwise_identical": {"arrays_checked": len(untouched), "PASS": bool(all_same)},
       "assert_3_reader_written_rows_without_weights": {"got": w_no_w, "expected": n_gf, "PASS": bool(w_no_w == n_gf)},
       "out_npz": p, "out_npz_sha256": sha(p), "out_receipt": rj, "out_receipt_sha256": sha(rj),
       "named_deviation": R["DIAGNOSTIC_B5"]}
json.dump(rec, open(f"{OUTD}/FA_B5TRANSFORM.json", "w"), indent=2, default=float)
assert n_changed == n_gf, f"assert 1 failed: {n_changed} != {n_gf}"
assert all_same, "assert 2 failed: an array other than scaled_kind changed"
assert w_no_w == n_gf, f"assert 3 failed: reader counts {w_no_w}, expected {n_gf}"
print("FA_B5TRANSFORM %s s%s changed=%d gate_fail=%d other_arrays_identical=%s reader_written_empty=%d ALL_ASSERTS_PASS=True"
      % (ARM, SEED, n_changed, n_gf, all_same, w_no_w), flush=True)
