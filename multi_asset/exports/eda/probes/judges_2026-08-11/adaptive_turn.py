"""自适应换手 · 两段判 · 判据冻结(先于数字)
段A 感知前置门: 候选条件量(全部严格≤t) vs 下4h书毛收益的逐锚相关 —— |corr|≥0.03 且逐年同号≥3/4
  才有资格进段B(感知不到东西的自适应=装饰)。候选: D=目标权重横截面离散度; M=Σ|Δtarget|(位移需求);
  V=宇宙均rvol。注: 按trailing-IC调速=已死族(AR1 −0.13), 不在候选内。
段B 政策臂(仅对过门条件量): 自适应α_t=0.05·(1+κ·z(cond)) 截断[0.02,0.15], κ∈{+0.5,−0.5};
  逐名信念带 b_i=0.002·clip(med|z|/|z_i|,0.5,2); 安慰剂=打乱的条件量(必须不改善)。
判据: Δ净@4.137 CI95>0 且 @6.23≥0 且逐年≥4/5 且夏普不降, vs 固定(0.05,0.002)。"""
import sys, json
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import numpy as np, pandas as pd
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
import legs as LG
import engine.replay_fullhist as RF
W = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}; C1, C2 = 4.137, 6.23; ANN = np.sqrt(6*365)
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N; n = len(a)
FI, RVI = src.fund_idx, src.ch.index("rvol_24h")
SYMS = [str(s) for s in src.symbols]
TGT, MSK, RET, RVm = [], [], [], []
held = {"k": np.full(N, np.nan), "s": np.full(N, np.nan), "f": np.full(N, np.nan)}
for i, t in enumerate(a):
    ti = int(t); m = np.asarray(src.tradeable(ti))
    if m.dtype == bool: m = np.where(m)[0]
    if i == 0 or ti % 8 == 0:
        v = np.full(N, np.nan); v[m] = src.king[ti, m]; held["k"] = v
    if i == 0 or ti % 24 == 0:
        v = np.full(N, np.nan); v[m] = src.s2[ti, m]; held["s"] = v
    if i == 0 or ti % 8 == 0:
        v = np.full(N, np.nan); v[m] = src.CH[ti, m, FI]; held["f"] = v
    rv = src.CH[ti, m, RVI].astype(float)
    r = LG.compose_book(held["k"][m], held["s"][m], held["f"][m], np.ones(len(m)),
                        weights=W, rvol=rv, risk_budget=RB)
    w = np.full(N, 0.0); w[m] = np.asarray(r["target_w"], float)
    TGT.append(w); MSK.append(m); RET.append(src.Y4[ti, m].astype(float))
    RVm.append(float(np.nanmean(rv)))
# ── 段A: 条件量(≤t)与下4h书毛的相关 ──
D = np.array([np.nanstd(TGT[i][MSK[i]]) for i in range(n)])
M = np.array([np.abs(TGT[i] - TGT[i-1]).sum() if i > 0 else 0 for i in range(n)])
V = np.array(RVm)
GROSS = np.array([float(np.nansum(TGT[i][MSK[i]] * np.nan_to_num(RET[i]))) * 1e4 for i in range(n)])
years = np.array(yr)
print("== 段A 感知前置门: corr(条件量_t, 书毛_t) ==")
passing = []
for nm, C in (("D 离散度", D), ("M 位移需求", M), ("V 波动状态", V)):
    c_all = float(np.corrcoef(C[1:], GROSS[1:])[0, 1])
    c_abs = float(np.corrcoef(C[1:], np.abs(GROSS[1:]))[0, 1])
    yrs = {}
    for y in sorted(set(years)):
        s = (years == y); s[0] = False
        if s.sum() > 200:
            yrs[int(y)] = round(float(np.corrcoef(C[s], GROSS[s])[0, 1]), 4)
    sign_ok = sum(1 for v_ in yrs.values() if v_ * c_all > 0)
    ok = abs(c_all) >= 0.03 and sign_ok >= len(yrs) - 1
    print(f"  {nm}: corr毛 {c_all:+.4f} corr|毛| {c_abs:+.4f} 逐年{yrs} {'★过门' if ok else 'fail'}")
    if ok: passing.append((nm, C, c_all))
