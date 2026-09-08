"""PREREG §2 self-check 3 follow-through: the 25,546 'OTHER' fills are a RED FLAG until characterised.
Compare _ext.npz vs _holefix.npz cell by cell over August and classify every changed cell."""
import numpy as np, sys, time, calendar
from collections import Counter
sys.path.insert(0, "/workspace"); from zload import zload
A = zload("/workspace/data/dlnative_5m_wide829_f16_ext.npz", allow_pickle=True)
B = zload("/workspace/data/dlnative_5m_wide829_f16_holefix.npz", allow_pickle=True)
ats = A["ts"].astype(np.int64); bts = B["ts"].astype(np.int64)
assert ats.shape == bts.shape and (ats == bts).all(), "ts axis changed"
SY = [str(s) for s in A["symbols"]]
assert [str(s) for s in B["symbols"]] == SY, "symbol axis changed"
AUG_LO = calendar.timegm((2026, 8, 1, 0, 0, 0))
pre = ats < AUG_LO
print("SELF-CHECK 4  (nothing outside 2026-08 changed):", flush=True)
da = np.array(A["data"][pre]); db = np.array(B["data"][pre])
same = np.array_equal(np.nan_to_num(da, nan=-9e9), np.nan_to_num(db, nan=-9e9))
print("   rows before 2026-08-01: %d -> identical: %s" % (int(pre.sum()), same), flush=True)
del da, db
assert same, "self-check 4 FAILED"
aug = ~pre
X = np.array(A["data"][aug]); Y = np.array(B["data"][aug]); ts = ats[aug]
fa = np.isfinite(X); fb = np.isfinite(Y)
newf = (~fa) & fb
lost = fa & (~fb)
chg = fa & fb & (X != Y)
print("SELF-CHECK 2  (no overwrite / no loss): cells lost %d | cells changed-in-place %d -> %s"
      % (int(lost.sum()), int(chg.sum()), "PASS" if lost.sum() == 0 and chg.sum() == 0 else "FAIL"), flush=True)
assert lost.sum() == 0 and chg.sum() == 0
HOLE_LO = calendar.timegm((2026, 8, 13, 0, 5, 0)); HOLE_HI = calendar.timegm((2026, 8, 24, 4, 0, 0))
D31_LO = calendar.timegm((2026, 8, 31, 0, 0, 0)); D31_HI = calendar.timegm((2026, 9, 1, 0, 0, 0))
r, c, ch = np.where(newf)
tt = ts[r]
inhole = (tt >= HOLE_LO) & (tt <= HOLE_HI)
ind31 = (tt >= D31_LO) & (tt < D31_HI)
oth = ~(inhole | ind31)
print("\ntotal new cells %d | hole %d | 08-31 %d | OTHER %d" % (len(r), int(inhole.sum()), int(ind31.sum()), int(oth.sum())), flush=True)
print("\n=== OTHER breakdown ===", flush=True)
ot = tt[oth]; oc = c[oth]; och = ch[oth]
print(" by timestamp (top 10):")
for k, v in Counter(time.strftime("%F %H:%M", time.gmtime(int(x))) for x in ot).most_common(10):
    print("   %s  %d cells" % (k, v))
print(" by channel:", dict(Counter(int(x) for x in och)))
print(" distinct symbols touched: %d" % len(set(oc.tolist())))
print(" by symbol (top 8):", [(SY[k], v) for k, v in Counter(int(x) for x in oc).most_common(8)])
print(" timestamp range: %s .. %s" % (time.strftime("%F %H:%M", time.gmtime(int(ot.min()))), time.strftime("%F %H:%M", time.gmtime(int(ot.max())))))
# per-day
print(" by day:", dict(Counter(time.strftime("%m-%d", time.gmtime(int(x))) for x in ot).most_common(12)))
