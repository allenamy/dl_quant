#!/usr/bin/env python3
"""r11 VERDICT arithmetic. ENV WHITELIST = EMPTY SET (asserted below).

Reproduces the pinned A0 planning number first-hand, verifies the unit caliber,
builds ARM C (fully cost-repriced, steady-state adverse selection) which no
upstream agent produced, and prices the leverage ladder on it.

Read-only. No network. No GPU. No live repo touched.
"""
import os, sys, json, hashlib, datetime as dt

import numpy as np   # imported BEFORE the guard: CPython bootstrap reads PYTHONUSERBASE etc.

# ---- E-0826-D: enumerate and ASSERT the env whitelist = EMPTY -------------
# The guard is installed AFTER stdlib/numpy import so it governs THIS analysis,
# not CPython's own bootstrap. Any env read by the code below raises.
_ALLOWED = set()
class _EnvGuard(dict):
    def __getitem__(self, k):
        if k not in _ALLOWED:
            raise RuntimeError("E-0826-D: env read outside whitelist: %r" % k)
        return dict.__getitem__(self, k)
    def get(self, k, default=None):
        if k not in _ALLOWED:
            raise RuntimeError("E-0826-D: env read outside whitelist: %r" % k)
        return dict.get(self, k, default)
_saved_environ = dict(os.environ)
os.environ = _EnvGuard(_saved_environ)
ENV_WHITELIST = sorted(_ALLOWED)
assert ENV_WHITELIST == [], ENV_WHITELIST

ROOT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"
PIN  = ROOT + "/r10_screen/CMUM_CARRY/pin/A0_PWR230k_s42.npz"

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

OUT = {"env_whitelist": ENV_WHITELIST, "gpu_used": False, "network_used": False,
       "live_touched": False,
       "device_self_sha256": sha256(os.path.abspath(__file__))[:16],
       "inputs_sha256": {"A0_PWR230k_s42.npz": sha256(PIN)}}

z = np.load(PIN, allow_pickle=True)
cols = [str(c) for c in z["cols"]]
rec  = z["rec"]
C = {c: i for i, c in enumerate(cols)}
cfg = json.loads(str(z["config_json"]))
OUT["artifact_config_CAL"] = cfg["CAL"]
OUT["artifact_config_PHI"] = cfg["PHI"]
OUT["artifact_config_COSTB"] = cfg["COSTB_JSON"]
assert cfg["CAL"] == "log", "E-0904-F: CAL must be log on this lineage"

# ---- post-warm drop first 900 (E-0911-A) + upper bound 2026-08-30 20Z ----
# E-0911-D: the archived A0 carries ONE row past the pinned bound
# (2026-08-31 00Z). Keeping it gives n=9139 / mean 0.6358645; the pinned
# planning number is n=9138 / mean 0.6341957. Bound applied explicitly.
import datetime as _dt
_BOUND = _dt.datetime(2026, 8, 30, 20, 0, tzinfo=_dt.UTC).timestamp()
r = rec[900:]
r = r[r[:, C["ts"]] <= _BOUND]
ts = r[:, C["ts"]]
n  = len(r)
OUT["n_anchors"] = int(n)
assert n == 9138, n

net_ex = r[:, C["net_ex"]]
gross  = r[:, C["gross_total"]]
turn   = r[:, C["turnover"]]
cost_ex= r[:, C["cost_ex"]]

g = net_ex / gross
OUT["A0_reproduction"] = {
    "mean_g_bps": float(g.mean()),
    "sharpe_ann": float(g.mean() / g.std(ddof=1) * np.sqrt(2190.0)),
    "SE_sharpe": float(np.sqrt(2190.0 / n)),
}

# ---- unit caliber (the closeout's defect) --------------------------------
OUT["unit_caliber"] = {
    "mean_gross_total": float(gross.mean()),
    "mean_turnover_RAW": float(turn.mean()),
    "mean_turnover_per_unit_gross": float((turn / gross).mean()),
    "mean_cost_ex_per_unit_gross": float((cost_ex / gross).mean()),
    "mean_cost_per_unit_gross": float((r[:, C["cost"]] / gross).mean()),
    "implied_model_rate_bps_per_unit_turnover_MATCHED":
        float((r[:, C["cost"]] / gross).mean() / (turn / gross).mean()),
    "implied_model_rate_bps_per_unit_turnover_MISMATCHED":
        float((r[:, C["cost"]] / gross).mean() / turn.mean()),
    "pinned_model_book_avg_bps": 2.9537,
}

