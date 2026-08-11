"""W4 G1 门 · 判据冻结 = PREREG 75a09de2 §4 (先于数字)
两段:
 S1 筛(廉价, 分数级混合近似): z(复合新鲜目标) + δ·z_f 的 Δxsec-rankIC, δ 符号与档位由
    扩展窗 walk-forward 因果选取(2022 烧入, 评估 2023-26)。过筛 = 平均 Δ ≥ +0.003 且
    评估年全部 ≥0 且与三腿 |pooled corr| < 0.6。4h/24h 成对特征按族 Bonferroni×2 心算报告。
 S2 净(仅幸存者): 候选作第4腿进 compose_book(size 槽, 其余腿 ×(1−w)), 全书 EMA+带重放,
    G 族: Δ净@4.137 CI95>0 且 @6.23≥0 且逐年≥4/5 且夏普不降。
特征因果化: 逐资产 rolling 180锚 中位/MAD z(shift 1 锚), 横截面 winsor ±3。"""
import sys
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
import numpy as np, pandas as pd
from scipy.stats import rankdata
import legs as LG
import engine.replay_fullhist as RF
WB = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}; C1, C2 = 4.137, 6.23; ANN = np.sqrt(6*365)
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N; n = len(a)
FI, RVI = src.fund_idx, src.ch.index("rvol_24h")
SYMS = [str(s) for s in src.symbols]
Z = np.load(f"{MA}/exports/w4_liq_proxy_v1.npz", allow_pickle=True)
zts = Z["ts"]; zsyms = list(Z["symbols"]); zfeats = list(Z["feats"]); zd = Z["data"]
ts2row = {int(t): i for i, t in enumerate(zts)}
sym2col = {s: j for j, s in enumerate(zsyms)}
col_of = np.array([sym2col.get(s, -1) for s in SYMS])
# 面板行=K线开盘时间索引(anchor_ts 名义−1h 家族, 偏移谱实测峰@+1h) ⇒ 决策墙钟 = ts+1h
anchor_epoch = (src.ts[np.asarray(a, dtype=np.int64)] // 1000 + 3600).astype(np.int64)
rows = np.array([ts2row.get(int(e), -1) for e in anchor_epoch])
print(f"anchor→feature 行映射命中率 {(rows>=0).mean():.1%} (必须>95%)", flush=True)
assert (rows >= 0).mean() > 0.95
def feat_panel(fi):
    X = np.full((n, N), np.nan, dtype=np.float32)
    ok = (rows >= 0)[:, None] & (col_of >= 0)[None, :]
    r = np.where(rows >= 0, rows, 0)
    c = np.where(col_of >= 0, col_of, 0)
    X[:] = zd[r][:, c, fi]
    X[~ok] = np.nan
    return X
def madz(X):
    df = pd.DataFrame(X)
    med = df.rolling(180, min_periods=60).median().shift(1)
    mad = (df - med).abs().rolling(180, min_periods=60).median().shift(1)
    z = (df - med) / (1.4826 * mad + 1e-12)
    return z.clip(-3, 3).to_numpy()
F1_24 = feat_panel(zfeats.index("f1_24"))
RET24 = feat_panel(zfeats.index("ret24"))
CAND = {
    "F1_4h": madz(feat_panel(zfeats.index("f1_4"))),
    "F1_24h": madz(F1_24),
    "F2_4h": madz(feat_panel(zfeats.index("f2_4"))),
    "F2_24h": madz(feat_panel(zfeats.index("f2_24"))),
    "F3_recency": madz(feat_panel(zfeats.index("f3"))),
    "F4_imbal": madz(feat_panel(zfeats.index("f4"))),
    "F5_liq_x_ret": madz(F1_24) * np.sign(np.nan_to_num(RET24)) * madz(np.abs(RET24)),
}
held = {"k": np.full(N, np.nan), "s": np.full(N, np.nan), "f": np.full(N, np.nan)}
COMP, MSK, RET, RV, KL, SL, FL, RETW = [], [], [], [], [], [], [], []
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
                        weights=WB, rvol=rv, risk_budget=RB)
    w = np.full(N, np.nan); w[m] = np.asarray(r["target_w"], float)
    COMP.append(w); MSK.append(m); RET.append(src.Y4[ti, m].astype(float)); RV.append(rv)
    yw = np.full(N, np.nan); yw[m] = src.Y4[ti, m].astype(float); RETW.append(yw)
    KL.append(held["k"].copy()); SL.append(held["s"].copy()); FL.append(held["f"].copy())
# ── 对齐红断言: RET24 特征 vs 面板过去24h(Σ前6个Y4), 偏移扫描峰必须在 0 ──
RW = np.array(RETW)
past24 = np.full((n, N), np.nan)
for i in range(6, n):
    blk = RW[i-6:i]
    cnt = np.isfinite(blk).sum(0)
    past24[i] = np.where(cnt >= 4, np.nansum(blk, 0), np.nan)
prof = {}
for off in (-2, -1, 0, 1, 2):
    cs = []
    for i in range(8, n, 7):
        r_ = rows[i] + off
        if not (0 <= r_ < zd.shape[0]): continue
        fv = np.full(N, np.nan)
        okc = col_of >= 0
        fv[okc] = zd[r_][col_of[okc], zfeats.index("ret24")]
        ok = np.isfinite(fv) & np.isfinite(past24[i])
        if ok.sum() > 30:
            cs.append(np.corrcoef(fv[ok], past24[i][ok])[0, 1])
    prof[off] = float(np.nanmedian(cs))
