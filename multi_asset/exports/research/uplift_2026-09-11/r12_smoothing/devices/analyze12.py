"""r12 main analysis. Windows, statistic, partition and objective all per PREREG_r12_smoothing (frozen)
+ the r12_regime agent's PREREG partition (families b/c/d/e), whose primitives file is used verbatim."""
import numpy as np, json, os, glob, calendar, time, hashlib
R = "/workspace/uplift_2026-09-11/r12_smoothing"
APY = 2190; B = 2000
TS_MAX = calendar.timegm((2026, 8, 30, 20, 0, 0))      # E-0911-D instrument ceiling (regime agent PREREG §5)
WARM = 900                                             # E-0911-A, ALPHA questions only
LEV = 2.0                                              # book gross 2.0 x NAV
LIVE_SIGMA_MULT = 1.4042                               # r11 measured live/replay daily sigma
HALT = -0.0400; ALERT = -0.0268; DDLIM = -0.25         # watchdog.py L109 / L117 / L131

# ---------- bootstrap (exact-equivalent closed form, r8_inbook/fastboot.py) ----------
def prep(x, days):
    ud, inv = np.unique(days, return_inverse=True); nd = len(ud)
    return nd, np.bincount(inv, minlength=nd).astype(float), np.bincount(inv, weights=x, minlength=nd), np.bincount(inv, weights=x * x, minlength=nd)
def draws(nd, k, B):
    return np.random.default_rng([20260905, k]).integers(0, nd, size=(B, nd))
def msd(idx, n, s, q):
    N = n[idx].sum(1); S = s[idx].sum(1); Q = q[idx].sum(1); mu = S / N
    return mu, np.sqrt(np.maximum((Q - N * mu * mu) / (N - 1.0), 0.0))
def boot_mean(x, days, k):
    nd, n, s, q = prep(x, days); mu, _ = msd(draws(nd, k, B), n, s, q); return mu
def boot_dmean(x, y, days, k):
    """paired: same day draws, mean(x)-mean(y) — x,y on the SAME anchor grid"""
    nd, n, sx, qx = prep(x, days); _, _, sy, qy = prep(y, days)
    idx = draws(nd, k, B); N = n[idx].sum(1)
    return sx[idx].sum(1) / N - sy[idx].sum(1) / N
def ci(v): return [float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))]

# ---------- regime primitives (r12_regime agent, verbatim file) ----------
P = np.load(R + "/causal_primitives_r12.npz", allow_pickle=True)
pc = {str(c): i for i, c in enumerate(P["cols"])}; pr = P["rec"]
pts = pr[:, pc["ts"]].astype(np.int64)
A_ew = pr[:, pc["A_ew"]]; B_br = pr[:, pc["B_breadth"]]; D_dis = pr[:, pc["D_disp_bps"]]
SIGF = pr[:, pc["SIGF"]]; FMED = pr[:, pc["FMED"]]; SPAY = pr[:, pc["SPAY"]]
n = len(pts)
def trail_mean(x, w):       # k in [i-w, i-1]  (strictly causal)
    out = np.full(n, np.nan)
    for i in range(w, n):
        s = x[i - w:i]
        if np.isfinite(s).all(): out[i] = s.mean()
    return out
def trail_sum(x, w):
    out = np.full(n, np.nan)
    for i in range(w, n):
        s = x[i - w:i]
        if np.isfinite(s).all(): out[i] = s.sum()
    return out
BRD6 = trail_mean(B_br, 6); XSV30 = trail_mean(D_dis, 30)
R24 = trail_sum(A_ew, 6); R72 = trail_sum(A_ew, 18)
MV30 = np.full(n, np.nan)
for i in range(30, n):
    s = A_ew[i - 30:i]
    if np.isfinite(s).all(): MV30[i] = 1e4 * s.std()
PRIM = {"ts": pts, "BRD6": BRD6, "XSV30": XSV30, "MV30": MV30, "SIGF": SIGF, "FMED": FMED, "SPAY": SPAY, "R24": R24, "R72": R72}

