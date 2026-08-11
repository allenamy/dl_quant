"""king 腿 4h→8h · 实盘 compose_book · 9821 锚 —— 8h 提案的效果全景。
事前预期(旧引擎装置记录, 两签名对照): 换手 ~−30%, 书秩IC ~−10%, 净@3.115 转正或近零。
臂: C4 = 在役节奏(king4/funding8/s2_24) · C8A = king8 相位00/08/16 · C8B = king8 相位04/12/20
诊断: 净额双档/夏普/逐年 · king 分数过期 4h 衰减 · 新鲜锚 vs 持有锚的书 IC · 滚动 50 锚净额>0 占比
"""
import sys, os, json, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
import legs as LG
import engine.replay_fullhist as RF
W = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}; COSTS = [3.115, 5.80]; ANN = np.sqrt(6*365)
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N
FI, RVI = src.fund_idx, src.ch.index("rvol_24h")
H_MS = 3600*1000

def hold_ok(ti, cad, phase):        # ti 是小时索引(replay 内部), 锚 4h 网格
    return (ti - phase) % cad == 0

def run(king_cad, king_phase):
    held = {"king": np.full(N, np.nan), "s2": np.full(N, np.nan), "fund": np.full(N, np.nan)}
    prev = None; pnl = np.zeros(len(a)); trn = np.zeros(len(a)); ric = np.full(len(a), np.nan)
    fresh = np.zeros(len(a), bool)
    for i, t in enumerate(a):
        ti = int(t); m = np.asarray(src.tradeable(ti))
        if m.dtype == bool: m = np.where(m)[0]
        if i == 0 or hold_ok(ti, king_cad, king_phase):
            v = np.full(N, np.nan); v[m] = src.king[ti, m]; held["king"] = v; fresh[i] = True
        if i == 0 or hold_ok(ti, 24, 0):
            v = np.full(N, np.nan); v[m] = src.s2[ti, m]; held["s2"] = v
        if i == 0 or hold_ok(ti, 8, 0):
            v = np.full(N, np.nan); v[m] = src.CH[ti, m, FI]; held["fund"] = v
        r = LG.compose_book(held["king"][m], held["s2"][m], held["fund"][m], np.ones(len(m)),
                            weights=W, rvol=src.CH[ti, m, RVI].astype(float), risk_budget=RB)
        w = np.asarray(r["target_w"], float); y = src.Y4[ti, m]; ok = np.isfinite(y)
        pnl[i] = float(np.nansum(w[ok]*y[ok]))
        cur = dict(zip(m, w))
        trn[i] = 0. if prev is None else sum(abs(cur.get(x, 0.)-prev.get(x, 0.)) for x in set(cur) | set(prev))
        if ok.sum() >= 10:
            ric[i] = float(np.corrcoef(pd.Series(w[ok]).rank(), pd.Series(y[ok]).rank())[0, 1])
        prev = cur
    return pnl, trn, ric, fresh

ARMS = [("C4 在役(king4h)", 4, 0), ("C8A king8h 相位0", 8, 0), ("C8B king8h 相位4", 8, 4)]
R = {}
print(f"{'臂':20s}{'毛bps':>8s}{'秩IC':>9s}{'换手':>8s}" + "".join(f"{'净@'+str(c):>9s}{'夏普':>7s}" for c in COSTS))
for nm, cad, ph in ARMS:
    p, t, ic, fr = run(cad, ph); R[nm] = (p, t, ic, fr)
    g = p.mean()*1e4; tt = t.sum()/len(t); row = f"{nm:20s}{g:+8.3f}{np.nanmean(ic):+9.5f}{tt:8.4f}"
    for c in COSTS:
        np_ = p*1e4 - t*2*c
        row += f"{np_.mean():+9.3f}{np_.mean()/np_.std(ddof=1)*ANN:+7.2f}"
    print(row, flush=True)

p4, t4, _, _ = R[ARMS[0][0]]
print("\n═══ 逐年 净@3.115 ═══")
for nm, _, _ in ARMS:
    p, t, _, _ = R[nm]
    dfy = pd.DataFrame({"y": yr, "n": p*1e4 - t*2*3.115}).groupby("y").n.mean()
    print(f"  {nm:20s} " + "  ".join(f"{int(k)}:{v:+7.3f}" for k, v in dfy.items()))

print("\n═══ 持续性: king 分数过期 4h 损失多少(8h臂里 新鲜锚 vs 持有锚 的书秩IC)═══")
for nm in [ARMS[1][0], ARMS[2][0]]:
    p, t, ic, fr = R[nm]
    print(f"  {nm}: 新鲜锚 IC {np.nanmean(ic[fr]):+.5f} (n={fr.sum()})   "
          f"持有锚 IC {np.nanmean(ic[~fr]):+.5f} (n={(~fr).sum()})   "
          f"衰减 {(1-np.nanmean(ic[~fr])/max(np.nanmean(ic[fr]),1e-9))*100:+.1f}%")

print("\n═══ 稳定度: 滚动 50 锚(≈8天)净@3.115 ═══")
for nm, _, _ in ARMS:
    p, t, _, _ = R[nm]
    roll = pd.Series(p*1e4 - t*2*3.115).rolling(50).mean().dropna().values
    print(f"  {nm:20s} 窗口>0 占比 {(roll>0).mean():.3f}   p5 {np.percentile(roll,5):+.3f}   "
          f"p50 {np.percentile(roll,50):+.3f}   最差 {roll.min():+.3f}")

d = (R[ARMS[1][0]][0]*1e4 - R[ARMS[1][0]][1]*2*3.115) - (p4*1e4 - t4*2*3.115)
rng = np.random.default_rng(7); bl = 5; n_ = len(d); k = int(np.ceil(n_/bl))
bs = []
for q in range(3000):
    st = rng.integers(0, max(n_-bl, 1), size=k)
    ix = (st[:, None]+np.arange(bl)[None, :]).ravel()[:n_]; ix = ix[ix < n_]
    bs.append(d[ix].mean())
lo, hi = np.percentile(bs, [2.5, 97.5])
print(f"\nΔ净@3.115 (C8A − 在役) = {d.mean():+.3f} bps  CI95[{lo:+.3f},{hi:+.3f}]")
print("CAD8_DONE")
