"""d1w_curve.py — WEEKLY-resolution IC-by-model-age curve from the K3 weekly boosters (team-lead addendum 2026-09-05: diagnostic only, not a decision
input, criteria unchanged). Read-only inputs; writes d1w_curve.json + d1w_matrices.npz + d1w_pred_age{1..8}.npy here.
Loads models_rollw1/fold*.txt (saved by pod_king_cadence.py MODE=weekly1); each weekly model predicts every row in [test_first, test_first + 8 weeks);
per-(model, anchor) rank-IC (Spearman over meta members with finite target, >=30 pairs) vs raw y4 (meta) and dlw y4s, and king leg (production leg definition).
Age w (1..8 weeks) for an anchor in calendar week W (Monday 00:00Z index from 2024-01-01) = model whose own test week is W-(w-1); age 1 = K3 itself.
Receipt: age-1 stitch from the saved boosters vs slow_pred_rollw1.npy (array_equal / max|Δ|). Data preparation block = pod_king_cadence.py verbatim.
"""
import os, sys, json, time, hashlib, calendar
import numpy as np
sys.path.insert(0, "/workspace")
from scipy.stats import rankdata, spearmanr
import lightgbm as lgb
ROOT = "/workspace/review_scratch/cadence_seats/axisA"; WMAX = 8; NB = 2000; SEED = 20260905
F = json.load(open(f"{ROOT}/folds_rollw1.json")); folds = F["folds"]
print("CONFIG " + json.dumps({"folds_json": f"{ROOT}/folds_rollw1.json", "n_models": len(folds), "WMAX_weeks": WMAX, "NB": NB, "seed": SEED, "self_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest(),
                              "lightgbm": lgb.__version__, "train_script_sha256": F["config"]["self_sha256"]}), flush=True)
t00 = time.time()
# ── production data preparation (pod_king_cadence.py / pod_export_bundle_v3.py L22, L26-47 verbatim) ──
PINS = json.load(open("/workspace/live_pins.json"))
FEA = np.load("/workspace/data/wide_fea_v2ext.npy")
MT = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]
names = [str(n) for n in MT["names"]]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
nA = len(E_ts); NW = 829
keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
assert [names[k] for k in keep] == PINS["keep_names"], "keep_names 与在役不一致"
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
rows_X, rows_y, rows_a = [], [], []
for i in range(nA):
    m = members[i]
    yv = y4[i, m]; ok = np.isfinite(yv)
    if ok.sum() < 50: continue
    rr = rankdata(yv[ok]) / max(ok.sum() - 1, 1) - 0.5
    rows_X.append(FEA[i, m[ok]][:, keep].astype(np.float32))
    rows_y.append(rr.astype(np.float32)); rows_a.append(np.full(ok.sum(), i, np.int32))
X = np.concatenate(rows_X); Y = np.concatenate(rows_y); A = np.concatenate(rows_a)
# ── end verbatim block ──
del rows_X, rows_y, rows_a, FEA
A_ts = E_ts[A]
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
print(f"PREP X {X.shape} rows_anchors {len(np.unique(A))}/{nA} prep_s {time.time()-t00:.1f}", flush=True)
T0 = calendar.timegm((2024, 1, 1, 0, 0, 0)); wk = np.where(E_ts >= T0, (E_ts - T0) // (7 * 86400), -1).astype(np.int64)
nM = len(folds)
for fi, f in enumerate(folds):
    assert f["fold"] == fi and f["key"] == time.strftime("%Y-%m-%d", time.gmtime(T0 + fi * 7 * 86400)), (fi, f["key"])
    assert (f["test_first"] - T0) // (7 * 86400) == fi, (fi, f["test_first"])
PW = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True); pw_ts = set(PW["ts"].astype(np.int64).tolist())
DT = np.load("/workspace/data/dlw_targets.npz", allow_pickle=True); dmap = {int(t): k for k, t in enumerate(DT["E_ts"].astype(np.int64))}; y4s_src = DT["y4s"]
Y4S = np.full((nA, NW), np.nan, np.float32)
for i in range(nA):
    kk = dmap.get(int(E_ts[i]))
    if kk is not None: Y4S[i] = y4s_src[kk]