def build_labels(ts):
    """labels on the W_TAIL span's own distribution; one label set shared by both windows (declared)."""
    idx = {int(t): i for i, t in enumerate(pts)}
    sel = np.array([idx[int(t)] for t in ts])
    g = {k: v[sel] for k, v in PRIM.items() if k != "ts"}
    L = {}
    L["YEAR"] = np.array(["Y%d" % time.gmtime(int(t)).tm_year for t in ts], object)
    def tert(x, nm):
        f = np.isfinite(x); q1, q2 = np.nanquantile(x[f], [1/3, 2/3])
        o = np.full(len(x), nm + "_NA", object)
        o[f & (x <= q1)] = nm + "_T1"; o[f & (x > q1) & (x <= q2)] = nm + "_T2"; o[f & (x > q2)] = nm + "_T3"
        return o
    L["BREADTH"] = tert(g["BRD6"], "BRD"); L["XSVOL"] = tert(g["XSV30"], "XSV")
    L["MKTVOL"] = tert(g["MV30"], "MV"); L["SIGFT"] = tert(g["SIGF"], "SIGF")
    ev = {}
    ev["POSTCRASH"] = np.isfinite(g["R24"]) & (g["R24"] <= -0.02)
    ev["BROADRALLY"] = np.isfinite(g["R24"]) & np.isfinite(g["BRD6"]) & (g["R24"] >= 0.02) & (g["BRD6"] >= 0.60)
    ev["ALTSURGE"] = np.isfinite(g["R72"]) & (g["R72"] >= 0.08)
    ev["ALTSURGE_BROAD"] = ev["ALTSURGE"] & np.isfinite(g["BRD6"]) & (g["BRD6"] >= 0.60)
    f = np.isfinite(g["FMED"]); d1 = np.nanquantile(g["FMED"][f], 0.10)
    ev["DEEPNEG_MKT"] = f & (g["FMED"] <= d1)
    f2 = np.isfinite(g["SPAY"]); d9 = np.nanquantile(g["SPAY"][f2], 0.90)
    ev["DEEPNEG_SHORT"] = f2 & (g["SPAY"] >= d9)
    # R72 quintile ladder (threshold-free companion to ALTSURGE)
    f3 = np.isfinite(g["R72"]); qs = np.nanquantile(g["R72"][f3], [.2, .4, .6, .8])
    o = np.full(len(ts), "R72_NA", object)
    o[f3] = np.array(["R72_Q%d" % (np.searchsorted(qs, v) + 1) for v in g["R72"][f3]], object)
    L["R72LADDER"] = o
    return L, ev, g

# ---------- per-arm ----------
def dayret(g_bps, days):
    ud = np.unique(days); out = np.zeros(len(ud))
    for i, d in enumerate(ud):
        out[i] = np.prod(1.0 + LEV * g_bps[days == d] * 1e-4) - 1.0
    return ud, out
def maxdd(r):
    eq = np.concatenate([[1.0], np.cumprod(1.0 + r)])      # prepend start (E-0909-C)
    return float((eq / np.maximum.accumulate(eq) - 1.0).min())
def roll1y(ud, r):
    """1-year windows keyed by calendar day; DD measured from window START (watchdog semantics)."""
    cg, dd = [], []
    for s in range(len(ud)):
        e = np.searchsorted(ud, ud[s] + 365 * 86400, side="right")
        if e - s < 300 or ud[e - 1] - ud[s] < 350 * 86400: continue
        w = r[s:e]; cum = np.cumprod(1.0 + w) - 1.0
        cg.append(float(cum[-1])); dd.append(float(cum.min()))
    return np.array(cg), np.array(dd)

arms = {}
for f in sorted(glob.glob(R + "/arms/S_*_s42.npz")):
    tag = os.path.basename(f)[:-4]; Z = np.load(f, allow_pickle=True)
    cfg = json.loads(str(Z["config_json"])); rec = Z["rec"]; aux = Z["R12A"]
    ts = rec[:, 0].astype(np.int64)
    arms[tag] = {"cfg": cfg, "rec": rec, "aux": aux, "ts": ts}
