"""压力 v2(用户质询三件): A. N_eff 实测(参与率, 残差化前后, 分年);
D. 残差相关探测器 v2(β_BTC 残差化 → 顶/底篮子残差相关 + 离散度 + 因子PnL 三联, 事件对齐);
C. 死币回补(LUNA/FTT/SRM/ANC 下载并入 2022 事件窗, 量化幸存者低估).
env: DAILY_IN CACHE_IN OUT_JSON
"""
import os, io, json, zipfile, urllib.request, socket
import numpy as np
import pandas as pd
socket.setdefaulttimeout(30)
D0 = np.load(os.environ["DAILY_IN"])
dret = D0["dret"].copy(); nD, NS = dret.shape
t0 = pd.Timestamp("2022-01-01")
dates = pd.date_range(t0, periods=nD, freq="D")
C = np.load(os.environ["CACHE_IN"], mmap_mode="r")
syms = [str(s) for s in C["symbols"]]; iBTC = syms.index("BTCUSDT")
res = {}
# ---- A. N_eff 参与率 ----
btc = np.nan_to_num(dret[:, iBTC])
def participation(Rm):
    sd = Rm.std(1)
    Rm = Rm[sd > 1e-9]
    Cm = np.nan_to_num(np.corrcoef(Rm), nan=0.0)
    np.fill_diagonal(Cm, 1.0)
    ev = np.linalg.eigvalsh(Cm)
    ev = ev[ev > 1e-12]
    return float(ev.sum() ** 2 / (ev ** 2).sum())
res["A_neff"] = {}
for tag, y0, y1 in (("2024", "2024-01-01", "2024-12-31"), ("2025", "2025-01-01", "2025-12-31"),
                    ("2026", "2026-01-01", "2026-08-01"), ("all_24_26", "2024-01-01", "2026-08-01")):
    m = (dates >= y0) & (dates <= y1)
    sub = dret[m]
    ok = np.isfinite(sub).sum(0) >= 0.9 * m.sum()
    X = sub[:, ok]
    X = np.where(np.isfinite(X), X, 0)
    b = btc[m]
    beta = (X * b[:, None]).sum(0) / max((b ** 2).sum(), 1e-12)
    Xr = X - b[:, None] * beta[None, :]
    res["A_neff"][tag] = {"n_names": int(ok.sum()),
                          "PR_raw": round(participation(X.T), 1),
                          "PR_resid_btc": round(participation(Xr.T), 1)}
    print("A", tag, res["A_neff"][tag], flush=True)
# ---- D. 探测器 v2 ----
R = pd.DataFrame(dret, index=dates)
mom30 = R.rolling(30, min_periods=20).sum().shift(2)
def basket_resid(top):
    out = np.full(nD, np.nan)
    for i in range(nD):
        f = mom30.values[i]; r = dret[i]
        ok = np.isfinite(f) & np.isfinite(r)
        if ok.sum() < 60: continue
        q = np.nanpercentile(f[ok], 90 if top else 10)
        mset = ((f >= q) if top else (f <= q)) & ok
        out[i] = np.nanmean(r[mset])
    s = pd.Series(out, index=dates)
    be = s.rolling(60, min_periods=40).cov(pd.Series(btc, index=dates)) / pd.Series(btc, index=dates).rolling(60, min_periods=40).var()
    return s - be * pd.Series(btc, index=dates)
topR, botR = basket_resid(True), basket_resid(False)
rc = topR.rolling(15).corr(botR)
disp = R.sub(R.mean(axis=1), axis=0).std(axis=1)
momLS = pd.Series([np.nan] * nD, index=dates)
for i in range(nD):
    f = mom30.values[i]; r = dret[i]
    ok = np.isfinite(f) & np.isfinite(r)
    if ok.sum() < 60: continue
    q = np.nanpercentile(f[ok], [10, 90])
    momLS.iloc[i] = np.nanmean(r[(f >= q[1]) & ok]) - np.nanmean(r[(f <= q[0]) & ok])
