"""0C: can gap(normfix) > gap(as_trained) ever CROSS?

Mechanism under test: the correction multiplies the 4h cohort's rate by 2. For POSITIVE funding
that raises them relative to 8h (gap up); for NEGATIVE funding it lowers them (gap down). So the
ordering should be a function of the 4h cohort's SIGN composition, not a law. If the empirical
33-month record simply never contained a predominantly-negative 4h cohort, the ordering gate is
untested exactly where it fails.
"""
import sys, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
from scipy.stats import rankdata
from engine.panel_source import PanelSource

src = PanelSource()
W = np.load("/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/wide_dl_full.npz",
            allow_pickle=True)
ch = [str(c) for c in W["ch_names"]]
AS = W["CH"][:, :, ch.index("funding_ema")].astype(np.float64)
Z = np.load("/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/eda/"
            "funding_ema_normfix.npz", allow_pickle=True)
FN = Z["FN"].astype(np.float64); IH = Z["IH"].astype(np.float64)
mem = src.member
dt = pd.to_datetime(src.ts, unit="ms", utc=True)
ym = np.array([f"{a}-{b:02d}" for a, b in zip(dt.year.to_numpy(), dt.month.to_numpy())])


def rc(x):
    r = rankdata(x); k = len(r)
    return 2.0 * (r - 1) / (k - 1) - 1.0 if k > 1 else np.zeros_like(x)


rows = []
for month in sorted(set(ym.tolist())):
    idx = np.where((ym == month))[0][::6]
    ga, gn, neg, n4s = [], [], [], []
    for t in idx:
        v = np.where(mem[t] & np.isfinite(AS[t]) & np.isfinite(FN[t]) & np.isfinite(IH[t]))[0]
        if v.size < 20:
            continue
        is4 = IH[t, v] <= 4.0
        if is4.sum() < 3 or (~is4).sum() < 3:
            continue
        a = rc(AS[t, v]); n = rc(FN[t, v])
        ga.append(a[is4].mean() - a[~is4].mean())
        gn.append(n[is4].mean() - n[~is4].mean())
        neg.append(float((FN[t, v][is4] < 0).mean()))
        n4s.append(float(is4.mean()))
    if len(ga) < 3:
        continue
    rows.append(dict(month=month, gap_as=np.mean(ga), gap_nf=np.mean(gn),
                     margin=np.mean(gn) - np.mean(ga), neg4=np.mean(neg), share4=np.mean(n4s)))

d = pd.DataFrame(rows)
print(f"months with both cohorts present: {len(d)}")
print(f"margin = gap_nf - gap_as : min {d.margin.min():+.4f}  p05 {d.margin.quantile(.05):+.4f}  "
      f"median {d.margin.median():+.4f}  max {d.margin.max():+.4f}")
print(f"months where ordering INVERTS (margin<0): {(d.margin < 0).sum()}")
print(f"months where margin < 0.02 (the proposed gate): {(d.margin < 0.02).sum()}")
print(f"\ncorr(margin, 4h-cohort NEGATIVE-funding share) = {d.margin.corr(d.neg4):+.3f}")
print(f"4h negative-funding share: min {d.neg4.min():.3f}  median {d.neg4.median():.3f}  max {d.neg4.max():.3f}")
print("\nthe 5 months with the SMALLEST margin (the stress cases for the ordering gate):")
print(d.nsmallest(5, "margin")[["month", "gap_as", "gap_nf", "margin", "neg4", "share4"]].to_string(index=False))
print("\nthe 5 months with the HIGHEST 4h negative share:")
print(d.nlargest(5, "neg4")[["month", "gap_as", "gap_nf", "margin", "neg4", "share4"]].to_string(index=False))
