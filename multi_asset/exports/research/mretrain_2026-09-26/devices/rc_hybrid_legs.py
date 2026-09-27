"""rc_hybrid_legs.py — (3b) single-condition legs for the King root-cause question (dlarch's request, fresh2 2026-09-27; DESCRIPTIVE).
  SEAT_ONLY : in-service A0_m0 legs with the seat weights WL taken from the RED (shuffled-King) legs  -> seats change, book King rank does not
  COMP_ONLY : in-service A0_m0 legs with the King rank KZ taken from the RED legs                  -> book King rank changes, seats do not
First every array of the two legs files is compared; the arrays that differ must be a subset of {KZ, LR, WL} (LR = leg returns, read
only by the seat computation, never by the combo; kept from A0 in both hybrids and named). Any other differing array => stop: the two
single conditions would not be defined. Writes <W>/work/legs.npz and <W>/receipts/P3_LEGS.json (mr_combo checks sha256 == the file).
usage: python rc_hybrid_legs.py <A0 legs> <RED legs> <W_seat_only> <W_comp_only>"""
import os, sys, json, hashlib
import numpy as np
A0p, REDp, WS, WC = sys.argv[1:5]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


a, r = np.load(A0p), np.load(REDp); assert sorted(a.files) == sorted(r.files)
same = lambda x, y: x.dtype == y.dtype and x.shape == y.shape and x.tobytes() == y.tobytes()
diff = sorted(k for k in a.files if not same(a[k], r[k]))
print("RC_HYBRID_LEGS differing arrays A0 vs RED:", diff, flush=True)
extra = sorted(set(diff) - {"KZ", "LR", "WL"})
if extra: print("RC_HYBRID_LEGS FAIL: arrays other than KZ/LR/WL differ:", extra, flush=True); sys.exit(1)
for W, name, swap in ((WS, "SEAT_ONLY", "WL"), (WC, "COMP_ONLY", "KZ")):
    d = {k: (r[k] if k == swap else a[k]) for k in a.files}
    os.makedirs(f"{W}/work", exist_ok=True); os.makedirs(f"{W}/receipts", exist_ok=True)
    out = f"{W}/work/legs.npz"; np.savez(out[:-4] + ".tmp.npz", **d); os.replace(out[:-4] + ".tmp.npz", out)
    chk = np.load(out); assert all(same(chk[k], d[k]) for k in a.files)
    rec = {"status": f"RC_HYBRID_{name}_DESCRIPTIVE", "output": out, "sha256": sha(out), "from_A0": {"path": A0p, "sha256": sha(A0p)},
           "from_RED": {"path": REDp, "sha256": sha(REDp)}, "array_taken_from_RED": swap, "arrays_differing_A0_vs_RED": diff,
           "LR_note": "LR (leg returns) kept from A0: the combo never reads it; the seat effect enters only through WL",
           "self_sha256": sha(os.path.abspath(__file__))}
    json.dump(rec, open(f"{W}/receipts/P3_LEGS.json", "w"), indent=1)
    print("RC_HYBRID_LEGS", name, rec["sha256"][:16], flush=True)
print("RC_HYBRID_LEGS DONE", flush=True)
