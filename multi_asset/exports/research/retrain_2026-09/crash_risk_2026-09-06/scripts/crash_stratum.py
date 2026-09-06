"""crash_stratum.py — PREREG_crash_continuation_parabolic_stratum_2026-09-06 (Phase 2c): confirmatory test of the post-hoc stratum from §Phase 2b.
P = onset events whose name had a 3-day gain ≥ +20% at the anchor (feature r3d, rows E−863..E, causal; same definition as Phase 2b); Q = the other onset events.
Inputs: continuation/events_theta{5,8,12}.npz (Phase 2b event tables: I, J, K, fwd_delay5m, weight, value_bps), features.npz (r3d), phase0.npz (COH), 5m cache
(for the two P-layer placebos: mirror up-onset ≥ +θ of P-layer names; random time at non-event anchors of P-layer names with k drawn from the P-layer event k's).
Forward quantity = r(τ+5m → next anchor) (primary), also 1h/3h/12h; years 2024/2025/2026≤08-10; UTC-day-block bootstrap 2000 seed 20260905; P − Q difference
by day-block bootstrap of (mean_P − mean_Q); value bound (P events only) = Σ_events w·(−r(τ+5m→next) − 8.9 bps) per anchor, mean over 2024→26 anchors.
Frozen reading (§2): CONFIRM = θ8 P r(τ+5m→next) CI95 upper < 0 in ≥ 2 of 3 years AND in 2026 AND θ5 and θ12 P point estimates < 0 AND P-layer mirror placebo
not negative (CI upper > 0 or point ≥ 0) AND P − Q CI95 upper < 0 AND value ≥ +0.03 bps/anchor/gross with CI lower > 0; REJECT = θ8 P 2026 CI lower > −15 bps
OR mirror placebo significantly negative; else UNDECIDED. Family = 1 confirmatory + 6 post-hoc strata = 7 cells (expected false positives at one-sided 5% = 0.35)."""
import os, sys, json, time, calendar, hashlib
import numpy as np
ROOT = "/workspace/review_scratch/crash_risk"; OUTD = f"{ROOT}/continuation/stratum"; os.makedirs(OUTD, exist_ok=True); SELF = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
def T(s): return int(calendar.timegm(time.strptime(s, "%Y-%m-%d")))
CUT = T("2026-08-10") + 20 * 3600; NB = 2000; BSEED = 20260905; THETAS = (0.05, 0.08, 0.12); COST = 8.9; GAIN = 0.20
sys.path.insert(0, "/workspace")
from zload import zload
Z = zload("/workspace/data/dlnative_5m_wide829_f16_ext.npz", allow_pickle=True); CTS = Z["ts"].astype(np.int64); T0 = int(CTS[0]); r5 = np.asarray(Z["data"][:, :, 0], np.float32); del Z
TT = len(CTS); fin = np.isfinite(r5); LC = np.cumsum(np.where(fin, np.log1p(np.clip(r5, -0.99, None)), 0.0), 0, dtype=np.float64); del r5, fin
P0 = np.load(f"{ROOT}/data/phase0.npz", allow_pickle=True); COH = P0["COH"]; E_ts = P0["E_ts"].astype(np.int64); nA = len(E_ts); Ei = (E_ts - T0) // 300
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); days = E_ts // 86400
F = np.load(f"{ROOT}/data/features.npz", allow_pickle=True); PI = F["PI"]; PJ = F["PJ"]; NM = [str(n) for n in F["names"]]; R3D = np.full(COH.shape, np.nan, np.float32); R3D[PI, PJ] = np.asarray(F["X"], np.float32)[:, NM.index("r3d")]
PMASK = COH & (R3D >= GAIN)   # P-layer (anchor, name) cells: cohort names with 3-day gain ≥ +20% at the anchor
rng = np.random.default_rng(BSEED)
def fwd(tau, i, j, delay=1):
    a = tau + delay; out = np.full((len(tau), 4), np.nan)
    for c, h in enumerate((12, 36, None, 144)):
        b = (Ei[i] + 48) if h is None else (tau + h); ok = (b > a) & (b < TT); out[ok, c] = np.expm1(LC[b[ok], j[ok]] - LC[a[ok], j[ok]])
    return out
