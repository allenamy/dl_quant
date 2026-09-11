"""r10_combine STEP 4 -- optimism penalty on the fitted allocation, return-preserving
frontier, regime splits, per-year table, and the distance-to-goal arithmetic.

ENV WHITELIST (E-0826-D) = EMPTY SET.  Caliber pin v4 (2026-09-09).
Inputs: series/books_on_pinned_axis.npz written by devices/s3_combine_final.py.
"""
import os, sys, json, hashlib, calendar, time
ENV_SEEN = sorted(os.environ.keys())
_FORBID = ("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
           "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG","TRADE_TOPN","TILT",
           "TILT_TAU","TILT_K","KMOD","KMOD_F10","KMOD_L","KMOD_AGREE","KTAIL","SEATF10","SEATNET",
           "FUNDSCALE","REF_SKIP","SLEEVE","CDAMP","LTRIM_TH","FTRIM_TH","RNSM","FTPOS","PANEL",
           "PANEL_IN","EXPORT_PANEL","EMA_STATE_JSON","JUDGE_HC","JUDGE_REQUIRE_W")
_v = [k for k in _FORBID if k in os.environ]
assert not _v, "E-0826-D env violation: %r" % _v
import numpy as np
from scipy.optimize import minimize

def T(*a): return calendar.timegm(a + (0,)*(6-len(a)))
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
OUT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/r10_combine"
SER = OUT + "/series/books_on_pinned_axis.npz"
APY = 2190.0; B = 2000; TARGET = 3.966
z = np.load(SER, allow_pickle=True)
TS = z["ts"]; NAMES = [str(x) for x in z["names"]]; G = z["G"]; TU = z["TU"]
n = len(TS); SE_SR = float(np.sqrt(APY/n))
IX = {k: i for i, k in enumerate(NAMES)}
R = {"step": "S4_OPTIMISM_REGIME", "self_sha256": sha(os.path.abspath(__file__)),
     "env_whitelist": [], "env_seen_at_runtime": ENV_SEEN,
     "input": {"path": SER, "sha256": sha(SER)}, "n": int(n),
     "SE_ann_sharpe": round(SE_SR, 4), "numpy": np.__version__}

def ann(x):
    s = np.std(x, ddof=1); return float(np.mean(x)/s*np.sqrt(APY)) if s > 0 else float("nan")
def mdd(x):
    c = np.concatenate([[0.0], np.cumsum(x)]); return float(np.max(np.maximum.accumulate(c)-c))
DAY = TS // 86400; ud, inv = np.unique(DAY, return_inverse=True); nd = len(ud)
def worstday(x):
    d = np.bincount(inv, weights=x, minlength=nd); i = int(np.argmin(d))
    return float(d[i]), time.strftime("%Y-%m-%d", time.gmtime(int(ud[i])*86400))
order = np.argsort(inv, kind="stable")
st = np.searchsorted(inv[order], np.arange(nd)); en = np.append(st[1:], len(order))
rng = np.random.default_rng([20260905, 1]); picks = rng.integers(0, nd, size=(B, nd))
BOOT = [np.concatenate([order[st[j]:en[j]] for j in picks[b]]) for b in range(B)]
def ci(v):
    v = np.asarray(v); v = v[np.isfinite(v)]
    return [round(float(np.percentile(v, 2.5)), 4), round(float(np.percentile(v, 97.5)), 4)]
SRB = lambda x: np.mean(x)/np.std(x, ddof=1)*np.sqrt(APY)

def fit_maxsharpe(Gk, minmean=None):
    m_ = Gk.mean(0); C_ = np.cov(Gk.T, ddof=1); k = Gk.shape[1]
    def neg(c):
        v = float(c @ C_ @ c); return 1e6 if v <= 0 else -float((c @ m_)/np.sqrt(v))
    cons = [{"type": "eq", "fun": lambda c: c.sum()-1.0}]
    if minmean is not None:
        cons.append({"type": "ineq", "fun": lambda c: float(c @ m_) - minmean})
    best = None
    for s0 in [np.ones(k)/k] + [np.eye(k)[i]*0.9 + 0.1/k for i in range(k)]:
        try:
            r_ = minimize(neg, s0, method="SLSQP", bounds=[(0, 1)]*k, constraints=cons,
                          options={"maxiter": 800, "ftol": 1e-12})
            if r_.success and (best is None or r_.fun < best.fun): best = r_
        except Exception: pass
    if best is None: return np.eye(k)[0]
    c = np.clip(best.x, 0, 1); return c/c.sum()

