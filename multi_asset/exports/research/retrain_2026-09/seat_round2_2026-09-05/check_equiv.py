"""check_equiv.py — bitwise cross-check of a health_check artifact against a reference artifact (lead's required receipt):
all four arrays (d30_n2_c42_rec, S0_rec, d30_n2_c42_W, S0_W) array_equal + config_json equal minus the per-device self-report keys
(AXISB from w10_universe_seats.py; REF_SKIP; HEALTH / COSTB_JSON / COST_B / UMASK_SCOPE from w10_health.py; SEAT2 / SEATCOST_BPS / PHIDYN / PHIDYN_LOOK / PHIDYN_CLIP from w10_seat2.py — their default values are asserted by judge_seat2.py ARM_EXPECT). Read-only; prints only.
usage: check_equiv.py <mine.npz> <ref.npz> [label]   -> exit 0 on PASS"""
import numpy as np, json, hashlib, sys
a, b = sys.argv[1], sys.argv[2]; lab = sys.argv[3] if len(sys.argv) > 3 else ""
A = np.load(a, allow_pickle=True); B = np.load(b, allow_pickle=True)
KEYS = ("d30_n2_c42_rec", "S0_rec", "d30_n2_c42_W", "S0_W")
eq = {k: bool(np.array_equal(A[k], B[k])) for k in KEYS}
shapes = {k: (tuple(A[k].shape), tuple(B[k].shape)) for k in KEYS}
nanA = {k: int(np.isnan(A[k]).sum()) for k in KEYS}
ca = json.loads(str(A["config_json"])); cb = json.loads(str(B["config_json"]))
for c in (ca, cb):
    for k in ("AXISB", "REF_SKIP", "HEALTH", "COSTB_JSON", "COST_B", "UMASK_SCOPE", "SEAT2", "SEATCOST_BPS", "PHIDYN", "PHIDYN_LOOK", "PHIDYN_CLIP"): c.pop(k, None)
ok = all(eq.values()) and ca == cb
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
print(f"{'PASS' if ok else 'FAIL'} [{lab}] {a} vs {b}: arrays {eq} shapes {shapes} nan_in_mine {nanA} config_equal(minus self-report keys)={ca == cb} sha(mine)={sha(a)} sha(ref)={sha(b)}")
if ca != cb: print("  config diff:", {k: (ca.get(k), cb.get(k)) for k in set(ca) | set(cb) if ca.get(k) != cb.get(k)})
if not all(eq.values()):
    for k in KEYS:
        if not eq[k] and A[k].shape == B[k].shape:
            d = np.abs(A[k].astype(np.float64) - B[k].astype(np.float64)); print(f"  {k}: max|diff| {np.nanmax(d):.3e} n_diff {(d > 0).sum()}")
sys.exit(0 if ok else 1)
