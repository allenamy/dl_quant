"""趋势条件化 β 敞口 · 判据冻结(先于数字) · 判官入库
机制: 书常态净空β −14.8% gross, 上涨段流血(空头亏损全因); 本臂只在上涨趋势中收缩 β 投影,
保留横截面倾斜(与 β 中性臂不同 —— 那是全时收缩, 已判死 Δ−0.478)。
趋势 = 过去 120 锚(20天)宇宙等权累计收益(严格因果)。
臂: trend>0 时 β 分量 ×s, s∈{0.5, 0}; 对照含"反向安慰剂"(trend<0 时收缩 —— 若也"改善"则是过拟合形状)。
判据: Δ净@4.137 CI95>0 且 @6.23≥0 且逐年≥4/5 且夏普不降。预写红方向: 切掉 β 项全史 +34% 利润的
一角 ⇒ 强年(22/25)先红; 安慰剂若同向 ⇒ 全案作废。"""
import sys, glob, json
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

WIN, MINW = 180, 60
BETA = np.full((n, N), np.nan)
TREND = np.full(n, np.nan)
buf_r = np.full((WIN, N), np.nan); buf_m = np.full(WIN, np.nan); ptr = 0; cnt = 0
trend_buf = []
for i in range(n):
    if i > 0:
        tp = int(a[i-1]); mp = np.asarray(src.tradeable(tp))
        if mp.dtype == bool: mp = np.where(mp)[0]
        r = np.full(N, np.nan); r[mp] = src.Y4[tp, mp].astype(float)
        mk = np.nanmean(r) if np.isfinite(r).sum() > 30 else np.nan
        buf_r[ptr] = r; buf_m[ptr] = mk; ptr = (ptr+1) % WIN; cnt += 1
        trend_buf.append(mk)
    if len(trend_buf) >= 120:
        TREND[i] = float(np.nansum(trend_buf[-120:]))
    if cnt >= MINW:
        mm = np.where(np.isfinite(buf_m), buf_m, 0.0)
        fin = np.isfinite(buf_r) & np.isfinite(buf_m)[:, None]
        nn = fin.sum(0).astype(float)
        rz = np.where(fin, buf_r, 0.0); mz = np.where(fin, mm[:, None], 0.0)
        with np.errstate(invalid="ignore", divide="ignore"):
            cov = (rz*mz).sum(0)/nn - (rz.sum(0)/nn)*(mz.sum(0)/nn)
            var = (mz**2).sum(0)/nn - (mz.sum(0)/nn)**2
            b_ = cov/var
        b_[nn < MINW] = np.nan
        BETA[i] = b_

def build(mode, s):
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
        b = BETA[i, m]; tr = TREND[i]
        fire = (np.isfinite(tr) and ((mode == "trend" and tr > 0) or (mode == "placebo" and tr < 0)))
        if mode != "base" and fire and np.isfinite(b).sum() > 30:
            bf = np.where(np.isfinite(b), b, np.nanmean(b[np.isfinite(b)]))
            X = np.stack([np.ones(len(w)), bf], 1)
            coef, *_ = np.linalg.lstsq(X, w, rcond=None)
            proj = X @ coef
            w = (w - proj) + s * proj
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

Tb, Mb, Rb = build("base", 1.0); p0, t0 = run(Tb, Mb, Rb); n0 = p0-t0*C1
print(f"基线: 净 {n0.mean():+.3f} 夏普 {n0.mean()/n0.std(ddof=1)*ANN:+.2f} | "
      f"trend>0 占比 {float(np.nanmean(TREND>0)):.2f}")
res = {}
for nm, mode, s in (("涨势β半收 s=.5", "trend", .5), ("涨势β全撤 s=0", "trend", 0.),
                    ("安慰剂(跌势收缩 s=.5)", "placebo", .5)):
    Ti, Mi, Ri = build(mode, s); p, t = run(Ti, Mi, Ri)
    d = (p-t*C1)-n0; lo, hi = boot(d)
    d2 = (p-t*C2)-(p0-t0*C2)
    dfy = pd.DataFrame({"y": yr, "d": d}).groupby("y").d.mean()
    sh = (p-t*C1).mean()/(p-t*C1).std(ddof=1)*ANN; sh0 = n0.mean()/n0.std(ddof=1)*ANN
    ok_ = "★PASS" if (lo > 0 and d2.mean() >= 0 and (dfy >= 0).sum() >= 4 and sh >= sh0) else "fail"
    res[nm] = dict(dnet=round(d.mean(),4), ci=[round(lo,4),round(hi,4)], yrs=int((dfy>=0).sum()),
                   sharpe=round(sh,3), by_year={str(k): round(v,3) for k,v in dfy.items()})
    print(f"{nm}: Δ净 {d.mean():+.4f} CI[{lo:+.4f},{hi:+.4f}] 逐年{int((dfy>=0).sum())}/5 "
          f"夏普 {sh:+.2f} 2026Δ {dfy.get(2026,float('nan')):+.3f} {ok_}")
json.dump(res, open(f"{PD}/trendbeta_result.json", "w"), indent=1)
print("TRENDBETA_DONE")
