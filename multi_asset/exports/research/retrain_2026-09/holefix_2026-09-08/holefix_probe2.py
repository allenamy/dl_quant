"""Two things the single-symbol probe surfaced, checked across the WHOLE cache before any repair:
 (1) is 2026-08-31 a SECOND universe-wide gap?  (2) where exactly does the cache's ts axis end?"""
import numpy as np, sys, time, calendar
sys.path.insert(0, "/workspace"); from zload import zload
Z = zload("/workspace/data/dlnative_5m_wide829_f16_ext.npz", allow_pickle=True)
CTS = Z["ts"].astype(np.int64); D = Z["data"]; syms = np.array([str(s) for s in Z["symbols"]])
print("cache ts axis: first %s  last %s  rows %d  step %ds"
      % (time.strftime("%F %H:%M", time.gmtime(CTS[0])), time.strftime("%F %H:%M", time.gmtime(CTS[-1])), len(CTS), int(CTS[1]-CTS[0])))
live = set(open("/Users/haosiyu/wide_shadow/syms450.txt").read().split()) if False else None
for d in range(25, 32):
    lo = calendar.timegm((2026, 8, d, 0, 0, 0)); hi = lo + 86400
    m = (CTS >= lo) & (CTS < hi)
    if m.sum() == 0: continue
    fin = np.isfinite(D[m][:, :, 0])
    per = fin.sum(0)
    print("  2026-08-%02d rows_in_axis %3d | symbols with >=1 finite %3d | median bars/symbol %5.1f | symbols with FULL %d bars: %d"
          % (d, int(m.sum()), int((per > 0).sum()), float(np.median(per)), int(m.sum()), int((per == m.sum()).sum())))
lo = calendar.timegm((2026, 9, 1, 0, 0, 0)); m = CTS >= lo
print("  rows at/after 2026-09-01 00:00 :", int(m.sum()))
