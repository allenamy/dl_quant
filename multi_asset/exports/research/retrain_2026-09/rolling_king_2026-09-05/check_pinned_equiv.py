"""check_pinned_equiv.py — bitwise cross-check of my pinned-king arms against pre-existing artifacts with identical config
(port_w10 probe_artifacts, refute_C6_2 altrun/newprod, combo_recheck dev_alt). Read-only; prints only."""
import numpy as np, json, hashlib, os
ROOT = "/workspace/review_scratch/rolling_king"
PAIRS = [
 ("dev/probe_artifacts/w10_ablation_series_Lfix_pinned_log_s42.npz", "/workspace/port_w10/probe_artifacts/w10_ablation_series_pod_live_w3fix_callog_s42.npz"),
 ("dev/probe_artifacts/w10_ablation_series_Ldyn_pinned_log_s42.npz", "/workspace/port_w10/probe_artifacts/w10_ablation_series_pod_live_callog_s42.npz"),
 ("dev/probe_artifacts/w10_ablation_series_Ldyn_pinned_log_s2027.npz", "/workspace/port_w10/probe_artifacts/w10_ablation_series_pod_live_callog_s2027.npz"),
 ("dev/probe_artifacts/w10_ablation_series_Cdyn_pinned_log_s42.npz", "/workspace/port_w10/probe_artifacts/w10_ablation_series_pod_canon_callog_s42.npz"),
 ("dev_alt/probe_artifacts/w10_ablation_series_Lfix_pinned_prod_s42.npz", "/workspace/review_scratch/refute_C6_2/altrun/newprod/probe_artifacts/w10_ablation_series_alt_newprod_w3fix.npz"),
 ("dev_alt/probe_artifacts/w10_ablation_series_Ldyn_pinned_prod_s42.npz", "/workspace/review_scratch/refute_C6_2/altrun/newprod/probe_artifacts/w10_ablation_series_alt_newprod_dyn.npz"),
 ("dev_alt/probe_artifacts/w10_ablation_series_Cdyn_pinned_prod_s42.npz", "/workspace/review_scratch/combo_recheck/dev_alt/probe_artifacts/w10_ablation_series_D_prod_s42.npz"),
]
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
allok = True
for a, b in PAIRS:
    pa = f"{ROOT}/{a}"
    if not os.path.exists(pa): print(f"MISSING {a}"); allok = False; continue
    A = np.load(pa, allow_pickle=True); B = np.load(b, allow_pickle=True)
    eq = {k: bool(np.array_equal(A[k], B[k])) for k in ("d30_n2_c42_rec", "S0_rec", "d30_n2_c42_W", "S0_W")}
    ca = json.loads(str(A["config_json"])); cb = json.loads(str(B["config_json"])); ca.pop("REF_SKIP", None); cb.pop("REF_SKIP", None)
    ok = all(eq.values()) and ca == cb; allok &= ok
    print(f"{'PASS' if ok else 'FAIL'} {a} vs {b}: {eq} config_equal(minus REF_SKIP)={ca == cb} sha(mine)={sha(pa)} sha(ref)={sha(b)}")
print("ALL_PINNED_EQUIV", allok)
print("NEW (no pre-existing counterpart): dev_alt/probe_artifacts/w10_ablation_series_Ldyn_pinned_prod_s2027.npz exists =", os.path.exists(f"{ROOT}/dev_alt/probe_artifacts/w10_ablation_series_Ldyn_pinned_prod_s2027.npz"))
