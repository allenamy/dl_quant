"""What exactly IS meta_newprod.npz? Verify before rebuilding its holefix analogue.
Hypothesis: = wide_fea_v2ext_meta.npz with y4 replaced by dlw_ext's y4s (compounded target), aligned by E_ts."""
import numpy as np, time
MN = np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz", allow_pickle=True)
KM = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True)
TG = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True)
print("meta_newprod files:", MN.files)
mt = MN["E_ts"].astype(np.int64); kt = KM["E_ts"].astype(np.int64); tt = TG["E_ts"].astype(np.int64)
print("anchors  meta_newprod %d | king_meta %d | dlw_targets %d" % (len(mt), len(kt), len(tt)))
print("E_ts identical to king meta: %s" % (mt.shape == kt.shape and bool((mt == kt).all())))
for k in ("members", "qvk"):
    if k in MN.files and k in KM.files:
        a, b = MN[k], KM[k]
        if k == "members":
            same = all(np.array_equal(np.asarray(a[i]), np.asarray(b[i])) for i in range(0, len(a), 500))
        else:
            same = np.array_equal(np.nan_to_num(np.asarray(a, float), nan=-9e9), np.nan_to_num(np.asarray(b, float), nan=-9e9))
        print("  %-10s identical to king meta: %s" % (k, same))
print("  y4 identical to king meta: %s" % np.array_equal(np.nan_to_num(MN["y4"], nan=-9e9), np.nan_to_num(KM["y4"], nan=-9e9)))
row = {int(t): i for i, t in enumerate(tt)}
idx = np.array([row.get(int(t), -1) for t in mt])
ok = idx >= 0
print("  meta_newprod anchors found in dlw_targets: %d/%d" % (int(ok.sum()), len(mt)))
A = MN["y4"][ok].astype(np.float64); B = TG["y4s"][idx[ok]].astype(np.float64)
f = np.isfinite(A) & np.isfinite(B)
print("  y4 (meta_newprod) vs y4s (dlw_ext): both-finite %d | maxabs %.3e | nan_mismatch %d"
      % (int(f.sum()), float(np.abs(A[f] - B[f]).max()) if f.any() else -1, int((np.isfinite(A) ^ np.isfinite(B)).sum())))
