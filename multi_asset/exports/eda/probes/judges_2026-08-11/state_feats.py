"""2A: 市场级状态特征(离散度/广度/相关水平) + 离线验证"disp 高 ⇒ 横截面 alpha 肥沃"。
全部面板衍生, 逐时刻横截面统计 ⇒ 天然因果。全局标量 → 广播为 (T,N) 通道。"""
import numpy as np, pandas as pd
R = np.load("/workspace/data/wide_dl_prodmask32.npz", allow_pickle=True)
P = np.load("/workspace/data/panel_targets.npz", allow_pickle=True)
names = [str(x) for x in R["ch_names"]]
ret1 = R["CH"][:, :, names.index("ret_1h")].astype(np.float64)
ret1[ret1 == 0] = np.nan
MEM = R["MEMBER110"]; Y4 = P["Y4"]
T, N = ret1.shape
r = np.where(MEM, ret1, np.nan)
disp = np.nanstd(r, axis=1)                                   # 横截面离散度
mom24 = pd.DataFrame(np.where(MEM, R["CH"][:, :, names.index("mom_24h")], np.nan))
breadth = (mom24 > 0).sum(axis=1).values / np.maximum(MEM.sum(axis=1), 1)   # 广度
rq = pd.DataFrame(r)
cs = rq.sub(rq.mean(axis=1), axis=0)
corr_lvl = 1.0 - (cs.std(axis=1) / rq.std(axis=1).replace(0, np.nan)).values ** 2  # 平均两两相关近似
S = {"disp": pd.Series(disp).rolling(24, min_periods=12).mean().values,
     "disp_chg": pd.Series(disp).rolling(24, min_periods=12).mean().values
                 - pd.Series(disp).rolling(168, min_periods=84).mean().values,
     "breadth": pd.Series(breadth).rolling(24, min_periods=12).mean().values,
     "corr_lvl": pd.Series(corr_lvl).rolling(24, min_periods=12).mean().values}
# 离线验证: 状态分位 × 下期横截面 rank-IC(用简单 mom 因子做探针)
def zr(v):
    m = np.isfinite(v); o = np.full(len(v), np.nan)
    if m.sum() < 20: return o
    rk = np.argsort(np.argsort(v[m])).astype(float)
    o[m] = (rk - rk.mean()) / (rk.std() + 1e-12); return o
rev = -R["CH"][:, :, names.index("rev_1h")].astype(np.float64)
rows = [i for i in range(200, T - 30) if i % 4 == 0]
ic = np.full(T, np.nan)
for i in rows:
    a = zr(np.where(MEM[i], rev[i], np.nan)); b = zr(np.where(MEM[i], Y4[i], np.nan))
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() >= 25: ic[i] = float(np.abs((a[m] * b[m]).mean()))   # |IC| = alpha 肥沃度
print("状态 → 下期 |IC|(反转探针) 分位表:")
for nm, s in S.items():
    v = s.copy(); msk = np.isfinite(v) & np.isfinite(ic)
    if msk.sum() < 500: print("  %s: 样本不足" % nm); continue
    q = np.nanquantile(v[msk], [0.2, 0.8])
    lo = np.nanmean(ic[msk & (v <= q[0])]); hi = np.nanmean(ic[msk & (v >= q[1])])
    print("  %-9s 低分位 |IC|=%.4f  高分位 |IC|=%.4f  比 %.2f" % (nm, lo, hi, hi/max(lo,1e-9)))
ST = np.stack([np.nan_to_num(s, nan=0.0) for s in S.values()], axis=1).astype(np.float32)
np.savez("/workspace/data/state_feats.npz", S=ST, names=np.array(list(S), object), ts=P["ts"])
print("saved state_feats.npz  (T,%d)" % ST.shape[1])
