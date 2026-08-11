"""track-2 discriminator (read-only, CPU). The leak is a per-anchor COMMON SCALAR; cross-sectionally
it can only express through beta_i. So the discriminator is the per-anchor cross-sectional
correlation between each OI channel and beta_24h.
  |corr| small => orthogonal to the leak direction => Ridge increment ~unbiased => FAIL stands => S
  |corr| large => overlaps what the leak already explains => increment MASKED => R
"""
import numpy as np
from scipy.stats import rankdata

E = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/"
P = np.load(E + "wide_dl_full.npz", allow_pickle=True)
M = np.load(E + "wide_metrics_ch.npz", allow_pickle=True)

ch = [str(c) for c in P["ch_names"]]
CH = P["CH"]; mem = P["MEMBER110"].astype(bool); cl4 = P["CL4"].astype(bool)
beta = CH[:, :, ch.index("beta_24h")].astype(np.float64)
names = [str(c) for c in M["ch_names"]]
MC = np.where(M["MASK"].astype(bool), M["CH"].astype(np.float64), np.nan)
print("panels:", CH.shape, MC.shape)
print("metrics channels:", names)

emask = mem & cl4
rows = np.where(emask.any(1))[0]
print("eval anchors:", len(rows))

def xsec(a, b, m):
    out = []
    for t in rows:
        k = m[t] & np.isfinite(a[t]) & np.isfinite(b[t])
        if k.sum() < 20:
            continue
        x, y = rankdata(a[t, k]), rankdata(b[t, k])
        if x.std() < 1e-12 or y.std() < 1e-12:
            continue
        out.append(np.corrcoef(x, y)[0, 1])
    return np.array(out)

hdr = "%-34s %8s %8s %8s %8s %7s" % ("channel", "mean", "median", "mean|r|", "p95|r|", "n")
print("\n=== per-anchor cross-sectional Spearman( channel , beta_24h ) ===")
print(hdr)
for j, nm in enumerate(names):
    r = xsec(MC[:, :, j], beta, emask)
    if r.size == 0:
        print("%-34s  (no usable anchors)" % nm); continue
    print("%-34s %+8.4f %+8.4f %8.4f %8.4f %7d" % (
        nm, r.mean(), np.median(r), np.abs(r).mean(), np.percentile(np.abs(r), 95), r.size))

print("\n=== reference rulers (opposite-side, TEAM_PROTOCOL 8-b) ===")
print(hdr)
for nm, j in [("beta_24h vs itself (UPPER=1)", ch.index("beta_24h")),
              ("mom_24h vs beta (price ch)", ch.index("mom_24h")),
              ("size_dvol vs beta (slow ch)", ch.index("size_dvol")),
              ("rvol_24h vs beta (vol ch)", ch.index("rvol_24h"))]:
    r = xsec(CH[:, :, j].astype(np.float64), beta, emask)
    print("%-34s %+8.4f %+8.4f %8.4f %8.4f %7d" % (
        nm, r.mean(), np.median(r), np.abs(r).mean(), np.percentile(np.abs(r), 95), r.size))