def collect(theta, mask, sign):
    I, J, K = [], [], []
    for i in range(nA):
        cj = np.where(mask[i])[0]
        if len(cj) == 0 or Ei[i] + 48 >= TT: continue
        cum = np.expm1(LC[Ei[i] + 1: Ei[i] + 49][:, cj] - LC[Ei[i], cj]); hit = (cum <= -theta) if sign < 0 else (cum >= theta); any_ = hit.any(0); k = hit.argmax(0) + 1
        I += [i] * int(any_.sum()); J += cj[any_].tolist(); K += k[any_].tolist()
    return np.array(I, int), np.array(J, int), np.array(K, int)
def boot_mean(x, d):
    ok = np.isfinite(x); x = x[ok]; d = d[ok]
    if len(x) < 10: return [None, None]
    ud, inv = np.unique(d, return_inverse=True); s1 = np.bincount(inv, x); c = np.bincount(inv).astype(float)
    g = np.random.default_rng(BSEED); idx = g.integers(0, len(ud), size=(NB, len(ud))); m = s1[idx].sum(1) / c[idx].sum(1); return [round(float(np.percentile(m, 2.5)), 1), round(float(np.percentile(m, 97.5)), 1)]
def boot_diff(xp, dp, xq, dq):
    """day-block bootstrap of mean_P − mean_Q: resample the union of days; each resample recomputes both means over the drawn days."""
    okp = np.isfinite(xp); okq = np.isfinite(xq); xp, dp, xq, dq = xp[okp], dp[okp], xq[okq], dq[okq]
    if len(xp) < 10 or len(xq) < 10: return [None, None]
    ud = np.unique(np.concatenate([dp, dq])); ip = np.searchsorted(ud, dp); iq = np.searchsorted(ud, dq)
    sp = np.bincount(ip, xp, minlength=len(ud)); cp = np.bincount(ip, minlength=len(ud)).astype(float); sq = np.bincount(iq, xq, minlength=len(ud)); cq = np.bincount(iq, minlength=len(ud)).astype(float)
    g = np.random.default_rng(BSEED); idx = g.integers(0, len(ud), size=(NB, len(ud))); mp = sp[idx].sum(1) / np.maximum(cp[idx].sum(1), 1); mq = sq[idx].sum(1) / np.maximum(cq[idx].sum(1), 1); d = mp - mq
    return [round(float(np.percentile(d, 2.5)), 1), round(float(np.percentile(d, 97.5)), 1)]
def st(v, d):
    ok = np.isfinite(v); return {"n": int(ok.sum()), "mean_bps": round(float(v[ok].mean() * 1e4), 1) if ok.any() else None, "ci95_bps": boot_mean(v * 1e4, d)}
