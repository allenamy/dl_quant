"""size 腿去混淆判定 —— king 权重固定, 只动 size, 每格配同槽位安慰剂, 实盘同构口径。

★ 判据(写死于跑之前, 见 LOG E68):
  GO 需同时: (a) 安慰剂修正后 ΔSharpe 在 3.63 与 5.8 【两档都 >0】
             (b) day-block bootstrap CI95 下界 > 0
             (c) 逐年 5 年里 ≥3 年同号
             (d) 剂量-反应在 w_size ∈ {.05,.10,.15} 上大致单调, 且【不】恰在最大测试权重处见顶
  任一不满足 ⇒ NO-GO(不录取), 且非单调/端点见顶一律标为可疑。

★ 混淆控制: king 固定 .5952380952380952 于【每一个】臂 —— RESULT_leg_marginal_audit §0 的教训:
  "摘掉腿 L 再归一" = "摘掉 L" 且 "把 king 顶上去", 任何非 king 腿都会被测成负。
"""
import sys, json, time, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
import engine.replay_fullhist as RF
from engine.signal_chain import SignalChain
from engine.funding_risk import FundingLegRiskControl
from engine.vol_gate import VolGate
from engine.netting import LEG_CADENCE_H

KING_W = 0.5952380952380952
KING_WS = [0.20,0.30,0.40,0.50,0.5952380952380952,0.70,0.80]
SEEDS = [0, 1, 2, 3, 4]
COSTS = [3.63, 5.80]
RB = {"alpha": 0.5, "lambda": 1.0}
KING = "/mnt/storage/private/work_hsy/probe_artifacts/king_pred_newgen.npz"
S2   = "/mnt/storage/private/work_hsy/probe_artifacts/s2_pred_newgen.npz"
OUT  = "/mnt/storage/private/work_hsy/probe_artifacts/king_w.json"

t0 = time.time()
src = RF.get_src(None, KING, S2)
anchors, yr = RF._all_anchors(src)
N = src.N; RVOL_I = src.ch.index("rvol_24h")
disp_ref = FundingLegRiskControl.calibrate_dispersion(src, anchors)
frc = FundingLegRiskControl(winsor_z=4.0, name_cap=0.15, disp_gate_z=4.0, disp_shrink=0.3, disp_ref=disp_ref)
chain = SignalChain(src, weights={"king": KING_W, "s2": .2, "funding": .2, "size": 0.0},
                    funding_mode="rank", vol_gate=VolGate(src), funding_risk=frc, pos_cap_pct=99.0)
chain.calibrator = None
cad = dict(LEG_CADENCE_H)
VARIANTS = ["real"] + [f"shuf{s}" for s in SEEDS]
rngs = {f"shuf{s}": np.random.default_rng(1000 + s) for s in SEEDS}
held = {k: np.zeros(N) for k in ["king", "s2", "funding"]}
sheld = {v: np.zeros(N) for v in VARIANTS}
HELD = np.zeros((len(anchors), 3, N)); SIZE = {v: np.zeros((len(anchors), N)) for v in VARIANTS}
M, RET, RVOL = [], [], []
frc.n_gated = 0
for i, t in enumerate(anchors):
    ti = int(t); legpos, m = chain.leg_positions(ti)
    for j, k in enumerate(["king", "s2", "funding"]):
        if i == 0 or (ti % cad[k] == 0):
            new = np.zeros(N); new[m] = legpos[k]; held[k] = new
        HELD[i, j] = held[k]
    for v in VARIANTS:
        if i == 0 or (ti % cad["size"] == 0):
            sig = legpos["size"] if v == "real" else rngs[v].permutation(legpos["size"])
            new = np.zeros(N); new[m] = sig; sheld[v] = new
        SIZE[v][i] = sheld[v]
    M.append(m); RET.append(src.Y4[ti, m]); RVOL.append(src.CH[ti, m, RVOL_I].astype(np.float64))
DAY = (src.ts[anchors] // (1000*3600*24)).astype(np.int64)
print(f"[A] done {time.time()-t0:.0f}s  N={N} anchors={len(anchors)}", flush=True)


def rb(shaped, rvol):
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


def daily(ws, variant):
    """实盘同构: cap99+demean → risk budget → l1(单位 gross)。返回逐日 (net@3.63, net@5.8)。"""
    rest = (1.0 - KING_W - ws) / 2.0
    wv = np.array([KING_W, rest, rest])
    prev = np.zeros(N); pnl = np.zeros(len(anchors)); turn = np.zeros(len(anchors))
    for i in range(len(anchors)):
        m = M[i]
        combo = wv @ HELD[i]
        if ws:
            combo = combo + ws * SIZE[variant][i]
        shaped = rb(chain.shape_position(combo[m]), RVOL[i])
        g = float(np.abs(shaped).sum())
        if g > 1e-12:
            shaped = shaped / g
        net = np.zeros(N); net[m] = shaped
        r = RET[i]; ok = np.isfinite(r)
        pnl[i] = float(np.nansum(shaped[ok] * r[ok]))
        turn[i] = 0.0 if i == 0 else float(np.abs(net - prev).sum())
        prev = net
    out = {}
    for c in COSTS:
        d = pd.DataFrame({"day": DAY, "yr": yr, "n": pnl - turn*c*1e-4}).groupby("day").agg(
            n=("n", "sum"), yr=("yr", "first")).reset_index()
        out[c] = d
    return out


def sh(x):  return RF._dsharpe(x)

def boot_ci(a, b, nb=4000, bl=5):
    rng = np.random.default_rng(777); n = len(a); nblk = int(np.ceil(n/bl))
    o = np.empty(nb)
    for k in range(nb):
        st = rng.integers(0, max(n-bl, 1), size=nblk)
        idx = (st[:, None] + np.arange(bl)[None, :]).ravel()[:n]; idx = idx[idx < n]
        o[k] = sh(a[idx]) - sh(b[idx])
    return float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))


