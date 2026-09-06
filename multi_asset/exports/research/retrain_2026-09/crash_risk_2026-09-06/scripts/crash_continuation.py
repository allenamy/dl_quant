"""crash_continuation.py — PREREG_crash_continuation_intra_anchor_2026-09-06 (Phase 2b): after the first large intra-anchor drop of a cohort long name,
does the price continue (exit has value) or revert? Event study on the 5m cache, cohort = Phase 1 C(t) (phase0.npz COH), 2022-01→2026-08.
Onset O(θ): within (E, E+4h] (cache rows Ei+1..Ei+48; row E = bar closing at the anchor), the cumulative return from the anchor close first ≤ −θ, θ ∈ {5, 8, 12}%;
τ = that bar's close, k = bars since anchor (minutes = 5k); one event per name per anchor. Forward from τ (causal): r(τ→τ+1h/3h/next anchor/12h) and the
execution-delay caliber r(τ+5m→…) (from the close of the bar after τ). Placebos: (a) same cohort names at non-event anchors with a random τ drawn from the event
k-distribution; (b) mirror: first cumulative return ≥ +θ; (c) non-cohort members with the same drop onset. Strata (θ=8): τ ≤ 60 / 60–180 / > 180 min,
at-cap (rate_over_cap ≥ 0.9), 3-day gain ≥ +20%, listing age ≤ 90 d, year. Value bound per event: exit at τ+5m (maker) vs hold to next anchor =
−r(τ+5m→next) − 8.9 bps (half round trip 3.92 + adverse markout 5), weighted by the name's normalised book weight (M1_UPIT_prod_s42 W/L1 at anchor t; 0 if not
held long) and summed per anchor → bps/anchor/gross over 2024→26 (≤ 2026-08-10 20:00Z), UTC-day-block bootstrap 2000 seed 20260905.
Frozen readings (§2): continuation_true = θ8 events' r(τ+5m→next) mean ≤ −40 bps AND CI95 upper < 0 in ≥ 2 of 2024/2025/2026 AND in 2026, AND every placebo
|mean| < 15 bps or opposite sign; valuable = continuation_true AND value ≥ +0.05 bps/anchor/gross (CI lower > 0) AND events ≥ 1/anchor; reject = r(τ+5m→next)
CI95 lower > −15 bps (2024→26 pooled) OR a placebo of the same magnitude (mean ≤ −15 with CI upper < 0); else UNDECIDED. Outputs: continuation/*.npz, results/continuation.json + .md"""
import os, sys, json, time, calendar, hashlib
import numpy as np
ROOT = "/workspace/review_scratch/crash_risk"; OUTD = f"{ROOT}/continuation"; os.makedirs(OUTD, exist_ok=True); SELF = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
def T(s): return int(calendar.timegm(time.strptime(s, "%Y-%m-%d")))
CUT = T("2026-08-10") + 20 * 3600; NB = 2000; BSEED = 20260905; THETAS = (0.05, 0.08, 0.12); COST = 8.9
sys.path.insert(0, "/workspace")
from zload import zload
Z = zload("/workspace/data/dlnative_5m_wide829_f16_ext.npz", allow_pickle=True); CTS = Z["ts"].astype(np.int64); T0 = int(CTS[0]); r5 = np.asarray(Z["data"][:, :, 0], np.float32); SYMS = [str(s) for s in Z["symbols"]]; del Z
NW = len(SYMS); TT = len(CTS); fin = np.isfinite(r5); LC = np.cumsum(np.where(fin, np.log1p(np.clip(r5, -0.99, None)), 0.0), 0, dtype=np.float64); del r5, fin
P0 = np.load(f"{ROOT}/data/phase0.npz", allow_pickle=True); COH = P0["COH"]; MEM = P0["MEM"]; E_ts = P0["E_ts"].astype(np.int64); nA = len(E_ts); Ei = (E_ts - T0) // 300; assert np.all(CTS[Ei] == E_ts)
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); days = E_ts // 86400
F = np.load(f"{ROOT}/data/features.npz", allow_pickle=True); PI = F["PI"]; PJ = F["PJ"]; X = np.asarray(F["X"], np.float32); NM = [str(n) for n in F["names"]]
fidx = {}
for r, (i, j) in enumerate(zip(PI, PJ)): fidx[(int(i), int(j))] = r
c_cap = NM.index("rate_over_cap"); c_r3d = NM.index("r3d"); c_age = NM.index("age_anchors")
z = np.load("/workspace/review_scratch/health_check/dev_alt/probe_artifacts/w10_ablation_series_M1_UPIT_prod_s42_ccal.npz", allow_pickle=True); R = np.asarray(z["d30_n2_c42_rec"], float); W = np.asarray(z["d30_n2_c42_W"], float)
bts = R[:, 0].astype(np.int64); WN = W / np.maximum(np.abs(W).sum(1)[:, None], 1e-12); brow = {int(t): k for k, t in enumerate(bts)}
rng = np.random.default_rng(BSEED)
def fwd(tau, i, j, delay):
    """forward returns from row tau (+delay bars): 1h, 3h, next anchor (row Ei+48), 12h; NaN if the window has no room."""
    a = tau + delay; out = np.full((len(tau), 4), np.nan)
    for c, h in enumerate((12, 36, None, 144)):
        b = (Ei[i] + 48) if h is None else (tau + h); ok = (b > a) & (b < TT)
        out[ok, c] = np.expm1(LC[b[ok], j[ok]] - LC[a[ok], j[ok]])
    return out
