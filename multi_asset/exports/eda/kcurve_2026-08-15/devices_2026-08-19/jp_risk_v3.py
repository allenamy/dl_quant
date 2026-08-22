"""风险探测器 v3 升级测量(描述性仪器, 判读预写: OOS AUC/固定10%告警率下精确召回, 基线=btc_vol5 单指标).
靶: 次日挤压日(底动量篮子超额>训练期q95) 与 次日书代理尾日(书日收益<训练期q05).
特征: 一阶基线 + 二阶(volvol/相关水平与变化/特征值占比/偏度/垃圾币动量/funding×动量交互/BTC书状态变化).
折: 训 2022-2024, 测 2025-2026(严格 OOS). env: DAILY_IN CACHE_IN FDIR LOB_IN OUT_JSON
"""
import os, glob, zipfile, io, json
import numpy as np
import pandas as pd
D0 = np.load(os.environ["DAILY_IN"])
dret = D0["dret"]; nD, NS = dret.shape
t0 = pd.Timestamp("2022-01-01"); dates = pd.date_range(t0, periods=nD, freq="D")
C = np.load(os.environ["CACHE_IN"], mmap_mode="r")
syms = [str(s) for s in C["symbols"]]; iBTC = syms.index("BTCUSDT")
R = pd.DataFrame(dret, index=dates)
btc = R[iBTC]
mom30 = R.rolling(30, min_periods=20).sum().shift(2)
mkt = R.mean(axis=1)
# 靶构造
botB = np.full(nD, np.nan); momLS = np.full(nD, np.nan); xskew = np.full(nD, np.nan)
for i in range(nD):
    f = mom30.values[i]; r = dret[i]
    ok = np.isfinite(f) & np.isfinite(r)
    if ok.sum() < 60: continue
    q = np.nanpercentile(f[ok], [10, 90])
    botB[i] = np.nanmean(r[(f <= q[0]) & ok])
    momLS[i] = np.nanmean(r[(f >= q[1]) & ok]) - botB[i]
    rr = r[ok] - np.nanmean(r[ok])
    s = np.nanstd(rr)
    xskew[i] = float(np.nanmean((rr / (s + 1e-12)) ** 3))
sq_excess = pd.Series(botB, index=dates) - mkt
book = pd.Series(momLS, index=dates)
# 特征
F = pd.DataFrame(index=dates)
F["btc_vol5"] = btc.abs().ewm(span=5, min_periods=3).mean()                     # 基线(一阶)
F["volvol"] = btc.abs().rolling(10, min_periods=6).std()                       # 二阶
corr20 = R.rolling(20).corr(mkt)
F["r2_mean"] = (corr20 ** 2).mean(axis=1)                                       # 相关水平
F["r2_chg5"] = F["r2_mean"] - F["r2_mean"].shift(5)                             # 相关变化
F["xskew"] = pd.Series(xskew, index=dates).rolling(3, min_periods=2).mean()
F["junk_mom5"] = sq_excess.rolling(5, min_periods=3).sum()                      # 垃圾币先跑
# funding
FUND = np.full((nD, NS), np.nan)
for si, s in enumerate(syms):
    rows = []
    for z in sorted(glob.glob(f"{os.environ['FDIR']}/{s}/*.zip")):
        try:
            with zipfile.ZipFile(z) as zf: rows.append(pd.read_csv(io.BytesIO(zf.read(zf.namelist()[0]))))
        except Exception: pass
    if not rows: continue
    d = pd.concat(rows)
    r8 = d["last_funding_rate"].values * (8.0 / np.maximum(d["funding_interval_hours"].values, 1))
    day = ((pd.to_datetime(d["calc_time"], unit="ms") - t0).dt.days).values
    ok = (day >= 0) & (day < nD)
    g = pd.DataFrame({"d": day[ok], "r": r8[ok]}).groupby("d")["r"].mean()
    FUND[g.index.values, si] = g.values
