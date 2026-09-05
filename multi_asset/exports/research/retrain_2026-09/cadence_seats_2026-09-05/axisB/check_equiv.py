"""check_equiv.py — bitwise cross-check of axis-B R0 artifacts (WRULE=msharpe LOOK=900, produced by w10_universe_seats.py) against
pre-existing identical-config artifacts: the port dynamic live form (lead's required receipt) and rolling_king's Ldyn arms (R0 baseline reuse check).
Read-only; prints only. config_json compared minus the keys AXISB (new self-report block) and REF_SKIP (absent in the port original)."""
import numpy as np, json, hashlib, os
ROOT = "/workspace/review_scratch/cadence_seats/axisB"; RK = "/workspace/review_scratch/rolling_king"
PAIRS = [("dev/probe_artifacts/w10_ablation_series_R0_pinned_log_s42.npz", "/workspace/port_w10/probe_artifacts/w10_ablation_series_pod_live_callog_s42.npz", "PORT dynamic live form s42 (required receipt)"),
         ("dev/probe_artifacts/w10_ablation_series_R0_pinned_log_s2027.npz", "/workspace/port_w10/probe_artifacts/w10_ablation_series_pod_live_callog_s2027.npz", "PORT dynamic live form s2027")]
for king in ("pinned", "rollm"):
    for cal, d in (("log", "dev"), ("prod", "dev_alt")):
        for seed in ("s42", "s2027"):
            PAIRS.append((f"{d}/probe_artifacts/w10_ablation_series_R0_{king}_{cal}_{seed}.npz", f"{RK}/{d}/probe_artifacts/w10_ablation_series_Ldyn_{king}_{cal}_{seed}.npz", "rolling_king Ldyn = R0 baseline"))
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
allok = True; n = 0
for a, b, what in PAIRS:
    pa = f"{ROOT}/{a}"
    if not os.path.exists(pa): print(f"MISSING {a}"); continue
    A = np.load(pa, allow_pickle=True); B = np.load(b, allow_pickle=True)
    eq = {k: bool(np.array_equal(A[k], B[k])) for k in ("d30_n2_c42_rec", "S0_rec", "d30_n2_c42_W", "S0_W")}
    ca = json.loads(str(A["config_json"])); cb = json.loads(str(B["config_json"])); ax = ca.pop("AXISB", None); ca.pop("REF_SKIP", None); cb.pop("REF_SKIP", None)
    ok = all(eq.values()) and ca == cb; allok &= ok; n += 1
    print(f"{'PASS' if ok else 'FAIL'} [{what}] {a} vs {b}: {eq} config_equal(minus AXISB/REF_SKIP)={ca == cb} device_sha={ax['device_sha256'][:16] if ax else None} sha(mine)={sha(pa)} sha(ref)={sha(b)}")
print("ALL_EQUIV", allok, "n", n)
