"""Is the STEP1 gate firing on a real regression, or on Pearson's outlier sensitivity in the region
the fix is SUPPOSED to change? Two measurements decide it."""
import numpy as np, time, calendar
V1 = np.load("/workspace/data/wide_panel_4h_v1.npz", allow_pickle=True)
VE = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True)
VH = np.load("/workspace/data/wide_panel_4h_v2holefix.npz", allow_pickle=True)
ts1 = V1["ts"].astype(np.int64); tse = VE["ts"].astype(np.int64)
row = {int(t): i for i, t in enumerate(tse)}
i1, ix = [], []
for a, t in enumerate(ts1):
    j = row.get(int(t))
    if j is not None: i1.append(a); ix.append(j)
i1 = np.array(i1); ix = np.array(ix)
CH = calendar.timegm((2026, 8, 12, 4, 0, 0))          # first anchor the fix is DESIGNED to change
pre = ts1[i1] < CH
print("overlap anchors %d | of which strictly BEFORE 2026-08-12 04:00Z: %d (%.3f%%)" % (len(i1), int(pre.sum()), 100*pre.mean()))
KEYS = ("f_rev_24h", "f_mom_7d", "f_vol_7d", "f_amihud_24h", "f_range_24h")
print("\n=== A. gate restricted to the region NOTHING should change (a true regression test) ===")
for key in KEYS:
    a = V1[key][i1[pre]].ravel().astype(np.float64); b = VH[key][ix[pre]].ravel().astype(np.float64)
    ok = np.isfinite(a) & np.isfinite(b)
    c = np.corrcoef(a[ok], b[ok])[0, 1]
    mx = float(np.abs(a[ok] - b[ok]).max())
    print("  v1 vs holefix (pre-change)  %-16s corr %.9f  maxabs %.3e  n %d" % (key, c, mx, ok.sum()))
print("\n=== B. what drives the amihud collapse on the FULL overlap ===")
a = V1["f_amihud_24h"][i1].ravel().astype(np.float64); b = VH["f_amihud_24h"][ix].ravel().astype(np.float64)
ok = np.isfinite(a) & np.isfinite(b); A = a[ok]; B = b[ok]
print("  full overlap corr %.6f  n %d" % (np.corrcoef(A, B)[0, 1], ok.sum()))
d = np.abs(A - B); order = np.argsort(-d)
for k in (1, 2, 3, 5, 10, 50, 200):
    keep = np.ones(len(A), bool); keep[order[:k]] = False
    print("    drop the %3d most-divergent cells -> corr %.9f" % (k, np.corrcoef(A[keep], B[keep])[0, 1]))
print("  top 5 divergent cells (v1 value, holefix value):", [(round(float(A[j]), 3), round(float(B[j]), 3)) for j in order[:5]])
print("  |A| p99.9 %.3f  max %.3f ; |B| p99.9 %.3f  max %.3f" % (np.percentile(np.abs(A), 99.9), np.abs(A).max(), np.percentile(np.abs(B), 99.9), np.abs(B).max()))
print("\n  Spearman (rank, outlier-robust) on the full overlap: %.6f" % __import__("scipy.stats", fromlist=["spearmanr"]).spearmanr(A, B).correlation)
