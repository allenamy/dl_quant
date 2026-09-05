"""d1_curve.py — D1 IC-vs-model-age curve (PREREG_retrain_cadence_and_seat_rule_2026-09-05 §1, diagnostic D1). Read-only inputs;
reads d1_matrices.npz + folds_d1.json (pod_king_cadence.py MODE=d1), writes d1_curve.json here; prints every table.
Age definition (fixed before any number): for an anchor in calendar month M (index mi, 2024-01 = 0), age k (1..12) uses the K1 model whose
own test month is M-(k-1) (model index mi-(k-1)); age 1 = K1 itself (slow_pred_rollm). Cutoff of model j = its last training label end
(train_last + 4h); "days since cutoff" = E_ts(anchor) - label_end(model).
Statistics: rank-IC = Spearman(prediction, target) over meta members with finite target (>=30 pairs), mean over anchors; targets raw y4
(meta, Σ5m simple [E,E+47]) and dlw y4s (Π(1+r5)-1 over [E+1,E+48]). King leg = production leg definition (bps per unit gross per anchor),
S = mean/std per anchor. Paired differences age1 - agek: mean and s.e. over anchors (s.e. = std/sqrt(n)), plus UTC-day-block bootstrap CI95
(2000 resamples, seed 20260905).
DECISION STATISTIC (frozen): paired IC(age1) - IC(age12) on the COMMON anchor set (anchors where all 12 ages exist and have a finite IC =
months 2024-12..2026-08), raw y4 primary and dlw y4s alongside; "12-month decay >= 0.003" (prereg threshold) on EITHER target => K3 runs.
"""
import json, time, calendar
import numpy as np
from scipy.stats import rankdata, spearmanr
ROOT = "/workspace/review_scratch/cadence_seats/axisA"; NB = 2000; SEED = 20260905; KMAX = 12; THR = 0.003
Z = np.load(f"{ROOT}/d1_matrices.npz", allow_pickle=True)
IC = {"raw": Z["IC_raw"].astype(np.float64), "y4s": Z["IC_y4s"].astype(np.float64)}; LEG = {"raw": Z["LEG_raw"].astype(np.float64), "y4s": Z["LEG_y4s"].astype(np.float64)}
E_ts = Z["E_ts"].astype(np.int64); mi = Z["month_index"].astype(np.int64); nM, nA = IC["raw"].shape
label_end = Z["model_train_last"].astype(np.int64) + int(Z["label_s"]); test_first = Z["model_test_first"].astype(np.int64)
F = json.load(open(f"{ROOT}/folds_d1.json"))
gm = [time.gmtime(int(t)) for t in E_ts]; yrs = np.array([g.tm_year for g in gm]); mon = np.array([g.tm_mon for g in gm])
days = np.array([time.strftime("%Y-%m-%d", g) for g in gm]); idx = np.arange(nA)
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
print("CONFIG " + json.dumps({"matrices": f"{ROOT}/d1_matrices.npz", "n_models": int(nM), "n_anchors": int(nA), "KMAX": KMAX, "threshold": THR, "NB": NB, "seed": SEED,
                              "d1_receipts": {k: F.get(k) for k in ("stitched_equal_k1", "stitched_maxabs_vs_k1", "all_asserts_true")},
                              "boosters_equal_k1": f"{sum(f['booster_equal_k1'] for f in F['folds'])}/{len(F['folds'])}"}), flush=True)
def age_series(M, k):
    out = np.full(nA, np.nan); fi = mi - (k - 1); ok = (mi >= 0) & (fi >= 0) & (fi < nM)
    out[ok] = M[fi[ok], idx[ok]]; return out
def age_days(k):
    out = np.full(nA, np.nan); fi = mi - (k - 1); ok = (mi >= 0) & (fi >= 0) & (fi < nM)
    out[ok] = (E_ts[ok] - label_end[fi[ok]]) / 86400.0; return out
