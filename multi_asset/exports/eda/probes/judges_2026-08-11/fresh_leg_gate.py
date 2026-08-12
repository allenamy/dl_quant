"""LGBM-fresh 第四腿 · 腿录取门 v2 · 判据冻结(先于数字)
候选: v4 装置的 LGBM(160 滞后特征, rank-z 目标, 逐年 walk-forward)每 4h 新鲜打分 —— 假设其价值
在 king 8h 刷新间隙的新鲜度。
S1 筛: z(复合新鲜目标)+δ·z(lgbm) Δxsec-rankIC, walk-forward 因果选 δ; 过筛 = 平均 ≥+0.003 且
  评估年全非负; 附 legCorr(与 king held 分数 pooled corr —— ≥0.6 记同簇警示但仍进 S2 由净额定生死,
  因为候选的论点恰是"同信息不同新鲜度")。
S2 净(两形态): ①全锚第4腿 w∈{.05,.1} ②仅 off-refresh 锚(ti%8!=0)注入 —— 新鲜度靶向形态。
  G 族: Δ净@4.137 CI95>0 且 @6.23≥0 且逐年≥4/5 且夏普不降(候选自身换手已内生定价)。
预写死法: S1 过而 S2 全灭于换手 = RM1 同款(第五例), 照记关闭。"""
import sys
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
import numpy as np, pandas as pd
from scipy.stats import rankdata, spearmanr
import lightgbm as lgb
import legs as LG
import engine.replay_fullhist as RF
PANEL = MA + "/exports/wide_dl_full_corrfund_causal_v1.npz"
src = RF.get_src(PANEL, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N; n = len(a)
C = src.CH.shape[2]; LAGS = [0, 1, 3, 6, 24]; F = C*len(LAGS)
FI, RVI = src.fund_idx, src.ch.index("rvol_24h")
SYMS = [str(s) for s in src.symbols]
X = np.full((n, N, F), np.nan, dtype=np.float32)
Y = np.full((n, N), np.nan, dtype=np.float32)
KING = np.full((n, N), np.nan, dtype=np.float32)
held_k = np.full(N, np.nan)
for i, t in enumerate(a):
    ti = int(t); m = np.asarray(src.tradeable(ti))
    if m.dtype == bool: m = np.where(m)[0]
    if i == 0 or ti % 8 == 0:
        v = np.full(N, np.nan); v[m] = src.king[ti, m]; held_k = v
    KING[i] = held_k; Y[i, m] = src.Y4[ti, m]
    for li, L in enumerate(LAGS):
        if ti - L >= 0: X[i, m, li*C:(li+1)*C] = src.CH[ti-L, m, :]
YRZ = np.full_like(Y, np.nan)
for i in range(n):
    ok = np.isfinite(Y[i])
    if ok.sum() >= 10:
        r_ = rankdata(Y[i, ok]); YRZ[i, ok] = (r_-(ok.sum()+1)/2)/max(ok.sum()-1, 1)
yrs = np.array(yr)
PAR = dict(objective="regression", num_leaves=63, learning_rate=0.03, min_data_in_leaf=200,
           feature_fraction=0.7, bagging_fraction=0.8, bagging_freq=1, verbosity=-1, num_threads=8)
LGP = np.full((n, N), np.nan, dtype=np.float32)
for Yv in (2023, 2024, 2025, 2026):
    tr = np.where(yrs < Yv)[0][::2]; te = np.where(yrs == Yv)[0]
    xs, ys = [], []
    for i in tr:
        ok = np.isfinite(YRZ[i]); xs.append(X[i, ok]); ys.append(YRZ[i, ok])
    mdl = lgb.train(PAR, lgb.Dataset(np.concatenate(xs), np.concatenate(ys)), num_boost_round=300)
    for i in te:
        ok = np.isfinite(Y[i]); LGP[i, ok] = mdl.predict(X[i, ok])
    print(f"fold {Yv} preds done", flush=True)
np.savez_compressed(f"{PD}/lgbm_fresh_pred.npz", pred=LGP, anchors=np.asarray(a), years=yrs)
def xz(v):
    ok = np.isfinite(v)
    if ok.sum() < 10: return np.full_like(v, np.nan)
    r_ = np.full_like(v, np.nan); r_[ok] = (rankdata(v[ok])-(ok.sum()+1)/2)/max(ok.sum()-1, 1)
    return r_
def spear(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    return spearmanr(x[ok], y[ok]).correlation if ok.sum() >= 10 else np.nan
held = {"k": np.full(N, np.nan), "s": np.full(N, np.nan), "f": np.full(N, np.nan)}
COMP, MSK, RET, RV, KL, SL, FL = [], [], [], [], [], [], []
W = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}; C1, C2 = 4.137, 6.23; ANN = np.sqrt(6*365)
for i, t in enumerate(a):
    ti = int(t); m = np.asarray(src.tradeable(ti))
    if m.dtype == bool: m = np.where(m)[0]
    if i == 0 or ti % 8 == 0:
        v = np.full(N, np.nan); v[m] = src.king[ti, m]; held["k"] = v.copy()
    if i == 0 or ti % 24 == 0:
        v = np.full(N, np.nan); v[m] = src.s2[ti, m]; held["s"] = v.copy()
    if i == 0 or ti % 8 == 0:
        v = np.full(N, np.nan); v[m] = src.CH[ti, m, FI]; held["f"] = v.copy()
    rv = src.CH[ti, m, RVI].astype(float)
    r = LG.compose_book(held["k"][m], held["s"][m], held["f"][m], np.ones(len(m)),
                        weights=W, rvol=rv, risk_budget=RB)
    w = np.full(N, np.nan); w[m] = np.asarray(r["target_w"], float)
    COMP.append(w); MSK.append(m); RET.append(src.Y4[ti, m].astype(float)); RV.append(rv)
    KL.append(held["k"].copy()); SL.append(held["s"].copy()); FL.append(held["f"].copy())
print("== S1 筛 ==", flush=True)
DELTAS = [0.05, 0.1, 0.2, 0.3]
ic_gain = np.full((n, len(DELTAS)), np.nan); kcors = []
for i in range(n):
    m = MSK[i]; y = RET[i]
    cz = xz(COMP[i][m]); fz = xz(LGP[i][m])
    if not np.isfinite(fz).any(): continue
    b = spear(cz, y)
    for j, d in enumerate(DELTAS):
        ic_gain[i, j] = spear(cz + d*np.nan_to_num(fz), y) - b
    okc = np.isfinite(fz) & np.isfinite(KL[i][m])
    if okc.sum() > 20: kcors.append(np.corrcoef(fz[okc], KL[i][m][okc])[0, 1])
gains = []
for Yv in (2024, 2025, 2026):
    trm = (yrs < Yv) & (yrs >= 2023); tem = yrs == Yv
    jstar = int(np.nanargmax(np.nanmean(ic_gain[trm], axis=0)))
    gains.append((Yv, DELTAS[jstar], float(np.nanmean(ic_gain[tem, jstar]))))
avg = float(np.mean([g[2] for g in gains])); allpos = all(g[2] >= 0 for g in gains)
print(f"S1: 逐年 {[(g[0], g[1], round(g[2],4)) for g in gains]} 均值 {avg:+.4f} "
      f"kingCorr {np.mean(kcors):+.2f} ⇒ {'★过筛' if avg>=0.003 and allpos else 'fail'}", flush=True)
print("== S2 净 ==", flush=True)
def run_book(w4=0.0, off_only=False):
    state = None; prev = np.zeros(N)
    pnl = np.zeros(n); trn = np.zeros(n)
    for i in range(n):
        m = MSK[i]; ti = int(a[i])
        use = w4 if (w4 > 0 and (not off_only or ti % 8 != 0) and np.isfinite(LGP[i][m]).any()) else 0.0
        if use > 0:
            sc = 1-use
            W_ = {"king": W["king"]*sc, "s2": W["s2"]*sc, "funding": W["funding"]*sc, "size": use}
            r = LG.compose_book(KL[i][m], SL[i][m], FL[i][m], np.nan_to_num(xz(LGP[i][m])),
                                weights=W_, rvol=RV[i], risk_budget=RB)
            tgt0 = np.asarray(r["target_w"], float)
        else:
            tgt0 = COMP[i][m]
        out = LG.apply_harvest_ema(tgt0, [SYMS[j] for j in m], state, 0.05)
        state = out["state"]; tgt = np.asarray(out["target_w"], float)
        w = prev.copy(); w[[j for j in range(N) if j not in set(m)]] = 0.0
        delta = tgt - w[m]; T = np.abs(delta) > 0.002
        wm = w[m].copy(); wm[T] = tgt[T]
        if T.any(): wm[T] -= wm.sum()/T.sum()
        w[m] = wm
        y = RET[i]; ok = np.isfinite(y)
        pnl[i] = float(np.nansum(w[m][ok]*y[ok]))*1e4
        trn[i] = float(np.abs(w-prev).sum()); prev = w
    return pnl, trn
def boot(d, nb=2000, bl=5):
    rng = np.random.default_rng(77); L = len(d); k = int(np.ceil(L/bl)); o = np.empty(nb)
    for q in range(nb):
        st = rng.integers(0, max(L-bl, 1), size=k)
        ix = (st[:, None]+np.arange(bl)[None, :]).ravel()[:L]; ix = ix[ix < L]
        o[q] = d[ix].mean()
    return float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))
