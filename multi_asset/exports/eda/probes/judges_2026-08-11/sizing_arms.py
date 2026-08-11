"""仓位映射规则五臂 —— 幅度到底带不带信息。
预注册 PREREG_value_space_and_sizing_2026-08-09  FROZEN ae1190cf… @ 14:10:08Z
S0 现状 |s|^0.5 · S1 纯秩 · S2 线性 · S3 |s|^0.25 · S4 分位桶20%
G1 毛额CI下界>0 · G2 净额双档均须≥S0 · G3 逐年≥80% · G4 机制自洽(压/放同向为正 ⇒ 全不采纳)
附: 未整形 DL 合成的长历史 rank-IC 基准(给 0.0953 定价)+ 值空间基准。
"""
import sys, json, time, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
import engine.replay_fullhist as RF
from engine.signal_chain import SignalChain
from engine.funding_risk import FundingLegRiskControl
from engine.vol_gate import VolGate
from engine.netting import LEG_CADENCE_H

PD = "/mnt/storage/private/work_hsy/probe_artifacts"
LIVE3 = {"king": 0.5952380952380952, "s2": 0.20238095238095238,
         "funding": 0.20238095238095238, "size": 0.0}
COSTS = [3.115, 5.80]
RB = {"alpha": 0.5, "lambda": 1.0}
OUT = f"{PD}/sizing_v2.json"

t0 = time.time()
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src)
N = src.N
RVI = src.ch.index("rvol_24h")
dref = FundingLegRiskControl.calibrate_dispersion(src, a)
frc = FundingLegRiskControl(winsor_z=4.0, name_cap=0.15, disp_gate_z=4.0, disp_shrink=0.3, disp_ref=dref)
chain = SignalChain(src, weights=LIVE3, funding_mode="rank", vol_gate=VolGate(src),
                    funding_risk=frc, pos_cap_pct=99.0)
chain.calibrator = None
cad = dict(LEG_CADENCE_H)
LK = ["king", "s2", "funding"]
held = {k: np.zeros(N) for k in LK}
H = np.zeros((len(a), 3, N))
M, RET, RV = [], [], []
KRAW, SRAW = [], []
for i, t in enumerate(a):
    ti = int(t); lp, m = chain.leg_positions(ti)
    for j, k in enumerate(LK):
        if i == 0 or (ti % cad[k] == 0):
            nw = np.zeros(N); nw[m] = lp[k]; held[k] = nw
        H[i, j] = held[k]
    M.append(m); RET.append(src.Y4[ti, m]); RV.append(src.CH[ti, m, RVI].astype(np.float64))
    KRAW.append(src.king[ti, m].astype(np.float64)); SRAW.append(src.s2[ti, m].astype(np.float64))
print(f"[build] {len(a)} 锚 N={N}  {time.time()-t0:.0f}s", flush=True)

# ═══════ 附: 未整形 DL 合成基准(秩 + 值), 给 0.0953 定价 ═══════
def z(v):
    s = np.nanstd(v)
    return (v - np.nanmean(v)) / s if s > 0 else v * np.nan
uic = np.full(len(a), np.nan); upi = np.full(len(a), np.nan)
for i in range(len(a)):
    k, s_, r = KRAW[i], SRAW[i], RET[i]
    ok = np.isfinite(k) & np.isfinite(s_) & np.isfinite(r)
    if ok.sum() < 10: continue
    c = z(k[ok]) + z(s_[ok])
    uic[i] = float(np.corrcoef(pd.Series(c).rank(), pd.Series(r[ok]).rank())[0, 1])
    upi[i] = float(np.corrcoef(c, r[ok])[0, 1])