rng = np.random.default_rng(SEED)
def boot_ci(x, d):
    ud, inv = np.unique(d, return_inverse=True); nd = len(ud)
    sums = np.bincount(inv, weights=x, minlength=nd); cnts = np.bincount(inv, minlength=nd)
    r = rng.integers(0, nd, size=(NB, nd)); means = sums[r].sum(1) / cnts[r].sum(1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)), int(nd)
A = {(t, k): age_series(IC[t], k) for t in ("raw", "y4s") for k in range(1, KMAX + 1)}
L = {(t, k): age_series(LEG[t], k) for t in ("raw", "y4s") for k in range(1, KMAX + 1)}
D = {k: age_days(k) for k in range(1, KMAX + 1)}
OUT = {"definition": "age k for an anchor in month M = K1 model with test month M-(k-1); age1 = K1", "full": {}, "common": {}, "paired_own": {}, "days_bins": {}, "by_year_common": {}, "pinned_month_of_year": {}, "leg": {}}
# ── Table A: full anchor set available at each age ──
print(f"\nTABLE A — IC and king-leg by model age, FULL anchor set available at each age (anchors 2024-01.. with a finite value; y4s only where a dlw row exists)")
print(f"{'age':>4s} {'n_raw':>6s} {'IC_raw':>8s} {'n_y4s':>6s} {'IC_y4s':>8s} {'days_since_cutoff mean/min/max':>32s} | {'n_leg':>6s} {'leg_raw':>8s} {'S_raw':>7s} {'leg_y4s':>8s} {'S_y4s':>7s}  months")
for k in range(1, KMAX + 1):
    a = A[("raw", k)]; b = A[("y4s", k)]; lr = L[("raw", k)]; ls = L[("y4s", k)]; dd = D[k]
    fa = np.isfinite(a); fb = np.isfinite(b); fl = np.isfinite(lr); fs = np.isfinite(ls)
    mths = sorted(set((yrs[fa] * 100 + mon[fa]).tolist()))
    rec = {"n_raw": int(fa.sum()), "IC_raw": float(a[fa].mean()), "n_y4s": int(fb.sum()), "IC_y4s": float(b[fb].mean()), "days_mean": float(dd[fa].mean()), "days_min": float(dd[fa].min()), "days_max": float(dd[fa].max()),
           "n_leg": int(fl.sum()), "leg_raw": float(lr[fl].mean()), "S_raw": float(lr[fl].mean() / lr[fl].std(ddof=1)), "leg_y4s": float(ls[fs].mean()), "S_y4s": float(ls[fs].mean() / ls[fs].std(ddof=1)), "first_month": mths[0], "last_month": mths[-1]}
    OUT["full"][k] = rec
    print(f"{k:4d} {rec['n_raw']:6d} {rec['IC_raw']:+8.4f} {rec['n_y4s']:6d} {rec['IC_y4s']:+8.4f} {rec['days_mean']:10.1f}/{rec['days_min']:6.1f}/{rec['days_max']:6.1f}         | {rec['n_leg']:6d} {rec['leg_raw']:+8.3f} {rec['S_raw']:+7.3f} {rec['leg_y4s']:+8.3f} {rec['S_y4s']:+7.3f}  {mths[0]}..{mths[-1]}")
