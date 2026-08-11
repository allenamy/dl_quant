"""宽度门第二轮执行器 —— PREREG_breadth_round2_basis_2026-08-09 (FROZEN bac67648, 03:41:45Z)

顺序按预注册: 关三先跑(最便宜且最可能杀死候选) → 关一 → 关二。
记账: 实盘同构 cap99+demean → risk_budget(α.5 λ1.0) → l1(单位 gross)。
"""
import sys, json, time, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
import engine.replay_fullhist as RF
from engine.signal_chain import SignalChain, _rank_centered, _l1
from engine.funding_risk import FundingLegRiskControl
from engine.vol_gate import VolGate
from engine.netting import LEG_CADENCE_H

LIVE3 = {"king": 0.5952380952380952, "s2": 0.20238095238095238, "funding": 0.20238095238095238, "size": 0.0}
WPROBE = [0.05, 0.10]
SEEDS = [0, 1, 2, 3, 4]
COSTS = [3.63, 5.80]
RB = {"alpha": 0.5, "lambda": 1.0}
BASIS_CAD = 8                      # 预注册: 与在役 funding 腿同
KING = "/mnt/storage/private/work_hsy/probe_artifacts/king_pred_newgen.npz"
S2   = "/mnt/storage/private/work_hsy/probe_artifacts/s2_pred_newgen.npz"
BAS  = "/mnt/storage/private/work_hsy/probe_artifacts/basis_premium_1h.npz"
OUT  = "/mnt/storage/private/work_hsy/probe_artifacts/breadth2.json"

t0 = time.time()
src = RF.get_src(None, KING, S2)
anchors, yr = RF._all_anchors(src)
N = src.N; RVOL_I = src.ch.index("rvol_24h")

# ── basis 对齐到引擎网格 ────────────────────────────────────────────────────
z = np.load(BAS, allow_pickle=True)
bts = z["ts_hour"].astype(np.int64); bsym = [str(x) for x in z["symbols"]]; PREM = z["PREM"].astype(np.float64)
ti_of = {int(t): i for i, t in enumerate(bts)}
col_of = {s: j for j, s in enumerate(bsym)}
cols = np.array([col_of.get(s, -1) for s in src.symbols])
rows = np.array([ti_of.get(int(t), -1) for t in src.ts])
BASIS = np.full((src.T, N), np.nan)
ok_r = rows >= 0; ok_c = cols >= 0
BASIS[np.ix_(ok_r, ok_c)] = PREM[np.ix_(rows[ok_r], cols[ok_c])]
print(f"[A] basis 对齐: 时间命中 {ok_r.mean():.3f} 符号命中 {ok_c.mean():.3f} "
      f"锚点上有限占比 {np.isfinite(BASIS[anchors]).mean():.3f}", flush=True)

disp_ref = FundingLegRiskControl.calibrate_dispersion(src, anchors)
frc = FundingLegRiskControl(winsor_z=4.0, name_cap=0.15, disp_gate_z=4.0, disp_shrink=0.3, disp_ref=disp_ref)
chain = SignalChain(src, weights=LIVE3, funding_mode="rank", vol_gate=VolGate(src),
                    funding_risk=frc, pos_cap_pct=99.0)
chain.calibrator = None
cad = dict(LEG_CADENCE_H)


def lsq_resid(y, x):
    """逐锚横截面: y 对 [1, x] 的最小二乘残差。"""
    ok = np.isfinite(y) & np.isfinite(x)
    r = np.full_like(y, np.nan)
    if ok.sum() < 5:
        return r
    X = np.column_stack([np.ones(ok.sum()), x[ok]])
    b, *_ = np.linalg.lstsq(X, y[ok], rcond=None)
    r[ok] = y[ok] - X @ b
    return r


