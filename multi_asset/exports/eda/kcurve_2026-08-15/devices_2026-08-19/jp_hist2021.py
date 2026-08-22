"""2020-21 重抓(日频 kline + funding 月度, 公共源)→ COVID/2021-May 事件窗因子压力.
口径声明: 用今日 450 名单回看 2020-21 = 幸存者口径(死币缺席), 读数为因子伤害的【下界】.
env: SYM_FILE OUT_DIR OUT_JSON
"""
import os, io, json, zipfile, urllib.request, socket
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd
socket.setdefaulttimeout(30)
SYMS = [s.strip() for s in open(os.environ["SYM_FILE"]) if s.strip()]
OUT = os.environ["OUT_DIR"]; os.makedirs(OUT + "/k1d", exist_ok=True); os.makedirs(OUT + "/fund", exist_ok=True)
MONTHS = [f"{y}-{m:02d}" for y in (2020, 2021) for m in range(1, 13)]
def dl(args):
    kind, s, mth = args
    base = "https://data.binance.vision/data/futures/um/monthly"
    url = (f"{base}/klines/{s}/1d/{s}-1d-{mth}.zip" if kind == "k" else f"{base}/fundingRate/{s}/{s}-fundingRate-{mth}.zip")
    out = f"{OUT}/{'k1d' if kind=='k' else 'fund'}/{s}_{mth}.zip"
    if os.path.exists(out) or os.path.exists(out + ".404"): return 0
    try:
        urllib.request.urlretrieve(url, out + ".p"); os.rename(out + ".p", out); return 1
    except Exception:
        open(out + ".404", "w").close(); return 0
jobs = [(k, s, m) for s in SYMS for m in MONTHS for k in ("k", "f")]
with ThreadPoolExecutor(max_workers=16) as ex:
    n = sum(ex.map(dl, jobs))
print(f"DL done new {n}", flush=True)
t0 = pd.Timestamp("2020-01-01"); nD = (pd.Timestamp("2022-01-01") - t0).days
dret = np.full((nD, len(SYMS)), np.nan); FUND = np.full((nD, len(SYMS)), np.nan)
for si, s in enumerate(SYMS):
    closes = {}
    for mth in MONTHS:
        p = f"{OUT}/k1d/{s}_{mth}.zip"
        if not os.path.exists(p): continue
        try:
            with zipfile.ZipFile(p) as z: raw = z.read(z.namelist()[0])
            d = pd.read_csv(io.BytesIO(raw), header=0 if raw[:1].isalpha() else None)
            for _, r in d.iterrows():
                day = (pd.Timestamp(int(r.iloc[0]), unit="ms") - t0).days
                if 0 <= day < nD: closes[day] = float(r.iloc[4])
        except Exception: pass
    if len(closes) < 30: continue
    days = sorted(closes)
    for a, b in zip(days, days[1:]):
        if b - a == 1: dret[b, si] = closes[b] / closes[a] - 1
    rows = []
    for mth in MONTHS:
        p = f"{OUT}/fund/{s}_{mth}.zip"
        if not os.path.exists(p): continue
        try:
            with zipfile.ZipFile(p) as z: rows.append(pd.read_csv(io.BytesIO(z.read(z.namelist()[0]))))
        except Exception: pass
    if rows:
        d = pd.concat(rows)
        tcol = "calc_time" if "calc_time" in d else d.columns[0]
        rcol = "last_funding_rate" if "last_funding_rate" in d else d.columns[-1]
        day = ((pd.to_datetime(d[tcol], unit="ms") - t0).dt.days).values
        g = pd.DataFrame({"d": day, "r": d[rcol].values}).groupby("d")["r"].mean()
        ok = (g.index >= 0) & (g.index < nD)
        FUND[g.index[ok], si] = g.values[ok]
print(f"panel built, 有数名/日中位 {np.median(np.isfinite(dret).sum(1)):.0f}", flush=True)
dates = pd.date_range(t0, periods=nD, freq="D")
R = pd.DataFrame(dret, index=dates)
mom30 = R.rolling(30, min_periods=20).sum().shift(2)
rev3 = (-R.rolling(3, min_periods=3).sum()).shift(1)
fnd = pd.DataFrame(FUND, index=dates).rolling(3, min_periods=2).mean().shift(1)
def ls_ret(F, short_high=False):
    out = np.full(nD, np.nan)
    for i in range(nD):
        f = F.values[i]; r = dret[i]
        ok = np.isfinite(f) & np.isfinite(r)
        if ok.sum() < 40: continue
        q = np.nanpercentile(f[ok], [10, 90])
        L, S = ((f <= q[0]), (f >= q[1])) if short_high else ((f >= q[1]), (f <= q[0]))
        out[i] = np.nanmean(r[L & ok]) - np.nanmean(r[S & ok])
    return pd.Series(out, index=dates)
momLS, revLS, fndLS = ls_ret(mom30), ls_ret(rev3), ls_ret(fnd, True)
book = 1.38 * (0.20 * momLS + 0.13 * revLS + 0.67 * fndLS)
mkt = R.mean(axis=1)
beta_r2 = R.rolling(20).corr(mkt).pow(2).mean(axis=1)
res = {"caliber": "survivor(今日449名单回看), 读数=伤害下界", "events": {}}
for k, (a, b) in {"COVID_2020": ("2020-03-08", "2020-03-16"), "MAY_2021": ("2021-05-16", "2021-05-25")}.items():
    sl = slice(a, b)
    res["events"][k] = {"n_names": int(np.isfinite(dret[(dates >= a) & (dates <= b)]).sum(1).max()),
        "mom_ls_worst_day_bps": round(float(momLS[sl].min() * 1e4), 1),
        "rev_ls_worst_day_bps": round(float(revLS[sl].min() * 1e4), 1),
        "fund_ls_worst_day_bps": round(float(fndLS[sl].min() * 1e4), 1),
        "book_worst_day_bps": round(float(book[sl].min() * 1e4), 1),
        "book_window_bps": round(float(book[sl].sum() * 1e4), 1),
        "corr_r2_peak": round(float(beta_r2[sl].max()), 2)}
    print(k, res["events"][k], flush=True)
ww = book.dropna()
res["full_2020_21"] = {"book_worst_day": round(float(ww.min() * 1e4), 1), "date": str(ww.idxmin().date()),
                       "book_worst_5d": round(float(ww.rolling(5).sum().min() * 1e4), 1)}
print("FULL:", res["full_2020_21"], flush=True)
json.dump(res, open(os.environ["OUT_JSON"], "w"), indent=1)
print("HIST2021_DONE", flush=True)
