"""空头侧规则 · 4 年离线回放
预注册 PREREG_short_side_rule_2026-08-09  FROZEN d89db4aa… @ 13:28:16Z
G1 毛额 · G2 随机安慰剂(5种子) · G3 反向对照 · G4 逐年 ≥80% 同号 · 净额双档必报

★ 单次连接内跑完, 不反复敲 jpline。
★ 口径: 实盘同构(cap99+demean → risk_budget α.5λ1.0 → l1), 规则插在 l1 之前。
★ trailing 24h 排序键 = 面板 mom_24h 通道(因果, 与训练同源)。
"""
import sys, json, time, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
import engine.replay_fullhist as RF
from engine.signal_chain import SignalChain, _l1
from engine.funding_risk import FundingLegRiskControl
from engine.vol_gate import VolGate
from engine.netting import LEG_CADENCE_H

PD = "/mnt/storage/private/work_hsy/probe_artifacts"
LIVE3 = {"king": 0.5952380952380952, "s2": 0.20238095238095238, "funding": 0.20238095238095238, "size": 0.0}
COSTS = [3.115, 5.80]
RB = {"alpha": 0.5, "lambda": 1.0}
THR = 0.40                      # ★ 冻结, 不在本次搜索
SEEDS = [0, 1, 2, 3, 4]
OUT = f"{PD}/shortrule_replay.json"

t0 = time.time()
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
anchors, yr = RF._all_anchors(src)
N = src.N
RVOL_I = src.ch.index("rvol_24h")
MOM_I = src.ch.index("mom_24h")
print(f"[A] N={N} anchors={len(anchors)}  mom_24h ch={MOM_I}", flush=True)
disp_ref = FundingLegRiskControl.calibrate_dispersion(src, anchors)
frc = FundingLegRiskControl(winsor_z=4.0, name_cap=0.15, disp_gate_z=4.0, disp_shrink=0.3, disp_ref=disp_ref)
chain = SignalChain(src, weights=LIVE3, funding_mode="rank", vol_gate=VolGate(src),
                    funding_risk=frc, pos_cap_pct=99.0)
chain.calibrator = None
cad = dict(LEG_CADENCE_H)
LK = ["king", "s2", "funding"]
held = {k: np.zeros(N) for k in LK}
HELD = np.zeros((len(anchors), 3, N))
M, RET, RVOL, MOM = [], [], [], []
frc.n_gated = 0
for i, t in enumerate(anchors):
    ti = int(t); lp, m = chain.leg_positions(ti)
    for j, k in enumerate(LK):
        if i == 0 or (ti % cad[k] == 0):
            new = np.zeros(N); new[m] = lp[k]; held[k] = new
        HELD[i, j] = held[k]
    M.append(m); RET.append(src.Y4[ti, m])
    RVOL.append(src.CH[ti, m, RVOL_I].astype(np.float64))
    MOM.append(src.CH[ti, m, MOM_I].astype(np.float64))
DAY = (src.ts[anchors] // (1000*3600*24)).astype(np.int64)
print(f"[A] done {time.time()-t0:.0f}s", flush=True)


def rb(s_, rvol):
    a, l = RB["alpha"], RB["lambda"]
    v = np.asarray(rvol, float); fin = np.isfinite(v) & (v > 0)
    if not fin.any(): return s_
    med = float(np.median(v[fin]))
    if med <= 0: return s_
    v = np.where(fin, v, med)
    w = np.sign(s_) * np.abs(s_)**a / np.power(v/med, l)
    return w - w.mean()


def run(mode, seed=0):
    wv = np.array([LIVE3[k] for k in LK]); rng = np.random.default_rng(seed)
    prev = np.zeros(N); pnl = np.zeros(len(anchors)); turn = np.zeros(len(anchors))
    ric = np.full(len(anchors), np.nan)
    for i in range(len(anchors)):
        m = M[i]
        shaped = rb(chain.shape_position((wv @ HELD[i])[m]), RVOL[i])
        if mode != "none":
            sh = shaped < 0
            mo = MOM[i]
            ok = sh & np.isfinite(mo)
            if ok.sum() >= 5:
                idx = np.where(ok)[0]; k = int(round(THR*len(idx)))
                if k > 0:
                    if mode == "rule":   pick = idx[np.argsort(mo[idx])[:k]]      # 最跌
                    elif mode == "anti": pick = idx[np.argsort(-mo[idx])[:k]]     # 最涨
                    else:                pick = rng.choice(idx, k, replace=False)  # 随机
                    shaped = shaped.copy(); shaped[pick] = 0.0
                    shaped = shaped - shaped.mean()
        g = float(np.abs(shaped).sum())
        if g > 1e-12: shaped = shaped/g
        net = np.zeros(N); net[m] = shaped
        r = RET[i]; okr = np.isfinite(r)
        pnl[i] = float(np.nansum(shaped[okr]*r[okr]))
        turn[i] = 0.0 if i == 0 else float(np.abs(net-prev).sum())
        if okr.sum() >= 5:
            ric[i] = float(np.corrcoef(pd.Series(shaped[okr]).rank(), pd.Series(r[okr]).rank())[0, 1])
        prev = net
    return pnl, turn, ric


def boot(a, b, nb=3000, bl=5):
    d = a - b; rng = np.random.default_rng(99); n = len(d); nb_ = int(np.ceil(n/bl)); o = np.empty(nb)
    for k in range(nb):
        st = rng.integers(0, max(n-bl, 1), size=nb_)
        ix = (st[:, None]+np.arange(bl)[None, :]).ravel()[:n]; ix = ix[ix < n]
        o[k] = d[ix].mean()*1e4
    return float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))


