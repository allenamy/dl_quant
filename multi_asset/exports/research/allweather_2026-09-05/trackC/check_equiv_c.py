"""check_equiv_c.py — bitwise cross-check of a Track C artifact against a health_check reference artifact (identity receipt for AGEW=0):
all four arrays (d30_n2_c42_rec, S0_rec, d30_n2_c42_W, S0_W) array_equal + config_json equal minus the per-device self-report keys
(HEALTH/COSTB_JSON/COST_B/UMASK_SCOPE from w10_health.py are kept in BOTH so they are compared; the Track C self-report keys AGEW/AGE_DAYS/TRACKC are popped and AGEW==0 asserted).
Copied from seat_round2/check_equiv.py; prints max|Δ| per array. Read-only; prints only. usage: check_equiv_c.py <mine.npz> <ref.npz> [label] -> exit 0 on PASS"""
import numpy as np, json, hashlib, sys
a, b = sys.argv[1], sys.argv[2]; lab = sys.argv[3] if len(sys.argv) > 3 else ""
A = np.load(a, allow_pickle=True); B = np.load(b, allow_pickle=True)
KEYS = ("d30_n2_c42_rec", "S0_rec", "d30_n2_c42_W", "S0_W")
eq = {k: bool(np.array_equal(A[k], B[k])) for k in KEYS}
mx = {k: (float(np.max(np.abs(A[k].astype(np.float64) - B[k].astype(np.float64)))) if A[k].shape == B[k].shape else float("nan")) for k in KEYS}
ca = json.loads(str(A["config_json"])); cb = json.loads(str(B["config_json"]))
assert ca.get("AGEW", 0.0) == 0.0, f"identity check requires AGEW=0, got {ca.get('AGEW')}"
for c in (ca, cb):
    for k in ("AGEW", "AGE_DAYS", "TRACKC", "HEALTH"): c.pop(k, None)   # HEALTH carries the device sha (differs by construction); everything else incl. COST_B/UMASK_SCOPE must match
ok = all(eq.values()) and ca == cb
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
print(f"{'PASS' if ok else 'FAIL'} [{lab}] {a} vs {b}: arrays_equal {eq} max_abs_diff {mx} shapes {[tuple(A[k].shape) for k in KEYS]} config_equal(minus self-report keys)={ca == cb} sha(mine)={sha(a)} sha(ref)={sha(b)}")
if ca != cb: print("  config diff:", {k: (ca.get(k), cb.get(k)) for k in set(ca) | set(cb) if ca.get(k) != cb.get(k)})
sys.exit(0 if ok else 1)