def collect(theta, mask_fn, sign):
    """events for all anchors with a panel-era cohort: returns dict of arrays."""
    I, J, K = [], [], []
    for i in range(nA):
        cj = np.where(mask_fn(i))[0]
        if len(cj) == 0 or Ei[i] + 48 >= TT: continue
        cum = np.expm1(LC[Ei[i] + 1: Ei[i] + 49][:, cj] - LC[Ei[i], cj]); hit = (cum <= -theta) if sign < 0 else (cum >= theta)
        any_ = hit.any(0); k = hit.argmax(0) + 1
        I += [i] * int(any_.sum()); J += cj[any_].tolist(); K += k[any_].tolist()
    return np.array(I, int), np.array(J, int), np.array(K, int)
def boot(x, d):
    ok = np.isfinite(x); x = x[ok]; d = d[ok]
    if len(x) < 10: return [None, None]
    ud, inv = np.unique(d, return_inverse=True); s1 = np.bincount(inv, x); c = np.bincount(inv).astype(float)
    g = np.random.default_rng(BSEED); idx = g.integers(0, len(ud), size=(NB, len(ud))); m = s1[idx].sum(1) / c[idx].sum(1)
    return [round(float(np.percentile(m, 2.5)), 1), round(float(np.percentile(m, 97.5)), 1)]
def stats(v, d):
    ok = np.isfinite(v); return {"n": int(ok.sum()), "mean_bps": round(float(v[ok].mean() * 1e4), 1) if ok.any() else None, "ci95_bps": boot(v * 1e4, d)}