# ── Table B: common anchor set (all 12 ages finite) with paired differences ──
for t in ("raw", "y4s"):
    common = np.ones(nA, bool)
    for k in range(1, KMAX + 1): common &= np.isfinite(A[(t, k)])
    n = int(common.sum()); mths = sorted(set((yrs[common] * 100 + mon[common]).tolist()))
    print(f"\nTABLE B[{t}] — COMMON anchor set (all 12 ages finite): n={n} anchors, months {mths[0]}..{mths[-1]}; paired Δ = IC(age1) − IC(age k) over anchors, s.e. = std/√n, day-block bootstrap CI95")
    print(f"{'age':>4s} {'IC':>8s} {'Δ(1−k)':>9s} {'s.e.':>7s} {'CI95 lo':>8s} {'CI95 hi':>8s} {'t':>6s} | {'leg':>8s} {'S':>7s} {'Δleg(1−k)':>10s} {'s.e.':>7s}")
    base = A[(t, 1)][common]; lbase = L[(t, 1)]
    lc = common & np.isfinite(lbase)
    for k in range(1, KMAX + 1): lc &= np.isfinite(L[(t, k)])
    for k in range(1, KMAX + 1):
        v = A[(t, k)][common]; d = base - v; se = float(d.std(ddof=1) / np.sqrt(n)) if k > 1 else 0.0
        lo, hi, nd = boot_ci(d, days[common]) if k > 1 else (0.0, 0.0, 0)
        lv = L[(t, k)][lc]; ld = L[(t, 1)][lc] - lv; lse = float(ld.std(ddof=1) / np.sqrt(lc.sum())) if k > 1 else 0.0
        rec = {"n": n, "IC": float(v.mean()), "delta_1_minus_k": float(d.mean()), "se": se, "ci_lo": lo, "ci_hi": hi, "t": (float(d.mean() / se) if se > 0 else 0.0), "n_days": nd,
               "n_leg": int(lc.sum()), "leg": float(lv.mean()), "S": float(lv.mean() / lv.std(ddof=1)), "dleg_1_minus_k": float(ld.mean()), "dleg_se": lse}
        OUT["common"][f"{t}/{k}"] = rec
        print(f"{k:4d} {rec['IC']:+8.4f} {rec['delta_1_minus_k']:+9.4f} {se:7.4f} {lo:+8.4f} {hi:+8.4f} {rec['t']:6.2f} | {rec['leg']:+8.3f} {rec['S']:+7.3f} {rec['dleg_1_minus_k']:+10.3f} {lse:7.3f}")
    OUT["common"][f"{t}/n"] = n; OUT["common"][f"{t}/months"] = [mths[0], mths[-1]]
# ── Table C: paired on each age's own anchor set ──
print(f"\nTABLE C — paired Δ = IC(age1) − IC(age k) on each age's OWN anchor set (all anchors where age k exists; age1 exists on all of them)")
print(f"{'age':>4s} {'n':>6s} {'IC1_raw':>8s} {'ICk_raw':>8s} {'Δraw':>8s} {'s.e.':>7s} {'CI95':>18s} | {'n':>6s} {'IC1_y4s':>8s} {'ICk_y4s':>8s} {'Δy4s':>8s} {'s.e.':>7s} {'CI95':>18s}")
for k in range(2, KMAX + 1):
    row = {}; cells = []
    for t in ("raw", "y4s"):
        ok = np.isfinite(A[(t, k)]) & np.isfinite(A[(t, 1)]); n = int(ok.sum()); d = A[(t, 1)][ok] - A[(t, k)][ok]; se = float(d.std(ddof=1) / np.sqrt(n)); lo, hi, nd = boot_ci(d, days[ok])
        row[t] = {"n": n, "IC1": float(A[(t, 1)][ok].mean()), "ICk": float(A[(t, k)][ok].mean()), "delta": float(d.mean()), "se": se, "ci_lo": lo, "ci_hi": hi}
        cells.append(f"{n:6d} {row[t]['IC1']:+8.4f} {row[t]['ICk']:+8.4f} {row[t]['delta']:+8.4f} {se:7.4f} [{lo:+.4f},{hi:+.4f}]")
    OUT["paired_own"][k] = row; print(f"{k:4d} " + " | ".join(cells))