has_panel = np.array([int(t) in pw_ts for t in E_ts])
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 10: out[ok] = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
    return out
def leg(score, yv):
    ok = np.isfinite(yv); z = np.nan_to_num(xz(score)); z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0
    g = np.abs(z).sum(); return float((z / g * np.nan_to_num(yv, nan=0.0)).sum() * 1e4) if g > 1e-9 else 0.0
IC_raw = np.full((nM, nA), np.nan, np.float32); IC_y4s = IC_raw.copy(); LEG_raw = IC_raw.copy(); LEG_y4s = IC_raw.copy()
AGE = {w: np.full((nA, NW), np.nan, np.float32) for w in range(1, WMAX + 1)}
label_end = np.array([f["train_last"] for f in folds], np.int64) + 48 * 300
t1 = time.time(); npred = 0
for fi, f in enumerate(folds):
    bst = lgb.Booster(model_file=f"{ROOT}/models_rollw1/fold{fi:03d}_{f['key']}.txt")
    tf = int(f["test_first"]); sel = (A_ts >= tf) & (A_ts < tf + WMAX * 7 * 86400)
    if not sel.any(): continue
    pv = bst.predict(X[sel]); a_s = A[sel]; npred += int(sel.sum())
    bounds = np.searchsorted(a_s, np.arange(nA + 1))
    for a in np.unique(a_s):
        m = members[a]; okm = np.isfinite(y4[a, m]); p = np.full(len(m), np.nan); p[okm] = pv[bounds[a]:bounds[a + 1]]
        IC_raw[fi, a] = sp(p, y4[a, m]); IC_y4s[fi, a] = sp(p, Y4S[a, m])
        if has_panel[a]: LEG_raw[fi, a] = leg(p, y4[a, m]); LEG_y4s[fi, a] = leg(p, Y4S[a, m])
        w = int(wk[a] - fi + 1)
        if 1 <= w <= WMAX: AGE[w][a, m[okm]] = pv[bounds[a]:bounds[a + 1]]
    if fi % 20 == 0: print(f"  model {fi}/{nM} predicted rows so far {npred} ({time.time()-t1:.0f}s)", flush=True)
K3 = np.load(f"{ROOT}/slow_pred_rollw1.npy")
eq = bool(np.array_equal(AGE[1], K3, equal_nan=True)); maxabs = float(np.nanmax(np.abs(AGE[1] - K3)))
print(f"RECEIPT age-1 stitch (saved boosters) vs slow_pred_rollw1.npy: array_equal(equal_nan) {eq} max|Δ| {maxabs:.3e}; predicted rows {npred}; finite IC_raw cells {int(np.isfinite(IC_raw).sum())} ({time.time()-t1:.0f}s)", flush=True)
for w in range(1, WMAX + 1): np.save(f"{ROOT}/d1w_pred_age{w}.npy", AGE[w])
np.savez_compressed(f"{ROOT}/d1w_matrices.npz", IC_raw=IC_raw, IC_y4s=IC_y4s, LEG_raw=LEG_raw, LEG_y4s=LEG_y4s, E_ts=E_ts, week_index=wk, model_test_first=np.array([f["test_first"] for f in folds]), model_train_last=np.array([f["train_last"] for f in folds]))
# ── curves ──
idx = np.arange(nA); days = np.array([time.strftime("%Y-%m-%d", time.gmtime(int(t))) for t in E_ts]); mon = np.array([time.gmtime(int(t)).tm_mon for t in E_ts])
def age_series(M, w):
    out = np.full(nA, np.nan); fi = wk - (w - 1); ok = (wk >= 0) & (fi >= 0) & (fi < nM); out[ok] = M[fi[ok], idx[ok]]; return out
def age_days(w):
    out = np.full(nA, np.nan); fi = wk - (w - 1); ok = (wk >= 0) & (fi >= 0) & (fi < nM); out[ok] = (E_ts[ok] - label_end[fi[ok]]) / 86400.0; return out