def zs(x):
    mu = pd.Series(x).rolling(180, min_periods=60).mean().to_numpy()
    sd = pd.Series(x).rolling(180, min_periods=60).std().to_numpy()
    z = (x - mu) / np.where(sd > 0, sd, 1)
    return np.nan_to_num(np.clip(z, -3, 3))
def run(alpha_series=None, bfunc=None):
    state = None; prev = np.zeros(N)
    pnl = np.zeros(n); trn = np.zeros(n)
    for i in range(n):
        m = MSK[i]; syms = [SYMS[j] for j in m]
        al = float(alpha_series[i]) if alpha_series is not None else 0.05
        out = LG.apply_harvest_ema(TGT[i][m], syms, state, al)
        state = out["state"]
        tgt = np.asarray(out["target_w"], float)
        w = prev.copy(); w[[j for j in range(N) if j not in set(m)]] = 0.0
        delta = tgt - w[m]
        if bfunc is None:
            bv = np.full(len(m), 0.002)
        else:
            bv = bfunc(tgt)
        T = np.abs(delta) > bv
        wm = w[m].copy(); wm[T] = tgt[T]
        if T.any(): wm[T] -= wm.sum()/T.sum()
        w[m] = wm
        y = RET[i]; ok = np.isfinite(y)
        pnl[i] = float(np.nansum(w[m][ok]*y[ok]))*1e4
        trn[i] = float(np.abs(w-prev).sum()); prev = w
    return pnl, trn
def boot(d, nb=2000, bl=5):
    rng = np.random.default_rng(99); L = len(d); k = int(np.ceil(L/bl)); o = np.empty(nb)
    for q in range(nb):
        st = rng.integers(0, max(L-bl, 1), size=k)
        ix = (st[:, None]+np.arange(bl)[None, :]).ravel()[:L]; ix = ix[ix < L]
        o[q] = d[ix].mean()
    return float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))
p0, t0 = run(); n0 = p0-t0*C1
print(f"\n基线(固定 0.05/0.002): 净 {n0.mean():+.3f} 夏普 {n0.mean()/n0.std(ddof=1)*ANN:+.2f}")
print("\n== 段B 政策臂 ==")
rng = np.random.default_rng(11)
arms = []
for nm, C, _ in passing:
    z = zs(C)
    for kap in (0.5, -0.5):
        arms.append((f"α自适应[{nm} κ={kap}]", np.clip(0.05*(1+kap*z), 0.02, 0.15), None))
    zp = z.copy(); rng.shuffle(zp)
    arms.append((f"安慰剂[{nm}打乱]", np.clip(0.05*(1+0.5*zp), 0.02, 0.15), None))
def conv_band(tgt):
    az = np.abs(tgt); med = np.median(az[az > 0]) if (az > 0).any() else 1.0
    return 0.002*np.clip(med/np.maximum(az, 1e-9), 0.5, 2.0)
arms.append(("逐名信念带 b_i∝1/|z|", None, conv_band))
for nm, alser, bf in arms:
    p, t = run(alser, bf)
    d = (p-t*C1)-n0; lo, hi = boot(d)
    d2 = (p-t*C2)-(p0-t0*C2)
    dfy = pd.DataFrame({"y": yr, "d": d}).groupby("y").d.mean()
    sh = (p-t*C1).mean()/(p-t*C1).std(ddof=1)*ANN; sh0 = n0.mean()/n0.std(ddof=1)*ANN
    ok_ = "★PASS" if (lo > 0 and d2.mean() >= 0 and (dfy >= 0).sum() >= 4 and sh >= sh0) else "fail"
    print(f"{nm}: Δ净 {d.mean():+.4f} CI[{lo:+.4f},{hi:+.4f}] 逐年{int((dfy>=0).sum())}/5 "
          f"夏普 {sh:+.2f} {ok_}", flush=True)
print("ADAPTIVE_DONE")
