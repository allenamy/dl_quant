"""Deploy-caliber compare: basis_2026_01 vs d1_2026_01_run1 (and basis_2025_10 vs
d1_2025_10_run1 when it lands). Reuses score_align's EXACT operators:
 raw cd = _cd(q50, y)                 -> reproduces statusline gate cd
 deploy cd = _cd(_demean_1h(q50), y)  -> decisive, slow-band-immune
 deploy health = _health(_demean_1h(q50), y): beta, sigma-ratio, DENSE
y = test_preds['targets'] (clipped-normalized y_600); same operator+target on BOTH folds
so the deploy ΔP is apples-to-apples. Corr is affine-invariant so normalized q50/y are fine.
"""
import os, sys
import numpy as np
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
sys.path.insert(0, MA)
from multi_asset.model.score_align import _cd, _demean_1h, _pear  # exact operators

def score(tag, ckpt):
    fp = f"{MA}/experiments/d1gate/{tag}/fold_0/{ckpt}.npz"
    z = np.load(fp, allow_pickle=True)
    q = z["predictions"][:, 1].astype(np.float64)
    y = z["targets"].astype(np.float64)
    ts = z["timestamps"].astype(np.int64)
    m = z["mask"].astype(bool) if "mask" in z.files else np.ones(len(q), bool)
    q, y, ts = q[m], y[m], ts[m]
    raw_cd, nd = _cd(q, y, ts)
    qdm = _demean_1h(q, ts)
    dep_cd, ndd = _cd(qdm, y, ts)
    # DENSE (all-row) health, matching statusline_d1.py convention (beta=cov(y,q)/var(q))
    def dense_health(p):
        pc = p - p.mean(); v = float((pc * pc).sum())
        beta = float((pc * (y - y.mean())).sum() / v) if v > 0 else float("nan")
        sr = float(p.std() / (y.std() + 1e-12))
        dense = _pear(p, y)
        return beta, sr, dense
    rb, rsr, rdense = dense_health(q)      # RAW dense (reproduces statusline beta/sigma/DENSE)
    db, dsr, ddense = dense_health(qdm)    # DEPLOY dense
    return dict(raw_cd=raw_cd, dep_cd=dep_cd, nd=nd,
                raw_beta=rb, raw_sr=rsr, raw_dense=rdense,
                dep_beta=db, dep_sr=dsr, dep_dense=ddense)

def run(basis_tag, run1_tag, label):
    print(f"\n===== {label}: {basis_tag} vs {run1_tag} =====")
    for ckpt in ["ema_test_preds", "test_preds"]:
        try:
            b = score(basis_tag, ckpt); r = score(run1_tag, ckpt)
        except FileNotFoundError as e:
            print(f"  [{ckpt}] MISSING: {e}"); continue
        ck = "EMA " if ckpt.startswith("ema") else "BEST"
        print(f"  --- {ck} ---")
        print(f"    RAW    cd: basis {b['raw_cd']:+.4f}  run1 {r['raw_cd']:+.4f}  ΔP {b['raw_cd']-r['raw_cd']:+.4f}   (gate caliber)")
        print(f"    DEPLOY cd: basis {b['dep_cd']:+.4f}  run1 {r['dep_cd']:+.4f}  ΔP {b['dep_cd']-r['dep_cd']:+.4f}   (decisive, slow-band-immune)")
        print(f"    basis DEPLOY health: beta {b['dep_beta']:+.3f}  sr {b['dep_sr']:.3f}  DENSE {b['dep_dense']:+.4f}")
        print(f"    run1  DEPLOY health: beta {r['dep_beta']:+.3f}  sr {r['dep_sr']:.3f}  DENSE {r['dep_dense']:+.4f}")
        print(f"    basis RAW   health: beta {b['raw_beta']:+.3f}  sr {b['raw_sr']:.3f}  DENSE {b['raw_dense']:+.4f}")
        print(f"    run1  RAW   health: beta {r['raw_beta']:+.3f}  sr {r['raw_sr']:.3f}  DENSE {r['raw_dense']:+.4f}  (days={r['nd']})")

if __name__ == "__main__":
    run("basis_2026_01", "d1_2026_01_run1", "DRIFT 2026-01")
    # strong lands later:
    if os.path.exists(f"{MA}/experiments/d1gate/basis_2025_10/fold_0/ema_test_preds.npz"):
        run("basis_2025_10", "d1_2025_10_run1", "STRONG 2025-10")