# ── Phase A: 现有三腿 + 两个候选 + 候选的同槽位安慰剂 ───────────────────────
CANDS = ["C1", "C2"]
VARS = ["real"] + [f"sh{s}" for s in SEEDS]
rngs = {f"sh{s}": np.random.default_rng(2000 + s) for s in SEEDS}
LK = ["king", "s2", "funding"]
held = {k: np.zeros(N) for k in LK}
cheld = {c: {v: np.zeros(N) for v in VARS} for c in CANDS}
HELD = np.zeros((len(anchors), 3, N))
CAND = {c: {v: np.zeros((len(anchors), N)) for v in VARS} for c in CANDS}
M, RET, RVOL = [], [], []
frc.n_gated = 0
for i, t in enumerate(anchors):
    ti = int(t); legpos, m = chain.leg_positions(ti)
    for j, k in enumerate(LK):
        if i == 0 or (ti % cad[k] == 0):
            new = np.zeros(N); new[m] = legpos[k]; held[k] = new
        HELD[i, j] = held[k]
    if i == 0 or (ti % BASIS_CAD == 0):
        b_raw = BASIS[ti, m]
        f_raw = src.CH[ti, m, src.fund_idx].astype(np.float64)
        b_r = _rank_centered(b_raw); f_r = _rank_centered(f_raw)
        sig = {"C1": -1.0 * b_r,
               "C2": -1.0 * _rank_centered(lsq_resid(b_r, f_r))}
        for c in CANDS:
            for v in VARS:
                s_ = sig[c] if v == "real" else rngs[v].permutation(sig[c])
                new = np.zeros(N); new[m] = _l1(s_); cheld[c][v] = new
    for c in CANDS:
        for v in VARS:
            CAND[c][v][i] = cheld[c][v]
    M.append(m); RET.append(src.Y4[ti, m]); RVOL.append(src.CH[ti, m, RVOL_I].astype(np.float64))
DAY = (src.ts[anchors] // (1000*3600*24)).astype(np.int64)
print(f"[A] done {time.time()-t0:.0f}s", flush=True)


def rb(s_, rvol):
    a, l = RB["alpha"], RB["lambda"]
    v = np.asarray(rvol, float); fin = np.isfinite(v) & (v > 0)
    if not fin.any():
        return s_
    med = float(np.median(v[fin]))
    if med <= 0:
        return s_
    v = np.where(fin, v, med)
    w = np.sign(s_) * np.abs(s_) ** a / np.power(v / med, l)
    return w - w.mean()


def run(cand=None, variant="real", w_c=0.0, apply_rb=True):
    """cand=None ⇒ 基线书。cand 给定 ⇒ 候选以 w_c 并入, 其余三腿按比例缩到 (1-w_c)。"""
    base_w = np.array([LIVE3["king"], LIVE3["s2"], LIVE3["funding"]]) * (1.0 - w_c)
    prev = np.zeros(N); pnl = np.zeros(len(anchors)); turn = np.zeros(len(anchors))
    ric = np.full(len(anchors), np.nan)
    for i in range(len(anchors)):
        m = M[i]
        combo = base_w @ HELD[i]
        if cand:
            combo = combo + w_c * CAND[cand][variant][i]
        act = combo[m]
        shaped = rb(chain.shape_position(act), RVOL[i]) if apply_rb else chain.shape_position(act)
        g = float(np.abs(shaped).sum())
        if g > 1e-12:
            shaped = shaped / g
        net = np.zeros(N); net[m] = shaped
        r = RET[i]; ok = np.isfinite(r)
        pnl[i] = float(np.nansum(shaped[ok] * r[ok]))
        turn[i] = 0.0 if i == 0 else float(np.abs(net - prev).sum())
        if ok.sum() >= 5:
            a_ = pd.Series(shaped[ok]).rank().values; b_ = pd.Series(r[ok]).rank().values
            ric[i] = float(np.corrcoef(a_, b_)[0, 1])
        prev = net
    return pnl, turn, ric


def solo(cand, variant="real"):
    """候选单独成书(单位 gross), 用于关三的逐锚净额。"""
    out = np.zeros(len(anchors))
    for i in range(len(anchors)):
        m = M[i]; p = CAND[cand][variant][i][m]
        g = float(np.abs(p).sum())
        if g > 1e-12:
            p = p / g
        r = RET[i]; ok = np.isfinite(r)
        out[i] = float(np.nansum(p[ok] * r[ok]))
    return out


def leg_solo(j):
    out = np.zeros(len(anchors))
    for i in range(len(anchors)):
        m = M[i]; p = HELD[i, j][m]
        g = float(np.abs(p).sum())
        if g > 1e-12:
            p = p / g
        r = RET[i]; ok = np.isfinite(r)
        out[i] = float(np.nansum(p[ok] * r[ok]))
    return out


R = {"prereg_sha": "bac676484df930afc861e14970f1fd847c0cc55bd317ebb3d33ba20e67a93887",
     "frozen": "2026-08-09T03:41:45Z", "anchors": int(len(anchors)), "gates": {}}

# ═══ 关三 先跑(预注册顺序: 最便宜且最可能杀死候选) ═══
print("\n═══ 关三 · 正交性 (|ρ| < 0.3 vs king/s2/funding) ═══")
legs_pnl = {k: leg_solo(j) for j, k in enumerate(LK)}
R["gates"]["G3"] = {}
for c in CANDS:
    cp = solo(c)
    rho = {}
    for k, v in legs_pnl.items():
        ok = np.isfinite(cp) & np.isfinite(v)
        rho[k] = float(np.corrcoef(cp[ok], v[ok])[0, 1])
    mx = max(abs(x) for x in rho.values())
    R["gates"]["G3"][c] = {"rho": {k: round(v, 4) for k, v in rho.items()},
                           "max_abs": round(mx, 4), "pass": bool(mx < 0.3)}
    print(f"  {c}: " + "  ".join(f"{k} {v:+.4f}" for k, v in rho.items()) +
          f"   max|ρ| {mx:.4f}  ⇒ {'PASS' if mx < 0.3 else 'FAIL'}", flush=True)

survivors = [c for c in CANDS if R["gates"]["G3"][c]["pass"]]
print(f"\n关三幸存: {survivors if survivors else '【无】'}", flush=True)

# ═══ 关一 + 关二 (仅对关三幸存者; 但 C1 的关三读数无论如何都要报) ═══
def sh(x):  return RF._dsharpe(x)
def dayagg(pnl, turn, c):
    return pd.DataFrame({"day": DAY, "yr": yr, "n": pnl - turn*c*1e-4}).groupby("day").agg(
        n=("n", "sum"), yr=("yr", "first")).reset_index()
def boot(a, b, nb=4000, bl=5):
    rng = np.random.default_rng(4242); n = len(a); nb_ = int(np.ceil(n/bl)); o = np.empty(nb)
    for k in range(nb):
        st = rng.integers(0, max(n-bl, 1), size=nb_)
        idx = (st[:, None] + np.arange(bl)[None, :]).ravel()[:n]; idx = idx[idx < n]
        o[k] = sh(a[idx]) - sh(b[idx])
    return float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))