rng = np.random.default_rng(SEED)
def boot_ci(x, d):
    ud, inv = np.unique(d, return_inverse=True); nd = len(ud); sums = np.bincount(inv, weights=x, minlength=nd); cnts = np.bincount(inv, minlength=nd)
    r = rng.integers(0, nd, size=(NB, nd)); means = sums[r].sum(1) / cnts[r].sum(1); return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)), int(nd)
ICm = {"raw": IC_raw.astype(np.float64), "y4s": IC_y4s.astype(np.float64)}; LEGm = {"raw": LEG_raw.astype(np.float64), "y4s": LEG_y4s.astype(np.float64)}
Aw = {(t, w): age_series(ICm[t], w) for t in ("raw", "y4s") for w in range(1, WMAX + 1)}; Lw = {(t, w): age_series(LEGm[t], w) for t in ("raw", "y4s") for w in range(1, WMAX + 1)}
OUT = {"receipt": {"age1_equal_k3": eq, "age1_maxabs_vs_k3": maxabs, "predicted_rows": npred}, "full": {}, "common": {}, "days_bins": {}, "fit_time": {}}
print(f"\nTABLE W-A — weekly age (weeks), FULL anchor set available at each age")
print(f"{'age_w':>5s} {'n_raw':>6s} {'IC_raw':>8s} {'n_y4s':>6s} {'IC_y4s':>8s} {'days mean/min/max':>22s} | {'n_leg':>6s} {'leg_raw':>8s} {'S_raw':>7s} {'leg_y4s':>8s} {'S_y4s':>7s}")
for w in range(1, WMAX + 1):
    a = Aw[("raw", w)]; b = Aw[("y4s", w)]; lr = Lw[("raw", w)]; ls = Lw[("y4s", w)]; dd = age_days(w); fa = np.isfinite(a); fb = np.isfinite(b); fl = np.isfinite(lr); fs = np.isfinite(ls)
    rec = {"n_raw": int(fa.sum()), "IC_raw": float(a[fa].mean()), "n_y4s": int(fb.sum()), "IC_y4s": float(b[fb].mean()), "days_mean": float(dd[fa].mean()), "days_min": float(dd[fa].min()), "days_max": float(dd[fa].max()),
           "n_leg": int(fl.sum()), "leg_raw": float(lr[fl].mean()), "S_raw": float(lr[fl].mean() / lr[fl].std(ddof=1)), "leg_y4s": float(ls[fs].mean()), "S_y4s": float(ls[fs].mean() / ls[fs].std(ddof=1))}
    OUT["full"][w] = rec
    print(f"{w:5d} {rec['n_raw']:6d} {rec['IC_raw']:+8.4f} {rec['n_y4s']:6d} {rec['IC_y4s']:+8.4f} {rec['days_mean']:8.1f}/{rec['days_min']:5.1f}/{rec['days_max']:5.1f} | {rec['n_leg']:6d} {rec['leg_raw']:+8.3f} {rec['S_raw']:+7.3f} {rec['leg_y4s']:+8.3f} {rec['S_y4s']:+7.3f}")
