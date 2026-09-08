"""STEP1 gate red on f_amihud_24h (corr 0.0546 vs v1). Two instruments disagree -> reconcile before touching anything.
Q1: does the EXISTING v2ext panel pass the same gate?  Q2: where do v2holefix and v2ext actually differ?"""
import numpy as np, time, calendar
V1 = np.load("/workspace/data/wide_panel_4h_v1.npz", allow_pickle=True)
VE = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True)
VH = np.load("/workspace/data/wide_panel_4h_v2holefix.npz", allow_pickle=True)
ts1 = V1["ts"].astype(np.int64); tse = VE["ts"].astype(np.int64); tsh = VH["ts"].astype(np.int64)
print("v1 anchors %d (%s..%s)" % (len(ts1), time.strftime("%F", time.gmtime(ts1[0])), time.strftime("%F", time.gmtime(ts1[-1]))))
print("v2ext %d | v2holefix %d | axes identical: %s" % (len(tse), len(tsh), tse.shape == tsh.shape and bool((tse == tsh).all())))
row = {int(t): i for i, t in enumerate(tse)}
i1 = []; ix = []
for a, t in enumerate(ts1):
    j = row.get(int(t))
    if j is not None: i1.append(a); ix.append(j)
i1 = np.array(i1); ix = np.array(ix)
print("overlap anchors with v1: %d  (%s .. %s)" % (len(i1), time.strftime("%F", time.gmtime(ts1[i1[0]])), time.strftime("%F", time.gmtime(ts1[i1[-1]]))))
print("\n=== Q1: the SAME gate applied to the EXISTING v2ext panel ===")
for key in ("f_rev_24h", "f_mom_7d", "f_vol_7d", "f_amihud_24h", "f_range_24h"):
    a = V1[key][i1].ravel().astype(np.float64); b = VE[key][ix].ravel().astype(np.float64)
    ok = np.isfinite(a) & np.isfinite(b)
    c = np.corrcoef(a[ok], b[ok])[0, 1]
    print("  v2ext vs v1  %-16s corr %.6f  n %d   %s" % (key, c, ok.sum(), "PASS" if c >= 0.999 else "*** FAIL ***"))
print("\n=== Q2: v2holefix vs v2ext, directly ===")
for key in ("f_rev_24h", "f_mom_7d", "f_vol_7d", "f_amihud_24h", "f_range_24h", "f_fund_now"):
    A = VE[key].astype(np.float64); B = VH[key].astype(np.float64)
    fa = np.isfinite(A); fb = np.isfinite(B)
    both = fa & fb
    d = np.abs(A[both] - B[both])
    ch = (d > 0)
    rows_changed = np.unique(np.where(both)[0][ch]) if ch.any() else np.array([])
    print("  %-16s both-finite %10d | changed %9d | maxabs %.3e | first changed anchor %s"
          % (key, both.sum(), int(ch.sum()), float(d.max()) if d.size else 0.0,
             time.strftime("%F %H:%MZ", time.gmtime(int(tse[rows_changed.min()]))) if rows_changed.size else "-"))
    print("      newly-finite %d | newly-NaN %d" % (int(((~fa) & fb).sum()), int((fa & (~fb)).sum())))