COLS = ["r1h", "r3h", "rnext", "r12h"]
res = {"self_sha256": SELF, "prereg": "PREREG_crash_continuation_parabolic_stratum_2026-09-06 commit 26aeb23 sha256 e6e3ef34c92504005598c101d6336b42cb76b142d0adc01c4147f9cbf57ce28b", "P_def": "onset events with r3d >= +0.20 at the anchor (rows E-863..E)", "family": {"cells": 7, "expected_false_positives_one_sided_5pct": 0.35}, "theta": {}}
for th in THETAS:
    k_ = f"theta{int(th*100)}"; ev = np.load(f"{ROOT}/continuation/events_theta{int(th*100)}.npz", allow_pickle=True); I, J, K = ev["I"], ev["J"], ev["K"]; f1 = ev["fwd_delay5m"]; wt = ev["weight"]; val = ev["value_bps"]
    g3 = R3D[I, J]; P = g3 >= GAIN; Q = np.isfinite(g3) & ~P; win = (yrs[I] >= 2024) & (E_ts[I] <= CUT); d = days[I]
    o = {"n_events_2024_26": int(win.sum()), "n_P": int((P & win).sum()), "n_Q": int((Q & win).sum()), "P_share": round(float((P & win).sum() / max(win.sum(), 1)), 3), "P": {}, "Q": {}, "P_minus_Q": {}}
    for lab, M in (("P", P), ("Q", Q)):
        o[lab]["pooled_2024_26"] = {c: st(f1[M & win, k], d[M & win]) for k, c in enumerate(COLS)}
        o[lab]["by_year"] = {str(y): {c: st(f1[M & win & (yrs[I] == y), k], d[M & win & (yrs[I] == y)]) for k, c in enumerate(COLS)} for y in (2024, 2025, 2026)}
    o["P_minus_Q"]["pooled_2024_26"] = {"rnext_diff_bps": round(float(np.nanmean(f1[P & win, 2]) - np.nanmean(f1[Q & win, 2])) * 1e4, 1), "ci95": boot_diff(f1[P & win, 2] * 1e4, d[P & win], f1[Q & win, 2] * 1e4, d[Q & win])}
    o["P_minus_Q"]["by_year"] = {str(y): {"rnext_diff_bps": round(float(np.nanmean(f1[P & win & (yrs[I] == y), 2]) - np.nanmean(f1[Q & win & (yrs[I] == y), 2])) * 1e4, 1), "ci95": boot_diff(f1[P & win & (yrs[I] == y), 2] * 1e4, d[P & win & (yrs[I] == y)], f1[Q & win & (yrs[I] == y), 2] * 1e4, d[Q & win & (yrs[I] == y)])} for y in (2024, 2025, 2026)}
    # placebos on P-layer names
    Im, Jm, Km = collect(th, PMASK, +1); okm = (yrs[Im] >= 2024) & (E_ts[Im] <= CUT); fm = fwd(Ei[Im] + Km, Im, Jm); o["placebo_mirror_up_P"] = {"n": int(okm.sum()), **{c: st(fm[okm, k], days[Im][okm]) for k, c in enumerate(COLS)}, "by_year_rnext": {str(y): st(fm[okm & (yrs[Im] == y), 2], days[Im][okm & (yrs[Im] == y)]) for y in (2024, 2025, 2026)}}
    evset = set(zip(I[P].tolist(), J[P].tolist())); Ir, Jr = np.where(PMASK & (yrs >= 2024)[:, None] & (E_ts <= CUT)[:, None]); keep = np.array([(int(a), int(b)) not in evset for a, b in zip(Ir, Jr)]); Ir, Jr = Ir[keep], Jr[keep]
    if len(Ir) and (P & win).any():
        sel = rng.choice(len(Ir), size=min(len(Ir), max(5000, 20 * int((P & win).sum()))), replace=False); Ir, Jr = Ir[sel], Jr[sel]; Kr = rng.choice(K[P & win], size=len(Ir), replace=True); fr = fwd(Ei[Ir] + Kr, Ir, Jr)
        o["placebo_random_time_P"] = {"n": int(len(Ir)), **{c: st(fr[:, k], days[Ir]) for k, c in enumerate(COLS)}}
    # value bound, P events only
    va = np.zeros(nA); vv = np.where(np.isfinite(val) & P, val, 0.0) * wt; np.add.at(va, I, vv); w_ = (yrs >= 2024) & (E_ts <= CUT)
    o["value_P_bps_anchor_per_gross"] = {"mean_2024_26": round(float(va[w_].mean()), 4), "ci95": boot_mean(va[w_], days[w_]), "by_year": {str(y): round(float(va[(yrs == y) & (E_ts <= CUT)].mean()), 4) for y in (2024, 2025, 2026)}, "n_P_events_with_weight": int(((wt > 0) & P & win & np.isfinite(val)).sum()), "mean_value_per_P_event_bps_notional": round(float(np.nanmean(val[P & win])), 1) if (P & win).any() else None}
    res["theta"][k_] = o
    print(f"[{k_}] P n {o['n_P']} ({o['P_share']:.2f}) Q n {o['n_Q']} | P rnext pooled {o['P']['pooled_2024_26']['rnext']['mean_bps']} {o['P']['pooled_2024_26']['rnext']['ci95_bps']} by year " + " ".join(f"{y}:{o['P']['by_year'][str(y)]['rnext']['mean_bps']} {o['P']['by_year'][str(y)]['rnext']['ci95_bps']} n{o['P']['by_year'][str(y)]['rnext']['n']}" for y in (2024, 2025, 2026)) + f" | Q pooled {o['Q']['pooled_2024_26']['rnext']['mean_bps']} {o['Q']['pooled_2024_26']['rnext']['ci95_bps']} | P−Q {o['P_minus_Q']['pooled_2024_26']} | mirror_P {o['placebo_mirror_up_P']['rnext']['mean_bps']} {o['placebo_mirror_up_P']['rnext']['ci95_bps']} n{o['placebo_mirror_up_P']['n']} | random_P {o.get('placebo_random_time_P', {}).get('rnext')} | value_P {o['value_P_bps_anchor_per_gross']['mean_2024_26']} {o['value_P_bps_anchor_per_gross']['ci95']}", flush=True)