v = uic[np.isfinite(uic)]; p = upi[np.isfinite(upi)]
print("\n" + "═"*76)
print("附 · 未整形 DL 合成(equal-z king+s2)在 9821 锚上的基准")
print("═"*76)
print(f"  秩空间 rank-IC  均值 {v.mean():+.5f}  sd {v.std():.4f}  IC>0 {(v>0).mean():.4f}")
print(f"  值空间 Pearson  均值 {p.mean():+.5f}  sd {p.std():.4f}  >0 {(p>0).mean():.4f}")
roll = pd.Series(v).rolling(50).mean().dropna().values
print(f"  ★ 50 锚窗口均值 ≥ +0.0953 的历史频率 = {(roll>=0.0953).mean():.4f}  (窗口数 {len(roll)})")
print(f"     该分布 p50={np.percentile(roll,50):+.4f}  p90={np.percentile(roll,90):+.4f}  p99={np.percentile(roll,99):+.4f}")
rollp = pd.Series(p).rolling(50).mean().dropna().values
print(f"  ★ 值空间 50 锚窗口 p50={np.percentile(rollp,50):+.5f}  p10={np.percentile(rollp,10):+.5f}")

# ═══════ 五臂 ═══════
def rb(s_, rvol):
    al, lm = RB["alpha"], RB["lambda"]
    q = np.asarray(rvol, float); fin = np.isfinite(q) & (q > 0)
    if not fin.any(): return s_
    med = float(np.median(q[fin]))
    if med <= 0: return s_
    q = np.where(fin, q, med)
    w = np.sign(s_) * np.abs(s_)**al / np.power(q/med, lm)
    return w - w.mean()


def shape(raw, arm):
    """分数 → 仓位, 只改这一步。raw 已过 cap99+demean(chain.shape_position 的前半)。"""
    if arm == "S0":  return np.sign(raw) * np.abs(raw)**0.5
    if arm == "S2":  return raw.copy()
    if arm == "S3":  return np.sign(raw) * np.abs(raw)**0.25
    if arm == "S1":
        r = pd.Series(raw).rank().values.astype(float)
        u = (r - 1) / max(len(r) - 1, 1) * 2 - 1
        return u - u.mean()
    if arm == "S4":
        r = pd.Series(raw).rank(pct=True).values
        w = np.where(r >= 0.8, 1.0, np.where(r <= 0.2, -1.0, 0.0))
        return w - w.mean()
    raise ValueError(arm)


def run(arm):
    wv = np.array([LIVE3[k] for k in LK])
    prev = np.zeros(N); pnl = np.zeros(len(a)); trn = np.zeros(len(a))
    for i in range(len(a)):
        m = M[i]
        raw = chain.shape_position((wv @ H[i])[m])
        # chain.shape_position 已含 |.|^0.5; 除掉它拿回 cap 后的线性分数
        lin = np.sign(raw) * np.abs(raw)**2.0
        s_ = shape(lin, arm)
        w = rb(s_, RV[i])
        g = float(np.abs(w).sum())
        if g > 1e-12: w = w/g
        net = np.zeros(N); net[m] = w
        r = RET[i]; ok = np.isfinite(r)
        pnl[i] = float(np.nansum(w[ok]*r[ok]))
        trn[i] = 0.0 if i == 0 else float(np.abs(net-prev).sum())
        prev = net
    return pnl, trn


def boot(dd, nb=3000, bl=5):
    rng = np.random.default_rng(99); n = len(dd); k = int(np.ceil(n/bl)); o = np.empty(nb)
    for q in range(nb):
        st = rng.integers(0, max(n-bl, 1), size=k)
        ix = (st[:, None]+np.arange(bl)[None, :]).ravel()[:n]; ix = ix[ix < n]
        o[q] = dd[ix].mean()*1e4
    return float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))


print("\n" + "═"*76)
print("五臂(只改 分数→仓位 一步)")
print("═"*76)
print(f"{'臂':16s} {'毛bps':>9s} {'换手':>8s} " + " ".join(f"{'净@'+str(c):>9s}" for c in COSTS))
res = {}
P = {}
for arm, nm in [("S0", "S0 现状^0.5"), ("S1", "S1 纯秩"), ("S2", "S2 线性^1.0"),
                ("S3", "S3 ^0.25"), ("S4", "S4 分位桶20%")]:
    pn, tn = run(arm); P[arm] = pn
    g = pn.mean()*1e4; tt = tn.sum()/len(tn)
    print(f"{nm:16s} {g:+9.3f} {tt:8.4f} " + " ".join(f"{g-tt*2*c:+9.3f}" for c in COSTS), flush=True)
    res[arm] = {"gross": round(float(g), 4), "turn": round(float(tt), 4),
                **{f"net@{c}": round(float(g-tt*2*c), 4) for c in COSTS}}

