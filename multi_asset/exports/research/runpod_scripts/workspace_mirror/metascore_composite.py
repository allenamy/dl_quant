"""B2: meta-score 合成 — 六显著签名 logistic 走前(E25 后续, DECISION §3-B2)
签名(E25 定案): taker_disp(稳健 log-IQR 版) / disp / rvol_med / fund_lvl / H_self / breadth
装置: 逐年走前 logistic(牛顿法, 6 特征), 判据 = 每年 OOS AUC>0.5 且无反年;
产物: metascore.npz(score 全序列 + 系数) —— 研究件, 供三级部署的后两级引用。"""
import numpy as np, pandas as pd, datetime as dt, faulthandler
faulthandler.enable()
R = np.load("/workspace/data/wide_dl_prodmask32.npz", allow_pickle=True)
M = np.load("/workspace/data/metrics_hourly.npz", allow_pickle=True)
S = np.load("/workspace/data/state_feats.npz", allow_pickle=True)
ML = np.load("/workspace/data/metalabel.npz", allow_pickle=True)
CH = R["CH"]; MEM = R["MEMBER110"]; names = [str(x) for x in R["ch_names"]]
MX = M["X"]; mn = [str(x) for x in M["feats"]]
TS = ML["ts"].astype(np.int64); T = len(TS)
YEAR = np.array([dt.datetime.fromtimestamp(int(t)/1000, dt.timezone.utc).year for t in TS])
MON = np.array([dt.datetime.fromtimestamp(int(t)/1000, dt.timezone.utc).month for t in TS])
H = ML["H"]; BAD = ML["BAD"]
fe = CH[:, :, names.index("funding_ema")].astype(np.float64); fe[fe == 0] = np.nan
rv = CH[:, :, names.index("rvol_24h")].astype(np.float64); rv[rv == 0] = np.nan
tk = np.where(MEM, MX[:, :, mn.index("taker_ls_mean")], np.nan)
# 稳健 taker_disp: log 变换后横截面 IQR(E25 处方)
with np.errstate(all="ignore"):
    ltk = np.log(np.where(tk > 0, tk, np.nan))
    q75 = np.nanpercentile(ltk, 75, axis=1); q25 = np.nanpercentile(ltk, 25, axis=1)
td = pd.Series(q75 - q25).rolling(24, min_periods=12).mean().values
F = {
 "taker_disp_r": td,
 "disp": S["S"][:, 0],
 "rvol_med": pd.Series(np.nanmedian(rv, 1)).rolling(24, min_periods=12).mean().values,
 "fund_lvl": pd.Series(np.nanmean(fe, 1)).rolling(24, min_periods=12).mean().values,
 "H_self": H,
 "breadth": S["S"][:, 2],
}
X = np.column_stack([np.asarray(v, float) for v in F.values()])
ok = np.isfinite(BAD) & np.all(np.isfinite(X), axis=1)
print("样本 %d/%d 锚可用" % (ok.sum(), T), flush=True)
def rankz(a):
    r = pd.Series(a).rank().values
    return (r - np.nanmean(r)) / (np.nanstd(r) + 1e-12)
def logit_fit(A, y, lam=1e-2, iters=60):
    w = np.zeros(A.shape[1] + 1); Ab = np.column_stack([np.ones(len(A)), A])
    for _ in range(iters):
        p = 1/(1+np.exp(-Ab@w)); g = Ab.T@(p-y) + lam*np.r_[0, w[1:]]
        Wd = p*(1-p); Hm = (Ab*Wd[:,None]).T@Ab + lam*np.eye(len(w))
        w -= np.linalg.solve(Hm, g)
    return w
def auc(s, y):
    r = pd.Series(s).rank().values; n1 = y.sum(); n0 = len(y)-n1
    return (r[y>0.5].sum() - n1*(n1+1)/2) / (n1*n0 + 1e-12)
print("%-6s %8s %8s %6s" % ("测试年", "AUC", "rcorr", "n"), flush=True)
res = {}
for y in (2024, 2025, 2026):
    tr = ok & (YEAR < y) & (YEAR >= 2022); te = ok & (YEAR == y)
    Az = np.column_stack([rankz(X[tr, j]) for j in range(X.shape[1])])
    mu_r = [(pd.Series(X[tr, j]).rank().values.mean(), pd.Series(X[tr, j]).rank().values.std()) for j in range(X.shape[1])]
    w = logit_fit(Az, BAD[tr])
    # 测试年特征用【训练年分布】的经验 CDF 映射(因果: 不看测试年分布)
    Ate = np.column_stack([
        (np.searchsorted(np.sort(X[tr, j]), X[te, j]) - mu_r[j][0]) / (mu_r[j][1] + 1e-12)
        for j in range(X.shape[1])])
    s = 1/(1+np.exp(-(np.column_stack([np.ones(te.sum()), Ate])@w)))
    a = auc(s, BAD[te]); rc = float(pd.Series(s).rank().corr(pd.Series(BAD[te]).rank()))
    res[y] = (a, rc); print("%-6d %8.3f %8.3f %6d" % (y, a, rc, te.sum()), flush=True)
# 全史模型 + 8 月读数
tr = ok & (YEAR >= 2022)
Az = np.column_stack([rankz(X[tr, j]) for j in range(X.shape[1])])
w = logit_fit(Az, BAD[tr])
score = np.full(T, np.nan)
Aall = np.column_stack([
    (np.searchsorted(np.sort(X[tr, j]), X[:, j]) - pd.Series(X[tr, j]).rank().values.mean())
    / (pd.Series(X[tr, j]).rank().values.std() + 1e-12) for j in range(X.shape[1])])
mfin = np.all(np.isfinite(Aall), axis=1)
score[mfin] = 1/(1+np.exp(-(np.column_stack([np.ones(mfin.sum()), Aall[mfin]])@w)))
aug = (YEAR == 2026) & (MON == 8) & np.isfinite(score)
hist = (YEAR < 2026) & np.isfinite(score)
if aug.sum():
    pct = float((score[hist][:, None] < score[aug][None, :]).mean())
    print("8月窗: %d 锚, score 均值 %.3f, 相对历史分位 %.1f%%" % (aug.sum(), score[aug].mean(), 100*pct), flush=True)
np.savez("/workspace/data/metascore.npz", ts=TS, score=score, coef=w,
         feat_names=np.array(list(F.keys())), auc_by_year=np.array([[y, *res[y]] for y in res]))
print("METASCORE_DONE", flush=True)
