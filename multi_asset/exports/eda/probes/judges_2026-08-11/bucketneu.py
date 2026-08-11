"""M1 后续: 跨波动档净敞口的镜像分解 · 判据先冻结
臂A 档内中性: w 在逐锚 rvol 三分位内各自 demean(杀跨档倾斜, 留档内选择)→ L1 → EMA.3 → 带.002
臂B 只留倾斜: 每档内 w 替换为档均值(杀档内选择, 留跨档倾斜)→ 同管线(对照, 预期亏)
采纳线(臂A): Δ净@4.137 CI下界>0 且 @6.23≥0 且 逐年≥4/5 且 夏普不降。臂B 无采纳线(纯机制对照)。
会红: 跨档倾斜可能与 BAB/风格纠缠(clean BAB tilt 2.3x 在案) —— 若臂A 强年(22/25)红, 即倾斜是真信号成分。"""
import sys, os, json, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
import legs as LG
import engine.replay_fullhist as RF
W = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}; C1, C2 = 4.137, 6.23; ANN = np.sqrt(6*365); BW = 0.002
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N
FI, RVI = src.fund_idx, src.ch.index("rvol_24h")
SYMS = [str(s) for s in src.symbols]

def build(mode):
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
        rv = src.CH[ti, m, RVI].astype(float)
        r = LG.compose_book(held["k"][m], held["s"][m], held["f"][m], np.ones(len(m)),
                            weights=W, rvol=rv, risk_budget=RB)
        w = np.asarray(r["target_w"], float)
        if mode in ("neu", "tilt"):
            f = np.isfinite(rv)
            q = np.nanpercentile(rv[f], [33.3, 66.7]) if f.sum() > 30 else None
            if q is not None:
                b_ = np.where(~f, 1, np.where(rv <= q[0], 0, np.where(rv <= q[1], 1, 2)))
                w2 = w.copy()
                for k_ in range(3):
                    sel = b_ == k_
                    if sel.sum() > 3:
                        mu = w[sel].mean()
                        if mode == "neu": w2[sel] = w[sel] - mu
                        else:             w2[sel] = mu
                w = w2
                s1 = np.abs(w).sum()
                if s1 > 0: w = w/s1
        wf = np.full(N, 0.0); wf[m] = w
        TGT.append(wf); MSK.append(m); RET.append(src.Y4[ti, m].astype(float))
    return TGT, MSK, RET

def run(TGT, MSK, RET):
    state = None; prev = np.zeros(N); n = len(a)
    pnl = np.zeros(n); trn = np.zeros(n)
    for i in range(n):
        m = MSK[i]; syms = [SYMS[j] for j in m]
        out = LG.apply_harvest_ema(TGT[i][m], syms, state, 0.3)
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
        trn[i] = float(np.abs(w-prev).sum())
        prev = w
    return pnl, trn

def boot(d, nb=3000, bl=5):
    rng = np.random.default_rng(99); L = len(d); k = int(np.ceil(L/bl)); o = np.empty(nb)
    for q in range(nb):
        st = rng.integers(0, max(L-bl, 1), size=k)
        ix = (st[:, None]+np.arange(bl)[None, :]).ravel()[:L]; ix = ix[ix < L]
        o[q] = d[ix].mean()
    return float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))

Tb, Mb, Rb = build("base"); pb, tb = run(Tb, Mb, Rb); nb_ = pb-tb*C1
print(f"基线: 净 {nb_.mean():+.3f} 夏普 {nb_.mean()/nb_.std(ddof=1)*ANN:+.2f}")
for mode, nm in (("neu", "臂A 档内中性(杀跨档倾斜)"), ("tilt", "臂B 只留倾斜(对照)")):
    Ti, Mi, Ri = build(mode); p, t = run(Ti, Mi, Ri)
    d = (p-t*C1)-nb_; lo, hi = boot(d)
    d2 = (p-t*C2)-(pb-tb*C2)
    dfy = pd.DataFrame({"y": yr, "d": d}).groupby("y").d.mean()
    sh = (p-t*C1).mean()/(p-t*C1).std(ddof=1)*ANN
    print(f"{nm}: 净 {(p-t*C1).mean():+.3f} Δ {d.mean():+.4f} CI[{lo:+.4f},{hi:+.4f}] "
          f"@6.23Δ {d2.mean():+.4f} 逐年{int((dfy>=0).sum())}/5 夏普 {sh:+.2f} "
          f"逐年Δ {dict(dfy.round(3))}")
print("BUCKETNEU_DONE")
