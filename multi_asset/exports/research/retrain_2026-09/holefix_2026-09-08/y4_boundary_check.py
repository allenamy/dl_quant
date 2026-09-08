"""GATE A flagged Y4 (14) and Y24 (84) nan_mismatch. Hypothesis: they are FORWARD-looking, so their
change boundary is anchor + horizon, not the anchor. Verify by locating every mismatch."""
import numpy as np, time, calendar
from collections import Counter
VE = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True)
VH = np.load("/workspace/data/wide_panel_4h_v2holefix.npz", allow_pickle=True)
ts = VH["ts"].astype(np.int64)
CH = calendar.timegm((2026, 8, 12, 4, 0, 0))
for k, hz in (("Y4", 4 * 3600), ("Y24", 24 * 3600)):
    A = np.asarray(VE[k]); B = np.asarray(VH[k])
    mm = np.isfinite(A) ^ np.isfinite(B)
    r, c = np.where(mm)
    tt = ts[r]
    print("%s: nan_mismatch %d | anchors involved: %s" % (k, len(r), sorted(set(time.strftime("%F %H:%MZ", time.gmtime(int(x))) for x in tt))))
    print("   all mismatches have anchor >= CH-horizon (%s)? %s"
          % (time.strftime("%F %H:%MZ", time.gmtime(CH - hz)), bool((tt >= CH - hz).all())))
    print("   all mismatches have anchor <  CH (%s)? %s" % (time.strftime("%F %H:%MZ", time.gmtime(CH)), bool((tt < CH).all())))
    newf = int(((~np.isfinite(A)) & np.isfinite(B))[mm].sum()) if mm.any() else 0
    lost = int((np.isfinite(A) & (~np.isfinite(B)))[mm].sum()) if mm.any() else 0
    print("   newly-finite %d | lost %d" % (newf, lost))
    # and: on the finite intersection over the whole pre-CH region, is it bitwise?
    pre = ts < CH
    Ap = A[pre]; Bp = B[pre]; ok = np.isfinite(Ap) & np.isfinite(Bp)
    print("   pre-CH finite intersection maxabs %.3e (n %d)\n" % (float(np.abs(Ap[ok] - Bp[ok]).max()), int(ok.sum())))