def boot_mean(d, nb=4000, bl=5):
    rng = np.random.default_rng(4242); n = len(d); nb_ = int(np.ceil(n/bl)); o = np.empty(nb)
    for k in range(nb):
        st = rng.integers(0, max(n-bl, 1), size=nb_)
        idx = (st[:, None] + np.arange(bl)[None, :]).ravel()[:n]; idx = idx[idx < n]
        o[k] = np.nanmean(d[idx])
    return float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))

bp, bt, bric = run(None)
R["baseline"] = {"rank_ic": round(float(np.nanmean(bric)), 5),
                 "sharpe": {str(c): round(sh(dayagg(bp, bt, c)["n"].values), 4) for c in COSTS}}
print(f"\n基线书: rank-IC {R['baseline']['rank_ic']:+.5f}  " +
      "  ".join(f"Sh@{c} {R['baseline']['sharpe'][str(c)]:+.4f}" for c in COSTS), flush=True)

R["gates"]["G1G2"] = {}
for c in CANDS:
    R["gates"]["G1G2"][c] = {}
    for w in WPROBE:
        rp, rt, rric = run(c, "real", w)
        dic = np.nanmean(rric - bric)
        lo_i, hi_i = boot_mean((rric - bric)[np.isfinite(rric - bric)])
        pl = [run(c, f"sh{s}", w) for s in SEEDS]
        dic_pl = [float(np.nanmean(p[2] - bric)) for p in pl]
        row = {"dIC": round(float(dic), 6), "dIC_CI": [round(lo_i, 6), round(hi_i, 6)],
               "dIC_placebo": [round(x, 6) for x in dic_pl], "by_cost": {}}
        for cc in COSTS:
            db = dayagg(bp, bt, cc); dr = dayagg(rp, rt, cc)
            dsh = sh(dr["n"].values) - sh(db["n"].values)
            lo, hi = boot(dr["n"].values, db["n"].values)
            dsh_pl = [sh(dayagg(p[0], p[1], cc)["n"].values) - sh(db["n"].values) for p in pl]
            row["by_cost"][str(cc)] = {"dSharpe": round(dsh, 4), "CI": [round(lo, 4), round(hi, 4)],
                                       "placebo_mean": round(float(np.mean(dsh_pl)), 4),
                                       "corrected": round(dsh - float(np.mean(dsh_pl)), 4)}
        R["gates"]["G1G2"][c][str(w)] = row
        print(f"  {c} w={w}: 关一 dIC {dic:+.5f} CI[{lo_i:+.5f},{hi_i:+.5f}] "
              f"安慰剂均值 {np.mean(dic_pl):+.5f} | " +
              " ".join(f"关二@{cc}: dSh {row['by_cost'][str(cc)]['dSharpe']:+.4f} "
                       f"CI[{row['by_cost'][str(cc)]['CI'][0]:+.4f},{row['by_cost'][str(cc)]['CI'][1]:+.4f}]"
                       for cc in COSTS), flush=True)

json.dump(R, open(OUT, "w"), indent=1)
print(f"\n[done] {time.time()-t0:.0f}s -> {OUT}\nBREADTH2_DONE")
