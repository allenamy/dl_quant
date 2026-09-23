#!/usr/bin/env python3
"""ens_combo_compare.py — positive control of ens_combo.py (prereg 45aba1f3f step 3): the wrapper run with --f10 s42 must reproduce the
researcher's combo_s42 array by array, bit for bit, for BOTH policy files (literal, scaled_diagnostic): same key set; E_ts / symbols / reason /
trade_mask array_equal; kc / fc / raw / weights equal as uint64 views (so ±0 and NaN payloads count). The receipts' per-policy reasons and
per-year publish counts must be equal too. File sha equality is reported (not required: np.savez_compressed stamps the zip members' mtime).
A red capability check runs first on a copy: one weight +1 ulp must make the comparator report NOT EQUAL (else the comparator is vacuous).
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B ens_combo_compare.py PATH,HOME,LC_CTYPE <ref_dir> <ref_scaled_sha> <ref_literal_sha>
       <new_dir> <out.json>
"""
import os, sys, json, time, hashlib

WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
import numpy as np

REF, RS, RL, NEW, OUT = sys.argv[2:7]
KEYS = {"E_ts", "symbols", "kc", "fc", "raw", "weights", "trade_mask", "reason"}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def cmp(A, B):
    if set(A) != KEYS or set(B) != KEYS: return {"equal": False, "why": f"key sets {sorted(A)} vs {sorted(B)}"}
    diffs = {}
    for k in sorted(KEYS):
        a, b = A[k], B[k]
        if a.dtype != b.dtype or a.shape != b.shape: diffs[k] = f"dtype/shape {a.dtype}{a.shape} vs {b.dtype}{b.shape}"; continue
        if a.dtype.kind == "f":
            ne = a.view(np.uint64) != b.view(np.uint64)
            if ne.any(): diffs[k] = f"{int(ne.sum())} elements differ bitwise"
        elif not np.array_equal(a, b): diffs[k] = "array_equal False"
    return {"equal": not diffs, "diffs": diffs}


rec = {"device": "ens_combo_compare.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "ref_dir": REF, "new_dir": NEW, "policies": {}}
want = {"scaled_diagnostic": RS, "literal": RL}
ok = True
for pol in ("scaled_diagnostic", "literal"):
    rp = os.path.join(REF, pol + ".npz"); npth = os.path.join(NEW, pol + ".npz")
    assert sha(rp) == want[pol], f"reference {pol} sha drift"
    A = dict(np.load(rp, allow_pickle=False)); B = dict(np.load(npth, allow_pickle=False))
    if pol == "scaled_diagnostic":                     # red capability check on a copy, before the real comparison
        Bm = {k: v.copy() for k, v in B.items()}; i, j = np.argwhere(Bm["weights"] != 0)[len(np.argwhere(Bm["weights"] != 0)) // 2]
        Bm["weights"][i, j] = np.nextafter(Bm["weights"][i, j], np.inf); red = cmp(A, Bm)
        rec["red_capability_one_ulp"] = {"reported_equal": red["equal"], "diffs": red["diffs"], "row": int(i), "col": int(j)}
        if red["equal"]: raise SystemExit("comparator is vacuous: +1 ulp reported equal")
    c = cmp(A, B); c["ref_sha256"] = want[pol]; c["new_sha256"] = sha(npth); c["file_sha_equal"] = c["ref_sha256"] == c["new_sha256"]
    c["n_anchors"] = int(len(A["E_ts"])); c["published"] = [int(A["trade_mask"].sum()), int(B["trade_mask"].sum())]
    rec["policies"][pol] = c; ok = ok and c["equal"]
RR = json.load(open(os.path.join(REF, "TARGET_RECEIPT.json"))); NR = json.load(open(os.path.join(NEW, "TARGET_RECEIPT.json")))
for pol in ("scaled_diagnostic", "literal"):
    same = RR["policies"][pol]["reasons"] == NR["policies"][pol]["reasons"] and RR["policies"][pol]["years"] == NR["policies"][pol]["years"]
    rec["policies"][pol]["receipt_reasons_and_years_equal"] = same; ok = ok and same
rec["VERDICT"] = "PASS" if ok else "FAIL"
json.dump(rec, open(OUT + ".tmp", "w"), indent=1); os.replace(OUT + ".tmp", OUT)
print(f"ENS_COMBO_COMPARE VERDICT={rec['VERDICT']} scaled_equal={rec['policies']['scaled_diagnostic']['equal']} literal_equal={rec['policies']['literal']['equal']} "
      f"red_capability_one_ulp_detected={not rec['red_capability_one_ulp']['reported_equal']} out_sha256={sha(OUT)}", flush=True)
sys.exit(0 if ok else 3)