tags = sorted(arms)
ts0 = arms[tags[0]]["ts"]
for t in tags: assert np.array_equal(arms[t]["ts"], ts0), "anchor grid differs: " + t
mT = ts0 <= TS_MAX
iW = np.zeros(len(ts0), bool); iW[WARM:] = True
mA = mT & iW
days_all = np.array([int(t) // 86400 * 86400 for t in ts0])
LAB, EV, GP = build_labels(ts0)
print("W_TAIL n=%d  W_ALPHA n=%d" % (mT.sum(), mA.sum()), flush=True)

DEP = "S_a010_b25e4_s42"
gdep = arms[DEP]["rec"][:, 18] / arms[DEP]["rec"][:, 5]
out = {"_meta": {"TS_MAX": int(TS_MAX), "n_W_TAIL": int(mT.sum()), "n_W_ALPHA": int(mA.sum()),
                 "WARM": WARM, "LEV": LEV, "LIVE_SIGMA_MULT": LIVE_SIGMA_MULT,
                 "HALT_PCT": HALT, "ALERT_PCT": ALERT, "DD_LIMIT": DDLIM, "B": B,
                 "deployed_cell": DEP, "K_grid": len(tags)}}
for t in tags:
    a = arms[t]; rec = a["rec"]; aux = a["aux"]; cfg = a["cfg"]
    gt = rec[:, 5]; g = rec[:, 18] / gt
    turn_raw = rec[:, 17]; turn_ex = aux[:, 1]
    o = {"SMA": cfg["SMA"], "SBAND": cfg["SBAND"]}
    # --- W_ALPHA ---
    gA = g[mA]; dA = days_all[mA]
    bm = boot_mean(gA, dA, 0); bm9 = boot_mean(gA, dA, 9)
    sd = float(gA.std(ddof=1))
    o["alpha"] = {"n": int(mA.sum()), "mean_g": float(gA.mean()), "ci95_k0": ci(bm), "ci95_k9": ci(bm9),
                  "sharpe": float(gA.mean() / sd * np.sqrt(APY)), "se_sharpe": float(np.sqrt(APY / mA.sum())),
                  "sd_g": sd,
                  "turn_matched_meanratio": float((turn_ex[mA] / gt[mA]).mean()),
                  "turn_matched_ratioofmeans": float(turn_ex[mA].mean() / gt[mA].mean()),
                  "turn_raw_file_caliber": float(turn_raw[mA].mean()),
                  "gross_total_mean": float(gt[mA].mean()),
                  "cost_over_gross": float((rec[mA, 21] / gt[mA]).mean()),
                  "carry_over_gross": float((rec[mA, 20] / gt[mA]).mean()),
                  "pnl_over_gross": float((rec[mA, 19] / gt[mA]).mean()),
                  "band_bite_frac_king": float((aux[mA, 4] / aux[mA, 6]).mean()),
                  "band_bite_frac_f10": float((aux[mA, 5] / aux[mA, 6]).mean()),
                  "dist_sm_tgt_over_gross": float((aux[mA, 3] / gt[mA]).mean()),
                  "gross_target_mean": float(aux[mA, 2].mean()),
                  "deadzone_b_over_alpha": cfg["SBAND"] / cfg["SMA"],
                  "mean_abs_w": float((gt[mA] / rec[mA, 8]).mean())}
    if t != DEP:
        d0 = boot_dmean(gA, gdep[mA], dA, 0); d9 = boot_dmean(gA, gdep[mA], dA, 9)
        o["alpha"]["dg_vs_deployed"] = float(gA.mean() - gdep[mA].mean())
        o["alpha"]["dg_ci95_k0"] = ci(d0); o["alpha"]["dg_ci95_k9"] = ci(d9)
        o["alpha"]["dg_p_ge0_k0"] = float((d0 > 0).mean())
    # cost effective rate self-check (constraint 5a)
    o["alpha"]["cost_rate_bps_per_unit_turnover"] = float((rec[mA, 21] / gt[mA]).mean() / (turn_ex[mA] / gt[mA]).mean())
    # --- per-regime (W_ALPHA) ---
    reg = {}
    for fam, lab in LAB.items():
        for u in sorted(set(lab[mA])):
            k = mA & (lab == u)
            if k.sum() < 30: continue
            x = g[k]; s = float(x.std(ddof=1))
            reg[u] = {"n": int(k.sum()), "mean_g": float(x.mean()), "sharpe": float(x.mean() / s * np.sqrt(APY)),
                      "se_sharpe": float(np.sqrt(APY / k.sum())),
                      "ci95": ci(boot_mean(x, days_all[k], 0)),
                      "turn_matched": float((turn_ex[k] / gt[k]).mean()),
                      "cost_over_gross": float((rec[k, 21] / gt[k]).mean()),
                      "pnl_over_gross": float((rec[k, 19] / gt[k]).mean()),
                      "carry_over_gross": float((rec[k, 20] / gt[k]).mean())}
            if t != DEP:
                dd = boot_dmean(x, gdep[k], days_all[k], 0)
                reg[u]["dg_vs_deployed"] = float(x.mean() - gdep[k].mean()); reg[u]["dg_ci95"] = ci(dd)
    for nm, msk in EV.items():
        for side, k in (("", mA & msk), ("_NOT", mA & (~msk))):
            if k.sum() < 30: continue
            x = g[k]; s = float(x.std(ddof=1))
            reg[nm + side] = {"n": int(k.sum()), "mean_g": float(x.mean()), "sharpe": float(x.mean() / s * np.sqrt(APY)),
                              "se_sharpe": float(np.sqrt(APY / k.sum())), "ci95": ci(boot_mean(x, days_all[k], 0)),
                              "turn_matched": float((turn_ex[k] / gt[k]).mean()),
                              "cost_over_gross": float((rec[k, 21] / gt[k]).mean()),
                              "pnl_over_gross": float((rec[k, 19] / gt[k]).mean()),
                              "carry_over_gross": float((rec[k, 20] / gt[k]).mean())}
            if t != DEP:
                dd = boot_dmean(x, gdep[k], days_all[k], 0)
                reg[nm + side]["dg_vs_deployed"] = float(x.mean() - gdep[k].mean()); reg[nm + side]["dg_ci95"] = ci(dd)
    o["regime"] = reg
    # --- W_TAIL (NO warm drop) ---
    gT = g[mT]; dT = days_all[mT]
    ud, rd = dayret(gT, dT)
    mu = rd.mean(); rs = mu + LIVE_SIGMA_MULT * (rd - mu)     # honest live-vol caliber: inflate sigma, keep mean
    yrs = (ud[-1] - ud[0]) / (365.25 * 86400)
    cg, dd = roll1y(ud, rd); cgs, dds = roll1y(ud, rs)
    o["tail"] = {"n_anchors": int(mT.sum()), "n_days": int(len(ud)), "years": float(yrs),
                 "mean_g": float(gT.mean()), "sharpe": float(gT.mean() / gT.std(ddof=1) * np.sqrt(APY)),
                 "replay": {"day_sigma_pct": float(rd.std(ddof=1) * 100), "worst_day_pct": float(rd.min() * 100),
                            "worst_day_utc": time.strftime("%Y-%m-%d", time.gmtime(int(ud[int(np.argmin(rd))]))),
                            "maxdd_pct": maxdd(rd) * 100, "n_halt": int((rd <= HALT).sum()), "n_alert": int((rd <= ALERT).sum()),
                            "halt_per_yr": float((rd <= HALT).sum() / yrs), "alert_per_yr": float((rd <= ALERT).sum() / yrs),
                            "median_1y_cagr_pct": float(np.median(cg) * 100), "p_1y_dd_ge25": float((dd <= DDLIM).mean()),
                            "n_1y_windows": int(len(cg))},
                 "live_vol": {"day_sigma_pct": float(rs.std(ddof=1) * 100), "worst_day_pct": float(rs.min() * 100),
                              "worst_day_utc": time.strftime("%Y-%m-%d", time.gmtime(int(ud[int(np.argmin(rs))]))),
                              "maxdd_pct": maxdd(rs) * 100, "n_halt": int((rs <= HALT).sum()), "n_alert": int((rs <= ALERT).sum()),
                              "halt_per_yr": float((rs <= HALT).sum() / yrs), "alert_per_yr": float((rs <= ALERT).sum() / yrs),
                              "median_1y_cagr_pct": float(np.median(cgs) * 100), "p_1y_dd_ge25": float((dds <= DDLIM).mean()),
                              "n_1y_windows": int(len(cgs))}}
    out[t] = o
    print("%-22s a=%.2f b=%.2e | g=%+.4f SR=%.3f turn=%.5f | halt/yr(live)=%.2f wd=%.2f%% mDD=%.1f%%" %
          (t, cfg["SMA"], cfg["SBAND"], o["alpha"]["mean_g"], o["alpha"]["sharpe"], o["alpha"]["turn_matched_meanratio"],
           o["tail"]["live_vol"]["halt_per_yr"], o["tail"]["live_vol"]["worst_day_pct"], o["tail"]["live_vol"]["maxdd_pct"]), flush=True)
json.dump(out, open(R + "/RESULT_R12.json", "w"), indent=1)
print("ANALYZE_DONE")