COLS = ["r1h", "r3h", "rnext", "r12h"]
res = {"self_sha256": SELF, "prereg": "PREREG_crash_continuation_intra_anchor_2026-09-06 df3e8ff sha256 3d907b89edaf071cf58f78c8cff7d8774eba7b26a959342262b7946e8cfaaa33", "cost_bps": COST, "thetas": THETAS, "events": {}, "placebos": {}, "strata_theta8": {}, "value": {}, "reading": {}}
EV = {}
for th in THETAS:
    I, J, K = collect(th, lambda i: COH[i], -1); tau = Ei[I] + K; ok_win = (yrs[I] >= 2024) & (E_ts[I] <= CUT)
    f0 = fwd(tau, I, J, 0); f1 = fwd(tau, I, J, 1); d = days[I]
    wt = np.array([WN[brow[int(E_ts[i])], j] if int(E_ts[i]) in brow else 0.0 for i, j in zip(I, J)]); wt = np.where(wt > 0, wt, 0.0)
    val = np.where(np.isfinite(f1[:, 2]), -f1[:, 2] * 1e4 - COST, np.nan)
    EV[th] = dict(I=I, J=J, K=K, f0=f0, f1=f1, wt=wt, val=val)
    e = {"n_events_all": int(len(I)), "n_events_2024_26": int(ok_win.sum()), "events_per_anchor_2024_26": round(float(ok_win.sum() / ((yrs >= 2024) & (E_ts <= CUT)).sum()), 3), "tau_minutes_median": float(np.median(K * 5)) if len(K) else None,
         "by_year": {}}
    for y in (2024, 2025, 2026):
        m = (yrs[I] == y) & (E_ts[I] <= CUT); e["by_year"][str(y)] = {"n": int(m.sum()), "incl_first_bar": {c: stats(f0[m, k], d[m]) for k, c in enumerate(COLS)}, "delay_5m": {c: stats(f1[m, k], d[m]) for k, c in enumerate(COLS)}}
    e["pooled_2024_26"] = {"incl_first_bar": {c: stats(f0[ok_win, k], d[ok_win]) for k, c in enumerate(COLS)}, "delay_5m": {c: stats(f1[ok_win, k], d[ok_win]) for k, c in enumerate(COLS)}}
    res["events"][f"theta{int(th*100)}"] = e; print(f"EVENTS θ={th}: n {len(I)} (2024→26 {ok_win.sum()}, {e['events_per_anchor_2024_26']}/anchor) delay5m rnext by year " + " ".join(f"{y}:{e['by_year'][str(y)]['delay_5m']['rnext']['mean_bps']} {e['by_year'][str(y)]['delay_5m']['rnext']['ci95_bps']}" for y in (2024, 2025, 2026)) + f" | pooled {e['pooled_2024_26']['delay_5m']['rnext']}", flush=True)
    np.savez_compressed(f"{OUTD}/events_theta{int(th*100)}.npz", I=I, J=J, K=K, fwd_incl=f0, fwd_delay5m=f1, weight=wt, value_bps=val, E_ts=E_ts[I], symbols=np.array(SYMS)[J])
    # placebos
    pl = {}
    # (b) mirror up-onset in the cohort
    Im, Jm, Km = collect(th, lambda i: COH[i], +1); okm = (yrs[Im] >= 2024) & (E_ts[Im] <= CUT); fm = fwd(Ei[Im] + Km, Im, Jm, 1); pl["mirror_up_cohort"] = {"n": int(okm.sum()), **{c: stats(fm[okm, k], days[Im][okm]) for k, c in enumerate(COLS)}}
    # (c) non-cohort members drop onset
    In, Jn, Kn = collect(th, lambda i: MEM[i] & ~COH[i], -1); okn = (yrs[In] >= 2024) & (E_ts[In] <= CUT); fn_ = fwd(Ei[In] + Kn, In, Jn, 1); pl["noncohort_drop"] = {"n": int(okn.sum()), **{c: stats(fn_[okn, k], days[In][okn]) for k, c in enumerate(COLS)}}
    # (a) random time, same cohort names at non-event anchors, k drawn from the event k distribution
    evset = set(zip(I.tolist(), J.tolist())); Ir, Jr = np.where(COH & (yrs >= 2024)[:, None] & (E_ts <= CUT)[:, None]); keep = np.array([(int(a), int(b)) not in evset for a, b in zip(Ir, Jr)]); Ir, Jr = Ir[keep], Jr[keep]
    sel = rng.choice(len(Ir), size=min(len(Ir), max(5000, 20 * int(ok_win.sum()))), replace=False); Ir, Jr = Ir[sel], Jr[sel]; Kr = rng.choice(K[ok_win], size=len(Ir), replace=True) if ok_win.any() else np.full(len(Ir), 24)
    fr = fwd(Ei[Ir] + Kr, Ir, Jr, 1); pl["random_time_cohort"] = {"n": int(len(Ir)), **{c: stats(fr[:, k], days[Ir]) for k, c in enumerate(COLS)}}
    res["placebos"][f"theta{int(th*100)}"] = pl; print(f"PLACEBO θ={th} (delay5m rnext): " + " | ".join(f"{k}: n {v['n']} mean {v['rnext']['mean_bps']} CI {v['rnext']['ci95_bps']}" for k, v in pl.items()), flush=True)
    # value bound per anchor (2024→26)
    win = (yrs >= 2024) & (E_ts <= CUT); va = np.zeros(nA); vv = np.where(np.isfinite(val), val, 0.0) * wt; np.add.at(va, I, vv)
    vw = va[win]; res["value"][f"theta{int(th*100)}"] = {"mean_bps_anchor_per_gross_2024_26": round(float(vw.mean()), 4), "ci95": boot(vw, days[win]), "n_anchors": int(win.sum()), "n_events_with_weight_gt0": int(((wt > 0) & ok_win & np.isfinite(val)).sum()), "mean_value_per_event_bps_notional": round(float(np.nanmean(val[ok_win])), 1) if ok_win.any() else None,
                                                 "by_year": {str(y): round(float(va[(yrs == y) & (E_ts <= CUT)].mean()), 4) for y in (2024, 2025, 2026)}}
    print(f"VALUE θ={th}: " + json.dumps(res["value"][f"theta{int(th*100)}"]), flush=True)
