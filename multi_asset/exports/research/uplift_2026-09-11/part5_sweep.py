#!/usr/bin/env python3
"""Part 5: alpha/band sweep on the DEPLOYED combo book, done properly — kc and fc legs are
inverted SEPARATELY (each is its own chain() with its own EMA state and its own band), then
re-smoothed at (alpha', band') and recombined 0.55/0.45, unit-grossed, scored, and costed.
Cost model = the producer's own COST_B scenario, calibrated against its logged cost_bps."""
import os, json, glob, time
import numpy as np
exec(open("/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/smooth_latency_core.py").read().split("# ---- 1.")[0])

# ---- calibrate the turnover cost from the producer's own log ----
sig = {}
for ln in open(f"{WS}/shadow_log.jsonl"):
    try: d = json.loads(ln)
    except Exception: continue
    if d.get("e") == "signal": sig[int(d["anchor_ts"])] = d
tv = np.array([d["turnover"] for d in sig.values()]); cb = np.array([d["cost_bps"] for d in sig.values()])
ok = tv > 1e-9
COST_PER_TURN = float(np.sum(cb[ok]) / np.sum(tv[ok]))
print(f"[COST CALIB] producer logged: mean turnover {tv.mean():.5f}/anchor, mean cost {cb.mean():.4f} bps/anchor "
      f"=> {COST_PER_TURN:.3f} bps per 1.0 of |dw| (n={ok.sum()})")

def build_leg(S, anchors):
    A = [a for a in anchors if (a - 14400) in S]
    T = len(A); EX = np.full((T, NW), np.nan); HH = np.zeros((T, NW)); SS = np.zeros((T, NW))
    for i, a in enumerate(A):
        H = S[a - 14400]; sm = S[a]; HH[i] = H; SS[i] = sm
        d = sm - H
        forced = (sm == 0.0) & (np.abs(H) > 1e-12)
        moved = (np.abs(d) > 1e-12) & (~forced)
        EX[i, moved] = H[moved] + d[moved] / ALPHA
        EX[i, forced] = 0.0
    return A, EX, HH, SS

def fill_interp(EX):
    T, N = EX.shape; out = EX.copy(); idx = np.arange(T)
    for j in range(N):
        col = EX[:, j]; k = np.isfinite(col)
        if k.sum() == 0: out[:, j] = 0.0
        elif k.sum() == 1: out[:, j] = col[k][0]
        else: out[:, j] = np.interp(idx, idx[k], col[k])
    return out

def renorm(TG, HH):
    out = TG.copy()
    for i in range(out.shape[0]):
        act = (np.abs(out[i]) > 1e-12) | (np.abs(HH[i]) > 1e-12)
        if act.sum() == 0: continue
        v = out[i].copy(); v[act] -= v[act].mean()
        g = np.abs(v).sum()
        if g > 1e-12: v /= g
        out[i] = v
    return out

AK, EXK, HHK, SSK = build_leg(SKC, sorted(SKC))
AF, EXF, HHF, SSF = build_leg(SFC, sorted(SFC))
assert AK == AF, "kc/fc anchor sets differ"
keep = [i for i, a in enumerate(AK) if y4_of(a) is not None]
A = [AK[i] for i in keep]
EXK, HHK, SSK = EXK[keep], HHK[keep], SSK[keep]
EXF, HHF, SSF = EXF[keep], HHF[keep], SSF[keep]
print(f"\n[COMBO LEGS] n_anchors={len(A)}  {time.strftime('%m-%d %H',time.gmtime(A[0]))}..{time.strftime('%m-%d %H',time.gmtime(A[-1]))}")
for nm_, EX, HH in (("kc", EXK, HHK), ("fc", EXF, HHF)):
    e1 = np.where(np.isfinite(EX), EX, HH); e2 = fill_interp(EX)
    print(f"  {nm_}: exact cells/anchor {np.isfinite(EX).sum(1).mean():.1f}; sum|tgt| E1 {np.abs(e1).sum(1).mean():.4f} "
          f"E2 {np.abs(e2).sum(1).mean():.4f}   (TRUTH 1.0000)")

EST = {}
EST["E1"] = (renorm(np.where(np.isfinite(EXK), EXK, HHK), HHK), renorm(np.where(np.isfinite(EXF), EXF, HHF), HHF))
EST["E2"] = (renorm(fill_interp(EXK), HHK), renorm(fill_interp(EXF), HHF))
FK = (SSK == 0.0) & (np.abs(HHK) > 1e-12); FF = (SSF == 0.0) & (np.abs(HHF) > 1e-12)

Y = [np.nan_to_num(y4_of(a), nan=0.0) for a in A]

