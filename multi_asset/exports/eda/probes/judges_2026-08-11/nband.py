"""中性保持型免交易带 · EMA α=0.3 精确变换之上 · 9821 锚
设计(CAMPAIGN E-1): 带作用在 EMA输出 vs 实际持有书 的差; 中性恢复=残差均摊到已交易集;
未交易名字零扰动; 出宇宙强制平仓不受带豁免; 不重归一(gross 漂移作观测)。
会红方向: (a) EMA 已压小 delta ⇒ 带增量可能亚阈; (b) 中性修正自身的换手吃掉收益;
(c) 大 b 下 gross 漂移失控。b=0 必须逐位复现 EMA-only(保真门)。"""
import sys, os, json, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
import legs as LG
import engine.replay_fullhist as RF
W = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}; C1, C2 = 4.137, 6.23; ANN = np.sqrt(6*365)
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

def run(alpha, b):
    state = None
    prev = np.zeros(N)                       # 实际持有书(带效应累积于此)
    pnl = np.zeros(n); trn = np.zeros(n)
    netdrift = np.zeros(n); gross = np.zeros(n)
    for i in range(n):
        m = MSK[i]; syms = [SYMS[j] for j in m]
        out = LG.apply_harvest_ema(TGT[i][m], syms, state, alpha)   # 实盘函数原样, 状态链不受带影响
        state = out["state"]
        tgt = np.asarray(out["target_w"], float)                    # EMA 后目标(中性, L1=1)
        w = prev.copy()
        w[[j for j in range(N) if j not in set(m)]] = 0.0           # 出宇宙强制平仓, 不受带豁免
        delta = tgt - w[m]
        if b > 0:
            T = np.abs(delta) > b
            wm = w[m].copy(); wm[T] = tgt[T]
            if T.any():
                wm[T] -= wm.sum() / T.sum()                          # 中性恢复: 残差均摊到已交易集
            w[m] = wm
        else:
            w[m] = tgt
        y = RET[i]; ok = np.isfinite(y)
        pnl[i] = float(np.nansum(w[m][ok]*y[ok]))*1e4
        trn[i] = float(np.abs(w-prev).sum())
        netdrift[i] = abs(float(w[m].sum())); gross[i] = float(np.abs(w[m]).sum())
        prev = w
    return pnl, trn, netdrift, gross

def boot(d, nb=3000, bl=5):
    rng = np.random.default_rng(99); L = len(d); k = int(np.ceil(L/bl)); o = np.empty(nb)
    for q in range(nb):
        st = rng.integers(0, max(L-bl, 1), size=k)
        ix = (st[:, None]+np.arange(bl)[None, :]).ravel()[:L]; ix = ix[ix < L]
        o[q] = d[ix].mean()
    return float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))

p0, t0, nd0, g0 = run(0.3, 0.0)              # EMA-only 基线(保真门: 复现 ema_exact α=0.3)
print(f"保真: b=0 毛 {p0.mean():+.3f} 换手 {t0.mean():.4f}(ema_exact α=0.3 应逐位同)")
res = {}
for b in (0.0005, 0.001, 0.002, 0.004):
    p, t, nd, g = run(0.3, b)
    n1 = p-t*C1; n0 = p0-t0*C1; d = n1-n0; lo, hi = boot(d)
    n2 = (p-t*C2)-(p0-t0*C2)
    dfy = pd.DataFrame({"y": yr, "d": d}).groupby("y").d.mean()
    yrs_ok = int((dfy >= 0).sum())
    sh1 = n1.mean()/n1.std(ddof=1)*ANN; sh0 = n0.mean()/n0.std(ddof=1)*ANN
    g1 = "P" if lo > 0 and n2.mean() >= 0 else "F"
    g2 = "P" if yrs_ok >= 4 else "F"
    g3 = "P" if sh1 >= sh0 else "F"
    g4 = "P" if nd.max() < 1e-9 else f"F(max|Σw|={nd.max():.2e})"
    res[b] = dict(gross_pnl=round(p.mean(),4), turn=round(t.mean(),5),
                  net=round(n1.mean(),4), dnet=round(d.mean(),4), ci=[round(lo,4),round(hi,4)],
                  dnet_c2=round(n2.mean(),4), sharpe=round(sh1,3), yrs=f"{yrs_ok}/5",
                  by_year={str(k): round(v,3) for k,v in dfy.items()},
                  g=[g1,g2,g3,g4], l1_p5=round(float(np.percentile(g,5)),4),
                  l1_p95=round(float(np.percentile(g,95)),4))
    print(f"b={b}: 毛 {p.mean():+.3f} 换手 {t.mean():.4f} Δ净@4.137 {d.mean():+.4f} "
          f"CI[{lo:+.4f},{hi:+.4f}] Δ净@6.23 {n2.mean():+.4f} 夏普 {sh1:+.2f}(基 {sh0:+.2f}) "
          f"逐年{yrs_ok}/5 G4中性 max|Σw| {nd.max():.1e} gross[{np.percentile(g,5):.3f},{np.percentile(g,95):.3f}]")
json.dump({"baseline_ema_only": dict(gross=round(p0.mean(),4), turn=round(t0.mean(),5),
           net=round((p0-t0*C1).mean(),4)), "arms": {str(k): v for k, v in res.items()}},
          open(f"{PD}/nband_result.json", "w"), indent=1)
print("NBAND_DONE")