POOLS = {"POOL_A_all_primary":  ["A0","TSMOM","VRP","CMUM","SLOW","COINT","REVS"],
         "POOL_B_survivors":    ["A0","TSMOM","VRP"],
         "POOL_C_survivors_bestarm": ["A0","TSMOM_best","VRP","CMUM_best","SLOW_best"]}
gA0 = G[:, IX["A0"]]
def stats(g, turn):
    wd, wdd = worstday(g)
    srb = np.array([SRB(g[ii]) for ii in BOOT])
    return {"mean_g_bps": round(float(g.mean()), 4), "mean_g_CI95": ci([g[ii].mean() for ii in BOOT]),
            "ann_sharpe": round(ann(g), 4), "ann_sharpe_CI95": ci(srb), "SE_ann_sharpe": round(SE_SR, 4),
            "sd_per_anchor_bps": round(float(np.std(g, ddof=1)), 4),
            "turnover_per_anchor": round(float(turn.mean()), 5),
            "maxDD_bps_of_gross": round(mdd(g), 1),
            "worst_UTC_day_bps": round(wd, 1), "worst_UTC_day": wdd,
            "NAV_pct_per_yr_at_2x_gross": round(float(g.mean())*APY*2.0/100.0, 2),
            "gap_to_target_in_SE": round((TARGET-ann(g))/SE_SR, 2),
            "CI95_lower_clears_3.0": bool(ci(srb)[0] > 3.0)}

# ---------------------------------------------------------------- return-preserving frontier
print("=== RETURN-PRESERVING max-Sharpe (c>=0, sum c=1, mean_g >= A0's %.4f) ===" % gA0.mean())
RP = {}
for pn, keys in POOLS.items():
    idx = [IX[k] for k in keys]; Gk = G[:, idx]; Tk = TU[:, idx]
    c = fit_maxsharpe(Gk, minmean=float(gA0.mean()))
    g = Gk @ c; s = stats(g, Tk @ c)
    s.update({"books": keys, "gross_share": [round(float(x), 5) for x in c],
              "d_ann_sharpe_vs_A0": round(ann(g)-ann(gA0), 4),
              "d_ann_sharpe_vs_A0_in_SE": round((ann(g)-ann(gA0))/SE_SR, 3)})
    RP[pn] = s
    print("%-28s SR %+7.4f (dA0 %+6.4f = %+5.2f SE)  g %+7.4f  NAV%%/yr %+6.2f  wday %+8.1f  c=%s"
          % (pn, s["ann_sharpe"], s["d_ann_sharpe_vs_A0"], s["d_ann_sharpe_vs_A0_in_SE"],
             s["mean_g_bps"], s["NAV_pct_per_yr_at_2x_gross"], s["worst_UTC_day_bps"],
             np.round(c, 4).tolist()), flush=True)
R["return_preserving_maxsharpe"] = RP

