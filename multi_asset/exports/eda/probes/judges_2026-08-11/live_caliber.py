"""实盘同构回放 —— 把引擎回放与在役 legs.py 的两处结构差补上, 然后重测所有腿/权重结论。

两处差(均由源码逐行确认, 非推断):
  (1) 归一: 在役 legs.py 末行 `return {"target_w": l1(shaped), ...}` = 逐锚单位 L1 gross;
      引擎 netting.py 是 `shaped * (gref/gsh)` = 缩回未整形书的离散度 ⇒ 书的规模随信号浮动。
      而实盘 gross = nav × target_leverage(2.0) 每锚重算 ⇒ 规模由政策定。★ 0C 的 /tmp/alt_gate.py:33
      `p / |p|.sum()` 与在役一致 —— 是引擎回放偏, 不是 0C 偏。
  (2) 风险预算(在役 2026-08-05 起, book.json alpha .5 lambda 1.0):
      w = sign(shaped)·|shaped|^α / (σ_i/median σ)^λ, 再 re-demean; σ = 面板 rvol_24h。
      引擎回放【没有】。

成本档按 STATE.md 令: 实测 3.63 与 CI 上界 5.8 双报(§0-quater/§290)。
"""
import sys, json, time, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
import engine.replay_fullhist as RF
from engine.signal_chain import SignalChain
from engine.funding_risk import FundingLegRiskControl
from engine.vol_gate import VolGate
from engine.netting import LEG_CADENCE_H

KING = "/mnt/storage/private/work_hsy/probe_artifacts/king_pred_newgen.npz"
S2   = "/mnt/storage/private/work_hsy/probe_artifacts/s2_pred_newgen.npz"
LEGS = ["king", "s2", "funding", "size"]
LIVE3 = {"king": 0.5952380952380952, "s2": 0.20238095238095238, "funding": 0.20238095238095238, "size": 0.0}
FOUR  = {"king": 0.50, "s2": 0.17, "funding": 0.17, "size": 0.16}
ALTA  = {"king": 0.5952380952380952, "s2": 0.135, "funding": 0.135, "size": 0.135}
SEEDS = [0, 1, 2, 3, 4]
COSTS = [3.63, 5.80]
RB = {"alpha": 0.5, "lambda": 1.0}          # book.json risk_budget, 在役
OUT = "/mnt/storage/private/work_hsy/probe_artifacts/live_caliber.json"

t0 = time.time()
src = RF.get_src(None, KING, S2)             # 干净世代
anchors, yr = RF._all_anchors(src)
N = src.N
RVOL_I = src.ch.index("rvol_24h")
print(f"[A] N={N} anchors={len(anchors)} rvol_ch={RVOL_I}", flush=True)
disp_ref = FundingLegRiskControl.calibrate_dispersion(src, anchors)
frc = FundingLegRiskControl(winsor_z=4.0, name_cap=0.15, disp_gate_z=4.0, disp_shrink=0.3, disp_ref=disp_ref)
chain = SignalChain(src, weights=LIVE3, funding_mode="rank", vol_gate=VolGate(src),
                    funding_risk=frc, pos_cap_pct=99.0)
chain.calibrator = None
cad = dict(LEG_CADENCE_H)

VARIANTS = ["real"] + [f"shuf{s}" for s in SEEDS]
rngs = {f"shuf{s}": np.random.default_rng(s) for s in SEEDS}
held = {k: np.zeros(N) for k in ["king", "s2", "funding"]}
sheld = {v: np.zeros(N) for v in VARIANTS}
HELD = np.zeros((len(anchors), 3, N)); SIZE = {v: np.zeros((len(anchors), N)) for v in VARIANTS}
T = {k: 0.0 for k in ["king", "s2", "funding"]}; TS = {v: 0.0 for v in VARIANTS}
M, RET, RVOL = [], [], []
frc.n_gated = 0
for i, t in enumerate(anchors):
    ti = int(t); legpos, m = chain.leg_positions(ti)
    for j, k in enumerate(["king", "s2", "funding"]):
        if i == 0 or (ti % cad[k] == 0):
            new = np.zeros(N); new[m] = legpos[k]
            T[k] += float(np.abs(new - held[k]).sum()); held[k] = new
        HELD[i, j] = held[k]
    for v in VARIANTS:
        if i == 0 or (ti % cad["size"] == 0):
            sig = legpos["size"] if v == "real" else rngs[v].permutation(legpos["size"])
            new = np.zeros(N); new[m] = sig
            TS[v] += float(np.abs(new - sheld[v]).sum()); sheld[v] = new
        SIZE[v][i] = sheld[v]
    M.append(m); RET.append(src.Y4[ti, m]); RVOL.append(src.CH[ti, m, RVOL_I].astype(np.float64))
