"""实盘数据驱动的候选: 大盘(BTC/ETH)剔除/减半 · 判据冻结(先于数字)
动机: 实盘一周 BTC/ETH −15.0(2名占gross~8%) + 档案先验(BTC 无idio, 模型强项在高idio alt)。
臂: A 全剔除(compose 后 w[BTC,ETH]=0 → re-demean → L1) B 减半。
判据(G族): Δ净@4.137 CI95>0 且 @6.23≥0 且逐年≥4/5 且夏普不降。
会红: BTC/ETH 是横截面的"锚"(高β端), 剔除可能改变全书β结构 ⇒ 附报净β变化。"""
import sys, json
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import numpy as np, pandas as pd
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
import legs as LG
import engine.replay_fullhist as RF
W = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}; C1, C2 = 4.137, 6.23; ANN = np.sqrt(6*365); BW = 0.002
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N; n = len(a)
FI, RVI = src.fund_idx, src.ch.index("rvol_24h")
SYMS = [str(s) for s in src.symbols]
MAJ = [i for i, s in enumerate(SYMS) if s in ("BTCUSDT", "ETHUSDT")]
print(f"majors idx: {MAJ}")

def build(scale):
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
        w = np.asarray(r["target_w"], float)
        if scale < 1.0:
            gm = np.isin(m, MAJ)
            if gm.any():
                w[gm] = w[gm] * scale
                w = w - w.mean()
                s1 = np.abs(w).sum()
                if s1 > 0: w = w / s1
        wf = np.full(N, 0.0); wf[m] = w
        TGT.append(wf); MSK.append(m); RET.append(src.Y4[ti, m].astype(float))
    return TGT, MSK, RET

def run(TGT, MSK, RET):
    state = None; prev = np.zeros(N)
    pnl = np.zeros(n); trn = np.zeros(n)
    for i in range(n):
        m = MSK[i]; syms = [SYMS[j] for j in m]
        out = LG.apply_harvest_ema(TGT[i][m], syms, state, 0.05)
        state = out["state"]
        tgt = np.asarray(out["target_w"], float)
        w = prev.copy(); w[[j for j in range(N) if j not in set(m)]] = 0.0
        delta = tgt - w[m]
        T = np.abs(delta) > BW
        wm = w[m].copy(); wm[T] = tgt[T]
        if T.any(): wm[T] -= wm.sum()/T.sum()
        w[m] = wm
        y = RET[i]; ok = np.isfinite(y)
        pnl[i] = float(np.nansum(w[m][ok]*y[ok]))*1e4
        trn[i] = float(np.abs(w-prev).sum()); prev = w
    return pnl, trn

def boot(d, nb=3000, bl=5):
    rng = np.random.default_rng(99); L = len(d); k = int(np.ceil(L/bl)); o = np.empty(nb)
    for q in range(nb):
        st = rng.integers(0, max(L-bl, 1), size=k)
        ix = (st[:, None]+np.arange(bl)[None, :]).ravel()[:L]; ix = ix[ix < L]
        o[q] = d[ix].mean()
    return float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))

Tb, Mb, Rb = build(1.0); p0, t0 = run(Tb, Mb, Rb); n0 = p0-t0*C1
print(f"基线: 净 {n0.mean():+.3f} 夏普 {n0.mean()/n0.std(ddof=1)*ANN:+.2f}")
for nm, sc in (("A 全剔除 BTC/ETH", 0.0), ("B 减半", 0.5)):
    Ti, Mi, Ri = build(sc); p, t = run(Ti, Mi, Ri)
    d = (p-t*C1)-n0; lo, hi = boot(d)
    d2 = (p-t*C2)-(p0-t0*C2)
    dfy = pd.DataFrame({"y": yr, "d": d}).groupby("y").d.mean()
    sh = (p-t*C1).mean()/(p-t*C1).std(ddof=1)*ANN; sh0 = n0.mean()/n0.std(ddof=1)*ANN
    ok_ = "★PASS" if (lo > 0 and d2.mean() >= 0 and (dfy >= 0).sum() >= 4 and sh >= sh0) else "fail"
    print(f"{nm}: Δ净 {d.mean():+.4f} CI[{lo:+.4f},{hi:+.4f}] @6.23 {d2.mean():+.4f} "
          f"逐年{int((dfy>=0).sum())}/5 夏普 {sh:+.2f} 2026Δ {dfy.get(2026,float('nan')):+.3f} {ok_}")
print("MAJORS_DONE")
