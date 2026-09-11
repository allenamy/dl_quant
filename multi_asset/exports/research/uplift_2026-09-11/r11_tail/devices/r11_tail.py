#!/usr/bin/env python3
"""r11_tail.py -- re-measure the tail/drawdown/stop family on the PINNED v4 caliber, and derive
the leverage ladder from the return distribution the book actually has.

ZERO-TOUCH: reads only research-repo artifacts. No network, no GPU, no live file touched.
E-0826-D: env whitelist is the EMPTY SET; asserted below.
E-0909-C: every drawdown function prepends the starting point.
E-0904-F: no expm1 is applied to any panel quantity. Intra-day NAV compounding is done with an
          explicit product of (1+r), never via log1p/expm1, so there is no transform to confuse.
"""
import os, sys, json, time, calendar, hashlib
import numpy as np

# ---- E-0826-D: enumerate + assert the env whitelist ------------------------------------------
ENV_WHITELIST = []          # EMPTY SET -- this is an analysis script
_WATCHED = ["CAL","LEGS","PHI","FSEED","FPRED","LOOK","WRULE","W3FIX","MEMBERS_TOPN","TRADE_TOPN",
            "FTRIM","FTRIM_TH","FTPOS","RNSM","LTRIM_TH","CDAMP","SLEEVE","SEATNET","SEATF10",
            "KTAIL","KMOD","KMOD_L","KMOD_AGREE","KMOD_F10","FUNDSCALE","FEMAT_NPZ","UMASK_NPZ",
            "UMASK_SCOPE","REF_SKIP","COSTB_JSON","SLOW_NPY","JUDGE_HC","JUDGE_REQUIRE_W",
            "PANEL_IN","EXPORT_PANEL","EMA_STATE_JSON","OMP_NUM_THREADS","PYTHONHASHSEED"]
_set = {k: os.environ[k] for k in _WATCHED if k in os.environ}
assert _set == {}, f"env whitelist violated (expected empty set), found: {_set}"

ROOT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"
PIN  = f"{ROOT}/r10_screen/CMUM_CARRY/pin/A0_PWR230k_s42.npz"
DEV  = f"{ROOT}/trackA/w10_sleeve.py"
OUT  = f"{ROOT}/r11_tail/receipts"

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""): h.update(ch)
    return h.hexdigest()

# ---- inputs, hashed first hand ----------------------------------------------------------------
INPUTS = {"pin_npz": {"path": PIN, "sha256": sha256(PIN)},
          "pinned_device_w10_sleeve.py": {"path": DEV, "sha256": sha256(DEV)}}
assert INPUTS["pinned_device_w10_sleeve.py"]["sha256"][:16] == "b88e35a46b93d712", "device sha != CALIBER PIN"

Z = np.load(PIN, allow_pickle=True)
CFG = json.loads(str(Z["config_json"]))
assert CFG["UPLIFT"]["self_sha256"][:16] == "b88e35a46b93d712", "artifact was not produced by the pinned device"
assert CFG["CAL"] == "log", "CAL must be 'log' on the v4 pod lineage (E-0904-F: no expm1)"
assert CFG["PHI"] == 0.45 and CFG["LEGS"] == "101" and CFG["WRULE"] == "msharpe" and CFG["LOOK"] == 900
assert CFG["UMASK_SCOPE"] == "m1" and CFG["W3FIX"] is None, "A0 must be the dynamic-seat live form"
assert CFG["COSTB_JSON"].endswith("costb_PWR_G230k.json")

COLS = [str(c) for c in Z["cols"]]; C = {k: i for i, k in enumerate(COLS)}
R = Z["rec"]
ts_all = R[:, C["ts"]].astype(np.int64)
g_all  = R[:, C["net_ex"]] / R[:, C["gross_total"]]           # bps / anchor / unit gross
tovfrac_all = R[:, C["turnover"]] / R[:, C["gross_total"]]    # turnover per unit gross (file caliber)
costfrac_all = R[:, C["cost_ex"]] / R[:, C["gross_total"]]    # modelled cost, bps per unit gross

WARM = 900                                                    # E-0911-A
UB   = calendar.timegm(time.strptime("2026-08-30 20", "%Y-%m-%d %H"))   # E-0911-D instrument ceiling
sl   = slice(WARM, None)
m    = ts_all[sl] <= UB
ts   = ts_all[sl][m]; g = g_all[sl][m]; tovf = tovfrac_all[sl][m]; costf = costfrac_all[sl][m]
assert len(g) == 9138, f"primary window must be n=9138, got {len(g)}"
assert abs(float(g.mean()) - 0.6342) < 5e-4 and abs(float(g.mean()/g.std(ddof=1)*np.sqrt(2190)) - 1.2912) < 5e-4, \
    "primary window must reproduce the closeout planning number"