# ── Table D: days-since-cutoff bins over ALL (model, anchor) pairs (ages up to 12 months only) ──
print(f"\nTABLE D — ALL (model, anchor) pairs binned by days since the model's cutoff (label end), 30-day bins to 360 d (pairs pooled; a given anchor appears once per model)")
print(f"{'bin(d)':>10s} {'pairs':>7s} {'IC_raw':>8s} {'IC_y4s':>8s} {'leg_raw':>8s} {'S_raw':>7s}")
DAYS = (E_ts[None, :] - label_end[:, None]) / 86400.0
for lo_d in range(0, 360, 30):
    sel = (DAYS >= lo_d) & (DAYS < lo_d + 30) & np.isfinite(IC["raw"]); n = int(sel.sum())
    if n == 0: continue
    sy = sel & np.isfinite(IC["y4s"]); sl = sel & np.isfinite(LEG["raw"]); lr = LEG["raw"][sl]
    rec = {"pairs": n, "IC_raw": float(IC["raw"][sel].mean()), "IC_y4s": float(IC["y4s"][sy].mean()), "leg_raw": float(lr.mean()), "S_raw": float(lr.mean() / lr.std(ddof=1))}
    OUT["days_bins"][f"{lo_d}-{lo_d+30}"] = rec
    print(f"{lo_d:4d}-{lo_d+30:<4d} {n:7d} {rec['IC_raw']:+8.4f} {rec['IC_y4s']:+8.4f} {rec['leg_raw']:+8.3f} {rec['S_raw']:+7.3f}")
# ── Table E: common set split by calendar year ──
print(f"\nTABLE E — COMMON set split by calendar year of the anchor (raw y4 IC; ages 1,2,3,6,9,12)")
commonr = np.ones(nA, bool)
for k in range(1, KMAX + 1): commonr &= np.isfinite(A[("raw", k)])
print(f"{'year':>6s} {'n':>6s} " + " ".join(f"{'age'+str(k):>9s}" for k in (1, 2, 3, 6, 9, 12)) + f" {'Δ(1−12)':>9s} {'s.e.':>7s}")
for y in sorted(set(yrs[commonr].tolist())):
    s = commonr & (yrs == y); n = int(s.sum()); vals = {k: float(A[("raw", k)][s].mean()) for k in (1, 2, 3, 6, 9, 12)}; d = A[("raw", 1)][s] - A[("raw", 12)][s]
    OUT["by_year_common"][int(y)] = {"n": n, **{f"age{k}": vals[k] for k in vals}, "delta_1_12": float(d.mean()), "se": float(d.std(ddof=1) / np.sqrt(n))}
    print(f"{y:6d} {n:6d} " + " ".join(f"{vals[k]:+9.4f}" for k in (1, 2, 3, 6, 9, 12)) + f" {d.mean():+9.4f} {d.std(ddof=1)/np.sqrt(n):7.4f}")
# ── Table F: K0 pinned (year folds) by month-of-year = age within its year (auxiliary; the deployed king's own age curve) ──
MT = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True); members = MT["members"]; y4 = MT["y4"]
DT = np.load("/workspace/data/dlw_targets.npz", allow_pickle=True); dmap = {int(t): k for k, t in enumerate(DT["E_ts"].astype(np.int64))}; y4s_src = DT["y4s"]
PW = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True); pw_ts = set(PW["ts"].astype(np.int64).tolist())
PIN = np.load("/workspace/shadow_bundle_v3/slow_pred_pinned.npy")
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 10: out[ok] = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
    return out
def leg(score, yv):
    ok = np.isfinite(yv); z = np.nan_to_num(xz(score)); z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0
    g = np.abs(z).sum(); return float((z / g * np.nan_to_num(yv, nan=0.0)).sum() * 1e4) if g > 1e-9 else 0.0
pic_r = np.full(nA, np.nan); pic_s = np.full(nA, np.nan); pleg = np.full(nA, np.nan)
for i in range(nA):
    if yrs[i] < 2024: continue
    m = members[i]; p = PIN[i, m]
    if not np.isfinite(p).any(): continue
    pic_r[i] = sp(p, y4[i, m]); kk = dmap.get(int(E_ts[i]))
    if kk is not None: pic_s[i] = sp(p, y4s_src[kk][m])
    if int(E_ts[i]) in pw_ts: pleg[i] = leg(p, y4[i, m])
