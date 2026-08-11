"""PREREG_leg_weight_netopt_2026-08-04 执行器 (冻结 SHA 见预注册 .sha256)

装置: 复用 engine/replay_fullhist + netting, 不复制逻辑。
可分离性(已由代码审阅确认, 并由 §PARITY 实测断言):
  - netting 的 held[k] 更新【不含权重】
  - gross_turn = Σ_k w_k · T_k, 对权重严格线性
  - 只有 shape_position(cap+demean) 非线性 ⇒ 每个权重点重算, 但【直接调用 chain.shape_position】
⇒ 231 格点是精确复现, 不是近似。
"""
import sys, json, time, itertools, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
import engine.replay_fullhist as RF
from engine.signal_chain import SignalChain
from engine.funding_risk import FundingLegRiskControl
from engine.vol_gate import VolGate
from engine.netting import CrossLegNetting, LEG_CADENCE_H

KING = "/mnt/storage/private/work_hsy/probe_artifacts/king_pred_newgen.npz"
S2   = "/mnt/storage/private/work_hsy/probe_artifacts/s2_pred_newgen.npz"
DEP  = {"king": 0.5952380952380952, "s2": 0.20238095238095238,
        "funding": 0.20238095238095238, "size": 0.0}
LEGS = ["king", "s2", "funding", "size"]
COSTS = [3.63, 5.80]
STEP = 0.05
OUT = "/mnt/storage/private/work_hsy/probe_artifacts/netopt_result.json"

t0 = time.time()
src = RF.get_src(None, KING, S2)
anchors, yr = RF._all_anchors(src)
N = src.N
print(f"[A] src N={N} anchors={len(anchors)} years={sorted(set(yr))}", flush=True)

disp_ref = FundingLegRiskControl.calibrate_dispersion(src, anchors)
frc = FundingLegRiskControl(winsor_z=4.0, name_cap=0.15, disp_gate_z=4.0,
                            disp_shrink=0.3, disp_ref=disp_ref)
chain = SignalChain(src, weights=DEP, funding_mode="rank", vol_gate=VolGate(src),
                    funding_risk=frc, pos_cap_pct=99.0)
chain.calibrator = None

# ── Phase A: 缓存与权重无关的一切 ────────────────────────────────────────────
cad = dict(LEG_CADENCE_H)
print(f"[A] leg cadence = {cad}", flush=True)
held = {k: np.zeros(N) for k in LEGS}
HELD = np.zeros((len(anchors), len(LEGS), N), dtype=np.float64)
T = {k: 0.0 for k in LEGS}
M, RET = [], []
frc.n_gated = 0
for i, t in enumerate(anchors):
    ti = int(t)
    legpos, m = chain.leg_positions(ti)
    for j, k in enumerate(LEGS):
        if i == 0 or (ti % cad[k] == 0):
            new = np.zeros(N); new[m] = legpos[k]
            T[k] += float(np.abs(new - held[k]).sum())
            held[k] = new
        HELD[i, j] = held[k]
    M.append(m); RET.append(src.Y4[ti, m])
    if i % 2000 == 0:
        print(f"[A] {i}/{len(anchors)}  {time.time()-t0:.0f}s", flush=True)