days = ts // 86400
ud, inv, cnt = np.unique(days, return_inverse=True, return_counts=True)
assert (cnt == 6).all(), "primary window must be whole UTC days of 6 anchors"
NDAY = len(ud); assert NDAY == 1523
G = g.reshape(NDAY, 6)                     # per-day anchor grid, chronological
TOVF = tovf.reshape(NDAY, 6)
ANN_D = 365.0

# ---- cost repricing arms ----------------------------------------------------------------------
GAP = 2.0884       # bps per unit traded notional, r9_critic C1 (realised 5.0421 - pinned 2.9537)
RATE = 2.9537      # pinned model book-average bps per unit turnover, r9_critic C1
# unit reconciliation, first hand: the pinned model's own cost per unit gross must equal
# RATE * turnover_per_unit_gross. If it does, turnover_per_unit_gross is the right multiplier.
UNIT_CHECK = {"mean_modelled_cost_bps_per_unit_gross": float(costf.mean()),
              "mean_turnover_per_unit_gross_file_caliber": float(tovf.mean()),
              "implied_turnover_per_unit_gross_from_cost/RATE": float(costf.mean() / RATE),
              "RATE_times_critic_turnover_0.03032": RATE * 0.03032,
              "RATE_times_measured_turnover_per_unit_gross": float(RATE * costf.mean() / RATE)}
TOVF_EX = costf / RATE                     # executor-caliber turnover per unit gross
ARMS = {
    "PINNED":            g.copy(),
    "REPRICED_CRITIC":   g - GAP * 0.03032,        # critic's own arithmetic, reproduced as stated
    "REPRICED_UNITFIX":  g - GAP * TOVF_EX,        # same gap, turnover expressed per unit gross
}

# ---- helpers ----------------------------------------------------------------------------------
def daily_from_grid(Gm, L):
    """UTC-day NAV return at gross multiple L. Explicit product, no expm1."""
    return np.prod(1.0 + L * Gm / 1e4, axis=1) - 1.0

def intraday_path(Gm, L):
    """running NAV factor within each UTC day, at the 6 anchor marks (shape NDAY x 6)."""
    return np.cumprod(1.0 + L * Gm / 1e4, axis=1) - 1.0

def maxdd(dr):
    nav = np.concatenate([[1.0], np.cumprod(1.0 + dr)])        # E-0909-C: prepend the start point
    return float((1.0 - nav / np.maximum.accumulate(nav)).max())

def worst_from_start(dr):
    nav = np.concatenate([[1.0], np.cumprod(1.0 + dr)])
    return float(nav.min() - 1.0)

def rolling_min_k(dr, k):
    if len(dr) < k: return None
    lf = np.concatenate([[1.0], np.cumprod(1.0 + dr)])
    return float((lf[k:] / lf[:-k] - 1.0).min())

def moments(x):
    x = np.asarray(x, float); mu = x.mean(); sd = x.std(ddof=1)
    return {"mean_pct": float(mu*100), "sd_pct": float(sd*100),
            "skew": float(((x-mu)**3).mean()/sd**3), "exkurt": float(((x-mu)**4).mean()/sd**4 - 3.0),
            "pct": {q: float(np.percentile(x, q)*100) for q in (0.1,1,5,25,50,75,95,99,99.9)}}

THRESH = [-0.02, -0.0268, -0.03, -0.04, -0.05]

def realised_block(Gm, L, ndays):
    dr = daily_from_grid(Gm, L)
    ip = intraday_path(Gm, L)
    out = {"n_days": int(ndays),
           "cagr_pct": float(((np.prod(1.0+dr))**(ANN_D/ndays) - 1.0)*100),
           "ann_vol_pct": float(dr.std(ddof=1)*np.sqrt(ANN_D)*100),
           "maxDD_pct": float(maxdd(dr)*100),
           "worst_from_start_pct": float(worst_from_start(dr)*100),
           "worst_day_pct": float(dr.min()*100),
           "worst_week_7d_pct": (lambda v: None if v is None else v*100)(rolling_min_k(dr, 7)),
           "worst_month_30d_pct": (lambda v: None if v is None else v*100)(rolling_min_k(dr, 30)),
           "daily": moments(dr)}
    for t in THRESH:
        n_cc = int((dr <= t).sum())
        n_id = int((ip.min(axis=1) <= t).sum())
        out[f"days_le_{abs(t)*100:.2f}pct"] = {"close_to_close_n": n_cc,
            "close_to_close_per_yr": round(n_cc/ndays*ANN_D, 4),
            "intraday_touch_n": n_id, "intraday_touch_per_yr": round(n_id/ndays*ANN_D, 4)}
    # rolling 1y (365d) maxDD over the realised path
    rdd = [maxdd(dr[i:i+365]) for i in range(0, len(dr)-365+1)]
    out["rolling_1y_maxDD_pct"] = {"max": float(max(rdd)*100), "p90": float(np.percentile(rdd,90)*100),
                                   "median": float(np.median(rdd)*100), "min": float(min(rdd)*100),
                                   "n_windows": len(rdd)}
    return out

