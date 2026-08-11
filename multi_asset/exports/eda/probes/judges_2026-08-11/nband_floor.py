"""地板口径补臂: 实盘隐性带(场所 5 USDT 地板, skip 无中性恢复)作为诚实基线。
两个 NAV 情景: 当前 gross 4300(b_impl=0.00116) / 入金后 24300(b_impl=0.000206)。
问题: 显式 b=0.002 中性带 vs 实盘现状的【真实增量】是多少, 入金前后各是多少。"""
import sys, os, json, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
import legs as LG
import engine.replay_fullhist as RF
W = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}; C1 = 4.137; ANN = np.sqrt(6*365)
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N
FI, RVI = src.fund_idx, src.ch.index("rvol_24h")
SYMS = [str(s) for s in src.symbols]
TGT, MSK, RET = [], [], []
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
    r = LG.compose_book(held["k"][m], held["s"][m], held["f"][m], np.ones(len(m)),
                        weights=W, rvol=src.CH[ti, m, RVI].astype(float), risk_budget=RB)
    w = np.full(N, 0.0); w[m] = np.asarray(r["target_w"], float)
    TGT.append(w); MSK.append(m); RET.append(src.Y4[ti, m].astype(float))
n = len(a)

def run(alpha, b, neutral):
    state = None; prev = np.zeros(N)
    pnl = np.zeros(n); trn = np.zeros(n); nd = np.zeros(n)
    for i in range(n):
        m = MSK[i]; syms = [SYMS[j] for j in m]
        out = LG.apply_harvest_ema(TGT[i][m], syms, state, alpha)
        state = out["state"]
        tgt = np.asarray(out["target_w"], float)
        w = prev.copy()
        w[[j for j in range(N) if j not in set(m)]] = 0.0
        delta = tgt - w[m]
        if b > 0:
            T = np.abs(delta) > b
            wm = w[m].copy(); wm[T] = tgt[T]
            if neutral and T.any():
                wm[T] -= wm.sum() / T.sum()
            w[m] = wm
        else:
            w[m] = tgt
        y = RET[i]; ok = np.isfinite(y)
        pnl[i] = float(np.nansum(w[m][ok]*y[ok]))*1e4
        trn[i] = float(np.abs(w-prev).sum())
        nd[i] = abs(float(w[m].sum()))
        prev = w
    return pnl, trn, nd

def boot(d, nb=3000, bl=5):
    rng = np.random.default_rng(99); L = len(d); k = int(np.ceil(L/bl)); o = np.empty(nb)
    for q in range(nb):
        st = rng.integers(0, max(L-bl, 1), size=k)
        ix = (st[:, None]+np.arange(bl)[None, :]).ravel()[:L]; ix = ix[ix < L]
        o[q] = d[ix].mean()
    return float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))

arms = {
  "实盘现状@4.3k(隐带.00116无恢复)": (0.00116, False),
  "实盘入金后@24.3k(隐带.000206无恢复)": (0.000206, False),
  "显式中性带b=.002": (0.002, True),
}
out = {}
for nm, (b, neu) in arms.items():
    p, t, nd = run(0.3, b, neu)
    net = p - t*C1
    out[nm] = (p, t, net, nd)
    print(f"{nm}: 毛 {p.mean():+.3f} 换手 {t.mean():.4f} 净 {net.mean():+.3f} "
          f"夏普 {net.mean()/net.std(ddof=1)*ANN:+.2f} max|Σw| {nd.max():.2e}")
for base in ("实盘现状@4.3k(隐带.00116无恢复)", "实盘入金后@24.3k(隐带.000206无恢复)"):
    d = out["显式中性带b=.002"][2] - out[base][2]
    lo, hi = boot(d)
    dfy = pd.DataFrame({"y": yr, "d": d}).groupby("y").d.mean()
    print(f"Δ(b.002中性 − {base}) = {d.mean():+.4f} CI[{lo:+.4f},{hi:+.4f}] "
          f"逐年 {int((dfy>=0).sum())}/5 {dict(dfy.round(3))}")
print("NBFLOOR_DONE")