print(f"\nTABLE F — K0 pinned (year folds: 2024 from <2024, 2025 from <2025, 2026 from <2026) by month-of-year = age within its year (auxiliary; 2024-01..2026-08 anchors)")
print(f"{'mon':>4s} {'n':>6s} {'IC_raw':>8s} {'IC_y4s':>8s} {'leg_raw':>8s} {'S_raw':>7s} | K1 age-1 on the same anchors: {'IC_raw':>8s}")
for mth in range(1, 13):
    s = (yrs >= 2024) & (mon == mth) & np.isfinite(pic_r); n = int(s.sum()); ss = s & np.isfinite(pic_s); sl = s & np.isfinite(pleg)
    rec = {"n": n, "IC_raw": float(pic_r[s].mean()), "IC_y4s": float(pic_s[ss].mean()), "leg_raw": float(pleg[sl].mean()), "S_raw": float(pleg[sl].mean() / pleg[sl].std(ddof=1)), "K1_age1_IC_raw": float(A[("raw", 1)][s].mean())}
    OUT["pinned_month_of_year"][mth] = rec
    print(f"{mth:4d} {n:6d} {rec['IC_raw']:+8.4f} {rec['IC_y4s']:+8.4f} {rec['leg_raw']:+8.3f} {rec['S_raw']:+7.3f} | {rec['K1_age1_IC_raw']:+8.4f}")
h1 = (yrs >= 2024) & (mon <= 6) & np.isfinite(pic_r); h2 = (yrs >= 2024) & (mon >= 7) & np.isfinite(pic_r)
OUT["pinned_halves"] = {"H1_IC_raw": float(pic_r[h1].mean()), "H2_IC_raw": float(pic_r[h2].mean()), "H1_n": int(h1.sum()), "H2_n": int(h2.sum()),
                        "H1_minus_H2": float(pic_r[h1].mean() - pic_r[h2].mean()), "se_unpaired": float(np.sqrt(pic_r[h1].var(ddof=1) / h1.sum() + pic_r[h2].var(ddof=1) / h2.sum()))}
print(f"  pinned H1(months 1-6) vs H2(7-12) IC_raw: {OUT['pinned_halves']['H1_IC_raw']:+.4f} vs {OUT['pinned_halves']['H2_IC_raw']:+.4f} (diff {OUT['pinned_halves']['H1_minus_H2']:+.4f} ± {OUT['pinned_halves']['se_unpaired']:.4f}, unpaired)")
# ── decision ──
dr = OUT["common"]["raw/12"]; ds = OUT["common"]["y4s/12"]
detect = (dr["delta_1_minus_k"] >= THR) or (ds["delta_1_minus_k"] >= THR)
OUT["decision"] = {"threshold": THR, "raw_delta_1_12": dr["delta_1_minus_k"], "raw_se": dr["se"], "raw_ci": [dr["ci_lo"], dr["ci_hi"]], "y4s_delta_1_12": ds["delta_1_minus_k"], "y4s_se": ds["se"], "y4s_ci": [ds["ci_lo"], ds["ci_hi"]],
                   "decay_detectable": bool(detect), "K3": "RUN" if detect else "SKIP"}
print(f"\nD1 DECISION (frozen: paired IC(age1)−IC(age12) on the common set, either target ≥ {THR} ⇒ K3 runs): raw {dr['delta_1_minus_k']:+.4f} ± {dr['se']:.4f} CI[{dr['ci_lo']:+.4f},{dr['ci_hi']:+.4f}] ; "
      f"y4s {ds['delta_1_minus_k']:+.4f} ± {ds['se']:.4f} CI[{ds['ci_lo']:+.4f},{ds['ci_hi']:+.4f}] ⇒ 12-month decay {'≥' if detect else '<'} {THR}: K3 {'RUNS' if detect else 'SKIPPED'}")
json.dump(OUT, open(f"{ROOT}/d1_curve.json", "w"), indent=1)
print(f"wrote {ROOT}/d1_curve.json")
