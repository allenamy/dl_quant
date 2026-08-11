"""用生产零掩码还原生产面板: CH_prod ≈ CH_mine * mask (非零格已验 corr 0.99999896)。
唯一失真: 产有我零的格(member 内实测 0.03%/2021, 其余 ~0) —— 可忽略。
这是【单变量】: 只改零格局, 数据值/目标/掩码/装置全同。"""
import numpy as np
M = np.load("/workspace/data/prod_nonzero_mask.npz", allow_pickle=True)
shape = tuple(int(v) for v in M["shape"])
mask = np.unpackbits(M["M"])[:int(np.prod(shape))].reshape(shape).astype(bool)
R = np.load("/workspace/data/wide_dl_rebuilt32.npz", allow_pickle=True)
CH = R["CH"].copy()
assert CH.shape == shape, (CH.shape, shape)
before = (CH != 0).mean()
CH[~mask] = 0.0
print("非零率: 我 %.4f -> 掩码后 %.4f  (生产 %.4f)" % (before, (CH != 0).mean(), mask.mean()))
d = {k: R[k] for k in R.files if k != "CH"}
d["CH"] = CH
np.savez("/workspace/data/wide_dl_prodmask32.npz", **d)
print("saved wide_dl_prodmask32.npz")
