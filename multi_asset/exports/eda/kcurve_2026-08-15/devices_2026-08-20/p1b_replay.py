"""P1b 簇断路器 5 年回放判官(验收门已冻结于会话: 触发率 2-3/年; 最坏年保费≤50bps; 磨损潮削减≥25%)。
基材=healthcheck 的 9,821 锚在役书精确回放(逐名贡献版)。
口径: pnl 单位=book bps(gross≈1); 实盘 NAV bps ≈ ×2(杠杆 2×)。触发=因果(过去6锚), 动作=后续6锚。
"""
import sys, json
import numpy as np, pandas as pd
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
import legs as LG
import engine.replay_fullhist as RF

W = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}; C1 = 4.137; BW = 0.002
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N; n = len(a)
FI, RVI = src.fund_idx, src.ch.index("rvol_24h")
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
state = None; prev = np.zeros(N)
Wgt = np.zeros((n, N)); PNLN = np.zeros((n, N)); trn = np.zeros(n)
for i in range(n):
    m = MSK[i]; syms = [str(src.symbols[j]) for j in m]
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
    pn = np.zeros(N); idx = m[ok]
    pn[idx] = w[m][ok]*y[ok]*1e4
    PNLN[i] = pn; Wgt[i] = w
    trn[i] = float(np.abs(w-prev).sum()); prev = w
g = PNLN.sum(1); net = g - trn*C1
print("回放核对: 全期净均值", round(net.mean(), 3), "bps/锚 (healthcheck 应≈同值)")
# 滚动6锚 + 簇归因(因果: 用 i-5..i 窗, 动作 i+1..i+6)
R6 = np.array([net[max(0, i-5):i+1].sum() for i in range(n)])
res = {}
for X in (120., 150., 180., 210., 250.):
    trigs = []
    i = 6; supp = -99
    while i < n - 7:
        if i - supp > 12 and R6[i] <= -X:
            win = PNLN[i-5:i+1]; wavg = Wgt[i-5:i+1].mean(0)
            contrib = win.sum(0)
            S = np.where((wavg < 0) & (contrib < 0))[0]
            shortloss = -contrib[S].sum(); tot = -min(R6[i], -1e-9)
            share = shortloss / max(tot, 1e-9)
            top10 = -np.sort(contrib[S])[:10].sum() / max(tot, 1e-9) if len(S) else 0.
            if share >= 0.6 and top10 >= 0.4:
                cf = 0.0
                for k in range(i+1, min(i+7, n)):
                    cf += -0.3 * PNLN[k][S].sum()
                cost = 0.6 * np.abs(Wgt[i][S]).sum() * C1 * 1e0
                trigs.append((int(yr[i]), float(cf - cost), float(R6[i])))
                supp = i
        i += 1
    byy = {}
    for y in sorted(set(t[0] for t in trigs)):
        vs = [t[1] for t in trigs if t[0] == y]
        byy[y] = {"n": len(vs), "sum_delta_bps": round(sum(vs), 1)}
    per = [t[1] for t in trigs]
    yrs_span = yr[-1] - yr[0] + 1
    res[f"X{int(X)}"] = {"n_trig": len(trigs), "per_year": round(len(trigs)/5.0, 1),
                         "mean_delta": round(float(np.mean(per)), 1) if per else None,
                         "worst_year_premium": round(min((b["sum_delta_bps"] for b in byy.values()), default=0), 1),
                         "by_year": byy}
print(json.dumps(res, ensure_ascii=False))
json.dump(res, open(f"{PD}/p1b_replay_result.json", "w"))