# strata (θ = 8%, delay-5m rnext)
I, J, K, f1, d = EV[0.08]["I"], EV[0.08]["J"], EV[0.08]["K"], EV[0.08]["f1"], days[EV[0.08]["I"]]; okw = (yrs[I] >= 2024) & (E_ts[I] <= CUT)
feat = np.array([fidx.get((int(i), int(j)), -1) for i, j in zip(I, J)]); has = feat >= 0
cap = np.where(has, X[np.maximum(feat, 0), c_cap], np.nan); r3d = np.where(has, X[np.maximum(feat, 0), c_r3d], np.nan); age = np.where(has, X[np.maximum(feat, 0), c_age], np.nan)
S = {"tau_le_60min": K * 5 <= 60, "tau_60_180min": (K * 5 > 60) & (K * 5 <= 180), "tau_gt_180min": K * 5 > 180, "at_cap": cap >= 0.9, "not_at_cap": cap < 0.9, "r3d_ge_20pct": r3d >= 0.2, "r3d_lt_20pct": r3d < 0.2, "age_le_90d": age <= 540, "age_gt_90d": age > 540}
for y in (2024, 2025, 2026): S[f"year_{y}"] = yrs[I] == y
res["strata_theta8"] = {k: {"n": int((m & okw).sum()), "rnext_delay5m": stats(f1[m & okw, 2], d[m & okw]), "r1h_delay5m": stats(f1[m & okw, 0], d[m & okw])} for k, m in S.items()}
print("STRATA θ=8 (delay5m rnext): " + " | ".join(f"{k}: n {v['n']} {v['rnext_delay5m']['mean_bps']} {v['rnext_delay5m']['ci95_bps']}" for k, v in res["strata_theta8"].items()), flush=True)
# frozen reading (θ = 8%)
e8 = res["events"]["theta8"]; pl8 = res["placebos"]["theta8"]; v8 = res["value"]["theta8"]
yr_ok = {y: (e8["by_year"][str(y)]["delay_5m"]["rnext"]["mean_bps"] is not None and e8["by_year"][str(y)]["delay_5m"]["rnext"]["mean_bps"] <= -40 and e8["by_year"][str(y)]["delay_5m"]["rnext"]["ci95_bps"][1] is not None and e8["by_year"][str(y)]["delay_5m"]["rnext"]["ci95_bps"][1] < 0) for y in (2024, 2025, 2026)}
plac_ok = {k: (v["rnext"]["mean_bps"] is not None and (abs(v["rnext"]["mean_bps"]) < 15 or v["rnext"]["mean_bps"] > 0)) for k, v in pl8.items()}
plac_same = {k: (v["rnext"]["mean_bps"] is not None and v["rnext"]["mean_bps"] <= -15 and v["rnext"]["ci95_bps"][1] is not None and v["rnext"]["ci95_bps"][1] < 0) for k, v in pl8.items()}
cont = sum(yr_ok.values()) >= 2 and yr_ok[2026] and all(plac_ok.values())
pooled = e8["pooled_2024_26"]["delay_5m"]["rnext"]
valuable = cont and v8["mean_bps_anchor_per_gross_2024_26"] >= 0.05 and v8["ci95"][0] is not None and v8["ci95"][0] > 0 and e8["events_per_anchor_2024_26"] >= 1
reject = (pooled["ci95_bps"][0] is not None and pooled["ci95_bps"][0] > -15) or any(plac_same.values())
res["reading"] = {"theta": 0.08, "year_continuation_ok": yr_ok, "placebo_ok_(abs<15_or_positive)": plac_ok, "placebo_same_magnitude": plac_same, "continuation_true": bool(cont), "valuable": bool(valuable), "reject_conditions": {"pooled_ci_lower_gt_-15": bool(pooled["ci95_bps"][0] is not None and pooled["ci95_bps"][0] > -15), "placebo_same_magnitude_any": bool(any(plac_same.values()))},
                  "verdict": "VALUABLE" if valuable else ("REJECT" if reject and not cont else ("CONTINUATION_TRUE_NOT_VALUABLE" if cont else ("REJECT" if reject else "UNDECIDED")))}
