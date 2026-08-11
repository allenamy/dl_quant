"""#53-C 深平滑生产折复现 · 研究分支定价 +1.7 夏普的唯一候选 · 9821 锚在役栈
==== 冻结判据(先于数字) ====
臂: α ∈ {0.3(基线), 0.2, 0.15, 0.1, 0.05, 0.03} × 带 ∈ {0, 0.002}。
采纳线(G族, vs α=0.3+带.002 在役基线): Δ净@4.137 CI95下界>0 且 @6.23≥0 且 逐年≥4/5 且夏普不降。
内点规则: 只推荐两方向邻格不劣的内点(防边缘解 —— 上轮 0.3 恰在网格边缘, 本轮把网格补全)。
会红方向: (a) 深平滑=有效记忆 1/α 锚(α=.03≈33锚≈5.5天), 远超 king 8h 设计 ⇒ regime 突变年(2022)先红;
(b) 带×深平滑交互: EMA 把 delta 压小 ⇒ 带吃掉的比例变大 ⇒ 书可能"冻住", 毛额塌 —— 逐年门捕捉;
(c) 研究分支 N9 的 +1.7 夏普是研究折/慢书装置, 生产折不复现 ⇒ 判负结案 #53。"""
import sys, os, json, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
import legs as LG
import engine.replay_fullhist as RF
W = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}; C1, C2 = 4.137, 6.23; ANN = np.sqrt(6*365)
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N; n = len(a)
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

def run(alpha, bw):
    state = None; prev = np.zeros(N)
    pnl = np.zeros(n); trn = np.zeros(n)
    for i in range(n):
        m = MSK[i]; syms = [SYMS[j] for j in m]
        out = LG.apply_harvest_ema(TGT[i][m], syms, state, alpha)
        state = out["state"]
        tgt = np.asarray(out["target_w"], float)
        w = prev.copy(); w[[j for j in range(N) if j not in set(m)]] = 0.0
        if bw > 0:
            delta = tgt - w[m]
            T = np.abs(delta) > bw
            wm = w[m].copy(); wm[T] = tgt[T]
            if T.any(): wm[T] -= wm.sum()/T.sum()
            w[m] = wm
        else:
            w[m] = tgt
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

p0, t0 = run(0.3, 0.002); n0 = p0-t0*C1
print(f"基线 α=0.3+带.002: 毛 {p0.mean():+.3f} 换手 {t0.mean():.4f} 净 {n0.mean():+.3f} "
      f"夏普 {n0.mean()/n0.std(ddof=1)*ANN:+.2f}")
res = {}
for al in (0.2, 0.15, 0.1, 0.05, 0.03):
    for bw in (0.002, 0.0):
        p, t = run(al, bw)
        net = p-t*C1
        d = net-n0; lo, hi = boot(d)
        d2 = (p-t*C2)-(p0-t0*C2)
        dfy = pd.DataFrame({"y": yr, "d": d}).groupby("y").d.mean()
        sh = net.mean()/net.std(ddof=1)*ANN; sh0 = n0.mean()/n0.std(ddof=1)*ANN
        ok_ = "★PASS" if (lo > 0 and d2.mean() >= 0 and (dfy >= 0).sum() >= 4 and sh >= sh0) else "fail"
        tag = f"α={al}+带{bw}"
        res[tag] = dict(gross=round(p.mean(),4), turn=round(t.mean(),5), net=round(net.mean(),4),
                        dnet=round(d.mean(),4), ci=[round(lo,4),round(hi,4)],
                        yrs=int((dfy>=0).sum()), sharpe=round(sh,3),
                        by_year={str(k): round(v,3) for k,v in dfy.items()})
        print(f"{tag}: 毛 {p.mean():+.3f} 换手 {t.mean():.4f} 净 {net.mean():+.3f} "
              f"Δ {d.mean():+.4f} CI[{lo:+.4f},{hi:+.4f}] 逐年{int((dfy>=0).sum())}/5 "
              f"夏普 {sh:+.2f} 2022Δ {dfy.get(2022,float('nan')):+.3f} 2026Δ {dfy.get(2026,float('nan')):+.3f} {ok_}")
json.dump(res, open(f"{PD}/deepsmooth_result.json", "w"), indent=1)
print("DEEPSMOOTH_DONE")