YEARS_SPAN = (int(src.ts[anchors[-1]]) - int(src.ts[anchors[0]])) / (1000*3600*24*365.25)
DAY = (src.ts[anchors] // (1000*3600*24)).astype(np.int64)
print(f"[A] done {time.time()-t0:.0f}s  T={ {k: round(v,1) for k,v in T.items()} }", flush=True)

# ── Phase B: 每个权重点的逐锚 P&L ────────────────────────────────────────────
def evaluate(w):
    wv = np.array([w.get(k, 0.0) for k in LEGS], dtype=np.float64)
    prev_net = np.zeros(N)
    pnl = np.zeros(len(anchors)); turn = np.zeros(len(anchors))
    for i in range(len(anchors)):
        m = M[i]
        active = (wv @ HELD[i])[m]
        base = active - active.mean()
        gref = float(np.abs(base).sum())
        shaped = chain.shape_position(active)          # ← 真代码, 不重写
        gsh = float(np.abs(shaped).sum())
        if gsh > 1e-12 and gref > 1e-12:
            shaped = shaped * (gref / gsh)
        net = np.zeros(N); net[m] = shaped
        ret = RET[i]; ok = np.isfinite(ret)
        pnl[i] = float(np.nansum(shaped[ok] * ret[ok]))
        # ★ run_replay 的 P&L 循环 prev=None ⇒ 首锚换手为 0(初始建仓不计)。必须同构, 否则第一年偏。
        turn[i] = 0.0 if i == 0 else float(np.abs(net - prev_net).sum())
        prev_net = net
    gross_ann = float(sum(wv[j] * T[k] for j, k in enumerate(LEGS)) / max(YEARS_SPAN, 1e-9))
    return pnl, turn, gross_ann

def daily_frame(pnl, turn, cost_bps):
    net = pnl - turn * cost_bps * 1e-4
    df = pd.DataFrame({"day": DAY, "yr": yr, "g": pnl, "n": net})
    return df.groupby("day").agg(g=("g","sum"), n=("n","sum"), yr=("yr","first")).reset_index()

def sharpe(x):
    return RF._dsharpe(x)

# ── PARITY: 快路径必须复现真 run_replay ─────────────────────────────────────
print("[P] parity check vs run_replay ...", flush=True)
RF.COST_BPS = COSTS[0]
ref = RF.run_replay(funding_mode="rank", use_c5=True, shaping="cap",
                    king=KING, s2=S2, weights=DEP, verbose=True)
p_dep, t_dep, gann_dep = evaluate(DEP)
d = daily_frame(p_dep, t_dep, COSTS[0])
mine = {int(y): round(sharpe(d[d.yr == y]["n"].values), 2) for y in sorted(set(yr))}
theirs = {int(y): v["net_of_cost_sharpe"] for y, v in ref["per_year"].items()}
gmatch = abs(gann_dep - ref["netting"]["gross_turn_ann"]) < 0.5
print(f"[P] mine  = {mine}")
print(f"[P] theirs= {theirs}")
print(f"[P] gross_turn_ann mine={gann_dep:.1f} theirs={ref['netting']['gross_turn_ann']:.1f} match={gmatch}")
dif = {y: round(mine[y] - theirs[y], 4) for y in mine}
print(f"[P] diff  = {dif}   (theirs 已被 run_replay 四舍五入到 2 位 ⇒ 容差 0.011)")
PARITY = all(abs(v) <= 0.011 for v in dif.values()) and gmatch
print(f"[P] PARITY = {PARITY}", flush=True)
if not PARITY:
    print("[P] ★ 对等断言失败 —— 停止, 不出任何权重结论。"); sys.exit(1)

# ── 网格 ────────────────────────────────────────────────────────────────────
n = int(round(1.0 / STEP))
GRID = [{"king": k/n, "s2": s/n, "funding": (n-k-s)/n, "size": 0.0}
        for k in range(n+1) for s in range(n+1-k)]
print(f"[B] grid = {len(GRID)} points", flush=True)

STORE = {}   # idx -> {"daily": {cost: df}, "gross_ann": ...}
for gi, w in enumerate(GRID):
    pnl, turn, gann = evaluate(w)
    STORE[gi] = {"w": w, "gross_ann": gann,
                 "daily": {c: daily_frame(pnl, turn, c) for c in COSTS}}
    if gi % 20 == 0:
        print(f"[B] {gi}/{len(GRID)}  {time.time()-t0:.0f}s", flush=True)
print(f"[B] done {time.time()-t0:.0f}s", flush=True)

# ── 判读协议 (预注册 §3, 逐字执行) ──────────────────────────────────────────
YEARS = sorted(set(int(y) for y in yr))
EVAL_YEARS = [y for y in YEARS if y >= 2023]
EQ = {"king": 1/3, "s2": 1/3, "funding": 1/3, "size": 0.0}

def sharpe_on(gi, cost, years):
    d = STORE[gi]["daily"][cost]
    return sharpe(d[d.yr.isin(years)]["n"].values)

def series_on(gi, cost, years):
    d = STORE[gi]["daily"][cost]
    dd = d[d.yr.isin(years)]
    return dd["day"].values, dd["n"].values

def add_named(tag, w):
    """现行权重(.5952…)与等权(1/3)都不落在 0.05 网格上 ⇒ 各自单独评估一次。"""
    p, t, ga = evaluate(w)
    STORE[tag] = {"w": w, "gross_ann": ga,
                  "daily": {c: daily_frame(p, t, c) for c in COSTS}}
    return tag

gi_dep = add_named("DEP", DEP)
gi_eq = add_named("EQ", EQ)
print(f"[B] 对照已评估: 现行 turn={STORE['DEP']['gross_ann']:.1f} "
      f"等权 turn={STORE['EQ']['gross_ann']:.1f}", flush=True)

RESULT = {"parity": PARITY, "anchors": int(len(anchors)), "N": int(N),
          "grid_points": len(GRID), "leg_cadence": cad, "T_weightfree": T,
          "years": YEARS, "eval_years": EVAL_YEARS, "by_cost": {}}

for cost in COSTS:
    # walk-forward: w*(Y) = 严格早于 Y 的年份上净夏普最大
    GKEYS = [gi for gi in STORE if isinstance(gi, int)]   # 只在网格上搜, 对照不参选
    wf = []
    for Y in EVAL_YEARS:
        prior = [y for y in YEARS if y < Y]
        sc = {gi: sharpe_on(gi, cost, prior) for gi in GKEYS}
        best_gi = max(GKEYS, key=lambda gi: sc[gi] if np.isfinite(sc[gi]) else -9e9)
        wf.append({"eval_year": Y, "prior": prior, "w_star": STORE[best_gi]["w"],
                   "gi": best_gi,
                   "insample_sharpe": round(sharpe_on(best_gi, cost, prior), 3),
                   "oos_sharpe": round(sharpe_on(best_gi, cost, [Y]), 3),
                   "gross_turn_ann": round(STORE[best_gi]["gross_ann"], 1)})
    oos_opt = float(np.mean([r["oos_sharpe"] for r in wf]))

    oos_dep = float(np.mean([sharpe_on(gi_dep, cost, [Y]) for Y in EVAL_YEARS]))
    oos_eq = float(np.mean([sharpe_on(gi_eq, cost, [Y]) for Y in EVAL_YEARS]))
    # 样本内最优(上界, 不可部署)
    sc_all = {gi: sharpe_on(gi, cost, YEARS) for gi in GKEYS}
    gi_is = max(GKEYS, key=lambda gi: sc_all[gi] if np.isfinite(sc_all[gi]) else -9e9)

    # OOS 策略的逐日序列: 每个评估年用它自己的 w*(Y)
    days_o, v_o, days_d, v_d = [], [], [], []
    for r in wf:
        Y = r["eval_year"]
        dO, sO = series_on(r["gi"], cost, [Y]); dD, sD = series_on(gi_dep, cost, [Y])
        assert np.array_equal(dO, dD), "日索引不对齐"
        days_o.append(dO); v_o.append(sO); v_d.append(sD)
    v_o = np.concatenate(v_o); v_d = np.concatenate(v_d)
    diff = v_o - v_d

    # day-block bootstrap on Sharpe difference
    rng = np.random.default_rng(12345)
    BL, NB = 5, 4000
    nblk = int(np.ceil(len(diff) / BL))
    boot = np.empty(NB)
    for b in range(NB):
        st = rng.integers(0, max(len(diff) - BL, 1), size=nblk)
        idx = (st[:, None] + np.arange(BL)[None, :]).ravel()[:len(diff)]
        idx = idx[idx < len(diff)]
        boot[b] = sharpe(v_o[idx]) - sharpe(v_d[idx])
    lo, hi = np.percentile(boot, [2.5, 97.5])
    point = sharpe(v_o) - sharpe(v_d)

    RESULT["by_cost"][str(cost)] = {
        "walk_forward": wf,
        "OOS_opt": round(oos_opt, 3),
        "OOS_current": round(oos_dep, 3),
        "OOS_equal": round(oos_eq, 3),
        "insample_best_w": STORE[gi_is]["w"],
        "insample_best_sharpe_UPPER_BOUND_NOT_DEPLOYABLE": round(sharpe_on(gi_is, cost, YEARS), 3),
        "current_gross_turn_ann": round(STORE[gi_dep]["gross_ann"], 1),
        "diff_sharpe_point": round(float(point), 4),
        "diff_sharpe_CI95": [round(float(lo), 4), round(float(hi), 4)],
        "verdict": ("权重可换" if lo > 0 else
                    ("装置没找到东西(不敌等权)" if oos_opt <= oos_eq else "不换(CI 含 0), 记为方向性证据")),
    }
    print(f"\n===== cost {cost} bps =====")
    print(f"  OOS 优化 {oos_opt:.3f} | 现行 {oos_dep:.3f} | 等权 {oos_eq:.3f}")
    print(f"  Δ夏普 {point:+.4f}  CI95 [{lo:+.4f}, {hi:+.4f}]  ⇒ {RESULT['by_cost'][str(cost)]['verdict']}")
    for r in wf:
        print(f"   {r['eval_year']}: w*={ {k: round(v,2) for k,v in r['w_star'].items() if v>0} } "
              f"IS {r['insample_sharpe']:+.2f} → OOS {r['oos_sharpe']:+.2f}  turn {r['gross_turn_ann']}")

json.dump(RESULT, open(OUT, "w"), indent=1, default=str)
print(f"\n[done] {time.time()-t0:.0f}s -> {OUT}", flush=True)
print("NETOPT_DONE")
