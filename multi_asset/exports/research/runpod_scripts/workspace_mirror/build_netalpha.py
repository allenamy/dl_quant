"""R2 净 alpha 目标(任务 #34, "最便宜的大改", 从未做过)。
动机: 书付的是【净】收益, 而模型训的是【毛】alpha ⇒ 目标与书的 P&L 不对齐。

★ 形态的关键推导(不能简单写 y - c):
  书是市场中性多空, 成本作用在 |权重| 上而非有符号收益 —— 做空高成本名同样付成本。
  所以"净 alpha = y − c"只对多头成立。正确的做法是【按成本收缩信号幅度而保号】:
      net = zr(YR4) * (1 − kappa * u_cost),  u_cost ∈ [0,1] 为成本的横截面分位
  贵的名字信号被压缩 ⇒ 模型自然少在它们上下注, 而便宜的名字保持原强度。kappa=0.5
  意味着最贵的那个名字信号减半。

成本代理(面板内已有列, 无新数据):
  cost ∝ 波动 / 流动性  ⇒  cost_z = zr(rvol_24h) − zr(size_dvol)
  (真实成本 ≈ a·spread + b·σ·sqrt(Q/ADV); 横截面上 σ↑ 或 ADV↓ 即更贵。)
  ⚠️ 这是代理不是实测成本: 实测逐名成本只在实盘订单里有, 且样本极少。
     所以本臂判的是"按成本收缩幅度这个【形态】有没有用", 不是精确净额。
"""
import numpy as np
P = "/workspace/data/wide_dl_pm32_hz.npz"
d = np.load(P, allow_pickle=True)
nm = [str(v) for v in d["ch_names"]]
CH = d["CH"]; MEM = d["MEMBER110"]; YR = d["YR4"]; CL = d["CL4"]; ts = d["ts"]
iv = nm.index("rvol_24h"); il = nm.index("size_dvol")
T, N = YR.shape
KAPPA = 0.5

def zr(v):
    m = np.isfinite(v); o = np.full(len(v), np.nan, np.float32)
    if m.sum() < 20: return o
    r = np.argsort(np.argsort(v[m])).astype(np.float64)
    o[m] = ((r - r.mean()) / (r.std() + 1e-12)).astype(np.float32); return o

def urank(v):
    m = np.isfinite(v); o = np.full(len(v), np.nan, np.float32)
    if m.sum() < 20: return o
    r = np.argsort(np.argsort(v[m])).astype(np.float64)
    o[m] = (r / max(len(r) - 1, 1)).astype(np.float32); return o

Y = np.full((T, N), np.nan, np.float32)
for i in range(T):
    m = MEM[i] & np.isfinite(YR[i])
    if m.sum() < 20: continue
    cost = zr(np.where(m, CH[i, :, iv], np.nan)) - zr(np.where(m, CH[i, :, il], np.nan))
    u = urank(cost)
    Y[i] = zr(np.where(m, YR[i], np.nan)) * (1.0 - KAPPA * np.nan_to_num(u, nan=0.5))
K = np.isfinite(Y) & MEM & CL
print("净alpha目标: 有效行占比 %.4f | 有效行名数中位 %d" % (K.any(1).mean(), int(np.median(K[K.any(1)].sum(1)))))
# 与原目标的相关(应高但不为 1 —— 否则收缩没起作用)
c = []
for i in np.where(K.any(1))[0][::37]:
    m = K[i]
    if m.sum() < 25: continue
    a = Y[i][m]; b = zr(np.where(MEM[i], YR[i], np.nan))[m]
    g = np.isfinite(a) & np.isfinite(b)
    if g.sum() >= 20: c.append(float(np.corrcoef(a[g], b[g])[0, 1]))
print("与原 YR4 的横截面相关 中位 %.4f (应 <1, 太接近 1 说明收缩无效)" % float(np.median(c)))
np.savez("/workspace/data/target_netalpha.npz", YR4K=np.nan_to_num(Y), KMASK=K, ts=ts)
print("NETALPHA_BUILD_DONE")
