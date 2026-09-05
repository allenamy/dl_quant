"""check_equiv.py <pinned|rollm> — bitwise cross-check of axisA L-fix artifacts against pre-existing identical-config artifacts
(port_w10 probe baseline = PREREG 作废条件; rolling_king dev/dev_alt; refute_C6_2 altrun). Read-only; prints only."""
import numpy as np, json, hashlib, os, sys
ROOT = "/workspace/review_scratch/cadence_seats/axisA"; RK = "/workspace/review_scratch/rolling_king"
PAIRS = {
 "pinned": [
  ("dev/probe_artifacts/w10_ablation_series_Lfix_pinned_log_s42.npz", "/workspace/port_w10/probe_artifacts/w10_ablation_series_pod_live_w3fix_callog_s42.npz", "PORT BASELINE (prereg voiding condition)"),
  ("dev/probe_artifacts/w10_ablation_series_Lfix_pinned_log_s42.npz", f"{RK}/dev/probe_artifacts/w10_ablation_series_Lfix_pinned_log_s42.npz", "rolling_king dev pinned"),
  ("dev_alt/probe_artifacts/w10_ablation_series_Lfix_pinned_prod_s42.npz", f"{RK}/dev_alt/probe_artifacts/w10_ablation_series_Lfix_pinned_prod_s42.npz", "rolling_king dev_alt pinned"),
  ("dev_alt/probe_artifacts/w10_ablation_series_Lfix_pinned_prod_s42.npz", "/workspace/review_scratch/refute_C6_2/altrun/newprod/probe_artifacts/w10_ablation_series_alt_newprod_w3fix.npz", "refute_C6_2 alt_newprod_w3fix"),
 ],
 "rollm": [
  ("dev/probe_artifacts/w10_ablation_series_Lfix_rollm_log_s42.npz", f"{RK}/dev/probe_artifacts/w10_ablation_series_Lfix_rollm_log_s42.npz", "rolling_king dev K1 (log)"),
  ("dev_alt/probe_artifacts/w10_ablation_series_Lfix_rollm_prod_s42.npz", f"{RK}/dev_alt/probe_artifacts/w10_ablation_series_Lfix_rollm_prod_s42.npz", "rolling_king dev_alt K1 (prod)"),
 ]}
which = sys.argv[1] if len(sys.argv) > 1 else "pinned"
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
allok = True
for a, b, desc in PAIRS[which]:
    pa = f"{ROOT}/{a}"
    if not os.path.exists(pa): print(f"MISSING {a}"); allok = False; continue
    A = np.load(pa, allow_pickle=True); B = np.load(b, allow_pickle=True)
    eq = {k: bool(np.array_equal(A[k], B[k])) for k in ("d30_n2_c42_rec", "S0_rec", "d30_n2_c42_W", "S0_W")}
    ca = json.loads(str(A["config_json"])); cb = json.loads(str(B["config_json"])); ca.pop("REF_SKIP", None); cb.pop("REF_SKIP", None)
    ok = all(eq.values()) and ca == cb; allok &= ok
    print(f"{'PASS' if ok else 'FAIL'} [{desc}] {a} vs {b}: {eq} config_equal(minus REF_SKIP)={ca == cb} sha(mine)={sha(pa)} sha(ref)={sha(b)}")
    if ca != cb: print("   config diff:", {k: (ca.get(k), cb.get(k)) for k in set(ca) | set(cb) if ca.get(k) != cb.get(k)})
print(f"ALL_EQUIV[{which}]", allok)