# ---- ARM construction ----------------------------------------------------
# model rate actually charged, per anchor, bps per unit turnover
RATE_MODEL = OUT["unit_caliber"]["implied_model_rate_bps_per_unit_turnover_MATCHED"]
GAP_60S    = 2.0884      # critic C1, 60s proxy
GAP_STEADY = 6.547452    # r11 cost truth, steady-state plateau
RATIO_STEADY = 3.216695  # realized / pinned, steady state

tpg = turn / gross                      # turnover per unit gross, per anchor
cpg = cost_ex / gross                   # modelled cost, bps per unit gross

ARMS = {}
ARMS["A_pinned"] = g.copy()
# Arm B: critic 60s gap, correct unit caliber (= tail agent's REPRICED_UNITFIX)
ARMS["B_60s_unitfix"] = g - GAP_60S * tpg
# Arm C: steady-state gap. additive and ratio routes, then their mean (same
# rule the cost agent used for the scalar).
c_add   = g - GAP_STEADY * tpg
c_ratio = g - cpg * (RATIO_STEADY - 1.0)
ARMS["C_steady_additive"] = c_add
ARMS["C_steady_ratio"]    = c_ratio
ARMS["C_steady"]          = 0.5 * (c_add + c_ratio)

OUT["arms_scalar"] = {}
for k, s in ARMS.items():
    OUT["arms_scalar"][k] = {
        "mean_g_bps": float(s.mean()),
        "sharpe_ann": float(s.mean() / s.std(ddof=1) * np.sqrt(2190.0)),
        "NAV_pct_yr_at_2x": float(s.mean() * 2190 * 2 / 100.0),
    }

# ---- UTC-day blocks ------------------------------------------------------
def utcday(t):
    return dt.datetime.fromtimestamp(float(t), dt.UTC).strftime("%Y-%m-%d")
days = np.array([utcday(t) for t in ts])
uday, inv = np.unique(days, return_inverse=True)
OUT["n_utc_days"] = int(len(uday))

def daily_returns(gs, L):
    """compound the anchors inside each UTC day, explicit product, no log1p."""
    rr = gs / 1e4 * L
    out = np.ones(len(uday))
    np.multiply.at(out, inv, 1.0)         # init
    out = np.ones(len(uday))
    for i in range(len(gs)):
        out[inv[i]] *= (1.0 + rr[i])
    return out - 1.0

def path_stats(dr):
    eq = np.cumprod(1.0 + dr)
    eq_p = np.concatenate([[1.0], eq])    # prepend start (maxDD caliber)
    peak = np.maximum.accumulate(eq_p)
    dd = eq_p / peak - 1.0
    yrs = len(dr) / 365.0
    return {
        "cagr_pct": float((eq[-1] ** (1.0 / yrs) - 1.0) * 100.0),
        "maxDD_pct": float(-dd.min() * 100.0),
        "worst_from_start_pct": float((eq_p.min() - 1.0) * 100.0),
        "worst_day_pct": float(dr.min() * 100.0),
        "daily_sd_pct": float(dr.std(ddof=1) * 100.0),
        "n_le_4pct": int((dr <= -0.04).sum()),
        "per_yr_le_4pct": float((dr <= -0.04).sum() / yrs),
        "n_le_2pct": int((dr <= -0.02).sum()),
        "per_yr_le_2pct": float((dr <= -0.02).sum() / yrs),
    }

def boot_1y(dr, B=2000, H=365):
    """UTC-day block bootstrap over whole days; 365-day paths."""
    mdd, frm, halts = [], [], []
    for k in range(B):
        rng = np.random.default_rng([20260905, k])
        idx = rng.integers(0, len(dr), H)
        p = dr[idx]
        eq = np.cumprod(1.0 + p)
        eq_p = np.concatenate([[1.0], eq])
        peak = np.maximum.accumulate(eq_p)
        mdd.append(-(eq_p / peak - 1.0).min())
        frm.append(eq_p.min() - 1.0)
        halts.append(int((p <= -0.04).sum()))
    mdd = np.array(mdd); frm = np.array(frm); halts = np.array(halts)
    return {
        "med_1y_maxDD_pct": float(np.median(mdd) * 100),
        "p90_1y_maxDD_pct": float(np.percentile(mdd, 90) * 100),
        "P_1y_maxDD_ge_25pct": float((mdd >= 0.25).mean() * 100),
        "P_from_start_le_m25pct": float((frm <= -0.25).mean() * 100),
        "E_halts_per_yr": float(halts.mean()),
        "P_ge1_halt_per_yr": float((halts >= 1).mean()),
        "P_ge3_halt_per_yr": float((halts >= 3).mean()),
    }