# ---------------------------------------------------------------- optimism penalty
print("\n=== OPTIMISM PENALTY on the in-sample-fitted max-Sharpe allocation ===")
OPT = {}
for pn, keys in POOLS.items():
    idx = [IX[k] for k in keys]; Gk = G[:, idx]; k = len(keys)
    c_is = fit_maxsharpe(Gk); sr_is = ann(Gk @ c_is)
    # (1) analytic: E[SRhat^2] ~ SR^2 + K/n  (per-anchor), annualise by APY
    defl = float(np.sqrt(max(0.0, sr_is**2 - APY*k/n)))
    # (2) contiguous-time 5-fold block CV on UTC days
    folds = np.array_split(np.arange(nd), 5); oos = []
    for f in folds:
        te = np.isin(inv, f); tr = ~te
        c = fit_maxsharpe(Gk[tr]); oos.append(Gk[te] @ c)
    g_cv = np.concatenate(oos); sr_cv = ann(g_cv)
    # (3) TRAIN 2022-06-30..2024-12-31 -> HOLDOUT 2025-01-01..2026-08-30
    tr = TS <= T(2024, 12, 31, 20); ho = TS >= T(2025, 1, 1, 0)
    c_tr = fit_maxsharpe(Gk[tr]); sr_tr = ann(Gk[tr] @ c_tr); sr_ho = ann(Gk[ho] @ c_tr)
    # (4) day-block bootstrap out-of-bag optimism (300 resamples)
    rng2 = np.random.default_rng([20260905, 77]); gaps = []
    for b in range(300):
        pk = rng2.integers(0, nd, nd)
        ib = np.concatenate([order[st[j]:en[j]] for j in pk])
        oob_days = np.setdiff1d(np.arange(nd), np.unique(pk))
        if len(oob_days) < 30: continue
        ob = np.concatenate([order[st[j]:en[j]] for j in oob_days])
        cb = fit_maxsharpe(Gk[ib])
        gaps.append(ann(Gk[ib] @ cb) - ann(Gk[ob] @ cb))
    gaps = np.array(gaps)
    OPT[pn] = {"in_sample_fitted_ann_sharpe": round(sr_is, 4),
               "gross_share_in_sample": [round(float(x), 5) for x in c_is],
               "penalty_1_analytic": {"rule": "SR_true ~ sqrt(SR_IS^2 - APY*K/n), K=#books",
                                      "K": k, "subtracted_sharpe2": round(APY*k/n, 4),
                                      "deflated_ann_sharpe": round(defl, 4),
                                      "penalty": round(sr_is-defl, 4)},
               "penalty_2_blockCV5": {"oos_pooled_ann_sharpe": round(sr_cv, 4),
                                      "oos_mean_g_bps": round(float(g_cv.mean()), 4),
                                      "penalty": round(sr_is-sr_cv, 4)},
               "penalty_3_train_holdout": {"train_ann_sharpe": round(sr_tr, 4),
                                           "holdout_ann_sharpe": round(sr_ho, 4),
                                           "holdout_n": int(ho.sum()),
                                           "holdout_SE": round(float(np.sqrt(APY/ho.sum())), 4),
                                           "penalty": round(sr_tr-sr_ho, 4)},
               "penalty_4_bootstrap_OOB": {"resamples": int(len(gaps)),
                                           "mean_IS_minus_OOB_sharpe": round(float(gaps.mean()), 4),
                                           "p50": round(float(np.median(gaps)), 4)},
               "honest_reading": None}
    worst = max(OPT[pn]["penalty_1_analytic"]["penalty"],
                OPT[pn]["penalty_2_blockCV5"]["penalty"],
                OPT[pn]["penalty_4_bootstrap_OOB"]["mean_IS_minus_OOB_sharpe"])
    OPT[pn]["honest_reading"] = ("in-sample %.4f minus the LARGEST measured penalty %.4f => %.4f"
                                 % (sr_is, worst, sr_is-worst))
    print("%-28s IS %+7.4f | analytic %+7.4f | blockCV5 %+7.4f | holdout %+7.4f | bootOOB gap %+7.4f"
          % (pn, sr_is, defl, sr_cv, sr_ho, gaps.mean()), flush=True)
R["optimism_penalty"] = OPT

# ---------------------------------------------------------------- regime splits
print("\n=== REGIME SPLITS ===")
WIN = {"FULL": np.ones(n, bool),
       "FROZEN_2025-03-01..2026-08-10": (TS >= T(2025,3,1)) & (TS <= T(2026,8,10,20)),
       "Y2026": TS >= T(2026,1,1),
       "HOLDOUT_2025-01-01..": TS >= T(2025,1,1)}
ALLOCS = {"A0_alone": ("A0_alone", ["A0"], np.array([1.0]))}
for pn, keys in POOLS.items():
    idx = [IX[k] for k in keys]
    sd = np.array([np.std(G[:, i], ddof=1) for i in idx]); er = (1/sd)/np.sum(1/sd)
    ALLOCS[pn+"|equal_risk"] = (pn, keys, er)
    ALLOCS[pn+"|maxSharpe_IS"] = (pn, keys, fit_maxsharpe(G[:, idx]))
    ALLOCS[pn+"|maxSharpe_RP"] = (pn, keys, fit_maxsharpe(G[:, idx], minmean=float(gA0.mean())))
REG = {}
for aname, (pn, keys, c) in ALLOCS.items():
    idx = [IX[k] for k in keys]; g = G[:, idx] @ c
    REG[aname] = {}
    for wn, m in WIN.items():
        if m.sum() < 200: continue
        se = float(np.sqrt(APY/m.sum()))
        REG[aname][wn] = {"n": int(m.sum()), "mean_g_bps": round(float(g[m].mean()), 4),
                          "ann_sharpe": round(ann(g[m]), 4), "SE_ann_sharpe": round(se, 4),
                          "A0_ann_sharpe": round(ann(gA0[m]), 4),
                          "d_vs_A0_in_SE": round((ann(g[m])-ann(gA0[m]))/se, 3),
                          "gap_to_target_in_SE": round((TARGET-ann(g[m]))/se, 2)}
    print("%-42s FULL %+6.3f  FROZEN %+6.3f (A0 %+6.3f)  2026 %+6.3f (A0 %+6.3f)"
          % (aname, REG[aname]["FULL"]["ann_sharpe"],
             REG[aname]["FROZEN_2025-03-01..2026-08-10"]["ann_sharpe"],
             REG[aname]["FROZEN_2025-03-01..2026-08-10"]["A0_ann_sharpe"],
             REG[aname]["Y2026"]["ann_sharpe"], REG[aname]["Y2026"]["A0_ann_sharpe"]), flush=True)
