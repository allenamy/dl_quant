"""两段装置 · 判据冻结(先于数字)
段1 口径分解(受据): 同一装置下三个 rank-IC —— king单腿分数 / 复合新鲜目标(EMA前) / 持仓书(EMA+带后)。
  回答"全书不是0.05+吗": 量化 EMA 陈旧化把 IC 折掉多少(那是买换手5.4×降的对价)。
段2 书级波动目标化(时序, 从未测过; 与已关闭的横截面 vol 族不同物):
  前置证据(今日段A实测): E[毛|V]≈0 (+0.003) 而 |毛| 对 V 强依赖(+0.254) ⇒ Moreira-Muir 条件成立,
  毛额均值不随波动升而方差随波动升 ⇒ 缩 gross∝1/σ̂ 应升夏普不伤均值。
  臂: s_t = clip(c/σ̂_t, lo, 1) 只降不升(尊重2×杠杆帽), σ̂ 两种(V=宇宙均rvol / 42锚滚动书pnl波动),
  档 lo∈{0.5, 0.7}; 安慰剂=打乱 σ̂(应无改善或更差)。作用在目标上(EMA后带前), 换手真实定价。
  判据(冻结): PASS = ΔSharpe ≥ +0.10 且 Δ净@4.137 CI95 上界>0(净不显著变差) 且 逐年夏普不差≥4/5
  且 最差年净额不降。PASS ⇒ 仅到提案(书行为改动需用户裁定), 不自动部署。"""
import sys
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
import numpy as np, pandas as pd
from scipy.stats import spearmanr
import legs as LG
import engine.replay_fullhist as RF
W = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}; C1, C2 = 4.137, 6.23; ANN = np.sqrt(6*365)
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N; n = len(a)
FI, RVI = src.fund_idx, src.ch.index("rvol_24h")
SYMS = [str(s) for s in src.symbols]
def spear(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    return spearmanr(x[ok], y[ok]).correlation if ok.sum() >= 10 else np.nan
TGT, MSK, RET, RVm, KIC = [], [], [], [], []
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
    y = src.Y4[ti, m].astype(float)
    TGT.append(w); MSK.append(m); RET.append(y); RVm.append(float(np.nanmean(rv)))
    KIC.append(spear(held["k"][m], y))
V = np.array(RVm)
def run(scale=None, collect_ic=False):
    state = None; prev = np.zeros(N)
    pnl = np.zeros(n); trn = np.zeros(n); icF = np.zeros(n); icH = np.zeros(n)
    for i in range(n):
        m = MSK[i]
        out = LG.apply_harvest_ema(TGT[i][m], [SYMS[j] for j in m], state, 0.05)
        state = out["state"]; tgt = np.asarray(out["target_w"], float)
        if scale is not None: tgt = tgt * scale[i]
        w = prev.copy(); w[[j for j in range(N) if j not in set(m)]] = 0.0
        delta = tgt - w[m]; T = np.abs(delta) > 0.002
        wm = w[m].copy(); wm[T] = tgt[T]
        if T.any(): wm[T] -= wm.sum()/T.sum()
        w[m] = wm
        y = RET[i]; ok = np.isfinite(y)
        pnl[i] = float(np.nansum(w[m][ok]*y[ok]))*1e4
        trn[i] = float(np.abs(w-prev).sum()); prev = w
        if collect_ic:
            icF[i] = spear(TGT[i][m], y); icH[i] = spear(w[m], y)
    return pnl, trn, icF, icH
p0, t0, icF, icH = run(collect_ic=True)
print("== 段1 口径分解(同装置三层 rank-IC) ==")
print(f"  king 单腿分数     : {np.nanmean(KIC):+.4f}")
print(f"  复合新鲜目标(EMA前): {np.nanmean(icF):+.4f}")
print(f"  持仓书(EMA+带后)  : {np.nanmean(icH):+.4f}   ← 实盘 ic_monitor 的口径")
n0 = p0 - t0*C1; sh0 = n0.mean()/n0.std(ddof=1)*ANN
print(f"\n基线: 净 {n0.mean():+.3f} 夏普 {sh0:+.2f} 换手 {t0.mean():.4f}")
print("\n== 段2 书级波动目标化(只降不升) ==")
def zs_causal(x, w=180):
    s = pd.Series(x)
    return ((s - s.rolling(w, min_periods=60).mean()) / s.rolling(w, min_periods=60).std()).fillna(0).clip(-3, 3).to_numpy()
sig_pnl = pd.Series(p0).rolling(42, min_periods=20).std().shift(1)
sig_pnl = sig_pnl.fillna(sig_pnl.median()).to_numpy()
def mk_scale(sig, lo):
    med = pd.Series(sig).rolling(360, min_periods=90).median().shift(1)
    med = med.fillna(pd.Series(sig).median()).to_numpy()
    return np.clip(med/np.maximum(sig, 1e-12), lo, 1.0)
def boot(d, nb=2000, bl=5):
    rng = np.random.default_rng(7); L = len(d); k = int(np.ceil(L/bl)); o = np.empty(nb)
    for q in range(nb):
        st = rng.integers(0, max(L-bl, 1), size=k)
        ix = (st[:, None]+np.arange(bl)[None, :]).ravel()[:L]; ix = ix[ix < L]
        o[q] = d[ix].mean()
    return float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))
Vlag = np.concatenate([[V[0]], V[:-1]])  # 严格 ≤t: 用上一锚的宇宙rvol
rng = np.random.default_rng(3)
arms = [("V宇宙rvol lo=.5", mk_scale(Vlag, 0.5)), ("V宇宙rvol lo=.7", mk_scale(Vlag, 0.7)),
        ("σ̂书pnl42 lo=.5", mk_scale(sig_pnl, 0.5)), ("σ̂书pnl42 lo=.7", mk_scale(sig_pnl, 0.7))]
shuf = mk_scale(Vlag, 0.5).copy(); rng.shuffle(shuf)
arms.append(("安慰剂(打乱V lo=.5)", shuf))
yrs = np.array(yr)
for nm, sc in arms:
    p, t, _, _ = run(scale=sc)
    net = p - t*C1; sh = net.mean()/net.std(ddof=1)*ANN
    d = net - n0; lo_, hi_ = boot(d)
    dfy = pd.DataFrame({"y": yrs, "b": n0, "a": net}).groupby("y")
    shy = sum(1 for _, g in dfy if (g.a.mean()/g.a.std(ddof=1)) >= (g.b.mean()/g.b.std(ddof=1)) - 1e-12)
    worst0 = min(g.b.mean() for _, g in dfy); worstA = min(g.a.mean() for _, g in dfy)
    ok_ = "★PASS" if (sh - sh0 >= 0.10 and hi_ > 0 and shy >= 4 and worstA >= worst0) else "fail"
    print(f"  {nm}: 净 {net.mean():+.3f} (Δ {d.mean():+.3f} CI[{lo_:+.3f},{hi_:+.3f}]) "
          f"夏普 {sh:+.2f} (Δ{sh-sh0:+.2f}) 逐年夏普不差 {shy}/5 最差年 {worst0:+.2f}→{worstA:+.2f} {ok_}", flush=True)
print("VOLTARGET_DONE")
