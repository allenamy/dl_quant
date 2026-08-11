"""在役 king 权重是否过高 —— 实盘同构口径, 配【全打乱】安慰剂。

★ 为什么问这个: size 判定 NO-GO(真实 ΔSh 随权重单调更负)⇒ E64 里四腿书 +0.060 的来源
  只能是 king 权重 .5952→.50。而 0C 在【脏面板 + 引擎记账】上测到的是相反方向(king 集中 +0.729)。

★ 安慰剂形状: 权重移动类比较必须用【全打乱】(每条腿都打乱, 两本书 alpha 同时归零),
  不是 size 判定用的【同槽位】安慰剂 —— RESULT_alt_weights §3-3 明令两类不可混用。
  0C 实测该形状的构造伪影是 −0.15(负的, 与真实效应反向) ⇒ 它压低而非解释正效应。

★ 判据(写死于起跑之前):
  "king 权重该降"需同时: (a) 真实曲线在某 w* 的净夏普 > 在 .5952 处, 【两档成本都是】
                        (b) 该差值的 day-block CI95 下界 > 0
                        (c) 全打乱安慰剂曲线【不】复现同一形状(否则是构造伪影)
                        (d) 逐年 5 年 ≥3 年同号
  任一不满足 ⇒ 不改权重, 记为方向性证据。
"""
import sys, json, time, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
import engine.replay_fullhist as RF
from engine.signal_chain import SignalChain
from engine.funding_risk import FundingLegRiskControl
from engine.vol_gate import VolGate
from engine.netting import LEG_CADENCE_H

KING_WS = [0.20, 0.30, 0.40, 0.50, 0.5952380952380952, 0.70, 0.80]
DEPLOYED = 0.5952380952380952
PSEEDS = [0, 1, 2]
COSTS = [3.63, 5.80]
RB = {"alpha": 0.5, "lambda": 1.0}
KING = "/mnt/storage/private/work_hsy/probe_artifacts/king_pred_newgen.npz"
S2   = "/mnt/storage/private/work_hsy/probe_artifacts/s2_pred_newgen.npz"
OUT  = "/mnt/storage/private/work_hsy/probe_artifacts/king_w.json"
LK = ["king", "s2", "funding"]

t0 = time.time()
src = RF.get_src(None, KING, S2)
anchors, yr = RF._all_anchors(src)
N = src.N; RVOL_I = src.ch.index("rvol_24h")
disp_ref = FundingLegRiskControl.calibrate_dispersion(src, anchors)
frc = FundingLegRiskControl(winsor_z=4.0, name_cap=0.15, disp_gate_z=4.0, disp_shrink=0.3, disp_ref=disp_ref)
chain = SignalChain(src, weights={"king": .6, "s2": .2, "funding": .2, "size": 0.0},
                    funding_mode="rank", vol_gate=VolGate(src), funding_risk=frc, pos_cap_pct=99.0)
chain.calibrator = None
cad = dict(LEG_CADENCE_H)

VAR = ["real"] + [f"sh{s}" for s in PSEEDS]
rngs = {f"sh{s}": np.random.default_rng(5000 + s) for s in PSEEDS}
held = {v: {k: np.zeros(N) for k in LK} for v in VAR}
HELD = {v: np.zeros((len(anchors), 3, N)) for v in VAR}
M, RET, RVOL = [], [], []
frc.n_gated = 0
for i, t in enumerate(anchors):
    ti = int(t); legpos, m = chain.leg_positions(ti)
    for v in VAR:
        for j, k in enumerate(LK):
            if i == 0 or (ti % cad[k] == 0):
                sig = legpos[k] if v == "real" else rngs[v].permutation(legpos[k])
                new = np.zeros(N); new[m] = sig; held[v][k] = new
            HELD[v][i, j] = held[v][k]
    M.append(m); RET.append(src.Y4[ti, m]); RVOL.append(src.CH[ti, m, RVOL_I].astype(np.float64))