R["regime_splits"] = REG

# ---------------------------------------------------------------- per-year
YR = {}
yrs = np.array([int(time.strftime("%Y", time.gmtime(int(t)))) for t in TS])
for aname, (pn, keys, c) in ALLOCS.items():
    idx = [IX[k] for k in keys]; g = G[:, idx] @ c; YR[aname] = {}
    for y in sorted(set(yrs.tolist())):
        m = yrs == y
        YR[aname][str(y)] = {"n": int(m.sum()), "mean_g_bps": round(float(g[m].mean()), 4),
                             "ann_sharpe": round(ann(g[m]), 4),
                             "NAV_pct_at_2x": round(float(g[m].sum())*2.0/100.0, 2)}
R["per_year"] = YR

# ---------------------------------------------------------------- distance arithmetic
best_key = max([k for k in ALLOCS if k != "A0_alone"],
               key=lambda k: REG[k]["FULL"]["ann_sharpe"])
srA0 = ann(gA0)
def need(sr_now):
    d2 = TARGET**2 - sr_now**2
    return {"gap_sharpe": round(TARGET-sr_now, 4), "gap_in_SE": round((TARGET-sr_now)/SE_SR, 2),
            "one_uncorrelated_source_standalone_sharpe_needed": round(float(np.sqrt(max(0.0, d2))), 4),
            "n_uncorrelated_copies_of_this_book_needed": round(float(d2/sr_now**2), 2) if sr_now > 0 else None}
R["distance_to_goal"] = {"target_point_estimate": TARGET,
                         "target_meaning": "CI95 lower bound above 3.0 at n=9138, i.e. point estimate 3.0 + 2*SE = 3.0+2*0.4895 = 3.979 (the brief's 3.966 uses a slightly different rounding); both are quoted",
                         "A0_alone": dict(ann_sharpe=round(srA0, 4), **need(srA0)),
                         "best_allocation_on_FULL": {"which": best_key,
                             "ann_sharpe": REG[best_key]["FULL"]["ann_sharpe"],
                             **need(REG[best_key]["FULL"]["ann_sharpe"])}}
for k in ("POOL_A_all_primary|maxSharpe_RP","POOL_B_survivors|maxSharpe_RP","POOL_C_survivors_bestarm|maxSharpe_IS"):
    R["distance_to_goal"][k] = dict(ann_sharpe=REG[k]["FULL"]["ann_sharpe"], **need(REG[k]["FULL"]["ann_sharpe"]))

# selection premium ladder
sp = {}
for rule in ("equal_risk", "maxSharpe_IS", "maxSharpe_RP"):
    a = REG["POOL_A_all_primary|"+rule]["FULL"]["ann_sharpe"]
    b = REG["POOL_B_survivors|"+rule]["FULL"]["ann_sharpe"]
    cc = REG["POOL_C_survivors_bestarm|"+rule]["FULL"]["ann_sharpe"]
    sp[rule] = {"POOL_A_all": a, "POOL_B_survivors": b, "POOL_C_best_arm": cc,
                "survivor_premium_B_minus_A": round(b-a, 4),
                "survivor_premium_in_SE": round((b-a)/SE_SR, 3),
                "arm_selection_premium_C_minus_B": round(cc-b, 4),
                "arm_selection_premium_in_SE": round((cc-b)/SE_SR, 3),
                "total_selection_premium_C_minus_A": round(cc-a, 4),
                "total_in_SE": round((cc-a)/SE_SR, 3)}
R["selection_premium"] = sp
print("\n=== SELECTION PREMIUM ===")
for rule, v in sp.items():
    print("%-14s A %+7.4f -> B %+7.4f (survivor %+6.4f) -> C %+7.4f (arm %+6.4f) | total %+6.4f = %+5.2f SE"
          % (rule, v["POOL_A_all"], v["POOL_B_survivors"], v["survivor_premium_B_minus_A"],
             v["POOL_C_best_arm"], v["arm_selection_premium_C_minus_B"],
             v["total_selection_premium_C_minus_A"], v["total_in_SE"]), flush=True)
json.dump(R, open(OUT + "/receipts/S4_OPTIMISM_REGIME.json", "w"), indent=1)
print("\nwrote", OUT + "/receipts/S4_OPTIMISM_REGIME.json", flush=True)
