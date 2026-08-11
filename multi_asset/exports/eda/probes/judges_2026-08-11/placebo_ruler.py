"""PREREG_leg_admission_v2_2026-08-09 §2 —— P2(装置对等) → P1(净夏普不变性) → P3(成本变号点)

★ 输入口径: 默认面板(= 0C 2026-08-01/02 当时用的【脏】DL 腿)。
  必须如此: P2 要复现 0C 发表的 +0.185 与 SQ 累计 +9.877, 那两个数是脏腿算的。
  用干净腿跑 P2 会"复现不出来", 并被误读成装置不同。干净腿的重测是 P1 通过之后的另一次运行。
"""
import sys, json, time, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
import engine.replay_fullhist as RF
from engine.signal_chain import SignalChain
from engine.funding_risk import FundingLegRiskControl
from engine.vol_gate import VolGate
from engine.netting import LEG_CADENCE_H

LEGS = ["king", "s2", "funding", "size"]
SQ   = {"king": 0.5952380952380952, "s2": 0.20238095238095238, "funding": 0.20238095238095238, "size": 0.0}
ALTA = {"king": 0.5952380952380952, "s2": 0.135, "funding": 0.135, "size": 0.135}
SEEDS = [0, 1, 2, 3, 4]                      # 预注册固定
COSTS = [1.9, 3.63, 5.80]
OUT = "/mnt/storage/private/work_hsy/probe_artifacts/placebo_ruler.json"

t0 = time.time()
src = RF.get_src()                            # ← 默认面板, 与 0C 同
anchors, yr = RF._all_anchors(src)
N = src.N
print(f"[A] N={N} anchors={len(anchors)}", flush=True)
disp_ref = FundingLegRiskControl.calibrate_dispersion(src, anchors)
frc = FundingLegRiskControl(winsor_z=4.0, name_cap=0.15, disp_gate_z=4.0,
                            disp_shrink=0.3, disp_ref=disp_ref)
chain = SignalChain(src, weights=SQ, funding_mode="rank", vol_gate=VolGate(src),
                    funding_risk=frc, pos_cap_pct=99.0)
chain.calibrator = None
cad = dict(LEG_CADENCE_H)

# ── Phase A: king/s2/funding 缓存一次; size 缓存 1(真) + 5(安慰剂) 份 ────────
VARIANTS = ["real"] + [f"shuf{s}" for s in SEEDS]
rngs = {f"shuf{s}": np.random.default_rng(s) for s in SEEDS}
held = {k: np.zeros(N) for k in ["king", "s2", "funding"]}
sheld = {v: np.zeros(N) for v in VARIANTS}
HELD = np.zeros((len(anchors), 3, N))
SIZE = {v: np.zeros((len(anchors), N)) for v in VARIANTS}
T = {k: 0.0 for k in ["king", "s2", "funding"]}
TS = {v: 0.0 for v in VARIANTS}
M, RET = [], []
frc.n_gated = 0
for i, t in enumerate(anchors):
    ti = int(t)
    legpos, m = chain.leg_positions(ti)
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
    M.append(m); RET.append(src.Y4[ti, m])