def run(TK, TF, alpha, band):
    Hk = HHK[0].copy(); Hf = HHF[0].copy()
    bps = []; tur = []
    for i in range(len(A)):
        for (H, T, F) in ((Hk, TK, FK), (Hf, TF, FF)):
            pass
        nk = Hk + alpha * (TK[i] - Hk); tk_ = nk - Hk
        nk = np.where(np.abs(tk_) < band, Hk, nk); nk = np.where(FK[i], 0.0, nk)
        nf = Hf + alpha * (TF[i] - Hf); tf_ = nf - Hf
        nf = np.where(np.abs(tf_) < band, Hf, nf); nf = np.where(FF[i], 0.0, nf)
        raw_prev = 0.55 * Hk + 0.45 * Hf
        raw = 0.55 * nk + 0.45 * nf
        g = np.abs(raw).sum(); gp = np.abs(raw_prev).sum()
        w = raw / g if g > 1e-12 else raw
        wp = raw_prev / gp if gp > 1e-12 else raw_prev
        bps.append(float((w * Y[i]).sum() * 1e4))
        tur.append(float(np.abs(w - wp).sum()))
        Hk, Hf = nk, nf
    return np.array(bps), np.array(tur)

# observed book, unit-gross caliber
obs = np.array([float((SMC[a] / max(np.abs(SMC[a]).sum(), 1e-12) * Y[i]).sum() * 1e4) for i, a in enumerate(A)])
obs_t = np.array([float(np.abs(SMC[a]/max(np.abs(SMC[a]).sum(),1e-12) - SMC[a-14400]/max(np.abs(SMC[a-14400]).sum(),1e-12)).sum()) for a in A if (a-14400) in SMC])
print(f"\n[OBSERVED deployed combo, unit gross] n={len(obs)} mean {obs.mean():+.4f} bps/anchor sd {obs.std(ddof=1):.3f} "
      f"turnover {obs_t.mean():.4f}")

# ---- day aggregation for tail metrics (6 anchors/day, UTC) ----
days = np.array([time.strftime("%Y-%m-%d", time.gmtime(a)) for a in A])
ud = sorted(set(days))
def daily(b):
    return np.array([b[days == d].sum() for d in ud])

def tails(b, t, lab):
    dd = daily(b - COST_PER_TURN * t)            # net of modelled turnover cost, bps of gross/day
    m = dd.mean(); s = dd.std(ddof=1)
    q = np.percentile(dd, 5)
    cv = dd[dd <= np.percentile(dd, 20)].mean()   # CVaR20 (n=17 days -> 5% is 1 obs)
    return dict(lab=lab, mean_bps_anchor=b.mean()-COST_PER_TURN*t.mean(), gross_bps=b.mean(),
                cost_bps=COST_PER_TURN*t.mean(), turnover=t.mean(),
                day_mean=m, day_sd=s, sharpe_ann=m/s*np.sqrt(365) if s>0 else np.nan,
                worst_day=dd.min(), q05=q, cvar20=cv, ndays=len(dd))

print(f"\n{'arm':<26s}{'gross':>8s}{'cost':>7s}{'net':>8s}{'turn':>7s} | {'day_mu':>8s}{'day_sd':>8s}{'Sh_ann':>7s}{'worst':>9s}{'CVaR20':>9s}")
print(f"{'-'*26}{'-'*30} | {'-'*41}")
res = {}
r = tails(obs, np.r_[obs_t[0], obs_t] if len(obs_t)<len(obs) else obs_t, "OBSERVED deployed")
print(f"{r['lab']:<26s}{r['gross_bps']:>8.3f}{r['cost_bps']:>7.3f}{r['mean_bps_anchor']:>8.3f}{r['turnover']:>7.4f} | "
      f"{r['day_mean']:>8.2f}{r['day_sd']:>8.2f}{r['sharpe_ann']:>7.2f}{r['worst_day']:>9.2f}{r['cvar20']:>9.2f}")
for est in ("E1", "E2"):
    TK, TF = EST[est]
    for alpha, band, lab in ((0.1, BAND, "deployed a=.10 b=2.5e-4"), (0.1, 0.0, "a=.10 band=0"),
                             (0.2, BAND, "a=.20 b=2.5e-4 (2x fast)"), (0.2, 0.0, "a=.20 band=0"),
                             (0.35, 0.0, "a=.35 band=0"), (0.5, 0.0, "a=.50 band=0"),
                             (1.0, 0.0, "a=1.0 band=0 (NO smooth)"), (0.05, BAND, "a=.05 (2x slower)")):
        b, t = run(TK, TF, alpha, band)
        r = tails(b, t, f"[{est}] {lab}")
        res[r['lab']] = r
        print(f"{r['lab']:<26s}{r['gross_bps']:>8.3f}{r['cost_bps']:>7.3f}{r['mean_bps_anchor']:>8.3f}{r['turnover']:>7.4f} | "
              f"{r['day_mean']:>8.2f}{r['day_sd']:>8.2f}{r['sharpe_ann']:>7.2f}{r['worst_day']:>9.2f}{r['cvar20']:>9.2f}")
json.dump({k: {kk: (float(vv) if isinstance(vv,(int,float,np.floating)) else vv) for kk,vv in v.items()} for k,v in res.items()},
          open(f"{OUT}/sweep_combo.json","w"), indent=1)
print(f"\ncost/turnover exchange rate used: {COST_PER_TURN:.3f} bps per 1.0 |dw|")
