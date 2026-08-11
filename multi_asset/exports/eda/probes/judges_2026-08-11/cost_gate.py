"""A 线: book→成本 前置门。目标 = maker 挂单成交概率(klines H/L 构造, 真目标)。
判据: book 特征的 AUC 必须超过 (rvol+turnover) 基线 +0.02, 否则=波动率换皮。"""
import numpy as np, datetime as dt
G = np.load("/workspace/data/ohlcv_grid.npz", allow_pickle=True)
B = np.load("/workspace/data/book1p_hourly.npz", allow_pickle=True)
R = np.load("/workspace/data/wide_dl_prodmask32.npz", allow_pickle=True)
C = G["CLOSE"].astype(np.float64); L = G["LOW"].astype(np.float64); H = G["HIGH"].astype(np.float64)
MEM = R["MEMBER110"]; T, N = C.shape
TS = np.asarray(G["ts"]).astype(np.int64)
YEAR = np.array([dt.datetime.fromtimestamp(int(t)/1000, dt.timezone.utc).year for t in TS])
# 目标: 下一小时, 低于 C*(1-δ) 的买单会成交
fill = {}
for d, dn in ((5e-4, "5bp"), (2e-3, "20bp")):
    f = np.full((T, N), np.nan, np.float32)
    f[:-1] = (L[1:] < C[:-1] * (1 - d)).astype(np.float32)
    f[:-1][~np.isfinite(L[1:]) | ~np.isfinite(C[:-1])] = np.nan
    fill[dn] = f
names32 = [str(x) for x in R["ch_names"]]
rvol = R["CH"][:, :, names32.index("rvol_6h")].astype(np.float64)
turn = R["CH"][:, :, names32.index("lturnover_24h")].astype(np.float64)
BX = B["X"]; bn = [str(x) for x in B["feats"]]
def auc(x, y):
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 500: return np.nan
    x, y = x[m], y[m]
    r = np.argsort(np.argsort(x)).astype(float) + 1
    n1 = (y > 0.5).sum(); n0 = len(y) - n1
    if n1 == 0 or n0 == 0: return np.nan
    return float((r[y > 0.5].sum() - n1*(n1+1)/2) / (n1*n0))
rows = [i for i in range(24, T-2) if YEAR[i] >= 2024 and i % 2 == 0]
print("目标基率与单变量 AUC (2024+, 逐格):")
for dn, f in fill.items():
    ys, rv, tn, ob, cv, dl = [], [], [], [], [], []
    for i in rows[::3]:
        m = MEM[i]
        ys.append(np.where(m, f[i], np.nan)); rv.append(np.where(m, rvol[i], np.nan))
        tn.append(np.where(m, turn[i], np.nan))
        ob.append(np.where(m, BX[i, :, bn.index("obi_mean")], np.nan))
        cv.append(np.where(m, BX[i, :, bn.index("cv_bid")], np.nan))
        dl.append(np.where(m, BX[i, :, bn.index("dep_lvl")], np.nan))
    y = np.concatenate(ys)
    print("  δ=%s  基率 %.3f | AUC: rvol %.3f  turn %.3f | book: obi %.3f  cv_bid %.3f  dep_lvl %.3f" % (
        dn, np.nanmean(y),
        auc(np.concatenate(rv), y), auc(np.concatenate(tn), y),
        auc(np.concatenate(ob), y), auc(np.concatenate(cv), y), auc(np.concatenate(dl), y)))
print("\n(多变量增量门下一步: logistic rvol+turn vs +book5, 逐年走前)")
