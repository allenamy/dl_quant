"""Sharpe 4 需要什么 —— 实测天花板, 不推算。
对每个臂算: 零成本夏普(信号本身的天花板) · 打平成本率 · 达到 Sharpe{1,2,3,4} 所需的 (毛额, 成本) 组合。
装置 = 实盘 compose_book, 9821 锚。"""
import sys, os, json, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
import legs as LG
import engine.replay_fullhist as RF
W = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}; ANN = np.sqrt(6*365)
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N
FI, RVI = src.fund_idx, src.ch.index("rvol_24h")

def run(king_cad, phase):
    held = {"k": np.full(N, np.nan), "s": np.full(N, np.nan), "f": np.full(N, np.nan)}
    prev = None; pnl = np.zeros(len(a)); trn = np.zeros(len(a))
    for i, t in enumerate(a):
        ti = int(t); m = np.asarray(src.tradeable(ti))
        if m.dtype == bool: m = np.where(m)[0]
        if i == 0 or (ti-phase) % king_cad == 0:
            v = np.full(N, np.nan); v[m] = src.king[ti, m]; held["k"] = v
        if i == 0 or ti % 24 == 0:
            v = np.full(N, np.nan); v[m] = src.s2[ti, m]; held["s"] = v
        if i == 0 or ti % 8 == 0:
            v = np.full(N, np.nan); v[m] = src.CH[ti, m, FI]; held["f"] = v
        r = LG.compose_book(held["k"][m], held["s"][m], held["f"][m], np.ones(len(m)), weights=W,
                            rvol=src.CH[ti, m, RVI].astype(float), risk_budget=RB)
        w = np.asarray(r["target_w"], float); y = src.Y4[ti, m]; ok = np.isfinite(y)
        pnl[i] = float(np.nansum(w[ok]*y[ok]))*1e4
        cur = dict(zip(m, w))
        trn[i] = 0. if prev is None else sum(abs(cur.get(x, 0.)-prev.get(x, 0.)) for x in set(cur) | set(prev))
        prev = cur
    return pnl, trn

ARMS = [("C4 在役 king4h", 4, 0), ("C8A king8h 相位0", 8, 0)]
print(f"{'臂':18s}{'毛bps':>8s}{'毛sd':>8s}{'换手':>7s}{'零成本夏普':>11s}{'打平成本/边':>12s}"
      f"{'净@3.115':>10s}{'夏普':>7s}{'净@1.5':>9s}{'夏普':>7s}")
R = {}
for nm, cad, ph in ARMS:
    p, t = run(cad, ph); R[nm] = (p, t)
    g = p.mean(); sd0 = p.std(ddof=1); tt = t.mean()
    be = g/(2*tt)
    row = f"{nm:18s}{g:+8.3f}{sd0:8.2f}{tt:7.4f}{g/sd0*ANN:+11.2f}{be:12.3f}"
    for c in (3.115, 1.5):
        npx = p - t*2*c
        row += f"{npx.mean():+10.3f}{npx.mean()/npx.std(ddof=1)*ANN:+7.2f}"
    print(row, flush=True)

print("\n" + "═"*82)
print("★ 要达到目标夏普, 需要 (毛额倍数 × 成本/边) 的组合 —— 以 C8A 为基准")
print("═"*82)
p, t = R["C8A king8h 相位0"]; g0, tt = p.mean(), t.mean(); sd0 = p.std(ddof=1)
print(f"  基准: 毛 {g0:.3f} bps, 逐锚毛sd {sd0:.2f} bps, 换手 {tt:.4f}")
print(f"  {'目标夏普':>8s}  {'需要净额':>9s} " + "".join(f"{'成本'+str(c)+'时毛额需×':>15s}" for c in (3.115, 2.0, 1.5, 1.0, 0.0)))
for S in (0, 1, 2, 3, 4):
    need = S*sd0/ANN
    row = f"  {S:>8d}  {need:+9.3f} "
    for c in (3.115, 2.0, 1.5, 1.0, 0.0):
        mult = (need + tt*2*c)/g0
        row += f"{mult:>14.2f}×"
    print(row)
print("\n  (毛额倍数 = 需要的毛额 ÷ 当前毛额; sd 假设随毛额同比例放大, 保守)")

print("\n" + "═"*82); print("★ 逐年 零成本夏普(信号本身在各 regime 的天花板)"); print("═"*82)
for nm in R:
    p, t = R[nm]
    df = pd.DataFrame({"y": yr, "p": p})
    s = df.groupby("y").p.apply(lambda x: x.mean()/x.std(ddof=1)*ANN)
    print(f"  {nm:18s} " + "  ".join(f"{int(k)}:{v:+6.2f}" for k, v in s.items()))
print("\nCEILING_DONE")
