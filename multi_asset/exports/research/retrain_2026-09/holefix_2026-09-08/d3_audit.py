"""Characterise D3 — the third gap on 2026-08-12 surfaced by the OTHER counter. Targeted rows only."""
import numpy as np, sys, time, calendar
sys.path.insert(0, "/workspace"); from zload import zload
A = zload("/workspace/data/dlnative_5m_wide829_f16_ext.npz", allow_pickle=True)
B = zload("/workspace/data/dlnative_5m_wide829_f16_holefix.npz", allow_pickle=True)
ts = A["ts"].astype(np.int64); SY = np.array([str(s) for s in A["symbols"]])
lo = calendar.timegm((2026, 8, 12, 0, 0, 0)); hi = calendar.timegm((2026, 8, 13, 0, 5, 0))
m = (ts >= lo) & (ts < hi)
X = np.array(A["data"][m]); Y = np.array(B["data"][m]); tt = ts[m]
fa = np.isfinite(X[:, :, 0]); fb = np.isfinite(Y[:, :, 0])
before = fa.sum(0); after = fb.sum(0)
gap = before < after
print("rows examined: %d (%s .. %s)" % (m.sum(), time.strftime("%F %H:%M", time.gmtime(tt[0])), time.strftime("%F %H:%M", time.gmtime(tt[-1]))))
print("symbols whose ch0 coverage improved on 08-12: %d" % int(gap.sum()))
print("%-16s %8s %8s %8s" % ("symbol", "before", "after", "gained"))
idx = np.argsort(-(after - before))
for k in idx[:20]:
    if not gap[k]: break
    print("%-16s %8d %8d %8d" % (SY[k], before[k], after[k], after[k] - before[k]))
full = int(((before == 0) & (after > 250)).sum())
print("\nsymbols with ZERO ch0 bars on 08-12 before, now full: %d" % full)
print("total ch0 bars recovered on 08-12: %d" % int((after - before).sum()))
# were these symbols also in the D1 hole set?
hl = calendar.timegm((2026, 8, 13, 0, 5, 0)); hh = calendar.timegm((2026, 8, 24, 4, 0, 0))
hm = (ts >= hl) & (ts <= hh)
nh = np.isfinite(np.array(A["data"][hm])).sum(axis=(0, 2))
pre = (ts >= hl - 7 * 86400) & (ts < hl); post = (ts > hh) & (ts <= hh + 5 * 86400)
alive = (np.isfinite(np.array(A["data"][pre])[:, :, 0]).sum(0) > 500) & (np.isfinite(np.array(A["data"][post])[:, :, 0]).sum(0) > 500)
d1 = (nh == 0) & alive
g = np.where(gap)[0]
print("of the %d symbols improved on 08-12, how many are in the 348 D1 hole set: %d" % (len(g), int(d1[g].sum())))
