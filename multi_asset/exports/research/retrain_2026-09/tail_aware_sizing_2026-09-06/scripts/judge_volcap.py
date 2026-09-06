"""judge_volcap.py — PREREG_tail_aware_sizing_2026-09-06 §2 frozen readings on the w10_volcap.py artifacts (arm d30_n2_c42).
Units chain (health_metrics.py): g = net_ex / gross_total [bps/anchor per unit gross]; NAV return at 2× = 2·g/1e4 per anchor; windows 2024→26 = 2024-01-01 .. CUT
2026-08-10 20:00Z (F10 leg absent after), yearly 2024 / 2025 / 2026→cut. Paired Δg = arm − baseline (same caliber, same seed, common anchors), UTC-day-block
bootstrap 2000 seed 20260905. Tail quantities per run (both seeds, 2024→26):
  (i)  days with 2× UTC-day equity change ≤ −2.68% (executor cond2 investigation tier): equity_day = Π_{anchors in day}(1 + 2g/1e4) − 1 from 1.0 at day start
  (ii) 2× maxDD of the NAV path Π(1 + 2g/1e4) over the window (%)
  (iii) worst-year anchor Sharpe = min over {2024, 2025, 2026→cut} of mean(g)/std(g,ddof=1)·√2190
  (iv) per-anchor net sd (bps/anchor/gross)
  (v)  geometric drag = [2·mean(g/1e4) − mean(log(1 + 2·g/1e4))] × 2190 × 100 (%/yr)
Frozen readings (prod caliber primary; log caliber reported): (A) some γ with, both seeds: Δg(2024→26) ≥ −0.05 AND CI95 upper > 0 AND (i) down ≥ 30% AND (ii) down ≥ 3 pp
AND (iii) Δ ≥ −0.05 AND turnover ≤ +10%, and the two doses' Δg same sign; (B) both doses Δg CI95 upper < 0 (both seeds), OR both doses (i) down < 10% (both seeds);
(C) otherwise. Report-only: mean n_capped per anchor, gross share removed, N_eff (from W, all arms), high-σ tercile gross share (from W and σ), cap ratio of the
2026 giveback names (4/CLO/APR/HEMI/COLLECT/BULLA/UAI/AKE) over 2026-08 anchors. usage: judge_volcap.py <ROOT> <out.json>"""
import os, sys, json, time, calendar, hashlib
import numpy as np
ROOT = sys.argv[1]; OUT = sys.argv[2]; SELF = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
COLS = ["ts", "net", "pnl", "carry", "cost", "gross_total", "gross_member", "gross_sel", "nsel", "nmember", "fires", "leg_king", "leg_rev24", "leg_fund", "w3_king", "w3_rev24", "w3_fund", "turnover", "net_ex", "pnl_ex", "carry_ex", "cost_ex", "netlong"]
C = {k: i for i, k in enumerate(COLS)}
def T(s): return int(calendar.timegm(time.strptime(s, "%Y-%m-%d")))
CUT = T("2026-08-10") + 20 * 3600; APY = 2190; NB = 2000; SEED = 20260905; L = 2.0; THR = -0.0268
WIN = {"2024": (T("2024-01-01"), T("2025-01-01")), "2025": (T("2025-01-01"), T("2026-01-01")), "2026->cut": (T("2026-01-01"), CUT + 1), "2024->26": (T("2024-01-01"), CUT + 1)}
GIVEBACK = ["4USDT", "CLOUSDT", "APRUSDT", "HEMIUSDT", "COLLECTUSDT", "BULLAUSDT", "UAIUSDT", "AKEUSDT"]
def load(cal, g, s):
    d = "dev_alt" if cal == "prod" else "dev"; p = f"{ROOT}/{d}/probe_artifacts/w10_ablation_series_VC_{cal}_g{g}_s{s}.npz"
    z = np.load(p, allow_pickle=True); assert [str(c) for c in z["cols"]] == COLS
    return p, z, np.asarray(z["d30_n2_c42_rec"], float), np.asarray(z["d30_n2_c42_W"], np.float64), [str(x) for x in z["symbols"]]
def boot(x, days):
    ud, inv = np.unique(days, return_inverse=True); s1 = np.bincount(inv, x); c = np.bincount(inv).astype(float)
    rng = np.random.default_rng(SEED); idx = rng.integers(0, len(ud), size=(NB, len(ud))); m = s1[idx].sum(1) / c[idx].sum(1)
    return [round(float(np.percentile(m, 2.5)), 4), round(float(np.percentile(m, 97.5)), 4)]