print("\n臂            毛bps/锚   ΔIC      换手     " + "  ".join(f"净@{c}" for c in COSTS))
print("-"*78)
res = {}
p0, t0_, r0 = run("none")
yrs = (int(src.ts[anchors[-1]])-int(src.ts[anchors[0]]))/(1000*3600*24*365.25)
def line(nm, p, t, r):
    g = p.mean()*1e4; tn = t.sum()/len(t)
    print(f"{nm:14s} {g:+9.3f} {np.nanmean(r):+8.5f} {tn:8.4f}  " +
          "  ".join(f"{g-tn*2*c:+8.3f}" for c in COSTS), flush=True)
    return {"gross_bps": round(float(g), 4), "ic": round(float(np.nanmean(r)), 5),
            "turn": round(float(tn), 4),
            **{f"net@{c}": round(float(g-tn*2*c), 4) for c in COSTS}}
res["base"] = line("现状", p0, t0_, r0)
p1, t1, r1 = run("rule");  res["rule"] = line("规则(剔最跌40%)", p1, t1, r1)
pa, ta, ra = run("anti");  res["anti"] = line("反向(剔最涨40%)", pa, ta, ra)
pls = []
for s in SEEDS:
    ps, ts_, rs = run("rand", seed=s); pls.append(ps)
    res[f"rand{s}"] = line(f"随机 seed{s}", ps, ts_, rs)

lo, hi = boot(p1, p0)
plm = np.mean(pls, axis=0)
lo2, hi2 = boot(p1, plm)
print(f"\n═══ 判据 ═══")
print(f"  G1 毛额: Δ={((p1-p0).mean()*1e4):+.3f} bps  CI95[{lo:+.3f},{hi:+.3f}]  ⇒ {'PASS' if lo>0 else 'FAIL'}")
print(f"  G2 vs 安慰剂: Δ={((p1-plm).mean()*1e4):+.3f} bps  CI95[{lo2:+.3f},{hi2:+.3f}]  ⇒ {'PASS' if lo2>0 else 'FAIL'}")
da = (pa-p0).mean()*1e4
print(f"  G3 反向须为负: Δ={da:+.3f} bps  ⇒ {'PASS' if da < 0 else 'FAIL'}")
dfy = pd.DataFrame({"yr": yr, "d": (p1-p0)*1e4}).groupby("yr").d.mean()
npos = int((dfy >= 0).sum())
print(f"  G4 逐年: {dict(dfy.round(3))}  ≥0 的 {npos}/{len(dfy)}  ⇒ {'PASS' if npos/len(dfy) >= 0.8 else 'FAIL'}")
res["gates"] = {"G1": bool(lo > 0), "G2": bool(lo2 > 0), "G3": bool(da < 0),
                "G4": bool(npos/len(dfy) >= 0.8), "per_year": {int(k): round(float(v), 4) for k, v in dfy.items()}}
json.dump(res, open(OUT, "w"), indent=1)
print(f"\n[done] {time.time()-t0:.0f}s -> {OUT}\nSHORTRULE_DONE")
