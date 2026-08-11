"""正式抗过拟合统计: PSR(概率夏普) + DSR(紧缩夏普, Bailey-LdP)对当前栈日收益序列。
试验数 N 的诚实处理: 未知精确值 ⇒ 给 N∈{50,150,500,1500} 四档的 DSR, 展示对假设的鲁棒性。"""
import numpy as np, json
from scipy.stats import norm, skew, kurtosis
d = np.load('/mnt/storage/private/work_hsy/probe_artifacts/healthcheck.json'.replace('healthcheck.json','') + 'healthcheck.json') if False else None
import sys
PD = "/mnt/storage/private/work_hsy/probe_artifacts"
# 重建日净序列(与 healthcheck 同装置): 直接从 rig 快跑
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
sys.path.insert(0, PD)
import legs as LG
import engine.replay_fullhist as RF
W = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}; C1 = 4.137; BW = 0.002
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N; n = len(a)
FI, RVI = src.fund_idx, src.ch.index("rvol_24h")
SYMS = [str(s) for s in src.symbols]
TGT, MSK, RET = [], [], []
held = {"k": np.full(N, np.nan), "s": np.full(N, np.nan), "f": np.full(N, np.nan)}
for i, t in enumerate(a):
    ti = int(t); m = np.asarray(src.tradeable(ti))
    if m.dtype == bool: m = np.where(m)[0]
    if i == 0 or ti % 8 == 0:
        v = np.full(N, np.nan); v[m] = src.king[ti, m]; held["k"] = v
    if i == 0 or ti % 24 == 0:
        v = np.full(N, np.nan); v[m] = src.s2[ti, m]; held["s"] = v
    if i == 0 or ti % 8 == 0:
        v = np.full(N, np.nan); v[m] = src.CH[ti, m, FI]; held["f"] = v
    r = LG.compose_book(held["k"][m], held["s"][m], held["f"][m], np.ones(len(m)),
                        weights=W, rvol=src.CH[ti, m, RVI].astype(float), risk_budget=RB)
    w = np.full(N, 0.0); w[m] = np.asarray(r["target_w"], float)
    TGT.append(w); MSK.append(m); RET.append(src.Y4[ti, m].astype(float))
state = None; prev = np.zeros(N); pnl = np.zeros(n); trn = np.zeros(n)
for i in range(n):
    m = MSK[i]; syms = [SYMS[j] for j in m]
    out = LG.apply_harvest_ema(TGT[i][m], syms, state, 0.05)
    state = out["state"]
    tgt = np.asarray(out["target_w"], float)
    w = prev.copy(); w[[j for j in range(N) if j not in set(m)]] = 0.0
    delta = tgt - w[m]
    T = np.abs(delta) > BW
    wm = w[m].copy(); wm[T] = tgt[T]
    if T.any(): wm[T] -= wm.sum()/T.sum()
    w[m] = wm
    y = RET[i]; ok = np.isfinite(y)
    pnl[i] = float(np.nansum(w[m][ok]*y[ok]))*1e4
    trn[i] = float(np.abs(w-prev).sum()); prev = w
net = pnl - trn*C1
# 聚合成日(6锚/日)
nd = len(net)//6*6
daily = net[:nd].reshape(-1, 6).sum(1)
T = len(daily)
sr_d = daily.mean()/daily.std(ddof=1)
sr_ann = sr_d*np.sqrt(365)
g3, g4 = skew(daily), kurtosis(daily, fisher=False)
def psr(sr_bench_ann):
    b = sr_bench_ann/np.sqrt(365)
    z = (sr_d - b)*np.sqrt(T-1)/np.sqrt(1 - g3*sr_d + (g4-1)/4*sr_d**2)
    return float(norm.cdf(z))
print(f"日序列 T={T} 夏普(年化) {sr_ann:.3f} skew {g3:+.2f} kurt {g4:.1f}")
print(f"PSR(>0): {psr(0):.4f} | PSR(>1.0): {psr(1.0):.4f} | PSR(>1.5): {psr(1.5):.4f}")
V = np.var([daily.mean()/daily.std(ddof=1)])  # placeholder
for Ntr in (50, 150, 500, 1500):
    emax = (1-0.5772)*norm.ppf(1-1/Ntr) + 0.5772*norm.ppf(1-1/(Ntr*np.e))
    sr0_d = emax*np.sqrt(1.0/T)   # 假设试验间 SR 方差 ≈ 抽样方差(保守中档)
    z = (sr_d - sr0_d)*np.sqrt(T-1)/np.sqrt(1 - g3*sr_d + (g4-1)/4*sr_d**2)
    print(f"DSR@N={Ntr}: E[maxSR_null](日)={sr0_d:.4f}(年化 {sr0_d*np.sqrt(365):.2f}) ⇒ DSR={norm.cdf(z):.4f}")
print("DSR_DONE")
