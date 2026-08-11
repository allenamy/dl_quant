"""空头侧/β 归因与干预 · 9821 锚 · 在役栈(EMA.3+带.002)
==== 冻结判据(先于数字) ====
测量 M(无门): 全史逐年 (a) 书净β敞口 Σwβ 与 β项盈亏 vs 残差盈亏 (b) 多/空侧净额拆分
(c) 逐侧幅度校准斜率。β = 因果滚动(过去180锚, 最少60, 对宇宙等权收益, 严格≤t)。
干预臂采纳线(G族): Δ净@4.137 CI95下界>0 且 @6.23≥0 且 逐年≥4/5 且 夏普不降。
臂: A β中性(w−a−bβ 联合解 Σw=0,Σwβ=0) | B β半中性(去一半净β) | C 不对称帽
(compose输出多侧clip至|w|多侧p{90,95}, 空侧p99, 再demean+L1) —— 08-04过门未上船件在新栈复验。
会红: A 若跨档倾斜与β纠缠, 强年(22/25)先红 ⇒ 倾斜是alpha成分, β敞口是其代价的一部分;
C 与今晨 shrink_long(分数空间)相邻但对象不同(权重百分位), 若同负则多尾干预整族关。"""
import sys, os, json, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
import legs as LG
import engine.replay_fullhist as RF
W = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}; C1, C2 = 4.137, 6.23; ANN = np.sqrt(6*365); BW = 0.002
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N; n = len(a)
FI, RVI = src.fund_idx, src.ch.index("rvol_24h")
SYMS = [str(s) for s in src.symbols]

# ---- 因果滚动 β: 用上一锚的已实现 Y4(t-1 锚的 4h 收益在 t 时已完整) ----
WIN, MINW = 180, 60
BETA = np.full((n, N), np.nan)
buf_r = np.full((WIN, N), np.nan); buf_m = np.full(WIN, np.nan); ptr = 0; cnt = 0
for i in range(n):
    if i > 0:
        ti_prev = int(a[i-1]); m_prev = np.asarray(src.tradeable(ti_prev))
        if m_prev.dtype == bool: m_prev = np.where(m_prev)[0]
        r = np.full(N, np.nan); r[m_prev] = src.Y4[ti_prev, m_prev].astype(float)
        mk = np.nanmean(r) if np.isfinite(r).sum() > 30 else np.nan
        buf_r[ptr] = r; buf_m[ptr] = mk; ptr = (ptr+1) % WIN; cnt += 1
    if cnt >= MINW:
        M_ = buf_m[np.isfinite(buf_m)]
        vm = np.var(M_)
        if vm > 0:
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

def build():
    TGT, MSK, RET, BET = [], [], [], []
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
        wf = np.full(N, 0.0); wf[m] = np.asarray(r["target_w"], float)
        TGT.append(wf); MSK.append(m); RET.append(src.Y4[ti, m].astype(float)); BET.append(BETA[i, m])
    return TGT, MSK, RET, BET

def transform(TGT, MSK, BET, mode, p_hi=None):
    out = []
    for i in range(n):
        m = MSK[i]; w = TGT[i][m].copy(); b = BET[i]
        if mode == "base":
            out.append((w, m)); continue
        if mode in ("bneu", "bhalf"):
            f = np.isfinite(b)
            if f.sum() > 30:
                bf = np.where(f, b, np.nanmean(b[f]))
                X = np.stack([np.ones(len(w)), bf], 1)
                coef, *_ = np.linalg.lstsq(X, w, rcond=None)
                proj = X @ coef
                w = w - (proj if mode == "bneu" else 0.5*proj)
            s1 = np.abs(w).sum()
            if s1 > 0: w = w/s1
        elif mode == "acap":
            pos = w > 0
            if pos.sum() > 10:
                lim = np.percentile(w[pos], p_hi)
                w[pos] = np.minimum(w[pos], lim)
            w = w - w.mean()
            s1 = np.abs(w).sum()
            if s1 > 0: w = w/s1
        out.append((w, m))
    return out

