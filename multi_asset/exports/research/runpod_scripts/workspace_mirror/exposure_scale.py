"""★ 响应#2 的离线量化: 「签名亮起就同期减敞口」到底值不值。
由用户 2026-08-09 的反证驱动 —— 在役已是最新重训模型, 失效照旧 ⇒ 模型侧无解,
只剩"承认不能预测、只能反应"的书级响应。本脚本回答: 这样做能不能提高 IC-Sharpe。

★ 因果纪律(比 E25 的 metascore 更严): 只用【5 个纯 ≤t 面板聚合签名】,
  **剔除 H_self**(它由实现 IC 构成, 含当期未来收益 —— 用作特征即泄漏)。
  签名 → 分位 → 敞口 w(t) = 1 − κ·u(t), u∈[0,1] 越大=预测越坏。
  权重逐年走前拟合(训练年只用先前年份), 不看当年。
代理: 秩中性书在固定 gross 下, 逐锚 P&L ∝ 该锚 IC ⇒ IC-Sharpe = mean/std × √(每年锚数)。
⚠️ 未计入调整敞口本身的换手成本 —— 这是【毛】前置门: 连毛都不改善就不必谈净。
"""
import numpy as np, glob, datetime as dt, json
d = np.load("/workspace/data/wide_dl_pm32_hz.npz", allow_pickle=True)
MEM = d["MEMBER110"]; CH = d["CH"]; Y = d["YR4"]; C = d["CL4"]; ts = d["ts"].astype(np.int64)
nm = [str(v) for v in d["ch_names"]]
M = np.load("/workspace/data/metrics_hourly.npz", allow_pickle=True)
S = np.load("/workspace/data/state_feats.npz", allow_pickle=True)
mn = [str(v) for v in M["feats"]]; MX = M["X"]
YEAR = np.array([dt.datetime.fromtimestamp(int(t)/1000, dt.timezone.utc).year for t in ts])
T = len(ts)

def zr(v):
    m = np.isfinite(v); o = np.full(len(v), np.nan)
    if m.sum() < 20: return o
    r = np.argsort(np.argsort(v[m])).astype(float)
    o[m] = (r - r.mean()) / (r.std() + 1e-12); return o

import pandas as pd
fe = CH[:, :, nm.index("funding_ema")].astype(np.float64); fe[fe == 0] = np.nan
rv = CH[:, :, nm.index("rvol_24h")].astype(np.float64); rv[rv == 0] = np.nan
tk = np.where(MEM, MX[:, :, mn.index("taker_ls_mean")], np.nan)
with np.errstate(all="ignore"):
    ltk = np.log(np.where(tk > 0, tk, np.nan))
    td = pd.Series(np.nanpercentile(ltk, 75, axis=1) - np.nanpercentile(ltk, 25, axis=1)).rolling(24, min_periods=12).mean().values
SIG = {"taker_disp_r": td, "disp": S["S"][:, 0], "breadth": S["S"][:, 2],
       "rvol_med": pd.Series(np.nanmedian(rv, 1)).rolling(24, min_periods=12).mean().values,
       "fund_lvl": pd.Series(np.nanmean(fe, 1)).rolling(24, min_periods=12).mean().values}
X = np.column_stack([np.asarray(v, float) for v in SIG.values()])
print("签名(5, 全部 ≤t, 已剔除 H_self):", list(SIG), flush=True)

def anchor_ic(tags):
    per = {}
    for tag in tags:
        for f in sorted(glob.glob(f"/workspace/exports_train/{tag}/fold_*_head_scores.npz")):
            z = np.load(f); te = z["te_rows"]; SC = z["scores"]
            for i in te:
                i = int(i); m = MEM[i] & C[i] & np.isfinite(Y[i])
                if m.sum() < 25: continue
                t_ = zr(np.where(m, Y[i], np.nan))[m]
                hs = np.column_stack([zr(np.where(m, SC[i, :, k], np.nan)) for k in range(SC.shape[2])])
                s_ = zr(np.nanmean(hs, axis=1))[m]
                g = np.isfinite(t_) & np.isfinite(s_)
                if g.sum() >= 20: per.setdefault(i, []).append(float(np.corrcoef(s_[g], t_[g])[0, 1]))
            del SC
    return {i: float(np.mean(v)) for i, v in per.items()}

IC = anchor_ic(["rb32_lam0_yr4_s42", "rb32_lam0_yr4_s2027", "rb32_lam0_yr4_s3037"])
rows = np.array(sorted(IC)); ic = np.array([IC[i] for i in rows])
ok = np.all(np.isfinite(X[rows]), axis=1)
rows, ic = rows[ok], ic[ok]
print("锚 %d (2022-2026)" % len(rows), flush=True)

def urank_walkforward(rows, X, ic):
    """逐年走前: 用先前年份拟合 '签名 -> 未来坏度' 的方向, 再在当年打分。"""
    u = np.full(len(rows), np.nan)
    yr = YEAR[rows]
    for y in sorted(set(yr.tolist())):
        tr = yr < y; te = yr == y
        if tr.sum() < 500 or te.sum() < 50: continue
        Xtr = X[rows[tr]]; Xte = X[rows[te]]
        # 目标 = 未来 8 锚的平均 IC 的负值(坏度), 训练年内可见
        fut = pd.Series(ic).shift(-8).rolling(8, min_periods=4).mean().values
        ytr = -fut[tr]
        m = np.isfinite(ytr)
        if m.sum() < 300: continue
        A = np.column_stack([np.ones(m.sum()), (Xtr[m] - Xtr[m].mean(0)) / (Xtr[m].std(0) + 1e-9)])
        w = np.linalg.lstsq(A, ytr[m], rcond=None)[0]
        s = np.column_stack([np.ones(te.sum()), (Xte - Xtr[m].mean(0)) / (Xtr[m].std(0) + 1e-9)]) @ w
        r = np.argsort(np.argsort(s)).astype(float)
        u[te] = r / max(len(r) - 1, 1)
    return u

u = urank_walkforward(rows, X, ic)
val = np.isfinite(u)
ann = np.sqrt(365 * 6)   # 4h 锚 => 每年 ~2190 锚; 用 sqrt(锚/年) 年化
n_per_year = len(rows) / max(len(set(YEAR[rows].tolist())), 1)
ann = np.sqrt(n_per_year)
base_sh = ic[val].mean() / (ic[val].std() + 1e-12) * ann
print("\n%-14s %9s %9s %9s %9s" % ("敞口规则", "均值IC", "std", "IC-Sharpe", "vs基线"), flush=True)
print("%-14s %9.4f %9.4f %9.3f %9s" % ("恒定 1.0", ic[val].mean(), ic[val].std(), base_sh, "—"), flush=True)
for k in (0.3, 0.6, 1.0):
    w = 1.0 - k * u[val]
    p = w * ic[val]
    sh = p.mean() / (p.std() + 1e-12) * ann
    print("%-14s %9.4f %9.4f %9.3f %+9.3f" % ("1−%.1f·u" % k, p.mean(), p.std(), sh, sh - base_sh), flush=True)
print("\n判据(毛前置门): IC-Sharpe 必须【提高】才值得谈净额与换手成本; 否则响应#2 关闭。", flush=True)
print("EXPOSURE_SCALE_DONE", flush=True)
