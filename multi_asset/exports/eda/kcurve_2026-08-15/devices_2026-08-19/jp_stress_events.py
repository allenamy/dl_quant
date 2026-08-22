"""压力测试仪器 v1(描述性测量, 无采纳判据): 事件窗内 因子 L/S 最差日/周 + 截面相关尖峰 + funding 爆炸.
因子: mom30 L/S(king 代理), rev3 L/S(rev24 代理), fund 秩 L/S(fund 腿代理; 空高费率).
另: 全样本最差日排名 / top-bottom 篮子相关→1 探测 / 书级换算(w3=[.20,.13,.67], gross 1.38).
env: DAILY_IN(daily_base.npz) FDIR OUT_JSON
"""
import os, glob, zipfile, io, json
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import pandas as pd

D0 = np.load(os.environ["DAILY_IN"])
dret = D0["dret"]  # (nD, NS) 2022-01-01 起
nD, NS = dret.shape
t0 = pd.Timestamp("2022-01-01")
dates = pd.date_range(t0, periods=nD, freq="D")
FDIR = os.environ["FDIR"]

def one_sym_fund(args):
    si, sym = args
    out = np.full(nD, np.nan)
    rows = []
    for z in sorted(glob.glob(f"{FDIR}/{sym}/*.zip")):
        try:
            with zipfile.ZipFile(z) as zf:
                rows.append(pd.read_csv(io.BytesIO(zf.read(zf.namelist()[0]))))
        except Exception: pass
    if not rows: return si, out
    d = pd.concat(rows)
    ts = pd.to_datetime(d["calc_time"], unit="ms")
    r8 = d["last_funding_rate"].values * (8.0 / np.maximum(d["funding_interval_hours"].values, 1))
    day = (ts - t0).dt.days.values
    ok = (day >= 0) & (day < nD)
    df = pd.DataFrame({"d": day[ok], "r": r8[ok]}).groupby("d")["r"].mean()
    out[df.index.values] = df.values
    return si, out

if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    C = np.load(os.environ.get("CACHE_IN", "/mnt/storage/private/work_hsy/w3lane/s30/cache450.npz"), mmap_mode="r")
    syms = [str(s) for s in C["symbols"]]
    FUND = np.full((nD, NS), np.nan)
    with ProcessPoolExecutor(max_workers=12) as ex:
        for si, arr in ex.map(one_sym_fund, list(enumerate(syms))):
            FUND[:, si] = arr
    print("funding daily built", flush=True)
    R = pd.DataFrame(dret, index=dates)
    mom30 = R.rolling(30, min_periods=20).sum().shift(2)   # 截至 t-2, 持有 t 日收益
    rev3 = (-R.rolling(3, min_periods=3).sum()).shift(1)
    fnd = pd.DataFrame(FUND, index=dates).rolling(3, min_periods=2).mean().shift(1)
    def ls_ret(F, short_high=False):
        out = np.full(nD, np.nan)
        for i in range(nD):
            f = F.values[i]; r = dret[i]
            ok = np.isfinite(f) & np.isfinite(r)
            if ok.sum() < 60: continue
            q = np.nanpercentile(f[ok], [10, 90])
            lo, hi = f <= q[0], f >= q[1]
            L, S = (lo, hi) if short_high else (hi, lo)
            out[i] = np.nanmean(r[L & ok]) - np.nanmean(r[S & ok])
        return pd.Series(out, index=dates)
    momLS = ls_ret(mom30)
    revLS = ls_ret(rev3)
    fndLS = ls_ret(fnd, short_high=True)  # 多低费率 空高费率
    # 截面相关(20日滚动平均两两相关的代理: 平均 R² of names vs 市场)
    mkt = R.mean(axis=1)
    beta_r2 = R.rolling(20).corr(mkt).pow(2).mean(axis=1)
    # top/bottom 篮子相关(mom 顶/底 decile 等权篮子 10 日滚动相关)
    def basket(F, top=True):
        out = np.full(nD, np.nan)
        for i in range(nD):
            f = F.values[i]; r = dret[i]
            ok = np.isfinite(f) & np.isfinite(r)
            if ok.sum() < 60: continue
            q = np.nanpercentile(f[ok], 90 if top else 10)
            m = (f >= q) if top else (f <= q)
            out[i] = np.nanmean(r[m & ok])
        return pd.Series(out, index=dates)
    topB, botB = basket(mom30, True), basket(mom30, False)
    tb_corr = topB.rolling(15).corr(botB)
    # 书级日收益代理(gross 1.38, w3)
    book = 1.38 * (0.20 * momLS + 0.13 * revLS + 0.67 * fndLS)
    fund_daily_paid = pd.DataFrame(FUND, index=dates).abs().mean(axis=1)
    EVENTS = {"LUNA_2022": ("2022-05-05", "2022-05-16"), "DELEV_3AC_2022": ("2022-06-10", "2022-06-20"),
              "FTX_2022": ("2022-11-05", "2022-11-15"), "YEN_CARRY_2024": ("2024-08-02", "2024-08-08"),
              "SQUEEZE_202608": ("2026-08-13", "2026-08-17")}
    res = {"events": {}}
    for k, (a, b) in EVENTS.items():
        sl = slice(a, b)
        seg = {"mom_ls_worst_day": round(float(momLS[sl].min() * 1e4), 1),
               "mom_ls_window_sum": round(float(momLS[sl].sum() * 1e4), 1),
               "rev_ls_worst_day": round(float(revLS[sl].min() * 1e4), 1),
               "fund_ls_worst_day": round(float(fndLS[sl].min() * 1e4), 1),
               "book_worst_day_bps": round(float(book[sl].min() * 1e4), 1),
               "book_window_bps": round(float(book[sl].sum() * 1e4), 1),
               "corr_r2_peak": round(float(beta_r2[sl].max()), 2),
               "tb_corr_peak": round(float(tb_corr[sl].max()), 2),
               "fund_abs_peak_bps8h": round(float(fund_daily_paid[sl].max() * 1e4), 2)}
        res["events"][k] = seg
        print(k, seg, flush=True)
    ww = book.dropna()
    res["full_sample"] = {
        "book_worst_day_bps": round(float(ww.min() * 1e4), 1), "book_worst_day_date": str(ww.idxmin().date()),
        "book_worst_5d_bps": round(float(ww.rolling(5).sum().min() * 1e4), 1),
        "book_worst_5d_end": str(ww.rolling(5).sum().idxmin().date()),
        "mom_worst_day": round(float(momLS.min() * 1e4), 1), "mom_worst_date": str(momLS.idxmin().date()),
        "tb_corr_max": round(float(tb_corr.max()), 2), "tb_corr_max_date": str(tb_corr.idxmax().date()),
        "n_days_tbcorr_gt_0.8": int((tb_corr > 0.8).sum())}
    print("FULL:", res["full_sample"], flush=True)
    json.dump(res, open(os.environ.get("OUT_JSON", "stress_events.json"), "w"), indent=1)
    print("STRESS_DONE", flush=True)
