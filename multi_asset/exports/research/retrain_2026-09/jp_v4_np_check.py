"""门V4-np @jpline: pod np 分数样本 vs jpline 重算(同权重同 gelu), Spearman>=0.99999 且 maxabs<=1e-5。"""
import numpy as np
from scipy.special import erf
from scipy.stats import spearmanr
Z = np.load("v4_np_sample.npz"); M = np.load("f10_live_s42_np.npz")
def gelu(x): return 0.5 * x * (1 + erf(x / np.sqrt(2)))
xz = Z["xz42"].astype(np.float64)
h = gelu(xz @ M["w0"].T.astype(np.float64) + M["b0"].astype(np.float64))
h = gelu(h @ M["w1"].T.astype(np.float64) + M["b1"].astype(np.float64))
s = (h @ M["w2"].T.astype(np.float64) + M["b2"].astype(np.float64)).squeeze(-1)
d = float(np.abs(s - Z["s42"]).max()); rho = float(spearmanr(s, Z["s42"]).correlation)
ok = rho >= 0.99999 and d <= 1e-5
print(f"V4-np jpline vs pod: spearman {rho:.7f} maxabs {d:.2e} -> {'PASS' if ok else 'FAIL'}")
