"""BTC 状态是否【领先】书的坏日/挤压日(用户点5的可行性事件研究; 描述性, 无采纳判据).
指标: BTC 已实现波动(5日EWM of |dret|)分位 / BTC 单日|ret|分位 / funding 截面均值分位.
被测: 书代理次日收益与|收益|; 挤压日(底动量篮子日收益 > q95)的领先指标状态.
env: DAILY_IN CACHE_IN OUT_JSON
"""
import os, json
import numpy as np
import pandas as pd
D0 = np.load(os.environ["DAILY_IN"])
dret = D0["dret"]; nD, NS = dret.shape
t0 = pd.Timestamp("2022-01-01"); dates = pd.date_range(t0, periods=nD, freq="D")
C = np.load(os.environ["CACHE_IN"], mmap_mode="r")
syms = [str(s) for s in C["symbols"]]; iBTC = syms.index("BTCUSDT")
R = pd.DataFrame(dret, index=dates)
mom30 = R.rolling(30, min_periods=20).sum().shift(2)
def ls_and_baskets():
    ls = np.full(nD, np.nan); bot = np.full(nD, np.nan)
    for i in range(nD):
        f = mom30.values[i]; r = dret[i]
        ok = np.isfinite(f) & np.isfinite(r)
        if ok.sum() < 60: continue
        q = np.nanpercentile(f[ok], [10, 90])
        ls[i] = np.nanmean(r[(f >= q[1]) & ok]) - np.nanmean(r[(f <= q[0]) & ok])
        bot[i] = np.nanmean(r[(f <= q[0]) & ok])
    return pd.Series(ls, index=dates), pd.Series(bot, index=dates)
momLS, botB = ls_and_baskets()
btc = pd.Series(dret[:, iBTC], index=dates)
vol5 = btc.abs().ewm(span=5, min_periods=3).mean()
volp = vol5.rank(pct=True)  # 全样本分位(描述性; 实盘应用须改滚动分位, 此处只测有无信息)
absp = btc.abs().rank(pct=True)
mkt = R.mean(axis=1)
sq = botB - mkt  # 底篮子超额(挤压强度)
sq_day = sq > sq.quantile(0.95)
book = momLS  # 以动量腿为书风险代理(挤压受害主体)
res = {}
def cond(name, indicator, k=1):
    hi = indicator.shift(k) > 0.9
    res[name] = {
        "n_hi": int(hi.sum()),
        "book_next_mean_bps": round(float(book[hi].mean() * 1e4), 1),
        "book_next_uncond_bps": round(float(book.mean() * 1e4), 1),
        "book_next_absmean_hi": round(float(book[hi].abs().mean() * 1e4), 1),
        "book_next_absmean_unc": round(float(book.abs().mean() * 1e4), 1),
        "squeeze_rate_hi_pct": round(float(sq_day[hi].mean() * 100), 1),
        "squeeze_rate_unc_pct": round(float(sq_day.mean() * 100), 1)}
    print(name, res[name], flush=True)
cond("btc_vol5_p90_lead1", volp, 1)
cond("btc_absret_p90_lead1", absp, 1)
# 挤压日前一日的指标状态(反向: 挤压可预警吗)
pre = sq_day.shift(-1).fillna(False)
res["day_before_squeeze"] = {
    "n": int(pre.sum()),
    "btc_volp_median": round(float(volp[pre].median()), 2),
    "btc_volp_all_median": round(float(volp.median()), 2)}
print("day_before_squeeze", res["day_before_squeeze"], flush=True)
json.dump(res, open(os.environ["OUT_JSON"], "w"), indent=1)
print("BTCVOL_DONE", flush=True)