for t in ("raw", "y4s"):
    common = np.ones(nA, bool)
    for w in range(1, WMAX + 1): common &= np.isfinite(Aw[(t, w)])
    n = int(common.sum()); base = Aw[(t, 1)][common]
    lc = common.copy()
    for w in range(1, WMAX + 1): lc &= np.isfinite(Lw[(t, w)])
    print(f"\nTABLE W-B[{t}] — COMMON anchor set (all 8 weekly ages finite): n={n}; paired Δ = IC(age 1w) − IC(age w), s.e. over anchors, day-block bootstrap CI95")
    print(f"{'age_w':>5s} {'IC':>8s} {'Δ(1−w)':>9s} {'s.e.':>7s} {'CI95 lo':>8s} {'CI95 hi':>8s} | {'leg':>8s} {'S':>7s} {'Δleg(1−w)':>10s} {'s.e.':>7s}")
    for w in range(1, WMAX + 1):
        v = Aw[(t, w)][common]; d = base - v; se = float(d.std(ddof=1) / np.sqrt(n)) if w > 1 else 0.0; lo, hi, nd = boot_ci(d, days[common]) if w > 1 else (0.0, 0.0, 0)
        lv = Lw[(t, w)][lc]; ld = Lw[(t, 1)][lc] - lv; lse = float(ld.std(ddof=1) / np.sqrt(lc.sum())) if w > 1 else 0.0
        rec = {"n": n, "IC": float(v.mean()), "delta_1_minus_w": float(d.mean()), "se": se, "ci_lo": lo, "ci_hi": hi, "n_leg": int(lc.sum()), "leg": float(lv.mean()), "S": float(lv.mean() / lv.std(ddof=1)), "dleg_1_minus_w": float(ld.mean()), "dleg_se": lse}
        OUT["common"][f"{t}/{w}"] = rec
        print(f"{w:5d} {rec['IC']:+8.4f} {rec['delta_1_minus_w']:+9.4f} {se:7.4f} {lo:+8.4f} {hi:+8.4f} | {rec['leg']:+8.3f} {rec['S']:+7.3f} {rec['dleg_1_minus_w']:+10.3f} {lse:7.3f}")
    # weeks 1-4 vs weeks 5-8 (≈ month 1 vs month 2 in the monthly curve), paired on the common set
    m14 = np.mean([Aw[(t, w)][common] for w in (1, 2, 3, 4)], axis=0); m58 = np.mean([Aw[(t, w)][common] for w in (5, 6, 7, 8)], axis=0); d = m14 - m58
    OUT["common"][f"{t}/w1-4_minus_w5-8"] = {"mean_w1_4": float(m14.mean()), "mean_w5_8": float(m58.mean()), "delta": float(d.mean()), "se": float(d.std(ddof=1) / np.sqrt(n))}
    print(f"  weeks 1-4 mean IC {m14.mean():+.4f} vs weeks 5-8 {m58.mean():+.4f}: paired Δ {d.mean():+.4f} ± {d.std(ddof=1)/np.sqrt(n):.4f}")
    OUT["common"][f"{t}/n"] = n
print(f"\nTABLE W-D — all (model, anchor) pairs binned by days since the model's cutoff (7-day bins to 56 d)")
DAYS = (E_ts[None, :] - label_end[:, None]) / 86400.0
for lo_d in range(0, 56, 7):
    sel = (DAYS >= lo_d) & (DAYS < lo_d + 7) & np.isfinite(ICm["raw"]); n = int(sel.sum())
    if n == 0: continue
    sy = sel & np.isfinite(ICm["y4s"]); sl = sel & np.isfinite(LEGm["raw"]); lr = LEGm["raw"][sl]
    rec = {"pairs": n, "IC_raw": float(ICm["raw"][sel].mean()), "IC_y4s": float(ICm["y4s"][sy].mean()), "leg_raw": float(lr.mean()), "S_raw": float(lr.mean() / lr.std(ddof=1))}
    OUT["days_bins"][f"{lo_d}-{lo_d+7}"] = rec; print(f"{lo_d:3d}-{lo_d+7:<3d} {n:7d} {rec['IC_raw']:+8.4f} {rec['IC_y4s']:+8.4f} {rec['leg_raw']:+8.3f} {rec['S_raw']:+7.3f}")
fits = [f["fit_s"] for f in folds]; OUT["fit_time"] = {"n_fits": len(fits), "fit_s_min": min(fits), "fit_s_median": sorted(fits)[len(fits) // 2], "fit_s_max": max(fits), "fit_s_total": F["total_fit_s"], "wall_s_total": F["wall_s"], "n_jobs": F["config"]["NJOBS"]}
print(f"\nFIT TIME (weekly, n_jobs {F['config']['NJOBS']}): {len(fits)} fits, per fit min/median/max {min(fits)}/{sorted(fits)[len(fits)//2]}/{max(fits)} s, total fit {F['total_fit_s']} s, wall {F['wall_s']} s")
json.dump(OUT, open(f"{ROOT}/d1w_curve.json", "w"), indent=1); print(f"wrote {ROOT}/d1w_curve.json ({time.time()-t00:.0f}s)")