# ---- UTC-day block bootstrap (frozen: 2000 resamples, default_rng([20260905,k])) ---------------
NB = 2000
def bootstrap_1y(Gm, L, halt_line=None):
    """draw 365 UTC day-blocks with replacement; one 'year' per resample."""
    n = Gm.shape[0]
    cagr=np.empty(NB); mdd=np.empty(NB); wfs=np.empty(NB); wd=np.empty(NB)
    h_cc=np.empty(NB,int); h_id=np.empty(NB,int); cagr_h=np.empty(NB); mdd_h=np.empty(NB)
    for k in range(NB):
        rng = np.random.default_rng([20260905, k])
        idx = rng.integers(0, n, 365)
        Gs = Gm[idx]
        dr = daily_from_grid(Gs, L)
        cagr[k] = np.prod(1.0+dr) - 1.0
        mdd[k]  = maxdd(dr); wfs[k] = worst_from_start(dr); wd[k] = dr.min()
        if halt_line is not None:
            ip = intraday_path(Gs, L)
            h_cc[k] = int((dr <= halt_line).sum())
            h_id[k] = int((ip.min(axis=1) <= halt_line).sum())
            # with-halt counterfactual: on a day that touches the line, flatten for the rest of
            # that UTC day (book flat -> remaining anchors contribute 0), resume next day.
            below = ip <= halt_line
            first = np.where(below.any(1), below.argmax(1), 6)
            mask = np.arange(6)[None,:] <= first[:,None]
            drh = np.prod(1.0 + L*Gs/1e4*mask, axis=1) - 1.0
            cagr_h[k] = np.prod(1.0+drh) - 1.0; mdd_h[k] = maxdd(drh)
    q = lambda a,p: float(np.percentile(a,p))
    o = {"n_resamples": NB, "horizon_days": 365,
         "cagr_pct": {"mean": float(cagr.mean()*100), "median": q(cagr,50)*100,
                      "p05": q(cagr,5)*100, "p95": q(cagr,95)*100, "p_negative": float((cagr<0).mean())},
         "maxDD_pct": {"median": q(mdd,50)*100, "p90": q(mdd,90)*100, "p99": q(mdd,99)*100,
                       "mean": float(mdd.mean()*100)},
         "P_maxDD_ge_25pct": float((mdd >= 0.25).mean()),
         "P_from_start_le_minus25pct": float((wfs <= -0.25).mean()),
         "worst_day_pct": {"median": q(wd,50)*100, "p05": q(wd,5)*100, "p01": q(wd,1)*100}}
    if halt_line is not None:
        o["halt"] = {"line_pct": halt_line*100,
            "close_to_close": {"E_per_yr": float(h_cc.mean()), "P_ge1": float((h_cc>=1).mean()),
                               "P_ge2": float((h_cc>=2).mean()), "P_ge3": float((h_cc>=3).mean())},
            "intraday_touch": {"E_per_yr": float(h_id.mean()), "P_ge1": float((h_id>=1).mean()),
                               "P_ge2": float((h_id>=2).mean()), "P_ge3": float((h_id>=3).mean())},
            "with_halt_applied": {"cagr_pct_median": q(cagr_h,50)*100,
                                  "maxDD_pct_median": q(mdd_h,50)*100,
                                  "P_maxDD_ge_25pct": float((mdd_h>=0.25).mean())}}
    return o

def boot_mean_g(x, tsx):
    """frozen judge statistic: UTC-day block bootstrap of mean g."""
    d = tsx//86400; u, iv = np.unique(d, return_inverse=True)
    grp = [x[iv==j] for j in range(len(u))]
    mus = np.empty(NB)
    for k in range(NB):
        rng = np.random.default_rng([20260905, k])
        idx = rng.integers(0, len(grp), len(grp))
        mus[k] = np.concatenate([grp[i] for i in idx]).mean()
    return float(np.percentile(mus,2.5)), float(np.percentile(mus,97.5))

# ================================ RUN ==========================================================
RES = {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "env_whitelist": ENV_WHITELIST, "env_observed_from_watchlist": _set,
       "gpu_used": False, "live_touched": False, "network_used": False,
       "inputs": INPUTS, "device_self_sha256": sha256(os.path.abspath(__file__)),
       "artifact_config": CFG, "unit_reconciliation_of_the_cost_gap": UNIT_CHECK,
       "window": {"rule": "post-warm drop first 900 anchors (E-0911-A); upper bound 2026-08-30 20Z (E-0911-D)",
                  "t0": time.strftime("%Y-%m-%d %HZ", time.gmtime(int(ts[0]))),
                  "t1": time.strftime("%Y-%m-%d %HZ", time.gmtime(int(ts[-1]))),
                  "n_anchors": int(len(g)), "n_utc_days": NDAY},
       "A0_reproduction": {"mean_g_bps": float(g.mean()),
                           "sharpe_ann": float(g.mean()/g.std(ddof=1)*np.sqrt(2190)),
                           "SE_sharpe": float(np.sqrt(2190/len(g)))}}
