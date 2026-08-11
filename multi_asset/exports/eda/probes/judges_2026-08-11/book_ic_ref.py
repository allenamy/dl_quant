"""离线书级 spearman(w_t, ret4h) — 实盘 ic_monitor(+0.0504/52锚) 的同口径对照。
在役格 (α=.05, b=.002, target)。输出: 全史/逐年均值 + 滚动52锚均值分布 + 实盘值分位。"""
import sys
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
import numpy as np, pandas as pd
import legs as LG
import engine.replay_fullhist as RF
W = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N; n = len(a)
FI, RVI = src.fund_idx, src.ch.index("rvol_24h")
SYMS = [str(s) for s in src.symbols]
held = {"k": np.full(N, np.nan), "s": np.full(N, np.nan), "f": np.full(N, np.nan)}
state = None; prev = np.zeros(N)
def spear(x, y):
    from scipy.stats import spearmanr
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 10: return np.nan
    return spearmanr(x[ok], y[ok]).correlation
IC = np.full(n, np.nan)
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
    tgt0 = np.asarray(r["target_w"], float)
    out = LG.apply_harvest_ema(tgt0, [SYMS[j] for j in m], state, 0.05)
    state = out["state"]; tgt = np.asarray(out["target_w"], float)
    w = prev.copy(); w[[j for j in range(N) if j not in set(m)]] = 0.0
    delta = tgt - w[m]; T = np.abs(delta) > 0.002
    wm = w[m].copy(); wm[T] = tgt[T]
    if T.any(): wm[T] -= wm.sum()/T.sum()
    w[m] = wm; prev = w
    y = src.Y4[ti, m].astype(float)
    IC[i] = spear(w[m], y)
df = pd.DataFrame({"y": yr, "ic": IC}).dropna()
print(f"全史 书级rankIC: mean {df.ic.mean():+.4f} sd {df.ic.std():.3f} n={len(df)}")
for y, g in df.groupby("y"):
    print(f"  {y}: {g.ic.mean():+.4f} (n={len(g)})")
roll = df.ic.rolling(52).mean().dropna()
live = 0.0504
pct = float((roll < live).mean()) * 100
print(f"滚动52锚均值分布: p5 {roll.quantile(.05):+.4f} 中位 {roll.median():+.4f} p95 {roll.quantile(.95):+.4f}")
print(f"实盘 +0.0504 落在离线滚动52分布的第 {pct:.0f} 百分位")
print("BOOKIC_DONE")