DAY = (src.ts[anchors] // (1000*3600*24)).astype(np.int64)
print(f"[A] done {time.time()-t0:.0f}s N={N} anchors={len(anchors)}", flush=True)


def rb(sh_, rvol):
    a, l = RB["alpha"], RB["lambda"]
    s = np.asarray(rvol, float); fin = np.isfinite(s) & (s > 0)
    if not fin.any():
        return sh_
    med = float(np.median(s[fin]))
    if med <= 0:
        return sh_
    s = np.where(fin, s, med)
    w = np.sign(sh_) * np.abs(sh_) ** a / np.power(s / med, l)
    return w - w.mean()


def daily(kw, variant):
    rest = (1.0 - kw) / 2.0
    wv = np.array([kw, rest, rest]); H = HELD[variant]
    prev = np.zeros(N); pnl = np.zeros(len(anchors)); turn = np.zeros(len(anchors))
    for i in range(len(anchors)):
        m = M[i]
        shaped = rb(chain.shape_position((wv @ H[i])[m]), RVOL[i])
        g = float(np.abs(shaped).sum())
        if g > 1e-12:
            shaped = shaped / g
        net = np.zeros(N); net[m] = shaped
        r = RET[i]; ok = np.isfinite(r)
        pnl[i] = float(np.nansum(shaped[ok] * r[ok]))
        turn[i] = 0.0 if i == 0 else float(np.abs(net - prev).sum())
        prev = net
    return {c: pd.DataFrame({"day": DAY, "yr": yr, "n": pnl - turn*c*1e-4}).groupby("day").agg(
        n=("n", "sum"), yr=("yr", "first")).reset_index() for c in COSTS}


def sh(x):  return RF._dsharpe(x)

def boot(a, b, nb=4000, bl=5):
    rng = np.random.default_rng(999); n = len(a); nb_ = int(np.ceil(n/bl)); o = np.empty(nb)
    for k in range(nb):
        st = rng.integers(0, max(n-bl, 1), size=nb_)
        idx = (st[:, None] + np.arange(bl)[None, :]).ravel()[:n]; idx = idx[idx < n]
        o[k] = sh(a[idx]) - sh(b[idx])
    return float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))


D = {kw: {v: daily(kw, v) for v in VAR} for kw in KING_WS}
print(f"[B] done {time.time()-t0:.0f}s", flush=True)

R = {"king_ws": KING_WS, "deployed": DEPLOYED, "placebo_seeds": PSEEDS, "curve": {}}
print("\nking_w |  cost |  真实Sh   全打乱安慰剂(3种子)均值   真−慰")
print("-"*70)
for kw in KING_WS:
    R["curve"][f"{kw:.4f}"] = {}
    for c in COSTS:
        rs = sh(D[kw]["real"][c]["n"].values)
        ps = [sh(D[kw][f"sh{s}"][c]["n"].values) for s in PSEEDS]
        R["curve"][f"{kw:.4f}"][str(c)] = {"real": round(rs, 4),
                                           "placebo_mean": round(float(np.mean(ps)), 4),
                                           "placebo_seeds": [round(x, 4) for x in ps]}
        mk = "  ← 在役" if abs(kw-DEPLOYED) < 1e-9 else ""
        print(f" {kw:.4f} | {c:5} | {rs:+8.4f}  {np.mean(ps):+10.4f}   {rs-np.mean(ps):+8.4f}{mk}", flush=True)

print("\n===== 相对在役权重的判据 =====")
R["vs_deployed"] = {}
for c in COSTS:
    base = D[DEPLOYED]["real"][c]
    for kw in KING_WS:
        if abs(kw-DEPLOYED) < 1e-9:
            continue
        a_ = D[kw]["real"][c]
        assert np.array_equal(a_["day"].values, base["day"].values)
        d = sh(a_["n"].values) - sh(base["n"].values)
        lo, hi = boot(a_["n"].values, base["n"].values)
        # 同一权重移动在全打乱书上的伪影
        art = float(np.mean([sh(D[kw][f"sh{s}"][c]["n"].values) - sh(D[DEPLOYED][f"sh{s}"][c]["n"].values)
                             for s in PSEEDS]))
        pery = [round(sh(a_["n"].values[base["yr"].values == y]) - sh(base["n"].values[base["yr"].values == y]), 3)
                for y in sorted(set(yr))]
        R["vs_deployed"].setdefault(str(c), {})[f"{kw:.4f}"] = {
            "dSharpe": round(d, 4), "ci95": [round(lo, 4), round(hi, 4)],
            "shuffle_artifact": round(art, 4), "artifact_corrected": round(d - art, 4),
            "per_year": pery, "n_years_pos": sum(1 for v in pery if v > 0)}
        print(f"  c={c} king {kw:.4f} vs 在役: Δ{d:+.4f} CI[{lo:+.4f},{hi:+.4f}] "
              f"伪影{art:+.4f} 修正后{d-art:+.4f} 逐年{sum(1 for v in pery if v>0)}/5 {pery}", flush=True)

json.dump(R, open(OUT, "w"), indent=1)
print(f"\n[done] {time.time()-t0:.0f}s -> {OUT}\nKINGW_DONE")
