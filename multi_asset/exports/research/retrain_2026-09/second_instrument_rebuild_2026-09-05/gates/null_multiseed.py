"""null_multiseed.py — POST-HOC DIAGNOSTIC for G4 (iii) (lead instruction 09-05; NOT a gate, the frozen G4b verdict stands).
Same X/Y/A construction, fold rule and LightGBM parameters as gate_G4b.py (400 trees); the within-year label permutation is refit for
10 seeds (0..9; seeds 0,1,2 reproduce the gate run) on every fold. Per fold: null IC per seed, mean, empirical sd (ddof=1), t = mean/(sd/√10),
share beyond ±2·SE_anchor and ±2·SE_dayblock (the analytic SEs of the gate), ratio sd/SE_anchor, and the expected exceedance of 15
independent two-sided 2σ tests (1−(1−p)^15, p = 2·(1−Φ(2))). Answers: null mean ≠ 0 (leakage-like) vs mean ≈ 0 with sd > SE (under-estimated SE)."""
import os, sys, json, time, hashlib, math
import numpy as np
from scipy.stats import rankdata, spearmanr, norm
import lightgbm as lgb
ROOT = os.environ.get("JR_ROOT", "/workspace/review_scratch/jpline_rebuild")
NSEED = int(os.environ.get("NULL_SEEDS", "10"))
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
T0 = time.time()
def log(*a): print(f"[{time.time()-T0:7.0f}s]", *a, flush=True)
FEA = np.load(f"{ROOT}/data/wide_fea_hist_rebuilt.npy", mmap_mode="r")
MT = np.load(f"{ROOT}/data/wide_fea_hist_meta_rebuilt.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; names = [str(n) for n in MT["names"]]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); nA = len(E_ts); NW = 829
keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
PRED0 = np.load(f"{ROOT}/data/slow_pred_hist_oos_rebuilt.npy")
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
def anchor_ics(P, anchors):
    return np.array([sp(P[a, members[a]], y4[a, members[a]]) for a in anchors])
rows_X, rows_y, rows_a = [], [], []
for i in range(nA):
    m = members[i]; yv = y4[i, m]; ok = np.isfinite(yv)
    if ok.sum() < 50: continue
    rr = rankdata(yv[ok]) / max(ok.sum() - 1, 1) - 0.5
    rows_X.append(np.asarray(FEA[i, m[ok]][:, keep], np.float32)); rows_y.append(rr.astype(np.float32)); rows_a.append(np.full(ok.sum(), i, np.int32))
X = np.concatenate(rows_X); Y = np.concatenate(rows_y); A = np.concatenate(rows_a); YRA = yrs[A]; del rows_X, rows_y, rows_a
log("X", X.shape)
PAR = dict(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8, colsample_bytree=0.8, n_jobs=-1, verbose=-1)
FOLDS = (2022, 2023, 2024, 2025, 2026)
out = {"self_sha256": sha(os.path.abspath(__file__)), "note": "post-hoc diagnostic, not a gate", "n_seeds": NSEED, "n_trees": PAR["n_estimators"], "folds": {}}
p2 = 2 * (1 - norm.cdf(2)); out["expected_exceedance_15_tests"] = {"p_two_sided_2sigma": p2, "P_at_least_one_of_15": 1 - (1 - p2) ** 15, "expected_count_of_15": 15 * p2}
for YV in FOLDS:
    tr = YRA < YV; te = YRA == YV
    anchors = np.unique(A[te]); ics = anchor_ics(PRED0, anchors)
    se_a = float(np.nanstd(ics) / np.sqrt(np.isfinite(ics).sum()))
    dd = np.array([time.strftime("%Y-%m-%d", time.gmtime(int(E_ts[a]))) for a in anchors]); ud, inv = np.unique(dd, return_inverse=True); okv = np.isfinite(ics)
    dsum = np.bincount(inv[okv], weights=ics[okv], minlength=len(ud)); dcnt = np.bincount(inv[okv], minlength=len(ud)); dm = dsum[dcnt > 0] / dcnt[dcnt > 0]
    se_d = float(np.std(dm, ddof=1) / np.sqrt(len(dm)))
    nulls = []
    for seed in range(NSEED):
        rng = np.random.default_rng(seed); Yp = Y.copy()
        for y in np.unique(YRA[tr]):
            idx = np.where(tr & (YRA == y))[0]; Yp[idx] = Yp[rng.permutation(idx)]
        g = lgb.LGBMRegressor(**PAR).fit(X[tr], Yp[tr]); pv = g.predict(X[te]); P = np.full((nA, NW), np.nan, np.float32); a_te = A[te]
        for a in np.unique(a_te):
            s_ = a_te == a; m = members[a]; okm = np.isfinite(y4[a, m]); P[a, m[okm]] = pv[s_]
        nulls.append(float(np.nanmean(anchor_ics(P, np.unique(a_te)))))
        log(f"fold {YV} seed {seed}: null IC {nulls[-1]:+.5f}")
    nv = np.array(nulls); mean = float(nv.mean()); sd = float(nv.std(ddof=1)); t = mean / (sd / math.sqrt(len(nv))) if sd > 0 else float("nan")
    rec = {"true_ic": float(np.nanmean(ics)), "se_anchor": se_a, "se_dayblock": se_d, "nulls": nulls, "null_mean": mean, "null_sd_empirical": sd, "t_mean_vs_zero": t,
           "share_beyond_2se_anchor": float(np.mean(np.abs(nv) > 2 * se_a)), "share_beyond_2se_dayblock": float(np.mean(np.abs(nv) > 2 * se_d)),
           "sd_over_se_anchor": sd / se_a, "sd_over_se_dayblock": sd / se_d, "mean_within_2se_anchor": bool(abs(mean) < 2 * se_a),
           "share_beyond_2sd_empirical": float(np.mean(np.abs(nv - mean) > 2 * sd))}
    out["folds"][str(YV)] = rec
    log(f"FOLD {YV}: true IC {rec['true_ic']:+.4f}; null mean {mean:+.5f} (t vs 0 = {t:+.2f}), empirical sd {sd:.5f}; SE_anchor {se_a:.5f} (sd/SE {sd/se_a:.2f}), SE_dayblock {se_d:.5f} (sd/SE {sd/se_d:.2f}); share beyond 2·SE_anchor {rec['share_beyond_2se_anchor']:.2f}, beyond 2·SE_dayblock {rec['share_beyond_2se_dayblock']:.2f}")
json.dump(out, open(f"{ROOT}/results/G4b_multiseed.json", "w"), indent=1)
log("wrote results/G4b_multiseed.json; expected exceedance of 15 independent 2σ tests:", out["expected_exceedance_15_tests"])
