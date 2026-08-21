"""53ch 装配: 自建 32(raw) + metrics 21(全史重建后 xsec rank-z) -> 单变量 A/B 面板。"""
import numpy as np
R = np.load("/workspace/data/wide_dl_rebuilt32.npz", allow_pickle=True)
M = np.load("/workspace/data/metrics_hourly.npz", allow_pickle=True)
X, FEAT = M["X"].astype(np.float32), [str(f) for f in M["feats"]]
MEM = R["MEMBER110"]
T, N, C21 = X.shape
out = np.full_like(X, np.nan)
for t in range(T):
    m = MEM[t]
    if m.sum() < 20: continue
    for c in range(C21):
        v = X[t, :, c]; f = m & np.isfinite(v)
        if f.sum() < 20: continue
        r = np.argsort(np.argsort(v[f])).astype(np.float32)
        out[t, f, c] = (r - r.mean()) / (r.std() + 1e-9)
np.nan_to_num(out, copy=False, nan=0.0)
CH53 = np.concatenate([R["CH"], out], axis=2)
names = [str(x) for x in R["ch_names"]] + FEAT
d = {k: R[k] for k in ("ts","symbols","MEMBER110","Y1","YR1","CL1","Y4","YR4","CL4",
                        "Y24","YR24","CL24","baseline_cols")}
d["CH"] = CH53; d["ch_names"] = np.array(names, object)
np.savez("/workspace/data/wide_dl_53ch.npz", **d)
print(f"saved wide_dl_53ch.npz  CH {CH53.shape}  metrics 填充(rank-z 非零) {(out!=0).mean():.3f}")
