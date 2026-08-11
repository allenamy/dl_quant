"""Causality sentinel for the npz_spot-sourced X_basis build (pure-function, no cache
mutation). Corrupt the per-second perp/spot return+obi series STRICTLY AFTER a cut
second C; rebuild X_basis; assert every window whose pred_sec <= C is byte-identical.
Proves the reconstruction + sampling are <= t (leak-free) with the NEW source."""
import os, sys
import numpy as np
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
sys.path.insert(0, MA)
import multi_asset.data.add_basis_dynamics as ab
ab.NPZV4_DIR = os.path.join(MA, "data", "npz_spot")
ab.PERP_DIR = os.path.join(MA, "data", "npz_perp")
ab.DUAL_DIR = os.path.join(MA, "data", "npz_v2arch")

def run(day):
    cur = ab._day_series(day)
    if cur is None:
        print(f"{day}: no-series"); return
    ts_sec, secg, pret, sret, pobi, sobi = cur
    base = np.load(os.path.join(ab.DUAL_DIR, f"{day}.npz"), allow_pickle=True)
    pred_secs = base["timestamps"].astype(np.int64) // ab.US
    Xb0 = ab._build_basis(pret, sret, pobi, sobi, pred_secs, secg)
    # cut at the median present second
    C = int(np.median(secg))
    fut = secg > C
    rng = np.random.default_rng(0)
    pret_c = pret.copy(); sret_c = sret.copy(); pobi_c = pobi.copy(); sobi_c = sobi.copy()
    for arr in (pret_c, sret_c, pobi_c, sobi_c):
        arr[fut] = rng.standard_normal(fut.sum()) * 1e3 + 1e6   # wild corruption AFTER C
    Xb1 = ab._build_basis(pret_c, sret_c, pobi_c, sobi_c, pred_secs, secg)
    le = pred_secs <= C                # windows ending at/before the cut
    gt = pred_secs > C
    n_le = int(le.sum())
    changed_le = int((Xb0[le] != Xb1[le]).any(axis=(1, 2)).sum()) if n_le else 0
    # windows AFTER the cut SHOULD change (sanity that corruption is effective)
    changed_gt = int((Xb0[gt] != Xb1[gt]).any(axis=(1, 2)).sum()) if gt.any() else 0
    ok = (changed_le == 0) and (changed_gt > 0)
    print(f"{day}: cut@{C}  windows<=C={n_le} changed<=C={changed_le} (want 0) | "
          f"windows>C={int(gt.sum())} changed>C={changed_gt} (want >0) -> "
          f"{'LEAK-FREE' if ok else 'CHECK'}")
    return ok

allok = True
for d in ["2026-01-15", "2025-10-15", "2026-01-10"]:
    allok &= bool(run(d))
print("SENTINEL:", "ALL LEAK-FREE" if allok else "REVIEW")
