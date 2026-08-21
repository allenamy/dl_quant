"""45ch = 自建32(生产掩码) + book13, xsec rank-z。族边界 split=32 供族塔用。"""
import numpy as np
R = np.load("/workspace/data/wide_dl_pm32_hz.npz", allow_pickle=True)
B = np.load("/workspace/data/book1p_hourly.npz", allow_pickle=True)
X, FE = B["X"].astype(np.float32), [str(f) for f in B["feats"]]
MEM = R["MEMBER110"]; T, N, C = X.shape
out = np.full_like(X, np.nan)
for t in range(T):
    m = MEM[t]
    if m.sum() < 20: continue
    for c in range(C):
        v = X[t, :, c]; f = m & np.isfinite(v)
        if f.sum() < 20: continue
        r = np.argsort(np.argsort(v[f])).astype(np.float32)
        out[t, f, c] = (r - r.mean()) / (r.std() + 1e-9)
np.nan_to_num(out, copy=False, nan=0.0)
d = {k: R[k] for k in R.files if k != "CH"}
d["CH"] = np.concatenate([R["CH"], out], axis=2)
d["ch_names"] = np.array([str(x) for x in R["ch_names"]] + FE, object)
np.savez("/workspace/data/wide_dl_45ch.npz", **d)
print("45ch: %s  book 非零率 %.4f" % (d["CH"].shape, float((out != 0).mean())))
