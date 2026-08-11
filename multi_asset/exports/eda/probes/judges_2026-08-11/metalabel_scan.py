"""meta-labeling 第一步: 信号健康度 H(t) 序列 + 失效签名扫描(5 年历史)。"""
import numpy as np, pandas as pd, datetime as dt
R = np.load("/workspace/data/wide_dl_prodmask32.npz", allow_pickle=True)
P = np.load("/workspace/data/panel_targets.npz", allow_pickle=True)
M = np.load("/workspace/data/metrics_hourly.npz", allow_pickle=True)
S = np.load("/workspace/data/state_feats.npz", allow_pickle=True)
CH = R["CH"]; names = [str(x) for x in R["ch_names"]]
MEM = R["MEMBER110"]; Y4 = P["Y4"]
TS = np.asarray(P["ts"]).astype(np.int64)
T, N = Y4.shape
YEAR = np.array([dt.datetime.fromtimestamp(int(t)/1000, dt.timezone.utc).year for t in TS])
def zr(v):
    m = np.isfinite(v); o = np.full(len(v), np.nan)
    if m.sum() < 20: return o
    r = np.argsort(np.argsort(v[m])).astype(float)
    o[m] = (r - r.mean()) / (r.std() + 1e-12); return o
rows = np.array([i for i in range(24, T - 8) if i % 4 == 0])
# 逐年 Ridge 走前 → 逐锚 OOS IC
ic = np.full(T, np.nan)
cols = list(range(CH.shape[2]))
for y in sorted(set(YEAR[rows]))[1:]:
    tr = rows[YEAR[rows] < y]; te = rows[YEAR[rows] == y]
    if len(tr) < 500 or len(te) < 50: continue
    XS, YS = [], []
    for i in tr[::2]:
        m = MEM[i] & np.isfinite(Y4[i])
        if m.sum() < 25: continue
        a = np.column_stack([zr(np.where(m, CH[i, :, k], np.nan)) for k in cols])[m]
        XS.append(np.nan_to_num(a)); YS.append(zr(np.where(m, Y4[i], np.nan))[m])
    A = np.vstack(XS); b = np.concatenate(YS)
    mu, sd = A.mean(0), A.std(0) + 1e-9
    w = np.linalg.solve(((A-mu)/sd).T @ ((A-mu)/sd) + 200*np.eye(A.shape[1]), ((A-mu)/sd).T @ b)
    for i in te:
        m = MEM[i] & np.isfinite(Y4[i])
        if m.sum() < 25: continue
        a = np.column_stack([zr(np.where(m, CH[i, :, k], np.nan)) for k in cols])[m]
        p = zr(np.nan_to_num((np.nan_to_num(a)-mu)/sd) @ w); t_ = zr(np.where(m, Y4[i], np.nan))[m]
        ok = np.isfinite(p) & np.isfinite(t_)
        if ok.sum() >= 20: ic[i] = float((p[ok]*t_[ok]).mean())
v = np.isfinite(ic)
print("健康度序列: %d 锚, IC 均值 %.4f" % (v.sum(), np.nanmean(ic)))
icf = pd.Series(ic).interpolate(limit=3)
H = icf.rolling(32, min_periods=16).mean()            # 8锚×4h=32h 平滑
FUT = icf.shift(-32).rolling(32, min_periods=16).mean()  # 未来 8 锚
bad_thr = FUT.quantile(0.2)
BAD = (FUT < bad_thr).astype(float)
# 候选特征(全 ≤t)
mn = [str(x) for x in M["feats"]]
MX = M["X"]
def xmean(k):  # 横截面均值(全局聚合)
    return np.nanmean(np.where(MEM, MX[:, :, k], np.nan), axis=1)
def xdisp(k):
    return np.nanstd(np.where(MEM, MX[:, :, k], np.nan), axis=1)
fe = CH[:, :, names.index("funding_ema")].astype(np.float64); fe[fe == 0] = np.nan
rv = CH[:, :, names.index("rvol_24h")].astype(np.float64); rv[rv == 0] = np.nan
rev = -CH[:, :, names.index("rev_1h")].astype(np.float64)
# 反转因子尾随 IC(信号族自身健康)
ric = np.full(T, np.nan)
for i in rows:
    a = zr(np.where(MEM[i], rev[i], np.nan)); b2 = zr(np.where(MEM[i], Y4[i], np.nan))
    m = np.isfinite(a) & np.isfinite(b2)
    if m.sum() >= 25: ric[i] = float((a[m]*b2[m]).mean())
CAND = {
 "H_self(健康度动量)": H.values,
 "rev_trailIC": pd.Series(ric).interpolate(limit=3).rolling(96, min_periods=48).mean().values,
 "fund_lvl": pd.Series(np.nanmean(fe, 1)).rolling(24, min_periods=12).mean().values,
 "fund_disp": pd.Series(np.nanstd(fe, 1)).rolling(24, min_periods=12).mean().values,
 "oi_chg_agg": pd.Series(xmean(mn.index("oi_chg24h"))).rolling(24, min_periods=12).mean().values,
 "taker_disp": pd.Series(xdisp(mn.index("taker_ls_mean"))).rolling(24, min_periods=12).mean().values,
 "rvol_med": pd.Series(np.nanmedian(rv, 1)).rolling(24, min_periods=12).mean().values,
 "rvol_chg": (pd.Series(np.nanmedian(rv,1)).rolling(24,min_periods=12).mean()
              / pd.Series(np.nanmedian(rv,1)).rolling(168,min_periods=84).mean() - 1).values,
 "disp": S["S"][:, 0], "breadth": S["S"][:, 2], "corr_lvl": S["S"][:, 3],
}
print("\n%-22s %9s %9s  %s" % ("候选(t 时刻,因果)", "corr", "boot95CI", "判"))
ok_feats = []
msk0 = np.isfinite(BAD.values)
rng = np.random.default_rng(7)
for nm, x in CAND.items():
    x = np.asarray(x, float)
    m = msk0 & np.isfinite(x)
    if m.sum() < 2000: print("%-22s 样本不足" % nm); continue
    xi = x[m]; yi = BAD.values[m]
    r = float(pd.Series(xi).rank().corr(pd.Series(yi)))
    # 周块 bootstrap
    n = len(xi); bs = []
    for _ in range(300):
        idx = []
        while len(idx) < n:
            s0 = rng.integers(0, n - 168)
            idx.extend(range(s0, min(s0 + 168, n)))
        idx = np.array(idx[:n])
        bs.append(float(pd.Series(xi[idx]).rank().corr(pd.Series(yi[idx]))))
    lo, hi = np.percentile(bs, [2.5, 97.5])
    sig = (lo > 0) or (hi < 0)
    if sig: ok_feats.append((nm, r))
    print("%-22s %+9.3f [%+.3f,%+.3f]  %s" % (nm, r, lo, hi, "★ 显著" if sig else "—"))
print("\n显著签名: %s" % ([f for f, _ in ok_feats] or "无"))
np.savez("/workspace/data/metalabel.npz", ic=ic, H=H.values, BAD=BAD.values, ts=TS)
print("saved metalabel.npz")
