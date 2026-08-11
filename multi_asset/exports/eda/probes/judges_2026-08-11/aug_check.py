"""meta-labeling 8月带外核对: 6 签名在 07-20→08-05 的逐日取值 vs 历史分位。
判读: 实盘坏块(08-05 20:00 起)之前, 组合签名是否已滑向"坏"侧。绝不拟合, 只核对。"""
import glob, numpy as np, pandas as pd, datetime as dt
R = np.load("/workspace/data/wide_dl_prodmask32.npz", allow_pickle=True)
M = np.load("/workspace/data/metrics_hourly.npz", allow_pickle=True)
S = np.load("/workspace/data/state_feats.npz", allow_pickle=True)
P = np.load("/workspace/data/panel_targets.npz", allow_pickle=True)
TS = np.asarray(P["ts"]).astype(np.int64)
names = [str(x) for x in R["ch_names"]]
MEM = R["MEMBER110"]
fe = R["CH"][:, :, names.index("funding_ema")].astype(np.float64); fe[fe==0]=np.nan
rv = R["CH"][:, :, names.index("rvol_24h")].astype(np.float64); rv[rv==0]=np.nan
mn = [str(x) for x in M["feats"]]
tk = M["X"][:, :, mn.index("taker_ls_mean")].astype(np.float64)
# 历史签名序列(与扫描同定义)
sig = {
 "taker_disp(坏↑)": pd.Series(np.nanstd(np.where(MEM, tk, np.nan),axis=1)).rolling(24,min_periods=12).mean().values,
 "disp(坏↓)":      S["S"][:,0],
 "rvol_med(坏↓)":  pd.Series(np.nanmedian(rv,1)).rolling(24,min_periods=12).mean().values,
 "fund_lvl(坏↓)":  pd.Series(np.nanmean(fe,1)).rolling(24,min_periods=12).mean().values,
 "breadth(坏↓)":   S["S"][:,2],
}
T = len(TS)
hist = slice(200, T-1500)   # 历史分位窗(留出近期)
print("%-16s %8s %8s | 近三周逐周取值(07-14/07-21/07-28→末) 与所处分位" % ("签名","P20","P80"))
import bisect
dts = np.array([dt.datetime.fromtimestamp(int(t)/1000, dt.timezone.utc) for t in TS])
wk_marks = [dt.datetime(2026,7,14,tzinfo=dt.timezone.utc), dt.datetime(2026,7,21,tzinfo=dt.timezone.utc),
            dt.datetime(2026,7,28,tzinfo=dt.timezone.utc), dt.datetime(2026,7,31,tzinfo=dt.timezone.utc)]
score = 0; nsig = 0
for nm, s in sig.items():
    s = np.asarray(s, float)
    h = s[hist]; h = h[np.isfinite(h)]
    q20, q80 = np.quantile(h, [0.2, 0.8])
    vals = []
    for a, b in zip(wk_marks[:-1], wk_marks[1:]):
        m = (dts >= a) & (dts < b) & np.isfinite(s)
        vals.append(np.nanmean(s[m]) if m.sum() else np.nan)
    pcts = [float((h < v).mean()) if np.isfinite(v) else np.nan for v in vals]
    bad_dir = "↑" in nm
    last = pcts[-1]
    lit = (bad_dir and last > 0.8) or ((not bad_dir) and last < 0.2)
    mild = (bad_dir and last > 0.6) or ((not bad_dir) and last < 0.4)
    nsig += 1; score += 1.0 if lit else (0.5 if mild else 0.0)
    print("%-16s %8.4g %8.4g | %s  %s" % (nm, q20, q80,
        "  ".join("%.0f%%" % (p*100) if np.isfinite(p) else "--" for p in pcts),
        "★点亮" if lit else ("~偏坏" if mild else "未亮")))
print("\n组合读数(0-1, 07-28→31 周): %.2f  (>0.5 = 签名在坏块前已偏坏)" % (score/nsig))