GROSS = [1.00, 1.25, 1.50, 1.75, 2.00, 2.50]
OUT["leverage_table"] = {}
for arm in ["A_pinned", "B_60s_unitfix", "C_steady"]:
    OUT["leverage_table"][arm] = {}
    for L in GROSS:
        dr = daily_returns(ARMS[arm], L)
        row = path_stats(dr)
        row.update(boot_1y(dr))
        row["NAV_pct_yr_linear"] = float(ARMS[arm].mean() * 2190 * L / 100.0)
        OUT["leverage_table"][arm]["%.2fx" % L] = row

# ---- live-vol-equivalent gross ------------------------------------------
LIVE_VOL_RATIO = 1.4042
OUT["live_vol_equivalent"] = {}
for arm in ["A_pinned", "C_steady"]:
    L = 2.0 * LIVE_VOL_RATIO
    dr = daily_returns(ARMS[arm], L)
    row = path_stats(dr); row.update(boot_1y(dr))
    OUT["live_vol_equivalent"]["%s_at_%.2fx" % (arm, L)] = row

# ---- the honest-gross question: gross that holds E[halts]<=1/yr ----------
OUT["gross_search"] = {}
for arm in ["A_pinned", "C_steady"]:
    tbl = {}
    for L in [1.00, 1.10, 1.20, 1.25, 1.30, 1.40, 1.50, 1.60, 1.75, 2.00]:
        dr = daily_returns(ARMS[arm], L)
        b = boot_1y(dr)
        s = path_stats(dr)
        tbl["%.2fx" % L] = {"E_halts_per_yr": b["E_halts_per_yr"],
                            "P_ge1_halt": b["P_ge1_halt_per_yr"],
                            "P_1y_maxDD_ge_25pct": b["P_1y_maxDD_ge_25pct"],
                            "med_1y_maxDD_pct": b["med_1y_maxDD_pct"],
                            "NAV_pct_yr_linear": float(ARMS[arm].mean()*2190*L/100.0),
                            "realised_n_le_4pct": s["n_le_4pct"]}
        # live-vol-adjusted: what this nominal gross actually behaves like
        drv = daily_returns(ARMS[arm], L * LIVE_VOL_RATIO)
        bv = boot_1y(drv)
        tbl["%.2fx" % L]["LIVEVOL_E_halts_per_yr"] = bv["E_halts_per_yr"]
        tbl["%.2fx" % L]["LIVEVOL_P_1y_maxDD_ge_25pct"] = bv["P_1y_maxDD_ge_25pct"]
    OUT["gross_search"][arm] = tbl

# ---- demonstrability arithmetic (Q5) ------------------------------------
def need_point(years):
    return 3.0 + 1.96 * np.sqrt(2190.0 / (years * 2190.0))
OUT["demonstrability"] = {
    "SE_formula": "sqrt(2190/n)",
    "point_needed_for_CI95_lo_gt_3": {("%.3gy" % y): float(need_point(y))
                                      for y in [1, 2, 3, 4.173, 10, 25, 100]},
    "years_needed_if_true_sharpe_is": {
        ("%.2f" % S): (float((1.96 / (S - 3.0)) ** 2) if S > 3.0 else None)
        for S in [3.5, 4.0, 5.0, 6.0]},
}
# drawdown-objective power: what n does a maxDD/halt-rate objective need?
OUT["alt_objective_power"] = {
    "note": "halt-rate objective: observed halts ~ Poisson(lambda*T). To show "
            "lambda <= 1/yr at 95% one-sided needs 0 halts in 3.0 yr, or "
            "<=1 halt in 4.7 yr (Poisson upper bound).",
    "poisson_upper95_for_k_events": {str(k): float(v) for k, v in
        {0: 2.996, 1: 4.744, 2: 6.296, 3: 7.754}.items()},
}

print(json.dumps(OUT, indent=1))
with open(ROOT + "/r11_verdict/receipts/RECEIPT_r11_verdict_arith.json", "w") as f:
    json.dump(OUT, f, indent=1)