YRS = (int(src.ts[anchors[-1]]) - int(src.ts[anchors[0]])) / (1000*3600*24*365.25)
DAY = (src.ts[anchors] // (1000*3600*24)).astype(np.int64)
print(f"[A] done {time.time()-t0:.0f}s", flush=True)


def risk_budget(shaped, rvol):
    """在役 legs.py 240-259 行的逐字复刻。"""
    a, l = RB["alpha"], RB["lambda"]
    s = np.asarray(rvol, float); fin = np.isfinite(s) & (s > 0)
    if not fin.any():
        return shaped
    med = float(np.median(s[fin]))
    if med <= 0:
        return shaped
    s = np.where(fin, s, med)
    w = np.sign(shaped) * np.abs(shaped) ** a / np.power(s / med, l)
    return w - w.mean()


def evaluate(w, variant, accounting, use_rb):
    wv = np.array([w[k] for k in ["king", "s2", "funding"]]); ws = w["size"]
    prev = np.zeros(N); pnl = np.zeros(len(anchors)); turn = np.zeros(len(anchors)); hhi = np.zeros(len(anchors))
    for i in range(len(anchors)):
        m = M[i]
        combo = wv @ HELD[i]
        if ws:
            combo = combo + ws * SIZE[variant][i]
        active = combo[m]
        shaped = chain.shape_position(active)                 # cap99 + demean (两侧共用)
        if use_rb:
            shaped = risk_budget(shaped, RVOL[i])
        if accounting == "live":
            g = float(np.abs(shaped).sum())
            shaped = shaped / g if g > 1e-12 else shaped      # ← 在役 l1(shaped): 单位 gross
        else:
            base = active - active.mean(); gref = float(np.abs(base).sum())
            gsh = float(np.abs(shaped).sum())
            if gsh > 1e-12 and gref > 1e-12:
                shaped = shaped * (gref / gsh)                # ← 引擎 netting 的 gref 缩放
        net = np.zeros(N); net[m] = shaped
        ret = RET[i]; ok = np.isfinite(ret)
        pnl[i] = float(np.nansum(shaped[ok] * ret[ok]))
        turn[i] = 0.0 if i == 0 else float(np.abs(net - prev).sum())
        gg = float(np.abs(shaped).sum())
        hhi[i] = float(((np.abs(shaped)/gg)**2).sum() * len(m)) if gg > 1e-12 else np.nan
        prev = net
    gt = (sum(wv[j]*T[k] for j, k in enumerate(["king", "s2", "funding"])) + ws*TS[variant]) / max(YRS, 1e-9)
    return pnl, turn, gt, float(np.nanmean(hhi))


def metrics(pnl, turn, cost):
    net = pnl - turn*cost*1e-4
    d = pd.DataFrame({"day": DAY, "yr": yr, "n": net}).groupby("day").agg(
        n=("n", "sum"), yr=("yr", "first")).reset_index()
    per = {int(y): round(RF._dsharpe(d[d.yr == y]["n"].values), 3) for y in sorted(set(yr))}
    return {"avg_sharpe": round(float(np.mean(list(per.values()))), 3), "per_year": per,
            "cum_net": round(float(net.sum()), 4)}


ARMS = [("LIVE3", LIVE3, "real"), ("FOUR_withsize", FOUR, "real"), ("ALTA_realsize", ALTA, "real")] + \
       [(f"ALTA_shuf{s}", ALTA, f"shuf{s}") for s in SEEDS]
R = {"panel": "clean newgen", "anchors": int(len(anchors)), "risk_budget": RB, "costs": COSTS, "modes": {}}
for accounting, use_rb, tag in [("engine", False, "engine_norb"), ("live", False, "live_norb"), ("live", True, "live_rb")]:
    R["modes"][tag] = {}
    print(f"\n########## {tag}  (归一={accounting}, 风险预算={use_rb}) ##########", flush=True)
    for name, w, v in ARMS:
        p, tu, gt, hh = evaluate(w, v, accounting, use_rb)
        R["modes"][tag][name] = {"gross_turn_ann": round(gt, 1), "hhi_eff": round(hh, 3),
                                 "by_cost": {str(c): metrics(p, tu, c) for c in COSTS}}
        e = R["modes"][tag][name]
        print(f"  {name:15s} turn={gt:7.1f} HHI={hh:5.2f}  " +
              "  ".join(f"Sh@{c}={e['by_cost'][str(c)]['avg_sharpe']:+.3f}" for c in COSTS), flush=True)
    m = R["modes"][tag]
    pl = [f"ALTA_shuf{s}" for s in SEEDS]
    for c in COSTS:
        dpl = [m[a]["by_cost"][str(c)]["avg_sharpe"] - m["LIVE3"]["by_cost"][str(c)]["avg_sharpe"] for a in pl]
        dre = m["ALTA_realsize"]["by_cost"][str(c)]["avg_sharpe"] - m["LIVE3"]["by_cost"][str(c)]["avg_sharpe"]
        print(f"   c={c}: 安慰剂 ΔSh 逐种子 " + ", ".join(f"{x:+.3f}" for x in dpl) +
              f" 均值 {np.mean(dpl):+.4f} | 真size ΔSh {dre:+.4f} | 安慰剂修正后 {dre-np.mean(dpl):+.4f}", flush=True)

json.dump(R, open(OUT, "w"), indent=1)
print(f"\n[done] {time.time()-t0:.0f}s -> {OUT}\nLIVECAL_DONE")
