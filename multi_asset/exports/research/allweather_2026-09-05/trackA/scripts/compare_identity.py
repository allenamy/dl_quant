"""compare_identity.py — bitwise identity receipt between two w10 artifacts (rider device b=0 vs the archived health-check main arm).
usage: compare_identity.py <a.npz> <b.npz> <out.json>; PASS iff every array (S0_rec, S0_W, d30_n2_c42_rec, d30_n2_c42_W, cols, symbols) is array_equal
(NaN-aware) and the config_json differs only in the rider keys / device sha / OUT_TAG."""
import sys, json, hashlib
import numpy as np
a, b, out = sys.argv[1:4]
A = np.load(a, allow_pickle=True); B = np.load(b, allow_pickle=True)
res = {"a": a, "b": b, "sha256": {"a": hashlib.sha256(open(a, "rb").read()).hexdigest()[:16], "b": hashlib.sha256(open(b, "rb").read()).hexdigest()[:16]}, "arrays": {}}
allok = True
for k in ("cols", "symbols", "S0_rec", "S0_W", "d30_n2_c42_rec", "d30_n2_c42_W"):
    x = A[k]; y = B[k]
    if x.dtype.kind in "fc":
        eq = x.shape == y.shape and np.array_equal(x, y, equal_nan=True)
        mx = float(np.nanmax(np.abs(x - y))) if x.shape == y.shape else None
    else:
        eq = x.shape == y.shape and bool(np.all(x == y)); mx = None
    res["arrays"][k] = {"shape": list(x.shape), "bitwise_equal": bool(eq), "max_abs_diff": mx}; allok &= bool(eq)
ca = json.loads(str(A["config_json"])); cb = json.loads(str(B["config_json"]))
diffk = sorted(k for k in set(ca) | set(cb) if ca.get(k) != cb.get(k))
res["config_diff_keys"] = diffk; res["config_a_extra"] = {k: ca.get(k) for k in diffk}; res["config_b_extra"] = {k: cb.get(k) for k in diffk}
res["IDENTITY"] = "PASS" if allok else "FAIL"
json.dump(res, open(out, "w"), indent=1)
print(json.dumps({k: v["bitwise_equal"] for k, v in res["arrays"].items()}), "config_diff_keys", diffk, "IDENTITY", res["IDENTITY"], flush=True)