lo, hi = boot_mean_g(g, ts); RES["A0_reproduction"]["mean_g_CI95"] = [lo, hi]

HALT = -0.04       # DAY_LOSS_LIMIT_PCT, watchdog.py L109, % of EQUITY
LADDER = [1.0, 1.25, 1.5, 1.75, 2.0, 2.5]

RES["part1_tail_on_corrected_caliber"] = {}
for arm, gx in ARMS.items():
    Gm = gx.reshape(NDAY, 6)
    RES["part1_tail_on_corrected_caliber"][arm] = realised_block(Gm, 2.0, NDAY)

# ---- companion window: NO warm-up drop. The post-warm rule (E-0911-A) was adopted for ALPHA
#      measurement; it removes 900 anchors that contain the sample's worst single day, so for a
#      TAIL question it must be reported alongside, not instead.
m2 = ts_all <= UB
ts2 = ts_all[m2]; g2 = g_all[m2]
d2 = ts2 // 86400; u2, c2 = np.unique(d2, return_counts=True)
assert (c2 == 6).all(), "NOWARM window must be whole UTC days"
NDAY2 = len(u2)
RES["part1_companion_NOWARM"] = {
    "window": {"t0": time.strftime("%Y-%m-%d %HZ", time.gmtime(int(ts2[0]))),
               "t1": time.strftime("%Y-%m-%d %HZ", time.gmtime(int(ts2[-1]))),
               "n_anchors": int(len(g2)), "n_utc_days": int(NDAY2),
               "mean_g_bps": float(g2.mean()),
               "sharpe_ann": float(g2.mean()/g2.std(ddof=1)*np.sqrt(2190))},
    "at_2.00x": realised_block(g2.reshape(NDAY2, 6), 2.0, NDAY2)}
RES["part1_companion_NOWARM"]["at_2.00x_bootstrap_1y"] = bootstrap_1y(g2.reshape(NDAY2,6), 2.0, -0.04)

RES["part2_leverage_ladder"] = {}
for arm, gx in ARMS.items():
    Gm = gx.reshape(NDAY, 6)
    RES["part2_leverage_ladder"][arm] = {}
    for L in LADDER:
        r = realised_block(Gm, L, NDAY)
        b = bootstrap_1y(Gm, L, HALT)
        RES["part2_leverage_ladder"][arm][f"{L:.2f}x"] = {"realised": r, "bootstrap_1y": b}
    print(f"ladder done {arm}", flush=True)

# ---- fine grid for the objectives -------------------------------------------------------------
GRID = [round(0.25 + 0.05*i, 2) for i in range(0, 56)]      # 0.25 .. 3.00
RES["part2_objective_grid"] = {}
for arm in ("PINNED", "REPRICED_UNITFIX"):
    Gm = ARMS[arm].reshape(NDAY, 6)
    rows = []
    for L in GRID:
        b = bootstrap_1y(Gm, L, HALT)
        rows.append({"L": L,
            "median_cagr_pct": b["cagr_pct"]["median"], "mean_cagr_pct": b["cagr_pct"]["mean"],
            "median_maxDD_pct": b["maxDD_pct"]["median"], "P_maxDD_ge25": b["P_maxDD_ge_25pct"],
            "P_from_start_le_m25": b["P_from_start_le_minus25pct"],
            "E_halt_cc_per_yr": b["halt"]["close_to_close"]["E_per_yr"],
            "E_halt_id_per_yr": b["halt"]["intraday_touch"]["E_per_yr"],
            "P_halt_ge1": b["halt"]["close_to_close"]["P_ge1"]})
        # expected log growth (Kelly) on the empirical daily distribution
        dr = daily_from_grid(Gm, L); rows[-1]["E_log_growth_ann_pct"] = float(np.log1p(dr).mean()*ANN_D*100)
        rows[-1]["calmar_median"] = (rows[-1]["median_cagr_pct"]/rows[-1]["median_maxDD_pct"]
                                     if rows[-1]["median_maxDD_pct"] > 0 else None)
    RES["part2_objective_grid"][arm] = rows
    print(f"grid done {arm}", flush=True)

json.dump(RES, open(f"{OUT}/RECEIPT_r11_tail_2026-09-12.json", "w"), indent=1)
print("WROTE", f"{OUT}/RECEIPT_r11_tail_2026-09-12.json")