print("\n" + "═"*76); print("判据"); print("═"*76)
for arm in ("S1", "S2", "S3", "S4"):
    dd = P[arm] - P["S0"]; lo, hi = boot(dd)
    g1 = lo > 0
    g2 = all(res[arm][f"net@{c}"] >= res["S0"][f"net@{c}"] for c in COSTS)
    dfy = pd.DataFrame({"y": yr, "d": dd*1e4}).groupby("y").d.mean()
    npos = int((dfy >= 0).sum()); g3 = npos/len(dfy) >= 0.8
    print(f"  {arm}: Δ毛={dd.mean()*1e4:+7.3f} CI95[{lo:+.3f},{hi:+.3f}] G1={'PASS' if g1 else 'FAIL'}  "
          f"G2(净额双档)={'PASS' if g2 else 'FAIL'}  G3 逐年 {npos}/{len(dfy)}={'PASS' if g3 else 'FAIL'}")
    print(f"       逐年 {dict(dfy.round(3))}")
    res[arm].update({"G1": bool(g1), "G2": bool(g2), "G3": bool(g3),
                     "delta_gross": round(float(dd.mean()*1e4), 4), "ci": [round(lo, 4), round(hi, 4)]})
comp = res["S1"]["delta_gross"] > 0 and res["S3"]["delta_gross"] > 0
expn = res["S2"]["delta_gross"] > 0
print(f"\n  G4 机制自洽: 压幅度(S1&S3)为正={comp}  放幅度(S2)为正={expn}  ⇒ "
      f"{'★同向为正 ⇒ 两假说皆不成立, 全不采纳' if comp and expn else 'OK(方向可分辨)'}")
res["G4_both_positive"] = bool(comp and expn)
res["unshaped_base"] = {"rank_ic": float(v.mean()), "pearson": float(p.mean()),
                        "p_ge_0953_50anchor": float((roll >= 0.0953).mean())}
json.dump(res, open(OUT, "w"), indent=1)

# ═══════ R · 风险预算三臂 (PREREG_risk_budget_relitigation 94fbcb86 @ 14:19:52Z) ═══════
print("\n" + "═"*76)
print("R · 风险预算三臂 —— 钱优先, 净夏普必报(它当初是拿 IC 换风险被接受的)")
print("═"*76)


def run_rb(alpha, lam):
    wv = np.array([LIVE3[k] for k in LK])
    prev = np.zeros(N); pnl = np.zeros(len(a)); trn = np.zeros(len(a)); hhi = np.zeros(len(a))
    for i in range(len(a)):
        m = M[i]
        sh = chain.shape_position((wv @ H[i])[m])       # 含 |.|^0.5, 与在役同构
        if not (alpha == 1.0 and lam == 0.0):
            q = np.asarray(RV[i], float); fin = np.isfinite(q) & (q > 0)
            med = float(np.median(q[fin])) if fin.any() else 0.0
            if med > 0:
                q = np.where(fin, q, med)
                sh = np.sign(sh)*np.abs(sh)**alpha/np.power(q/med, lam)
                sh = sh - sh.mean()
        g = float(np.abs(sh).sum())
        if g > 1e-12: sh = sh/g
        net = np.zeros(N); net[m] = sh
        r = RET[i]; ok = np.isfinite(r)
        pnl[i] = float(np.nansum(sh[ok]*r[ok]))
        trn[i] = 0.0 if i == 0 else float(np.abs(net-prev).sum())
        hhi[i] = float((sh**2).sum()/max((np.abs(sh).sum()/len(sh))**2*len(sh), 1e-18))
        prev = net
    return pnl, trn, hhi