print("对齐偏移谱 corr(ret24_feat, panel_past24):", {k: round(v, 3) for k, v in prof.items()}, flush=True)
assert max(prof, key=prof.get) == 0 and prof[0] > 0.3, f"对齐红断言 FAIL: {prof}"
def xz(v):
    ok = np.isfinite(v)
    if ok.sum() < 10: return v
    r_ = np.full_like(v, np.nan)
    r_[ok] = (rankdata(v[ok]) - (ok.sum()+1)/2) / max(ok.sum()-1, 1)
    return r_
def spear(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 10: return np.nan
    from scipy.stats import spearmanr
    return spearmanr(x[ok], y[ok]).correlation
yrs = np.array(yr)
DELTAS = [-0.2, -0.1, -0.05, 0.05, 0.1, 0.2]
print("== S1 筛 ==", flush=True)
survivors = []
for nm, Xz in CAND.items():
    ic_gain = np.full((n, len(DELTAS)), np.nan)
    base_ic = np.full(n, np.nan)
    cors = []
    for i in range(n):
        m = MSK[i]; y = RET[i]
        cz = xz(COMP[i][m]); fz = Xz[i][m]
        b = spear(cz, y); base_ic[i] = b
        for j, d in enumerate(DELTAS):
            ic_gain[i, j] = spear(cz + d*np.nan_to_num(fz), y) - b
        ok = np.isfinite(fz)
        if ok.sum() > 20:
            for L, tag in ((KL[i][m], "k"), (SL[i][m], "s"), (FL[i][m], "f")):
                okk = ok & np.isfinite(L)
                if okk.sum() > 20:
                    cors.append((tag, np.corrcoef(fz[okk], L[okk])[0, 1]))
    gains = []
    for Y in (2023, 2024, 2025, 2026):
        tr = yrs < Y; te = yrs == Y
        jstar = int(np.nanargmax(np.nanmean(ic_gain[tr], axis=0)))
        gains.append((Y, DELTAS[jstar], float(np.nanmean(ic_gain[te, jstar]))))
    avg = float(np.mean([g[2] for g in gains]))
    allpos = all(g[2] >= 0 for g in gains)
    cdf = pd.DataFrame(cors, columns=["leg", "c"]).groupby("leg").c.mean() if cors else pd.Series(dtype=float)
    maxc = float(cdf.abs().max()) if len(cdf) else 0.0
    passed = avg >= 0.003 and allpos and maxc < 0.6
    print(f"  {nm}: 平均Δic {avg:+.4f} 逐年{[(g[0], g[1], round(g[2],4)) for g in gains]} "
          f"maxLegCorr {maxc:+.2f} {'★过筛' if passed else 'fail'}", flush=True)
    if passed: survivors.append((nm, Xz, gains))
print(f"\n== S2 净(幸存者 {len(survivors)} 个) ==", flush=True)
def run_book(extra=None, w4=0.0):
    state = None; prev = np.zeros(N)
    pnl = np.zeros(n); trn = np.zeros(n)
    for i in range(n):
        m = MSK[i]
        if extra is None:
            tgt0 = COMP[i][m]
        else:
            sc = (1-w4)
            W_ = {"king": WB["king"]*sc, "s2": WB["s2"]*sc, "funding": WB["funding"]*sc, "size": w4}
            r = LG.compose_book(KL[i][m], SL[i][m], FL[i][m], np.nan_to_num(extra[i][m]),
                                weights=W_, rvol=RV[i], risk_budget=RB)
            tgt0 = np.asarray(r["target_w"], float)
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
    rng = np.random.default_rng(31); L = len(d); k = int(np.ceil(L/bl)); o = np.empty(nb)
    for q in range(nb):
        st = rng.integers(0, max(L-bl, 1), size=k)
        ix = (st[:, None]+np.arange(bl)[None, :]).ravel()[:L]; ix = ix[ix < L]
        o[q] = d[ix].mean()
    return float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))
p0, t0 = run_book(); n0 = p0-t0*C1; sh0 = n0.mean()/n0.std(ddof=1)*ANN
print(f"基线: 净 {n0.mean():+.3f} 夏普 {sh0:+.2f}", flush=True)
for nm, Xz, gains in survivors:
    sgn = np.sign(np.median([g[1] for g in gains]))
    for w4 in (0.05, 0.10):
        p, t = run_book(extra=[sgn*Xz[i] for i in range(n)], w4=w4)
        net = p-t*C1; d = net-n0; lo, hi = boot(d)
        d2 = (p-t*C2).mean()-(p0-t0*C2).mean()
        dfy = pd.DataFrame({"y": yrs, "d": d}).groupby("y").d.mean()
        sh = net.mean()/net.std(ddof=1)*ANN
        ok_ = "★PASS" if (lo > 0 and d2 >= 0 and (dfy >= 0).sum() >= 4 and sh >= sh0) else "fail"
        print(f"  {nm} w={w4} sign={int(sgn)}: Δ净 {d.mean():+.4f} CI[{lo:+.4f},{hi:+.4f}] "
              f"@6.23 {d2:+.4f} 逐年{int((dfy>=0).sum())}/5 夏普 {sh:+.2f} {ok_}", flush=True)
print("W4GATE1_DONE", flush=True)
