"""check_equiv_dyn.py — AMENDMENT 2 receipts: my L-dyn K0/K1 artifacts (w10_universe_recheck.py, dev/ + dev_alt/) vs axisB R0 artifacts (w10_universe_seats.py)
and vs rolling_king Ldyn artifacts; bitwise on the four arrays; config equal minus REF_SKIP / AXISB keys. Read-only; prints only."""
import numpy as np, json, hashlib, os
ROOT = "/workspace/review_scratch/cadence_seats/axisA"; RK = "/workspace/review_scratch/rolling_king"; AB = "/workspace/review_scratch/cadence_seats/axisB"
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
allok = True; n = 0
for king in ("pinned", "rollm"):
    for cal, d in (("log", "dev"), ("prod", "dev_alt")):
        for seed in ("s42", "s2027"):
            mine = f"{ROOT}/{d}/probe_artifacts/w10_ablation_series_Ldyn_{king}_{cal}_{seed}.npz"
            for desc, ref in ((f"axisB R0 {king} {cal} {seed}", f"{AB}/{d}/probe_artifacts/w10_ablation_series_R0_{king}_{cal}_{seed}.npz"),
                              (f"rolling_king Ldyn {king} {cal} {seed}", f"{RK}/{d}/probe_artifacts/w10_ablation_series_Ldyn_{king}_{cal}_{seed}.npz")):
                if not os.path.exists(mine): print(f"MISSING {mine}"); allok = False; continue
                if not os.path.exists(ref): print(f"NOREF {ref}"); continue
                A = np.load(mine, allow_pickle=True); B = np.load(ref, allow_pickle=True)
                eq = {k: bool(np.array_equal(A[k], B[k])) for k in ("d30_n2_c42_rec", "S0_rec", "d30_n2_c42_W", "S0_W")}
                ca = json.loads(str(A["config_json"])); cb = json.loads(str(B["config_json"]))
                for k in ("REF_SKIP", "AXISB"): ca.pop(k, None); cb.pop(k, None)
                ok = all(eq.values()) and ca == cb; allok &= ok; n += 1
                print(f"{'PASS' if ok else 'FAIL'} [{desc}] {eq} config_equal(minus REF_SKIP/AXISB)={ca == cb} sha(mine)={sha(mine)} sha(ref)={sha(ref)}")
                if ca != cb: print("   config diff:", {k: (ca.get(k), cb.get(k)) for k in set(ca) | set(cb) if ca.get(k) != cb.get(k)})
print("ALL_EQUIV_DYN", allok, "n", n)