def sharpe(x): return float(x.mean() / x.std(ddof=1) * np.sqrt(APY)) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")
def tails(g, ts):
    r = L * g / 1e4; days = ts // 86400; ud, inv = np.unique(days, return_inverse=True)
    lg = np.log1p(r); dsum = np.bincount(inv, lg); deq = np.expm1(dsum)            # (i) intraday compounding from 1.0
    nav = np.exp(np.cumsum(lg)); dd = 1 - nav / np.maximum.accumulate(nav)            # (ii)
    yrs = np.array([time.gmtime(int(t)).tm_year for t in ts]); sh = {int(y): round(sharpe(g[yrs == y]), 3) for y in sorted(set(yrs.tolist()))}
    drag = (2 * np.mean(g / 1e4) - np.mean(np.log1p(r))) * APY * 100                  # (v)
    return {"i_days_le_-2.68pct_at_2x": int((deq <= THR).sum()), "i_n_days": int(len(ud)), "i_worst_day_pct_at_2x": round(float(deq.min() * 100), 3),
            "ii_maxdd_pct_at_2x": round(float(dd.max() * 100), 3), "iii_worst_year_sharpe": round(float(min(sh.values())), 3), "iii_sharpe_by_year": sh,
            "iv_anchor_sd_bps_per_gross": round(float(g.std(ddof=1)), 3), "v_geometric_drag_pct_yr": round(float(drag), 3), "mean_g": round(float(g.mean()), 4), "sharpe_anchor": round(sharpe(g), 3)}
def neff_hivol(W, ts, sig=None):
    """N_eff = (Σ|w|)²/Σw² per anchor from the book weights W; high-σ tercile gross share if σ given."""
    a = np.abs(W); s1 = a.sum(1); ne = np.where(s1 > 0, s1 ** 2 / np.maximum((W ** 2).sum(1), 1e-18), np.nan)
    hv = np.full(len(ts), np.nan)
    if sig is not None:
        for k in range(len(ts)):
            sg = sig[k]; ok = np.isfinite(sg) & (a[k] > 0)
            if ok.sum() >= 3:
                thr = np.percentile(sg[ok], 200.0 / 3); hv[k] = a[k][ok & (sg >= thr)].sum() / s1[k] if s1[k] > 0 else np.nan
    return ne, hv