ANN = np.sqrt(6*365)
RES = {}
print(f"{'臂':22s} {'毛bps':>8s} {'换手':>7s} " +
      " ".join(f"{'净@'+str(c):>8s} {'夏普@'+str(c):>9s}" for c in COSTS) + f" {'HHI':>7s}")
for nm, al, lm in [("R-on 在役 α.5 λ1", 0.5, 1.0), ("R-off (λ=0)", 1.0, 0.0), ("R-half α.5 λ.5", 0.5, 0.5)]:
    pn, tn, hh = run_rb(al, lm)
    g = pn.mean()*1e4; tt = tn.sum()/len(tn)
    row = f"{nm:22s} {g:+8.3f} {tt:7.4f} "
    d = {"gross": round(float(g), 4), "turn": round(float(tt), 4), "hhi": round(float(hh.mean()), 4)}
    for c in COSTS:
        npn = pn*1e4 - tn*2*c
        sh_ = float(npn.mean()/npn.std(ddof=1)*ANN) if npn.std(ddof=1) > 0 else float("nan")
        row += f"{npn.mean():+8.3f} {sh_:+9.3f} "
        d[f"net@{c}"] = round(float(npn.mean()), 4); d[f"sharpe@{c}"] = round(sh_, 4)
    print(row + f"{hh.mean():7.3f}", flush=True)
    RES[nm] = d; RES[nm]["_pnl"] = pn; RES[nm]["_turn"] = tn

print("\n  判据 G1(钱, 主判): Δ(R-off − R-on)")
on = RES["R-on 在役 α.5 λ1"]; off = RES["R-off (λ=0)"]
dg = off["_pnl"] - on["_pnl"]; lo, hi = boot(dg)
print(f"    Δ毛 = {dg.mean()*1e4:+.3f} bps  CI95[{lo:+.3f},{hi:+.3f}]")
allc = True
for c in COSTS:
    dn = (off["_pnl"]*1e4 - off["_turn"]*2*c) - (on["_pnl"]*1e4 - on["_turn"]*2*c)
    l2, h2 = np.percentile([dn[np.random.default_rng(k).integers(0, len(dn), len(dn))].mean()
                            for k in range(1500)], [2.5, 97.5])
    tag = "R-off更赚" if l2 > 0 else ("R-on更赚" if h2 < 0 else "覆盖0")
    allc = allc and (l2 <= 0 <= h2)
    print(f"    Δ净@{c} = {dn.mean():+.3f} bps  CI95[{l2:+.3f},{h2:+.3f}]  ⇒ {tag}")
print(f"    ⇒ G1 {'判【中性】: 风险预算不是根因, 本门结束' if allc else '非中性, 进 G2'}")
print("\n  判据 G2(净夏普 —— 它当初被接受的理由):")
for c in COSTS:
    print(f"    @{c}:  R-on {on[f'sharpe@{c}']:+.3f}   R-off {off[f'sharpe@{c}']:+.3f}   "
          f"R-half {RES['R-half α.5 λ.5'][f'sharpe@{c}']:+.3f}   "
          f"⇒ {'关掉更好' if off[f'sharpe@{c}'] > on[f'sharpe@{c}'] else '★在役更好'}")
print(f"    HHI: R-on {on['hhi']:.3f}  R-off {off['hhi']:.3f}  (当初记录 2.075→1.274)")
dfy = pd.DataFrame({"y": yr, "d": (off["_pnl"]-on["_pnl"])*1e4}).groupby("y").d.mean()
print(f"\n  G3 逐年 Δ毛(off−on): {dict(dfy.round(3))}   ≥0 的 {int((dfy>=0).sum())}/{len(dfy)}")
for k in RES: RES[k].pop("_pnl", None); RES[k].pop("_turn", None)
res["risk_budget"] = RES
res["risk_budget_gates"] = {"G1_neutral": bool(allc),
                            "per_year": {int(x): round(float(y_), 4) for x, y_ in dfy.items()}}
json.dump(res, open(OUT, "w"), indent=1)
print(f"\n[done] {time.time()-t0:.0f}s -> {OUT}\nSIZING_DONE")
