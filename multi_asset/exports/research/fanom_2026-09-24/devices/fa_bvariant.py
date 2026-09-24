"""fa_bvariant.py — PREREG docs/PREREG_fresh_rootcause_B_2026-09-24.md (56c0177aa).
Builds a diagnostic variant combo (B4 / B5) by POST-PROCESSING, which §0 proves is bitwise equivalent to
changing the kernel, because evolve() carries kc/fc/raw forward regardless of the publication decision.
Asserts the contract actually fired and that the state chain is unchanged.
usage: ... fa_bvariant.py WL <arm_root> <seed> <B4|B5> <outdir>
"""
import os, sys, json, time, hashlib, shutil
import numpy as np
WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x
ROOT, SEED, VAR, OUTD = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
assert VAR in ("B4", "B5")
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()

src = f"{ROOT}/work/combo_s{SEED}"
os.makedirs(OUTD, exist_ok=True)
rec = {"device": "fa_bvariant.py", "self_sha256": sha(os.path.abspath(__file__)),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "variant": VAR, "source_combo": src,
       "prereg": {"path": "docs/PREREG_fresh_rootcause_B_2026-09-24.md", "commit": "56c0177aa"},
       "equivalence_argument": "continuous_combo.evolve L36-42: kc/fc/raw are written unconditionally; only "
                               "trade_mask/weights depend on `accepted`. So post-processing the published fields is "
                               "bitwise equivalent to changing the kernel. Asserted below.",
       "policies": {}}
for pol in ("scaled_diagnostic", "literal"):
    C = np.load(f"{src}/{pol}.npz", allow_pickle=True)
    tm = np.asarray(C["trade_mask"]).astype(bool); raw = C["raw"]; reason = np.array([str(x) for x in C["reason"]])
    gate_fail = (~tm) & (reason != "unready causal legs")
    n_gate_fail = int(gate_fail.sum())
    new_tm = tm.copy(); new_w = C["weights"].copy(); new_reason = reason.copy()
    if VAR == "B4":
        new_w[gate_fail] = np.where(np.abs(raw[gate_fail]) > 1e-9, raw[gate_fail], 0.0)
    else:
        new_w[gate_fail] = 0.0
    new_tm[gate_fail] = True
    # A kernel implementing this variant would return accepted=True and reason='publish' on these anchors, and the
    # adapter enforces reason=='publish' <=> trade_mask. So setting it is what the kernel variant WOULD produce --
    # it strengthens the equivalence rather than bending the artifact. The original reasons are preserved below.
    orig_reasons = {k: int(v) for k, v in zip(*np.unique(reason[gate_fail], return_counts=True))}
    new_reason[gate_fail] = "publish"
    n_changed = int((new_tm != tm).sum())
    out = {k: C[k] for k in C.files}
    out["trade_mask"] = new_tm; out["weights"] = new_w; out["reason"] = new_reason
    p = f"{OUTD}/{pol}.npz"; np.savez_compressed(p + ".tmp.npz", **out); os.replace(p + ".tmp.npz", p)
    V = np.load(p, allow_pickle=True)
    state_ok = all(np.array_equal(np.nan_to_num(V[k], nan=-9e9), np.nan_to_num(C[k], nan=-9e9)) for k in ("kc", "fc", "raw", "E_ts", "symbols"))
    rec["policies"][pol] = {"original_reasons_on_overridden_anchors": orig_reasons,
                            "overridden_anchor_indices_sha256": hashlib.sha256(np.flatnonzero(gate_fail).tobytes()).hexdigest(),
                            "gate_fail_anchors": n_gate_fail, "anchors_flipped_to_publish": n_changed,
                            "contract_fired": bool(n_changed == n_gate_fail and n_gate_fail > 0),
                            "state_chain_unchanged": bool(state_ok), "out_npz": p, "sha256": sha(p),
                            "source_sha256": sha(f"{src}/{pol}.npz")}
    assert state_ok, f"{pol}: state chain changed -- post-processing equivalence broken"
    assert n_changed == n_gate_fail and n_gate_fail > 0, \
        f"{pol}: contract did not fire ({n_changed} flipped vs {n_gate_fail} gate failures)"
# The receipt must describe the artifact it accompanies: the adapter checks policies[pol].sha against the npz.
# Update path / sha / reason counts to the variant's own, and keep the ORIGINAL values inside for provenance.
import collections
TR = json.load(open(f"{src}/TARGET_RECEIPT.json"))
TR["DIAGNOSTIC_VARIANT"] = {"variant": VAR, "source_combo": src,
                            "note": "a configuration this pipeline cannot produce; hold-contract research arm",
                            "original_policies": {k: {"path": v.get("path"), "sha": v.get("sha"), "reasons": v.get("reasons")}
                                                  for k, v in TR.get("policies", {}).items()}}
for pol in ("scaled_diagnostic", "literal"):
    V = np.load(f"{OUTD}/{pol}.npz", allow_pickle=True)
    cnt = dict(collections.Counter(str(x) for x in V["reason"]))
    TR["policies"][pol]["path"] = f"{OUTD}/{pol}.npz"
    TR["policies"][pol]["sha"] = sha(f"{OUTD}/{pol}.npz")
    TR["policies"][pol]["reasons"] = cnt
json.dump(TR, open(f"{OUTD}/TARGET_RECEIPT.json", "w"), indent=2)
json.dump(rec, open(f"{OUTD}/FA_BVARIANT_RECEIPT.json", "w"), indent=2, default=float)
print("FA_BVARIANT %s %s s%s gate_fail=%s flipped=%s contract_fired=%s state_unchanged=%s"
      % (VAR, os.path.basename(ROOT), SEED,
         {k: v["gate_fail_anchors"] for k, v in rec["policies"].items()},
         {k: v["anchors_flipped_to_publish"] for k, v in rec["policies"].items()},
         all(v["contract_fired"] for v in rec["policies"].values()),
         all(v["state_chain_unchanged"] for v in rec["policies"].values())), flush=True)
