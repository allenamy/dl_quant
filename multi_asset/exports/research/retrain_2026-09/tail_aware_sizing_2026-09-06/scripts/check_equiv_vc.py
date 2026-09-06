"""check_equiv_vc.py — identity receipt for VOLCAP_GAMMA=0 (PREREG_tail_aware_sizing §1, same form as Track C check_equiv_c.py): all four arrays
(d30_n2_c42_rec, S0_rec, d30_n2_c42_W, S0_W) np.array_equal against the health_check reference artifact M1_UPIT_<cal>_s<seed>_ccal, and config_json
equal after popping the per-device self-report keys (VOLCAP_GAMMA/VOLCAP_WIN/VOLCAP_MIN_N/VOLCAP/HEALTH); VOLCAP_GAMMA==0 asserted.
usage: check_equiv_vc.py <mine.npz> <ref.npz> [label] -> exit 0 on PASS"""
import numpy as np, json, hashlib, sys
a, b = sys.argv[1], sys.argv[2]; lab = sys.argv[3] if len(sys.argv) > 3 else ""
A = np.load(a, allow_pickle=True); B = np.load(b, allow_pickle=True)
KEYS = ("d30_n2_c42_rec", "S0_rec", "d30_n2_c42_W", "S0_W")
eq = {k: bool(np.array_equal(A[k], B[k])) for k in KEYS}
mx = {k: (float(np.max(np.abs(A[k].astype(np.float64) - B[k].astype(np.float64)))) if A[k].shape == B[k].shape else float("nan")) for k in KEYS}
ca = json.loads(str(A["config_json"])); cb = json.loads(str(B["config_json"]))
assert ca.get("VOLCAP_GAMMA", 0.0) == 0.0, f"identity check requires VOLCAP_GAMMA=0, got {ca.get('VOLCAP_GAMMA')}"
for c in (ca, cb):
    for k in ("VOLCAP_GAMMA", "VOLCAP_WIN", "VOLCAP_MIN_N", "VOLCAP", "HEALTH"): c.pop(k, None)
ok = all(eq.values()) and ca == cb
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
print(f"{'PASS' if ok else 'FAIL'} [{lab}] {a} vs {b}: arrays_equal {eq} max_abs_diff {mx} shapes {[tuple(A[k].shape) for k in KEYS]} config_equal(minus self-report keys)={ca == cb} sha(mine)={sha(a)} sha(ref)={sha(b)}")
if ca != cb: print("  config diff:", {k: (ca.get(k), cb.get(k)) for k in set(ca) | set(cb) if ca.get(k) != cb.get(k)})
sys.exit(0 if ok else 1)