res = {"self_sha256": SELF, "root": ROOT, "units": "g = net_ex/gross_total bps/anchor per gross; NAV at 2x; Δ = arm − baseline paired on common anchors; bootstrap UTC-day blocks 2000 seed 20260905", "cut": "2026-08-10 20:00Z", "runs": {}, "delta": {}, "reading": {}}
for cal in ("prod", "log"):
    base = {}
    for s in (42, 2027):
        p0, z0, R0, W0, syms = load(cal, "0", s); ts0 = R0[:, C["ts"]].astype(np.int64); g0 = R0[:, C["net_ex"]] / R0[:, C["gross_total"]]
        base[s] = (ts0, g0, R0, W0)
        m = (ts0 >= WIN["2024->26"][0]) & (ts0 < WIN["2024->26"][1]); ne, _ = neff_hivol(W0, ts0)
        res["runs"][f"{cal}_g0_s{s}"] = {"path": p0, "sha256": hashlib.sha256(open(p0, "rb").read()).hexdigest()[:16], "tails_2024_26": tails(g0[m], ts0[m]),
                                          "by_year": {y: {"mean_g": round(float(g0[(ts0 >= lo) & (ts0 < hi)].mean()), 4), "sharpe": round(sharpe(g0[(ts0 >= lo) & (ts0 < hi)]), 3)} for y, (lo, hi) in WIN.items()},
                                          "turnover_per_gross_2024_26": round(float((R0[m, C["turnover"]] / R0[m, C["gross_total"]]).mean()), 5), "neff_mean_2024_26": round(float(np.nanmean(ne[m])), 2)}
    for gam in ("0.5", "1.0"):
        for s in (42, 2027):
            p, z, R, W, syms = load(cal, gam, s); ts = R[:, C["ts"]].astype(np.int64); g = R[:, C["net_ex"]] / R[:, C["gross_total"]]
            ts0, g0, R0, W0 = base[s]; assert np.array_equal(ts, ts0), "arm and baseline anchor sequences differ (the cap acts after sel/g screens, so they must be identical)"
            sig = np.asarray(z["volcap_sigma"], np.float64); vts = z["volcap_meta_ts"].astype(np.int64); vmap = {int(t): k for k, t in enumerate(vts)}; rows = np.array([vmap[int(t)] for t in ts])
            sig_r = sig[rows]; diag = np.asarray(z["volcap_diag"], float)[rows]; ratio = np.asarray(z["volcap_ratio"], np.float64)
            ne, hv = neff_hivol(W, ts, sig_r); ne0, hv0 = neff_hivol(W0, ts0, sig_r)
            key = f"{cal}_g{gam}_s{s}"; run = {"path": p, "sha256": hashlib.sha256(open(p, "rb").read()).hexdigest()[:16], "windows": {}}
            for w, (lo, hi) in WIN.items():
                mm = (ts >= lo) & (ts < hi); d = g[mm] - g0[mm]; days = ts[mm] // 86400
                tb = R0[mm, C["turnover"]] / R0[mm, C["gross_total"]]; ta = R[mm, C["turnover"]] / R[mm, C["gross_total"]]
                run["windows"][w] = {"n": int(mm.sum()), "base_mean_g": round(float(g0[mm].mean()), 4), "arm_mean_g": round(float(g[mm].mean()), 4), "delta_g": round(float(d.mean()), 4), "delta_ci95": boot(d, days), "p_delta_gt0": round(float(np.mean(d > 0)), 3),
                                     "base_sharpe": round(sharpe(g0[mm]), 3), "arm_sharpe": round(sharpe(g[mm]), 3), "turnover_change": round(float(ta.mean() / tb.mean() - 1), 4) if tb.mean() > 0 else None}
            m = (ts >= WIN["2024->26"][0]) & (ts < WIN["2024->26"][1])
            run["tails_2024_26"] = tails(g[m], ts[m]); tb0 = res["runs"][f"{cal}_g0_s{s}"]["tails_2024_26"]; ta_ = run["tails_2024_26"]
            run["tail_delta"] = {"i_days_change_pct": round(float((ta_["i_days_le_-2.68pct_at_2x"] - tb0["i_days_le_-2.68pct_at_2x"]) / max(tb0["i_days_le_-2.68pct_at_2x"], 1) * 100), 1), "i_days_base_arm": [tb0["i_days_le_-2.68pct_at_2x"], ta_["i_days_le_-2.68pct_at_2x"]],
                                 "ii_maxdd_change_pp": round(ta_["ii_maxdd_pct_at_2x"] - tb0["ii_maxdd_pct_at_2x"], 3), "iii_worst_year_sharpe_delta": round(ta_["iii_worst_year_sharpe"] - tb0["iii_worst_year_sharpe"], 3),
                                 "iv_sd_change_bps": round(ta_["iv_anchor_sd_bps_per_gross"] - tb0["iv_anchor_sd_bps_per_gross"], 3), "v_drag_change_pct_yr": round(ta_["v_geometric_drag_pct_yr"] - tb0["v_geometric_drag_pct_yr"], 3)}
            gb = {}
            for nm in GIVEBACK:
                if nm in syms:
                    j = syms.index(nm); k26 = [vmap[int(t)] for t in ts if t >= T("2026-08-01")]; rr = ratio[k26, j]; ww = np.abs(W[ts >= T("2026-08-01"), j])
                    held = ww > 0; gb[nm] = {"cap_ratio_mean_2026-08": round(float(rr[held].mean()), 3) if held.any() else None, "cap_ratio_min": round(float(rr[held].min()), 3) if held.any() else None, "n_anchors_held": int(held.sum())}
            run["report_only_2024_26"] = {"n_capped_mean": round(float(np.nanmean(diag[m, 0])), 2), "gross_removed_share_mean": round(float(np.nanmean(diag[m, 1])), 4), "neff_target_after_renorm_mean": round(float(np.nanmean(diag[m, 2])), 2),
                                           "neff_book_W_mean_arm": round(float(np.nanmean(ne[m])), 2), "neff_book_W_mean_base": round(float(np.nanmean(ne0[m])), 2), "hivol_tercile_gross_share_arm": round(float(np.nanmean(hv[m])), 4), "hivol_tercile_gross_share_base": round(float(np.nanmean(hv0[m])), 4),
                                           "hivol_tercile_gross_share_target_arm": round(float(np.nanmean(diag[m, 3])), 4), "giveback_names_2026-08": gb}
            res["delta"][key] = run
            w = run["windows"]["2024->26"]; td = run["tail_delta"]
            print(f"[{key}] Δg 2024->26 {w['delta_g']:+.4f} {w['delta_ci95']} (base {w['base_mean_g']:+.4f} S {w['base_sharpe']:.2f} -> {w['arm_sharpe']:.2f}) turnover {w['turnover_change']:+.1%} | yearly Δg " + "/".join(f"{run['windows'][y]['delta_g']:+.3f}" for y in ("2024", "2025", "2026->cut")) + f" | (i) days {td['i_days_base_arm']} ({td['i_days_change_pct']:+.0f}%) (ii) maxDD {tb0['ii_maxdd_pct_at_2x']:.2f}->{ta_['ii_maxdd_pct_at_2x']:.2f} ({td['ii_maxdd_change_pp']:+.2f} pp) (iii) worst-yr S {tb0['iii_worst_year_sharpe']:.2f}->{ta_['iii_worst_year_sharpe']:.2f} (iv) sd {tb0['iv_anchor_sd_bps_per_gross']:.2f}->{ta_['iv_anchor_sd_bps_per_gross']:.2f} (v) drag {tb0['v_geometric_drag_pct_yr']:.2f}->{ta_['v_geometric_drag_pct_yr']:.2f} | capped {run['report_only_2024_26']['n_capped_mean']} removed {run['report_only_2024_26']['gross_removed_share_mean']:.3f} Neff {run['report_only_2024_26']['neff_book_W_mean_base']}->{run['report_only_2024_26']['neff_book_W_mean_arm']} hivol {run['report_only_2024_26']['hivol_tercile_gross_share_base']:.3f}->{run['report_only_2024_26']['hivol_tercile_gross_share_arm']:.3f}", flush=True)
    # frozen reading per caliber
    def cond(gam, s):
        r = res["delta"][f"{cal}_g{gam}_s{s}"]; w = r["windows"]["2024->26"]; td = r["tail_delta"]
        return {"dg": w["delta_g"], "ci_hi": w["delta_ci95"][1], "noninf": w["delta_g"] >= -0.05 and w["delta_ci95"][1] > 0, "i_down_ge30": td["i_days_change_pct"] <= -30, "i_down_lt10": td["i_days_change_pct"] > -10,
                "ii_down_ge3pp": td["ii_maxdd_change_pp"] <= -3, "iii_ok": td["iii_worst_year_sharpe_delta"] >= -0.05, "turn_ok": (w["turnover_change"] is not None and w["turnover_change"] <= 0.10)}
    cc = {gam: {s: cond(gam, s) for s in (42, 2027)} for gam in ("0.5", "1.0")}
    same_sign = all(np.sign(cc["0.5"][s]["dg"]) == np.sign(cc["1.0"][s]["dg"]) for s in (42, 2027))
    A_by_gamma = {gam: all(cc[gam][s]["noninf"] and cc[gam][s]["i_down_ge30"] and cc[gam][s]["ii_down_ge3pp"] and cc[gam][s]["iii_ok"] and cc[gam][s]["turn_ok"] for s in (42, 2027)) and same_sign for gam in cc}
    B_alpha = all(cc[gam][s]["ci_hi"] < 0 for gam in cc for s in (42, 2027)); B_tail = all(cc[gam][s]["i_down_lt10"] for gam in cc for s in (42, 2027))
    verdict = "A_candidate" if any(A_by_gamma.values()) else ("B_reject" if (B_alpha or B_tail) else "C_UNDECIDED")
    res["reading"][cal] = {"conditions": cc, "adjacent_doses_same_sign": bool(same_sign), "A_by_gamma": A_by_gamma, "B_alpha_both_doses_ci_upper_lt0_both_seeds": bool(B_alpha), "B_tail_both_doses_i_down_lt10_both_seeds": bool(B_tail), "verdict": verdict, "role": "primary" if cal == "prod" else "secondary (report)"}
    print(f"READING {cal}: A_by_gamma {A_by_gamma} same_sign {same_sign} | B_alpha {B_alpha} B_tail {B_tail} -> {verdict}", flush=True)
json.dump(res, open(OUT, "w"), indent=1); print("JUDGE_VOLCAP_DONE", flush=True)
