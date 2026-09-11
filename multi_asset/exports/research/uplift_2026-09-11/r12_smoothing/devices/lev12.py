"""r12 §5: the drawdown-aware objective made FEASIBLE by treating leverage as the free variable.
   max_over(cell, L)  median 1y CAGR   s.t.  E[halt touches] <= 1/yr  and  P(1y maxDD >= 25%) <= 10%
Halt/DD lines from watchdog.py (L109 -4.0% of equity per UTC day; L131 -25% of STARTING equity).
Honest live-vol caliber: day returns are mean-preserving sigma-inflated by 1.4042 (r11)."""
import numpy as np, json, glob, os, calendar, time
R = "/workspace/uplift_2026-09-11/r12_smoothing"
TS_MAX = calendar.timegm((2026, 8, 30, 20, 0, 0))
HALT = -0.04; DDLIM = -0.25; MULT = 1.4042
def dayret(g, days, L):
    ud = np.unique(days); out = np.zeros(len(ud))
    for i, d in enumerate(ud): out[i] = np.prod(1.0 + L * g[days == d] * 1e-4) - 1.0
    return ud, out
def roll(ud, r):
    cg, dd = [], []
    for s in range(len(ud)):
        e = np.searchsorted(ud, ud[s] + 365 * 86400, side="right")
        if e - s < 300 or ud[e - 1] - ud[s] < 350 * 86400: continue
        c = np.cumprod(1.0 + r[s:e]) - 1.0; cg.append(c[-1]); dd.append(c.min())
    return np.array(cg), np.array(dd)
def maxdd(r):
    eq = np.concatenate([[1.0], np.cumprod(1.0 + r)]); return float((eq / np.maximum.accumulate(eq) - 1.0).min())
LEVS = [round(x, 2) for x in np.arange(0.25, 2.01, 0.125)]
out = {}
for f in sorted(glob.glob(R + "/arms/S_*.npz")):
    tag = os.path.basename(f)[:-4]; Z = np.load(f, allow_pickle=True)
    cfg = json.loads(str(Z["config_json"])); rec = Z["rec"]
    ts = rec[:, 0].astype(np.int64); m = ts <= TS_MAX
    g = (rec[:, 18] / rec[:, 5])[m]; days = (ts[m] // 86400 * 86400)
    yrs = (days[-1] - days[0]) / (365.25 * 86400)
    rows = {}
    for L in LEVS:
        ud, rd = dayret(g, days, L); mu = rd.mean(); rs = mu + MULT * (rd - mu)
        cg, dd = roll(ud, rs)
        rows[str(L)] = {"halt_per_yr": float((rs <= HALT).sum() / yrs), "p_1y_dd_ge25": float((dd <= DDLIM).mean()),
                        "median_1y_cagr_pct": float(np.median(cg) * 100), "worst_day_pct": float(rs.min() * 100),
                        "maxdd_pct": maxdd(rs) * 100, "day_sigma_pct": float(rs.std(ddof=1) * 100)}
    feas = [L for L in LEVS if rows[str(L)]["halt_per_yr"] <= 1.0 and rows[str(L)]["p_1y_dd_ge25"] <= 0.10]
    best = max(feas) if feas else None
    out[tag] = {"SMA": cfg["SMA"], "SBAND": cfg["SBAND"], "rows": rows,
                "max_feasible_leverage": best,
                "median_1y_cagr_at_feasible_pct": rows[str(best)]["median_1y_cagr_pct"] if best else None}
    print("%-22s a=%.2f b=%.1e | feasible L<=%s  med1yCAGR@L=%s" % (tag, cfg["SMA"], cfg["SBAND"], best,
          ("%+.1f%%" % out[tag]["median_1y_cagr_at_feasible_pct"]) if best else "n/a"), flush=True)
json.dump(out, open(R + "/LEV12.json", "w"), indent=1); print("LEV_DONE")
