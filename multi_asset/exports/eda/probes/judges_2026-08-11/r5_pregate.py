"""R5 uplift 线性前置门 · 判据冻结(先于数字)
命题: 决策相关性加权训练 —— 名字按 |持仓| 加权进损失(钱在哪精度就在哪), 是 R5(边际净贡献目标)
在 CPU 上可判的形态。另一形态"逐名换手税"已推导关闭(成本仅占毛额 8.5%, 上界 ~0.1bps/锚)。
装置: 同面板 32ch 特征, 均匀 Ridge vs |w_held| 加权 Ridge, walk-forward(2022 烧入, 评估 2023-26)。
判据: PASS = 加权变体 值空间IC − 均匀变体 ≥ +0.002 且 4/4 评估年非负(值口径 = R5 的目标口径)。
PASS ⇒ GPU 决策加权训练提案; FAIL ⇒ R5 线性级关闭(与换手税推导合并入档)。
诊断附注(不改判): 加权是否把精度挪向高|w|三分位。"""
import sys
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
import numpy as np, pandas as pd
from scipy.stats import rankdata, spearmanr
import legs as LG
import engine.replay_fullhist as RF
WB = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N; n = len(a)
FI, RVI = src.fund_idx, src.ch.index("rvol_24h")
SYMS = [str(s) for s in src.symbols]
C = src.CH.shape[2]
held = {"k": np.full(N, np.nan), "s": np.full(N, np.nan), "f": np.full(N, np.nan)}
state = None; prev = np.zeros(N)
X = np.full((n, N, C), np.nan, dtype=np.float32)
Y = np.full((n, N), np.nan, dtype=np.float32)
WH = np.zeros((n, N), dtype=np.float32)
MS = []
for i, t in enumerate(a):
    ti = int(t); m = np.asarray(src.tradeable(ti))
    if m.dtype == bool: m = np.where(m)[0]
    MS.append(m)
    if i == 0 or ti % 8 == 0:
        v = np.full(N, np.nan); v[m] = src.king[ti, m]; held["k"] = v
    if i == 0 or ti % 24 == 0:
        v = np.full(N, np.nan); v[m] = src.s2[ti, m]; held["s"] = v
    if i == 0 or ti % 8 == 0:
        v = np.full(N, np.nan); v[m] = src.CH[ti, m, FI]; held["f"] = v
    rv = src.CH[ti, m, RVI].astype(float)
    r = LG.compose_book(held["k"][m], held["s"][m], held["f"][m], np.ones(len(m)),
                        weights=WB, rvol=rv, risk_budget=RB)
    out = LG.apply_harvest_ema(np.asarray(r["target_w"], float), [SYMS[j] for j in m], state, 0.05)
    state = out["state"]; tgt = np.asarray(out["target_w"], float)
    w = prev.copy(); w[[j for j in range(N) if j not in set(m)]] = 0.0
    delta = tgt - w[m]; T = np.abs(delta) > 0.002
    wm = w[m].copy(); wm[T] = tgt[T]
    if T.any(): wm[T] -= wm.sum()/T.sum()
    w[m] = wm; prev = w
    WH[i, m] = np.abs(w[m])
    X[i, m, :] = src.CH[ti, m, :]
    Y[i, m] = src.Y4[ti, m]
# 特征横截面 rank-z(逐锚逐通道)
def xsec_rankz(A):
    out = np.full_like(A, np.nan)
    for i in range(A.shape[0]):
        v = A[i]; ok = np.isfinite(v)
        if ok.sum() < 10: continue
        out[i, ok] = (rankdata(v[ok]) - (ok.sum()+1)/2) / max(ok.sum()-1, 1)
    return out
for c in range(C):
    X[:, :, c] = xsec_rankz(X[:, :, c])
yrs = np.array(yr)
def fit_ridge(Xtr, ytr, wtr, lam):
    XW = Xtr * wtr[:, None]
    A_ = Xtr.T @ XW + lam*np.eye(Xtr.shape[1])
    return np.linalg.solve(A_, XW.T @ ytr)
def year_eval(pred, i_idx):
    vic, ric = [], []
    for i in i_idx:
        m = MS[i]; p = pred[i, m]; y = Y[i, m]
        ok = np.isfinite(p) & np.isfinite(y)
        if ok.sum() < 30: continue
        vic.append(np.corrcoef(p[ok], y[ok])[0, 1])
        ric.append(spearmanr(p[ok], y[ok]).correlation)
    return float(np.nanmean(vic)), float(np.nanmean(ric))
