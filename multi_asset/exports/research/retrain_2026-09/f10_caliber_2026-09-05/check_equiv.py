"""check_equiv.py — bitwise cross-check of an f10_caliber artifact against a health_check reference artifact (PREREG §2 receipt).
Copied from health_check/check_equiv.py; additionally pops UMASK_NPZ (my layout uses a byte-identical copy of the mask file at a different path —
the copy's sha256 equality vs the health_check original is asserted separately in setup.sh / REPORT) and prints the four-array equality.
usage: check_equiv.py <mine.npz> <ref.npz> [label]   -> exit 0 on PASS"""
import numpy as np, json, hashlib, sys
a, b = sys.argv[1], sys.argv[2]; lab = sys.argv[3] if len(sys.argv) > 3 else ""
A = np.load(a, allow_pickle=True); B = np.load(b, allow_pickle=True)
KEYS = ("d30_n2_c42_rec", "S0_rec", "d30_n2_c42_W", "S0_W")
eq = {k: bool(np.array_equal(A[k], B[k])) for k in KEYS}
shapes = {k: (tuple(A[k].shape), tuple(B[k].shape)) for k in KEYS}
nanA = {k: int(np.isnan(A[k]).sum()) for k in KEYS}
ca = json.loads(str(A["config_json"])); cb = json.loads(str(B["config_json"]))
dev_sha = (ca.get("HEALTH", {}).get("device_sha256"), cb.get("HEALTH", {}).get("device_sha256"))
for c in (ca, cb):
    for k in ("AXISB", "REF_SKIP", "HEALTH", "COSTB_JSON", "COST_B", "UMASK_SCOPE", "UMASK_NPZ"): c.pop(k, None)
ok = all(eq.values()) and ca == cb and dev_sha[0] == dev_sha[1]
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
print(f"{'PASS' if ok else 'FAIL'} [{lab}] {a} vs {b}: arrays {eq} shapes {shapes} nan_in_mine {nanA} config_equal(minus self-report/path keys)={ca == cb} device_sha_equal={dev_sha[0] == dev_sha[1]} ({str(dev_sha[0])[:16]}) sha(mine)={sha(a)} sha(ref)={sha(b)}")
if ca != cb: print("  config diff:", {k: (ca.get(k), cb.get(k)) for k in set(ca) | set(cb) if ca.get(k) != cb.get(k)})
if not all(eq.values()):
    for k in KEYS:
        if not eq[k] and A[k].shape == B[k].shape:
            d = np.abs(A[k].astype(np.float64) - B[k].astype(np.float64)); print(f"  {k}: max|diff| {np.nanmax(d):.3e} n_diff {(d > 0).sum()}")
sys.exit(0 if ok else 1)