F["fund_abs"] = pd.DataFrame(FUND, index=dates).abs().mean(axis=1)
F["fund_x_junk"] = F["fund_abs"].rank(pct=True) * F["junk_mom5"].rank(pct=True)  # 交互(二阶跨源)
# BTC 书状态(2023+)
L = np.load(os.environ["LOB_IN"])
lts = L["ts_min"].astype(np.int64); lf = L["feat"]
o = np.argsort(lts); lts, lf = lts[o], lf[o]
ldays = lts // 1440
bdf = pd.DataFrame({"d": ldays, "spread": lf[:, 0], "depth": lf[:, 1]}).groupby("d").mean()
bidx = pd.to_datetime(bdf.index * 86400, unit="s")
sp = bdf["spread"].reindex((dates - pd.Timestamp("1970-01-01")).days // 1).values if False else None
spread_d = pd.Series(bdf["spread"].values, index=bidx).reindex(dates)
depth_d = pd.Series(bdf["depth"].values, index=bidx).reindex(dates)
F["spread_chg3"] = spread_d - spread_d.shift(3)
F["depth_chg3"] = depth_d - depth_d.shift(3)
# ---- OOS 评估 ----
tr = dates < "2025-01-01"; te = ~tr
def make_target(kind):
    if kind == "squeeze":
        thr = sq_excess[tr].quantile(0.95); y = (sq_excess > thr)
    else:
        thr = book[tr].quantile(0.05); y = (book < thr)
    return y.shift(-1)  # 次日
def auc(score, y):
    ok = np.isfinite(score) & y.notna()
    s, yy = score[ok], y[ok].astype(bool)
    if yy.sum() < 5: return np.nan
    r = pd.Series(s).rank()
    return float((r[yy.values].mean() - (len(s) + 1) / 2) / (len(s) - yy.sum()) + 0.5)
def pr_at10(score, y):
    ok = np.isfinite(score) & y.notna()
    s, yy = score[ok], y[ok].astype(bool)
    k = max(int(0.10 * len(s)), 1)
    idx = np.argsort(-s.values)[:k]
    hit = yy.values[idx].sum()
    return round(hit / k, 3), round(hit / max(yy.sum(), 1), 3)
res = {}
# 分位化(只用训练期分布, 防 OOS 泄漏)
Fq = pd.DataFrame(index=dates)
for c in F.columns:
    q = F.loc[tr, c].rank(pct=True)
    Fq[c] = F[c].map(lambda v, s=F.loc[tr, c].dropna().sort_values(): np.searchsorted(s.values, v) / max(len(s), 1) if np.isfinite(v) else np.nan)
import itertools
W2 = ["volvol", "r2_mean", "r2_chg5", "xskew", "junk_mom5", "fund_abs", "fund_x_junk", "spread_chg3", "depth_chg3"]
for tgt in ("squeeze", "tail"):
    y = make_target(tgt)
    base = Fq["btc_vol5"]
    comp = Fq[["btc_vol5"] + W2].mean(axis=1, skipna=True)
    # 简单训练期贪心加权(仅方向: 训练期 AUC<0.5 的特征取反)
    parts = []
    for c in ["btc_vol5"] + W2:
        a_tr = auc(Fq.loc[tr, c], y[tr])
        parts.append(Fq[c] if (a_tr or 0.5) >= 0.5 else (1 - Fq[c]))
    comp2 = pd.concat(parts, axis=1).mean(axis=1, skipna=True)
    res[tgt] = {"n_te_events": int(y[te].sum()),
        "base_auc_te": round(auc(base[te], y[te]), 3),
        "comp_auc_te": round(auc(comp2[te], y[te]), 3),
        "base_pr_rec@10%": pr_at10(base[te], y[te]),
        "comp_pr_rec@10%": pr_at10(comp2[te], y[te])}
    print(tgt, res[tgt], flush=True)
json.dump(res, open(os.environ["OUT_JSON"], "w"), indent=1)
print("RISKV3_DONE", flush=True)