print("== R5 线性前置门: 均匀 vs |w_held| 加权 Ridge ==", flush=True)
res = {"unif": [], "wght": []}
diag = []
for Yv in (2023, 2024, 2025, 2026):
    tr = np.where(yrs < Yv)[0]; te = np.where(yrs == Yv)[0]
    rowsX, rowsY, rowsW = [], [], []
    for i in tr:
        m = MS[i]; ok = np.isfinite(Y[i, m]) & np.all(np.isfinite(X[i, m, :]), axis=1)
        rowsX.append(X[i, m, :][ok]); rowsY.append(Y[i, m][ok])
        wv = WH[i, m][ok]; rowsW.append(0.1 + wv/ (wv.mean() + 1e-12))
    Xtr = np.concatenate(rowsX); ytr = np.concatenate(rowsY); wtr = np.concatenate(rowsW)
    ntr = len(Xtr); cut = int(ntr*0.8)
    best = {}
    for tag, wa in (("unif", np.ones(ntr)), ("wght", wtr)):
        scores = []
        for lam in (1e1, 1e2, 1e3, 1e4):
            b = fit_ridge(Xtr[:cut], ytr[:cut], wa[:cut], lam)
            pv = Xtr[cut:] @ b
            scores.append((np.corrcoef(pv, ytr[cut:])[0, 1], lam))
        lam = max(scores)[1]
        best[tag] = fit_ridge(Xtr, ytr, wa, lam)
    for tag in ("unif", "wght"):
        P = np.full((n, N), np.nan, dtype=np.float32)
        for i in te:
            m = MS[i]; xm = X[i, m, :]
            ok = np.all(np.isfinite(xm), axis=1)
            pv = np.full(len(m), np.nan); pv[ok] = xm[ok] @ best[tag]
            P[i, m] = pv
        vic, ric = year_eval(P, te)
        res[tag].append((Yv, vic, ric))
    # 诊断: 加权变体在高|w|三分位上的值IC vs 其余
    Pw = np.full((n, N), np.nan, dtype=np.float32)
    for i in te:
        m = MS[i]; xm = X[i, m, :]; ok = np.all(np.isfinite(xm), axis=1)
        pv = np.full(len(m), np.nan); pv[ok] = xm[ok] @ best["wght"]
        Pw[i, m] = pv
    hi, lo = [], []
    for i in te:
        m = MS[i]; wv = WH[i, m]; p = Pw[i, m]; y = Y[i, m]
        ok = np.isfinite(p) & np.isfinite(y)
        if ok.sum() < 30: continue
        thr = np.quantile(wv[ok], 2/3)
        h = ok & (wv >= thr); l = ok & (wv < thr)
        if h.sum() > 10: hi.append(np.corrcoef(p[h], y[h])[0, 1])
        if l.sum() > 10: lo.append(np.corrcoef(p[l], y[l])[0, 1])
    diag.append((Yv, float(np.nanmean(hi)), float(np.nanmean(lo))))
for tag, nm in (("unif", "均匀"), ("wght", "|w|加权")):
    rows = res[tag]
    print(f"  {nm}: " + " ".join(f"{y}:v{v:+.4f}/r{r:+.4f}" for y, v, r in rows) +
          f" | 均值 v{np.mean([v for _,v,_ in rows]):+.4f} r{np.mean([r for _,_,r in rows]):+.4f}", flush=True)
dv = [res["wght"][k][1] - res["unif"][k][1] for k in range(4)]
print(f"  Δ值IC 逐年 {[round(x,4) for x in dv]} 均值 {np.mean(dv):+.4f}", flush=True)
print(f"  诊断(加权变体 高|w|三分位 vs 其余 值IC): {[(y, round(h,4), round(l,4)) for y,h,l in diag]}", flush=True)
ok_ = np.mean(dv) >= 0.002 and all(x >= 0 for x in dv)
print("★PASS ⇒ GPU 决策加权提案" if ok_ else "FAIL ⇒ R5 线性级关闭(与换手税推导合并)", flush=True)
print("R5_DONE", flush=True)