print("READING " + json.dumps(res["reading"]), flush=True)
json.dump(res, open(f"{ROOT}/results/continuation.json", "w"), indent=1)
L = ["| θ | events 2024→26 (/anchor) | delay-5m r(τ→1h) | r(τ→3h) | **r(τ→next anchor)** | r(τ→12h) | incl-first-bar r(τ→next) | value bound bps/anchor/gross [CI] |", "|---|---|---|---|---|---|---|---|"]
for th in THETAS:
    k = f"theta{int(th*100)}"; e = res["events"][k]["pooled_2024_26"]; v = res["value"][k]; f = lambda s: f"{s['mean_bps']:+.1f} [{s['ci95_bps'][0]:+.1f}, {s['ci95_bps'][1]:+.1f}] (n {s['n']})" if s["mean_bps"] is not None else "–"
    L.append(f"| {int(th*100)}% | {res['events'][k]['n_events_2024_26']} ({res['events'][k]['events_per_anchor_2024_26']}) | {f(e['delay_5m']['r1h'])} | {f(e['delay_5m']['r3h'])} | **{f(e['delay_5m']['rnext'])}** | {f(e['delay_5m']['r12h'])} | {f(e['incl_first_bar']['rnext'])} | {v['mean_bps_anchor_per_gross_2024_26']:+.4f} [{v['ci95'][0]}, {v['ci95'][1]}] |")
L += ["", "| θ | by year: delay-5m r(τ→next) 2024 / 2025 / 2026 | placebo random-time | placebo mirror-up | placebo non-cohort drop |", "|---|---|---|---|---|"]
for th in THETAS:
    k = f"theta{int(th*100)}"; e = res["events"][k]["by_year"]; p = res["placebos"][k]; g = lambda s: f"{s['mean_bps']:+.1f} [{s['ci95_bps'][0]:+.1f}, {s['ci95_bps'][1]:+.1f}] n {s['n']}" if s["mean_bps"] is not None else "–"
    L.append(f"| {int(th*100)}% | " + " / ".join(g(e[str(y)]["delay_5m"]["rnext"]) for y in (2024, 2025, 2026)) + f" | {g(p['random_time_cohort']['rnext'])} | {g(p['mirror_up_cohort']['rnext'])} | {g(p['noncohort_drop']['rnext'])} |")
L += ["", "strata θ=8 (delay-5m r(τ→next), bps [CI], n): " + "; ".join(f"{k} {v['rnext_delay5m']['mean_bps']} {v['rnext_delay5m']['ci95_bps']} n{v['n']}" for k, v in res["strata_theta8"].items()), "", "reading: " + json.dumps(res["reading"])]
open(f"{ROOT}/results/continuation.md", "w").write("\n".join(L) + "\n"); print("CONTINUATION_DONE", flush=True)