def run(book):
    state = None; prev = np.zeros(N)
    pnl = np.zeros(n); trn = np.zeros(n); WH = []
    for i in range(n):
        w_, m = book[i]; syms = [SYMS[j] for j in m]
        o = LG.apply_harvest_ema(w_, syms, state, 0.3)
        state = o["state"]
        tgt = np.asarray(o["target_w"], float)
        w = prev.copy(); w[[j for j in range(N) if j not in set(m)]] = 0.0
        delta = tgt - w[m]
        T = np.abs(delta) > BW
        wm = w[m].copy(); wm[T] = tgt[T]
        if T.any(): wm[T] -= wm.sum()/T.sum()
        w[m] = wm
        y = np.full(N, np.nan); y[m] = RET[i]
        ok = np.isfinite(y)
        pnl[i] = float(np.nansum(w[ok]*y[ok]))*1e4
        trn[i] = float(np.abs(w-prev).sum()); prev = w; WH.append(w.copy())
    return pnl, trn, WH

def boot(d, nb=3000, bl=5):
    rng = np.random.default_rng(99); L = len(d); k = int(np.ceil(L/bl)); o = np.empty(nb)
    for q in range(nb):
        st = rng.integers(0, max(L-bl, 1), size=k)
        ix = (st[:, None]+np.arange(bl)[None, :]).ravel()[:L]; ix = ix[ix < L]
        o[q] = d[ix].mean()
    return float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))

TGT, MSK, RET, BET = build()
base = transform(TGT, MSK, BET, "base")
p0, t0, WH0 = run(base); n0 = p0-t0*C1
print(f"基线: 净 {n0.mean():+.3f} 夏普 {n0.mean()/n0.std(ddof=1)*ANN:+.2f}")

# ---- M: β项/侧拆分/逐侧斜率, 逐年 ----
rows = []
for i in range(n):
    m = MSK[i]; w = WH0[i][m]; y = RET[i]; b = BET[i]
    ok = np.isfinite(y) & np.isfinite(b)
    if ok.sum() < 30: continue
    mk = np.nanmean(y[np.isfinite(y)])
    nb_ = float((w[ok]*b[ok]).sum())
    bt = nb_*mk*1e4
    L_, S_ = ok & (w > 0), ok & (w < 0)
    pl = float((w[L_]*y[L_]).sum())*1e4; ps = float((w[S_]*y[S_]).sum())*1e4
    slL = slS = np.nan
    if L_.sum() > 15 and np.std(w[L_]) > 0: slL = float(np.polyfit(w[L_], y[L_], 1)[0])
    if S_.sum() > 15 and np.std(w[S_]) > 0: slS = float(np.polyfit(w[S_], y[S_], 1)[0])
    rows.append(dict(y=yr[i], netbeta=nb_, beta_pnl=bt, long=pl, short=ps, slL=slL, slS=slS))
df = pd.DataFrame(rows)
g = df.groupby("y").agg(netbeta=("netbeta","mean"), beta_pnl=("beta_pnl","sum"),
                        long=("long","sum"), short=("short","sum"),
                        slL=("slL","mean"), slS=("slS","mean"))
print("\nM 逐年(bps 累计, netbeta=均值权重单位):")
print(g.round(2).to_string())
tot_b = df.beta_pnl.sum(); tot = df.long.sum()+df.short.sum()
print(f"全史: β项 {tot_b:+.0f} / 总盈亏 {tot:+.0f} = {tot_b/tot:.1%} | "
      f"净β敞口均值 {df.netbeta.mean():+.4f}(权重单位, ≈gross的{abs(df.netbeta.mean())*100:.1f}%)")

# ---- 臂 ----
for nm, mode, kw in (("A β中性", "bneu", {}), ("B β半中性", "bhalf", {}),
                     ("C 不对称帽 p90", "acap", {"p_hi": 90}),
                     ("C 不对称帽 p95", "acap", {"p_hi": 95})):
    bk = transform(TGT, MSK, BET, mode, **kw)
    p, t, _ = run(bk)
    d = (p-t*C1)-n0; lo, hi = boot(d)
    d2 = (p-t*C2)-(p0-t0*C2)
    dfy = pd.DataFrame({"y": yr, "d": d}).groupby("y").d.mean()
    sh = (p-t*C1).mean()/(p-t*C1).std(ddof=1)*ANN; sh0 = n0.mean()/n0.std(ddof=1)*ANN
    ok_ = "★PASS" if (lo > 0 and d2.mean() >= 0 and (dfy >= 0).sum() >= 4 and sh >= sh0) else "fail"
    print(f"{nm}: Δ净 {d.mean():+.4f} CI[{lo:+.4f},{hi:+.4f}] @6.23 {d2.mean():+.4f} "
          f"逐年{int((dfy>=0).sum())}/5 夏普 {sh:+.2f} 2026Δ {dfy.get(2026, float('nan')):+.3f} {ok_}")
print("BETASIDE_DONE")
