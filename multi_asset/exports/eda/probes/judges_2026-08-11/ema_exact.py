"""EMA α=0.3 · 实盘精确变换(apply_harvest_ema 原样 import)· 9821 锚
与网格臂的差: 混合后 demean+L1 重归一(gross 恒 1), prev=状态(混合前向量)而非持有书。
输出与在役基线的 Δ净@4.137/@6.23、CI、逐年、重归一带来的额外换手定量。"""
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

def run(alpha):
    state = None
    prev = np.zeros(N); pnl = np.zeros(n); trn = np.zeros(n)
    for i in range(n):
        m = MSK[i]; syms = [SYMS[j] for j in m]
        out = LG.apply_harvest_ema(TGT[i][m], syms, state, alpha)   # ★ 实盘函数原样
        state = out["state"]
        net = np.zeros(N); net[m] = np.asarray(out["target_w"], float)
        y = RET[i]; ok = np.isfinite(y)
        pnl[i] = float(np.nansum(net[m][ok]*y[ok]))*1e4
        trn[i] = float(np.abs(net-prev).sum())
        prev = net
    return pnl, trn

def boot(d, nb=3000, bl=5):
    rng = np.random.default_rng(99); L = len(d); k = int(np.ceil(L/bl)); o = np.empty(nb)
    for q in range(nb):
        st = rng.integers(0, max(L-bl, 1), size=k)
        ix = (st[:, None]+np.arange(bl)[None, :]).ravel()[:L]; ix = ix[ix < L]
        o[q] = d[ix].mean()
    return float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))

p1, t1 = run(1.0)          # 在役(α=1 = 逐位无操作, 亦即保真门)
p3, t3 = run(0.3)          # ★ 实盘精确变换
print(f"保真: α=1 毛 {p1.mean():+.3f} 换手 {t1.mean():.4f} vs C8A +1.669/0.3120 ⇒ "
      f"{'PASS' if abs(p1.mean()-1.669)<.04 and abs(t1.mean()-.312)<.007 else '★FAIL'}")
for nm, p, t in (("在役 α=1.0", p1, t1), ("★实盘精确 α=0.3", p3, t3)):
    n1 = p-t*C1; n2 = p-t*C2
    print(f"  {nm:16s} 毛 {p.mean():+.3f}  换手 {t.mean():.4f}  净@4.137 {n1.mean():+.3f} "
          f"夏普 {n1.mean()/n1.std(ddof=1)*ANN:+.2f}  净@6.23 {n2.mean():+.3f}")
d = (p3-t3*C1)-(p1-t1*C1); lo, hi = boot(d)
dfy = pd.DataFrame({"y": yr, "d": d}).groupby("y").d.mean()
print(f"\nΔ净@4.137 = {d.mean():+.3f}  CI95[{lo:+.3f},{hi:+.3f}]  逐年 {dict(dfy.round(3))}")
print(f"网格臂(不重归一)给的是 +0.290 —— 差值 = 重归一的代价定量")
print(f"盈亏平衡成本 = {(p1.mean()-p3.mean())/(t1.mean()-t3.mean()):.3f} bps/单位换手(实测 4.137)")
print("EMA_EXACT_DONE")