q_rc, q_dp = rc.quantile(0.9), disp.quantile(0.9)
trig = (rc > q_rc) & (disp > q_dp)
fwd5 = momLS.rolling(5).sum().shift(-5)
res["D_detector"] = {"share_days_resid_corr_gt_0.8": round(float((rc > 0.8).mean()), 3),
    "n_trigger_days": int(trig.sum()),
    "momLS_next5d_on_trigger_bps": round(float(fwd5[trig].mean() * 1e4), 1),
    "momLS_next5d_uncond_bps": round(float(fwd5.mean() * 1e4), 1),
    "worst_day_rc": round(float(rc.loc["2025-12-16"]) if "2025-12-16" in rc.index else np.nan, 2),
    "events_rc_peak": {k: round(float(rc[slice(a, b)].max()), 2) for k, (a, b) in
        {"LUNA": ("2022-05-05", "2022-05-16"), "FTX": ("2022-11-05", "2022-11-15"),
         "YEN24": ("2024-08-02", "2024-08-08")}.items()}}
print("D", res["D_detector"], flush=True)
# ---- C. 死币回补 ----
DEAD = ["LUNAUSDT", "FTTUSDT", "SRMUSDT", "ANCUSDT"]
base = "https://data.binance.vision/data/futures/um/monthly/klines"
dead_ret = {}
for s in DEAD:
    closes = {}
    for mth in [f"{y}-{m:02d}" for y in (2021, 2022) for m in range(1, 13)]:
        url = f"{base}/{s}/1d/{s}-1d-{mth}.zip"
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "M"}), timeout=20).read()
            with zipfile.ZipFile(io.BytesIO(raw)) as z: b = z.read(z.namelist()[0])
            d = pd.read_csv(io.BytesIO(b), header=0 if b[:1].isalpha() else None)
            for _, r in d.iterrows():
                day = (pd.Timestamp(int(r.iloc[0]), unit="ms") - t0).days
                if 0 <= day < nD: closes[day] = float(r.iloc[4])
        except Exception: pass
    if len(closes) > 20:
        v = np.full(nD, np.nan)
        days = sorted(closes)
        for a, b2 in zip(days, days[1:]):
            if b2 - a == 1: v[b2] = closes[b2] / closes[a] - 1
        dead_ret[s] = v
        print("C dead", s, "days", len(closes), "min_dayret", round(np.nanmin(v), 3), flush=True)
if dead_ret:
    ext = np.column_stack([dret] + [dead_ret[s] for s in dead_ret])
    Rx = pd.DataFrame(ext, index=dates)
    momX = Rx.rolling(30, min_periods=20).sum().shift(2)
    revX = (-Rx.rolling(3, min_periods=3).sum()).shift(1)
    def ls2(F, i):
        f = F.values[i]; r = ext[i]
        ok = np.isfinite(f) & np.isfinite(r)
        if ok.sum() < 60: return np.nan
        q = np.nanpercentile(f[ok], [10, 90])
        return np.nanmean(r[(f >= q[1]) & ok]) - np.nanmean(r[(f <= q[0]) & ok])
    res["C_dead_names"] = {}
    for k, (a, b) in {"LUNA_withdead": ("2022-05-05", "2022-05-16"), "FTX_withdead": ("2022-11-05", "2022-11-15")}.items():
        m = np.where((dates >= a) & (dates <= b))[0]
        mm = [ls2(momX, i) for i in m]; rr = [ls2(revX, i) for i in m]
        res["C_dead_names"][k] = {"mom_ls_worst_day_bps": round(float(np.nanmin(mm) * 1e4), 1),
                                  "rev_ls_worst_day_bps": round(float(np.nanmin(rr) * 1e4), 1),
                                  "mom_window_bps": round(float(np.nansum(mm) * 1e4), 1)}
        print("C", k, res["C_dead_names"][k], flush=True)
json.dump(res, open(os.environ["OUT_JSON"], "w"), indent=1)
print("STRESSV2_DONE", flush=True)
