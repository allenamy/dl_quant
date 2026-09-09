"""Reviewer item 5: in the 2022-01 region, did the hole fix change VALUE columns too, or only rank columns? Count exactly."""
import numpy as np, time, calendar
MO = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True); eo = MO["E_ts"].astype(np.int64); names = [str(x) for x in MO["names"]]
FO = np.load("/workspace/data/wide_fea_v2ext.npy", mmap_mode="r"); FN = np.load("/workspace/data/wide_fea_v2holefix.npy", mmap_mode="r")
isv = np.array([n.endswith("_v") for n in names]); isr = np.array([n.endswith("_r") for n in names]); isf = ~(isv | isr)
lim = calendar.timegm((2022, 2, 1, 0, 0, 0)); cv = cr = cf = 0; av = 0
for i in range(len(eo)):
    if eo[i] >= lim: break
    a = np.asarray(FO[i], dtype=np.float64); b = np.asarray(FN[i], dtype=np.float64)
    d = (np.isfinite(a) ^ np.isfinite(b)) | (np.isfinite(a) & np.isfinite(b) & (a != b))
    cv += int(d[:, isv].sum()); cr += int(d[:, isr].sum()); cf += int(d[:, isf].sum())
    if d[:, isv].any(): av += 1
print("2022-01 region (anchors < 2022-02-01): changed cells value-cols %d (anchors %d), rank-cols %d, fund-cols %d" % (cv, av, cr, cf))
print("=> the statement 'only rank columns changed' is %s" % ("WRONG (value columns changed too)" if cv else "correct"))
