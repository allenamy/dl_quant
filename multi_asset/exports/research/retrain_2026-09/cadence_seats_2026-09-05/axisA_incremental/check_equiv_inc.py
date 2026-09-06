"""check_equiv_inc.py — receipts: my K1 (rollm) reruns in axisA_incremental (L-dyn 4 cells + L-fix 2 cells) vs axisA's archived artifacts: four arrays bitwise + config equal minus REF_SKIP. Read-only; prints only."""
import numpy as np, json, hashlib, os
ROOT = "/workspace/review_scratch/cadence_seats/axisA_incremental"; AXA = "/workspace/review_scratch/cadence_seats/axisA"
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
allok = True; n = 0
for form, seeds in (("Ldyn", ("s42", "s2027")), ("Lfix", ("s42",))):
    for cal, d in (("log", "dev"), ("prod", "dev_alt")):
        for seed in seeds:
            mine = f"{ROOT}/{d}/probe_artifacts/w10_ablation_series_{form}_rollm_{cal}_{seed}.npz"; ref = f"{AXA}/{d}/probe_artifacts/w10_ablation_series_{form}_rollm_{cal}_{seed}.npz"
            if not os.path.exists(mine) or not os.path.exists(ref): print(f"MISSING {mine if not os.path.exists(mine) else ref}"); allok = False; continue
            A = np.load(mine, allow_pickle=True); B = np.load(ref, allow_pickle=True)
            eq = {k: bool(np.array_equal(A[k], B[k])) for k in ("d30_n2_c42_rec", "S0_rec", "d30_n2_c42_W", "S0_W")}
            ca = json.loads(str(A["config_json"])); cb = json.loads(str(B["config_json"])); ca.pop("REF_SKIP", None); cb.pop("REF_SKIP", None)
            ok = all(eq.values()) and ca == cb; allok &= ok; n += 1
            print(f"{'PASS' if ok else 'FAIL'} [{form} rollm {cal} {seed}] {eq} config_equal={ca == cb} sha(mine)={sha(mine)} sha(axisA)={sha(ref)}")
            if ca != cb: print("   config diff:", {k: (ca.get(k), cb.get(k)) for k in set(ca) | set(cb) if ca.get(k) != cb.get(k)})
print("ALL_EQUIV_INC", allok, "n", n)
