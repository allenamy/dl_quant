# SMOKE diagnostic on SYNTHETIC returns only (L2_smoke2 / L2_smoke3 data files built from noise y4): feature-vs-target association.
import numpy as np, sys
from scipy.stats import rankdata
for S in ("L2_smoke2", "L2_smoke3"):
    Z = np.load("/workspace/uplift_r3_2026-09-13/%s/out/L2_B_data_s42.npz" % S)
    I = Z["i"]; YR = Z["year"]; F = Z["F"]; feats = [str(x) for x in Z["feats"]]
    for T in ("A", "B"):
        r = Z["r" + T]; ok = (YR >= 2023) & np.isfinite(r)
        ii = I[ok]; rr = r[ok]; FF = F[ok]
        uniq, st, ct = np.unique(ii, return_index=True, return_counts=True)
        res = {f: [] for f in feats}
        for q in range(0, uniq.size, 7):
            sl = slice(st[q], st[q] + ct[q])
            if ct[q] < 10: continue
            y = rankdata(rr[sl]); y -= y.mean()
            for c, f in enumerate(feats):
                x = FF[sl, c]; g = np.isfinite(x)
                if g.sum() < 10: continue
                xr = rankdata(x[g]); yr = rankdata(rr[sl][g]); xr -= xr.mean(); yr -= yr.mean()
                d = np.sqrt((xr * xr).sum() * (yr * yr).sum())
                if d > 0: res[f].append((xr * yr).sum() / d)
        print(S, T, {f: (round(float(np.mean(v)), 4), round(float(np.std(v) / np.sqrt(len(v))), 4)) for f, v in res.items() if v})