p0, t0 = run_book(); n0 = p0-t0*C1; sh0 = n0.mean()/n0.std(ddof=1)*ANN
print(f"基线: 净 {n0.mean():+.3f} 夏普 {sh0:+.2f} 换手 {t0.mean():.4f}", flush=True)
for nm, w4, off in (("全锚 w=.05", .05, False), ("全锚 w=.10", .10, False),
                    ("off-refresh w=.05", .05, True), ("off-refresh w=.10", .10, True)):
    p, t = run_book(w4, off)
    net = p-t*C1; d = net-n0; lo, hi = boot(d)
    d2 = (p-t*C2).mean()-(p0-t0*C2).mean()
    dfy = pd.DataFrame({"y": yrs, "d": d}).groupby("y").d.mean()
    sh = net.mean()/net.std(ddof=1)*ANN
    ok_ = "★PASS" if (lo > 0 and d2 >= 0 and (dfy >= 0).sum() >= 4 and sh >= sh0) else "fail"
    print(f"  {nm}: Δ净 {d.mean():+.4f} CI[{lo:+.4f},{hi:+.4f}] @6.23 {d2:+.4f} "
          f"逐年{int((dfy>=0).sum())}/5 换手 {t.mean():.4f} 夏普 {sh:+.2f} {ok_}", flush=True)
print("FRESHLEG_DONE", flush=True)