YRS = (int(src.ts[anchors[-1]]) - int(src.ts[anchors[0]])) / (1000*3600*24*365.25)
DAY = (src.ts[anchors] // (1000*3600*24)).astype(np.int64)
print(f"[A] done {time.time()-t0:.0f}s", flush=True)

def evaluate(w, variant):
    wv = np.array([w[k] for k in ["king", "s2", "funding"]])
    ws = w["size"]
    prev = np.zeros(N); pnl = np.zeros(len(anchors)); turn = np.zeros(len(anchors))
    for i in range(len(anchors)):
        m = M[i]
        combo = wv @ HELD[i]
        if ws:
            combo = combo + ws * SIZE[variant][i]
        active = combo[m]
        base = active - active.mean(); gref = float(np.abs(base).sum())
        shaped = chain.shape_position(active)
        gsh = float(np.abs(shaped).sum())
        if gsh > 1e-12 and gref > 1e-12:
            shaped = shaped * (gref / gsh)
        net = np.zeros(N); net[m] = shaped
        ret = RET[i]; ok = np.isfinite(ret)
        pnl[i] = float(np.nansum(shaped[ok] * ret[ok]))
        turn[i] = 0.0 if i == 0 else float(np.abs(net - prev).sum())
        prev = net
    gturn = (sum(wv[j]*T[k] for j, k in enumerate(["king", "s2", "funding"])) + ws*TS[variant])
    return pnl, turn, gturn / max(YRS, 1e-9)

def metrics(pnl, turn, cost):
    net = pnl - turn*cost*1e-4
    d = pd.DataFrame({"day": DAY, "yr": yr, "n": net}).groupby("day").agg(
        n=("n", "sum"), yr=("yr", "first")).reset_index()
    per = {int(y): round(RF._dsharpe(d[d.yr == y]["n"].values), 3) for y in sorted(set(yr))}
    return {"cum_net": float(net.sum()), "avg_sharpe": float(np.mean(list(per.values()))),
            "per_year": per, "cum_gross": float(pnl.sum()), "cum_turn": float(turn.sum())}

R = {"src": "DEFAULT(dirty DL legs, = 0C 2026-08-01/02)", "anchors": int(len(anchors)),
     "N": int(N), "seeds": SEEDS, "arms": {}}
for name, w, v in ([("SQ", SQ, "real"), ("ALTA_real", ALTA, "real")] +
                   [(f"ALTA_{s}", ALTA, s) for s in VARIANTS if s != "real"]):
    p, t, ga = evaluate(w, v)
    R["arms"][name] = {"gross_turn_ann": round(ga, 1),
                       "by_cost": {str(c): metrics(p, t, c) for c in COSTS}}
    print(f"[E] {name:12s} turn={ga:7.1f}  " +
          "  ".join(f"c{c}: cum{R['arms'][name]['by_cost'][str(c)]['cum_net']:+.4f} "
                    f"Sh{R['arms'][name]['by_cost'][str(c)]['avg_sharpe']:+.3f}" for c in COSTS), flush=True)

# ── 判读 ────────────────────────────────────────────────────────────────────
def d(a, b, c, key):  return R["arms"][a]["by_cost"][str(c)][key] - R["arms"][b]["by_cost"][str(c)][key]
PL = [f"ALTA_shuf{s}" for s in SEEDS]
print("\n===== P2 装置对等: ΔNet@1.9 应复现 0C 的 +0.15~+0.25 =====")
print(f"  SQ 累计净@1.9 = {R['arms']['SQ']['by_cost']['1.9']['cum_net']:+.5f}   (0C 发表 +9.87732)")
p2 = [d(a, "SQ", 1.9, "cum_net") for a in PL]
print("  安慰剂 ΔNet@1.9 逐种子 = " + ", ".join(f"{x:+.5f}" for x in p2) + f"  均值 {np.mean(p2):+.5f}")
print(f"  真 size ΔNet@1.9 = {d('ALTA_real','SQ',1.9,'cum_net'):+.5f}   (0C 发表 +0.26698)")
P2 = 0.15 <= np.mean(p2) <= 0.25
print(f"  ⇒ P2 = {P2}")

print("\n===== P1 净夏普不变性: 安慰剂 ΔSharpe 均值 |·|<0.10 且至多 1 个种子 |·|>0.20 =====")
for c in COSTS:
    p1 = [d(a, "SQ", c, "avg_sharpe") for a in PL]
    n_big = sum(abs(x) > 0.20 for x in p1)
    ok = abs(np.mean(p1)) < 0.10 and n_big <= 1
    print(f"  c={c:5}: 逐种子 " + ", ".join(f"{x:+.3f}" for x in p1) +
          f"  均值 {np.mean(p1):+.4f}  |·|>0.2 的种子数 {n_big}  ⇒ {'PASS' if ok else 'FAIL'}")
    print(f"          真 size ΔSharpe = {d('ALTA_real','SQ',c,'avg_sharpe'):+.4f}")

print("\n===== P3 安慰剂 ΔNet 的成本变号点(预言 ≈6.5 bps) =====")
dg = np.mean([d(a, "SQ", 1.9, "cum_gross") for a in PL])
dt = np.mean([d(a, "SQ", 1.9, "cum_turn") for a in PL])
print(f"  ΔGross {dg:+.5f}  ΔTurn {dt:+.1f}  ⇒ 变号点 c* = {dg/dt*1e4:.2f} bps")

json.dump(R, open(OUT, "w"), indent=1)
print(f"\n[done] {time.time()-t0:.0f}s -> {OUT}\nPLACEBO_DONE")
