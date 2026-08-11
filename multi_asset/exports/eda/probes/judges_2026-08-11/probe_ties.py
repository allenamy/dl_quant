"""0C migration audit ①: does argsort().argsort() (ordinal) vs rankdata (average) matter for the
funding leg? Ties are the whole question. Measured on the REAL corrected funding_ema panel."""
import sys, numpy as np
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
from scipy.stats import rankdata
from engine.panel_source import PanelSource

src = PanelSource()
FN = np.load("/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/eda/"
             "funding_ema_normfix.npz", allow_pickle=True)["FN"].astype(np.float64)
import pandas as pd
months = [f"{y}-{m:02d}" for y in range(2022, 2027) for m in range(1, 13) if not (y == 2026 and m > 6)]
anchors = np.unique(np.concatenate([src.month_anchors(ym) for ym in months]))


def rc_ordinal(x):                       # live/legs.py implementation
    x = np.asarray(x, float); m = np.isfinite(x); out = np.zeros_like(x)
    if m.sum() >= 3:
        order = x[m].argsort().argsort().astype(float) + 1.0
        k = len(order)
        out[m] = (2.0 * (order - 1) / (k - 1) - 1.0) if k > 1 else 0.0
    return out


def rc_average(x):                       # research signal_chain.py (scipy rankdata)
    x = np.asarray(x, float); m = np.isfinite(x); out = np.zeros_like(x)
    if m.sum() >= 3:
        r = rankdata(x[m]); k = len(r)
        out[m] = (2.0 * (r - 1) / (k - 1) - 1.0) if k > 1 else 0.0
    return out


def l1(x):
    g = np.abs(x).sum(); return x / g if g > 1e-9 else x


n_tie_anchor = 0; tie_frac = []; maxgrp = []; l1diff = []; corrs = []
idx_bias = []
N = src.N
for t in anchors[::7]:
    ti = int(t); m = src.tradeable(ti)
    v = FN[ti, m]
    v = v[np.isfinite(v)]
    if v.size < 20:
        continue
    u, cnt = np.unique(v, return_counts=True)
    tied = cnt[cnt > 1].sum()
    tie_frac.append(tied / v.size)
    maxgrp.append(int(cnt.max()))
    if tied > 0:
        n_tie_anchor += 1
    a = l1(-rc_ordinal(FN[ti, m])); b = l1(-rc_average(FN[ti, m]))
    l1diff.append(float(np.abs(a - b).sum()))
    if a.std() > 0 and b.std() > 0:
        corrs.append(float(np.corrcoef(a, b)[0, 1]))
    # is the ordinal error correlated with symbol index? (deterministic order artifact)
    d = a - b
    if d.std() > 1e-15:
        idx_bias.append(float(np.corrcoef(np.arange(len(d)), d)[0, 1]))

print(f"anchors sampled            : {len(tie_frac)}")
print(f"anchors WITH ties          : {n_tie_anchor} ({n_tie_anchor/len(tie_frac):.1%})")
print(f"tied-name fraction         : mean {np.mean(tie_frac):.3f}  median {np.median(tie_frac):.3f}  max {np.max(tie_frac):.3f}")
print(f"largest tie group (names)  : mean {np.mean(maxgrp):.1f}  max {np.max(maxgrp)}")
print(f"leg-weight L1 difference   : mean {np.mean(l1diff):.4f}  p90 {np.percentile(l1diff,90):.4f}  max {np.max(l1diff):.4f}")
print(f"  (leg is unit L1 gross=1, so this is a FRACTION OF THE WHOLE LEG)")
print(f"corr(ordinal, average) leg : mean {np.mean(corrs):.6f}  min {np.min(corrs):.6f}")
print(f"corr(symbol index, error)  : mean {np.mean(idx_bias):+.4f}  |mean| {abs(np.mean(idx_bias)):.4f}")
print(f"  (non-zero => the tie-break is a deterministic function of array order, not noise)")
