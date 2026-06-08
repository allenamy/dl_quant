"""Root-cause diagnostic for the A2 negative-Pearson red flag.
Does weak signal exist at the feature level? Is negative Pearson an outlier artifact?"""
import numpy as np, json, os.path as p
from scipy.stats import pearsonr, spearmanr

CACHE = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/panel_cache"
names = json.load(open(p.join(CACHE, "feature_names.json")))

def wins(a, q=0.005):
    lo, hi = np.quantile(a, [q, 1 - q])
    return np.clip(a, lo, hi)

for sym in ["bnfbtc", "bnfeth", "bnffil"]:
    d = np.load(p.join(CACHE, f"{sym}.npz"))
    X, y, clean = d["X"], d["y"], d["clean600"]
    m = clean & np.isfinite(y) & np.isfinite(X).all(1)
    Xc, yc = X[m], y[m]
    exk = ((yc - yc.mean())**4).mean() / yc.var()**2 - 3
    print(f"\n===== {sym}: clean n={m.sum()}, y_std={yc.std()*1e4:.2f}bps, excess_kurt={exk:.1f} =====")
    rows = []
    for i, nm in enumerate(names):
        f = Xc[:, i]
        if f.std() < 1e-12:
            continue
        pr = pearsonr(f, yc)[0]
        sp = spearmanr(f, yc)[0]
        prw = pearsonr(wins(f), wins(yc))[0]
        rows.append((nm, pr, sp, prw))
    rows.sort(key=lambda r: -abs(r[2]))
    print(f"{'feature':26s} {'Pear':>8s} {'Spear':>8s} {'PearWins':>9s}")
    for nm, pr, sp, prw in rows[:12]:
        print(f"{nm:26s} {pr:>+8.4f} {sp:>+8.4f} {prw:>+9.4f}")
    print(f"max|Spear|={max(abs(r[2]) for r in rows):.4f}  "
          f"#|Spear|>0.02={sum(abs(r[2])>0.02 for r in rows)}  "
          f"mean Pear={np.mean([r[1] for r in rows]):+.4f} vs PearWins={np.mean([r[3] for r in rows]):+.4f}")