# frozen reading
t8 = res["theta"]["theta8"]; by = t8["P"]["by_year"]
yr_ok = {y: (by[str(y)]["rnext"]["ci95_bps"][1] is not None and by[str(y)]["rnext"]["ci95_bps"][1] < 0) for y in (2024, 2025, 2026)}
same_sign = all(res["theta"][k]["P"]["pooled_2024_26"]["rnext"]["mean_bps"] is not None and res["theta"][k]["P"]["pooled_2024_26"]["rnext"]["mean_bps"] < 0 for k in ("theta5", "theta12"))
mir = t8["placebo_mirror_up_P"]["rnext"]; mirror_not_neg = (mir["ci95_bps"][1] is not None and mir["ci95_bps"][1] > 0) or (mir["mean_bps"] is not None and mir["mean_bps"] >= 0)
mirror_sig_neg = mir["mean_bps"] is not None and mir["mean_bps"] < 0 and mir["ci95_bps"][1] is not None and mir["ci95_bps"][1] < 0
pq = t8["P_minus_Q"]["pooled_2024_26"]; pq_ok = pq["ci95"][1] is not None and pq["ci95"][1] < 0
v = t8["value_P_bps_anchor_per_gross"]; val_ok = v["mean_2024_26"] >= 0.03 and v["ci95"][0] is not None and v["ci95"][0] > 0
confirm = sum(yr_ok.values()) >= 2 and yr_ok[2026] and same_sign and mirror_not_neg and pq_ok and val_ok
reject = (by["2026"]["rnext"]["ci95_bps"][0] is not None and by["2026"]["rnext"]["ci95_bps"][0] > -15) or mirror_sig_neg
res["reading"] = {"theta8_P_years_ci_upper_lt0": yr_ok, "theta5_theta12_P_point_negative": bool(same_sign), "mirror_placebo_P_not_negative": bool(mirror_not_neg), "mirror_placebo_P_significantly_negative": bool(mirror_sig_neg), "P_minus_Q_ci_upper_lt0": bool(pq_ok), "value_ok_ge_0.03_ci_lower_gt0": bool(val_ok), "reject_2026_ci_lower_gt_-15": bool(by["2026"]["rnext"]["ci95_bps"][0] is not None and by["2026"]["rnext"]["ci95_bps"][0] > -15),
                  "verdict": "CONFIRM" if confirm else ("REJECT" if reject else "UNDECIDED")}
print("READING " + json.dumps(res["reading"]), flush=True)
json.dump(res, open(f"{ROOT}/results/stratum.json", "w"), indent=1)
L = ["| θ | P n (share) | P r(τ+5m→next) pooled [CI] | P by year 2024 / 2025 / 2026 | Q pooled | P − Q [CI] | mirror-up P | random-time P | value P bps/anchor/gross [CI] |", "|---|---|---|---|---|---|---|---|---|"]
for k, o in res["theta"].items():
    f = lambda s: f"{s['mean_bps']:+.1f} [{s['ci95_bps'][0]:+.1f}, {s['ci95_bps'][1]:+.1f}] n{s['n']}" if s and s.get("mean_bps") is not None else "–"
    L.append(f"| {k} | {o['n_P']} ({o['P_share']:.2f}) | {f(o['P']['pooled_2024_26']['rnext'])} | " + " / ".join(f(o['P']['by_year'][str(y)]['rnext']) for y in (2024, 2025, 2026)) + f" | {f(o['Q']['pooled_2024_26']['rnext'])} | {o['P_minus_Q']['pooled_2024_26']['rnext_diff_bps']:+.1f} {o['P_minus_Q']['pooled_2024_26']['ci95']} | {f(o['placebo_mirror_up_P']['rnext'])} | {f(o.get('placebo_random_time_P', {}).get('rnext'))} | {o['value_P_bps_anchor_per_gross']['mean_2024_26']:+.4f} {o['value_P_bps_anchor_per_gross']['ci95']} |")
L += ["", "reading: " + json.dumps(res["reading"])]
open(f"{ROOT}/results/stratum.md", "w").write("\n".join(L) + "\n"); print("STRATUM_DONE", flush=True)
