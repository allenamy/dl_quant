"""在役配置(8h+EMA0.3 精确变换)的收益/波动/回撤全画像 — 入金决策依据。
逐锚净额序列(@实测成本4.137)→ 年化收益/波动/夏普(1×/2×/3× 杠杆), 逐年绝对净额,
最大回撤(实测路径 + 5000 次日块 bootstrap 的 1 年期回撤分布), 距 −25% 停机线的余量。"""
import sys, json, numpy as np, pandas as pd
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
state = None; prev = np.zeros(N); net = np.zeros(n)
for i in range(n):
    m = MSK[i]; syms = [SYMS[j] for j in m]
    out = LG.apply_harvest_ema(TGT[i][m], syms, state, 0.3)
    state = out["state"]
    w = np.zeros(N); w[m] = np.asarray(out["target_w"], float)
    y = RET[i]; ok = np.isfinite(y)
    net[i] = float(np.nansum(w[m][ok]*y[ok]))*1e4 - float(np.abs(w-prev).sum())*C1
    prev = w
print(f"[EMA0.3 精确] {n} 锚  净均值 {net.mean():+.3f} bps/锚  sd {net.std(ddof=1):.2f}")
print("\n═══ 逐年【绝对】净额 + 年化(gross 口径, 1×)═══")
df = pd.DataFrame({"y": yr, "p": net})
for y_, g in df.groupby("y"):
    ann_r = g.p.mean()*6*365/1e4; ann_v = g.p.std(ddof=1)*ANN/1e4
    print(f"  {int(y_)}: 净 {g.p.mean():+6.3f} bps/锚  年化收益 {ann_r:+7.2%}  波动 {ann_v:6.2%}  夏普 {g.p.mean()/g.p.std(ddof=1)*ANN:+5.2f}")
print("\n═══ 回撤(实测 4.5 年路径, gross 口径)═══")
cum = np.cumsum(net)/1e4
dd = cum - np.maximum.accumulate(cum)
print(f"  全期最大回撤 = {dd.min():.2%} of gross   (发生于第 {int(np.argmin(dd))} 锚)")
for y_, g in df.groupby("y"):
    c = np.cumsum(g.p.values)/1e4; d = (c-np.maximum.accumulate(c)).min()
    print(f"  {int(y_)} 年内最大回撤 {d:.2%} of gross")
print("\n═══ 1 年期回撤分布(5000 次日块 bootstrap, 块=5 锚≈20h)═══")
rng = np.random.default_rng(7); L = 2190; bl = 5
dds = []
for _ in range(5000):
    st = rng.integers(0, n-bl, size=L//bl+1)
    path = np.concatenate([net[s:s+bl] for s in st])[:L]
    c = np.cumsum(path)/1e4
    dds.append((c-np.maximum.accumulate(c)).min())
dds = np.array(dds)
print(f"  中位 {np.percentile(dds,50):.2%} · p75 {np.percentile(dds,25):.2%} · p95 {np.percentile(dds,5):.2%} · p99 {np.percentile(dds,1):.2%}  (of gross)")
print("\n═══ 杠杆换算表(NAV 口径; 回撤停机线 −25% NAV)═══")
mu = net.mean()*6*365/1e4; sig = net.std(ddof=1)*ANN/1e4
for lev in (2.0, 3.0):
    print(f"  {lev:.0f}×: 年化收益 {mu*lev:+7.2%}  波动 {sig*lev:6.2%}  "
          f"实测最大DD {dd.min()*lev:.1%}  1年p95 DD {np.percentile(dds,5)*lev:.1%}  p99 {np.percentile(dds,1)*lev:.1%}"
          f"   {'★p99 触 −25% 线' if np.percentile(dds,1)*lev <= -0.25 else '距 −25% 线有余量'}")
print("DD_DONE")
