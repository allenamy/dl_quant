"""check_equiv_t3c.py — bitwise cross-check of a t3c artifact (verbatim health_check device, knobs off) against the archived health_check M1 artifact: four arrays array_equal + max|Δ| + config equal (HEALTH popped only for symmetry; the device is byte-identical so it would match anyway). usage: <mine.npz> <ref.npz> [label]"""
import numpy as np, json, hashlib, sys
a, b = sys.argv[1], sys.argv[2]; lab = sys.argv[3] if len(sys.argv) > 3 else ""
A = np.load(a, allow_pickle=True); B = np.load(b, allow_pickle=True); KEYS = ("d30_n2_c42_rec", "S0_rec", "d30_n2_c42_W", "S0_W")
eq = {k: bool(np.array_equal(A[k], B[k])) for k in KEYS}; mx = {k: float(np.max(np.abs(A[k].astype(np.float64) - B[k].astype(np.float64)))) if A[k].shape == B[k].shape else float("nan") for k in KEYS}
ca = json.loads(str(A["config_json"])); cb = json.loads(str(B["config_json"]))
for k in ("KMOD_F10", "KMOD", "KMOD_AGREE", "KTAIL"): assert ca.get(k) in (0, 0.0), f"identity requires knobs off: {k}={ca.get(k)}"
hs = (ca.get("HEALTH", {}).get("device_sha256"), cb.get("HEALTH", {}).get("device_sha256"))
for c in (ca, cb): c.pop("HEALTH", None)
ok = all(eq.values()) and ca == cb
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
print(f"{'PASS' if ok else 'FAIL'} [{lab}] {a} vs {b}: arrays_equal {eq} max_abs_diff {mx} config_equal={ca == cb} device_sha(mine,ref)={hs} sha(mine)={sha(a)} sha(ref)={sha(b)}")
if ca != cb: print("  config diff:", {k: (ca.get(k), cb.get(k)) for k in set(ca) | set(cb) if ca.get(k) != cb.get(k)})
sys.exit(0 if ok else 1)
