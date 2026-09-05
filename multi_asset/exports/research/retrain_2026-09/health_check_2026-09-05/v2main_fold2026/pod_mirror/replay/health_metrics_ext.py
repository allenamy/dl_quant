#!/usr/bin/env python
"""health_metrics.py — PREREG_live_form_health_check_2026-09-05 §2 metrics for device artifacts (arm d30_n2_c42, rec columns of w10_universe_recheck.py).
UNITS CHAIN (E-0904-G, printed again at run time): rec net_ex = bps per anchor earned by the unit replay book whose gross is gross_total
  ⇒ per-gross return g = net_ex / gross_total  [bps/anchor per unit gross]
  ⇒ the executor sizes gross = L × NAV at every anchor ⇒ NAV return r_L = g × L  [bps/anchor of NAV]
  ⇒ NAV path = Π(1 + r_L/1e4) (anchor-level compounding); UTC day = calendar day of the anchor ts (anchor 20:00Z accrues 20–24Z, same day)
  ⇒ arithmetic annualisation: mean(r_L) × 2190 / 1e4 → %/yr; CAGR from the compounded path; anchor Sharpe = mean/std(ddof=1) × √2190 (L-invariant);
     daily Sharpe/Sortino from compounded UTC-day returns × √365.
Windows: 2024 | 2024-H1 (flag: seat warm-up — pinned king NaN before 2024 ⇒ the msharpe-900 window fills by ~2024-06) | 2024-H2 | 2025 | 2026→cut | 2024→26 | 2025→26 |
  calendar quarters (2026-Q3 → cut) | 2026-postcut (flag: F10 leg absent after 2026-08-10 20:00Z — not the live form). cut = 2026-08-10 20:00Z (last finite F10 row).
Slices over 2024→cut: σ_fund terciles (exact axisB R5 / judge.py definition: per anchor std(ddof=0) over META members with finite f_fund_now of f_fund_now·8/ivf·1e4 bps/8h,
  NaN if <50 finite; 30-anchor trailing mean (≥15 valid) over the legs() anchor sequence; causal expanding 33.33/66.67 cuts over positions strictly before t, ≥300 finite history),
  breadth = nsel (tradeable names in the rec; regime_dash.py has no wide/narrow cut — the memory's "宽档/窄档" were monthly breadth terciles), negative-funding-share
  (share of META members with finite f_fund_now whose 8h-equivalent rate < 0; 30-anchor trailing mean), BTC 30-day realised vol (masks/btc_rv30.npz, 5m cache) — all four with
  the same causal expanding tercile rule (primary) and descriptive terciles over the window (secondary, equal-n).
Bootstrap: UTC-day blocks, 2000 resamples, seed 20260905; CI95 of the window mean (bps/anchor per gross) and of the anchor Sharpe; P(mean>0).
Liquidation proximity: margin ratio at anchor end = (1 + r_L/1e4)/L (gross reset to L×NAV at every anchor) vs maintenance MAINT = 1.5% of gross; also over 8-anchor windows.
usage: health_metrics.py <artifact.npz> [...]  → results/<tag>.json + results/<tag>.txt   (tag = artifact filename minus w10_ablation_series_ / .npz)"""
import numpy as np, json, time, sys, os, hashlib, calendar
ROOT = "/workspace/review_scratch/v2main_fold2026/replay"   # health_metrics_ext (v2main_fold2026): ROOT redirected; base = health_check/health_metrics.py sha 6cdb34f3…
PANEL = "/workspace/data/wide_panel_4h_v2ext.npz"; META = "/workspace/data/wide_fea_v2ext_meta.npz"; BTC = f"{ROOT}/masks/btc_rv30.npz"; REG = f"{ROOT}/masks/regime_series.npz"
LS = [2.0, 2.5, 3.0]; NB = 2000; SEED = 20260905; MAINT = 0.015; APY = 2190; DPY = 365
def T(s): return int(calendar.timegm(time.strptime(s, "%Y-%m-%d")))
CUT = T("2026-08-10") + 20 * 3600; assert time.strftime("%Y-%m-%d %H:%M", time.gmtime(CUT)) == "2026-08-10 20:00"
END = T("2026-08-30") + 20 * 3600; assert time.strftime("%Y-%m-%d %H:%M", time.gmtime(END)) == "2026-08-30 20:00"   # ext2026: last anchor with the F10 leg from the new fold
COLS = ["ts", "net", "pnl", "carry", "cost", "gross_total", "gross_member", "gross_sel", "nsel", "nmember", "fires", "leg_king", "leg_rev24", "leg_fund", "w3_king", "w3_rev24", "w3_fund", "turnover", "net_ex", "pnl_ex", "carry_ex", "cost_ex", "netlong"]
C = {k: i for i, k in enumerate(COLS)}
WIN = {"2024": (T("2024-01-01"), T("2025-01-01")), "2024-H1": (T("2024-01-01"), T("2024-07-01")), "2024-H2": (T("2024-07-01"), T("2025-01-01")), "2025": (T("2025-01-01"), T("2026-01-01")),
       "2026->cut": (T("2026-01-01"), CUT + 1), "2024->26": (T("2024-01-01"), CUT + 1), "2025->26": (T("2025-01-01"), CUT + 1), "2026-postcut": (CUT + 1, 2**40),
       "2026->0830": (T("2026-01-01"), END + 1), "2026-08-11->0830": (CUT + 1, END + 1), "2024->0830": (T("2024-01-01"), END + 1), "2025->0830": (T("2025-01-01"), END + 1), "2026-Q3->0830": (T("2026-07-01"), END + 1)}
for y in (2024, 2025, 2026):
    for q in (1, 2, 3, 4):
        lo = T(f"{y}-{3*q-2:02d}-01"); hi = T(f"{y+1}-01-01") if q == 4 else T(f"{y}-{3*q+1:02d}-01")
        if lo > CUT: continue
        WIN[f"{y}-Q{q}"] = (lo, min(hi, CUT + 1))
FLAG = {"2024-H1": "seat warm-up (pinned king NaN before 2024; msharpe-900 window fills ~2024-06)", "2026-postcut": "anchors after the health_check cut 2026-08-10 20:00Z (F10 leg present iff FPRED covers them — see config.FPRED)", "2026-Q3": "→ cut 2026-08-10 20:00Z",
        "2026->0830": "ext2026: F10 leg from the new 2026 fold over the whole window", "2026-08-11->0830": "ext2026 stretch: F10 leg present (new fold); 120 anchors / 20 days", "2024->0830": "full-through incl. 08-11→08-30", "2025->0830": "full-through incl. 08-11→08-30", "2026-Q3->0830": "Q3 through 08-30"}
BOOT_WINDOWS = ("2024", "2024-H2", "2025", "2026->cut", "2024->26", "2025->26", "2026->0830", "2026-08-11->0830", "2024->0830", "2025->0830")
def pct(x, q): return float(np.percentile(x, q)) if len(x) else float("nan")
def sharpe(x, per): return float(x.mean() / x.std(ddof=1) * np.sqrt(per)) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")
def sortino(x, per):
    d = np.minimum(x, 0.0); ds = np.sqrt((d ** 2).mean()) if len(x) > 2 else 0.0
    return float(x.mean() / ds * np.sqrt(per)) if ds > 0 else float("nan")
def r4(v): return None if v is None or (isinstance(v, float) and not np.isfinite(v)) else round(float(v), 4)
def boot(r, days):
    ud, inv = np.unique(days, return_inverse=True); nd = len(ud)
    if nd < 5 or len(r) < 10: return {"n_days": int(nd), "mean_ci95": [None, None], "sharpe_ci95": [None, None], "p_mean_gt0": None}
    s1 = np.bincount(inv, r); s2 = np.bincount(inv, r * r); c = np.bincount(inv).astype(float)
    rng = np.random.default_rng(SEED); idx = rng.integers(0, nd, size=(NB, nd))
    S1 = s1[idx].sum(1); S2 = s2[idx].sum(1); Cn = c[idx].sum(1)
    m = S1 / Cn; var = np.maximum((S2 - Cn * m * m) / (Cn - 1), 1e-18); sh = m / np.sqrt(var) * np.sqrt(APY)
    return {"n_days": int(nd), "mean_ci95": [r4(pct(m, 2.5)), r4(pct(m, 97.5))], "sharpe_ci95": [r4(pct(sh, 2.5)), r4(pct(sh, 97.5))], "p_mean_gt0": r4((m > 0).mean())}
def causal_ter(x, min_hist=300):
    x = np.asarray(x, float); out = np.full(len(x), -1, np.int8); cuts = np.full((len(x), 2), np.nan)
    for p in range(len(x)):
        h = x[:p]; h = h[np.isfinite(h)]
        if len(h) >= min_hist and np.isfinite(x[p]):
            q1, q2 = np.percentile(h, [100.0 / 3, 200.0 / 3]); cuts[p] = (q1, q2); out[p] = 0 if x[p] <= q1 else (1 if x[p] <= q2 else 2)
    return out, cuts
def desc_ter(x):
    x = np.asarray(x, float); out = np.full(len(x), -1, np.int8); f = np.isfinite(x)
    if f.sum() < 30: return out, (np.nan, np.nan)
    q1, q2 = np.percentile(x[f], [100.0 / 3, 200.0 / 3]); out[f] = np.where(x[f] <= q1, 0, np.where(x[f] <= q2, 1, 2)); return out, (float(q1), float(q2))
def dd_stats(nav, ts):
    cm = np.maximum.accumulate(nav); dd = 1.0 - nav / cm; k = int(np.argmax(dd)) if len(dd) else 0
    # duration: longest peak-to-recovery span (days); the span containing the max-DD trough; unrecovered flag
    under = dd > 0; spans = []; i = 0
    while i < len(under):
        if under[i]:
            j = i
            while j < len(under) and under[j]: j += 1
            pk = i - 1 if i > 0 else 0; spans.append((pk, j, j < len(under))); i = j
        else: i += 1
    longest = max(((ts[min(e, len(ts) - 1)] - ts[s]) / 86400.0, rec) for s, e, rec in spans) if spans else (0.0, True)
    cont = next(((ts[min(e, len(ts) - 1)] - ts[s]) / 86400.0, rec) for s, e, rec in spans if s <= k < e) if spans else (0.0, True)
    return {"maxdd_pct": r4(dd.max() * 100), "maxdd_trough": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(ts[k]))), "maxdd_span_days": r4(cont[0]), "maxdd_recovered": bool(cont[1]),
            "longest_dd_days": r4(longest[0]), "longest_dd_recovered": bool(longest[1])}
def rolling_sharpe(dret, dids, lo_day, hi_day):
    out = []
    for e in range(len(dids)):
        if dids[e] < lo_day or dids[e] >= hi_day: continue
        m = (dids > dids[e] - 90) & (dids <= dids[e]); x = dret[m]
        if m.sum() >= 80: out.append(sharpe(x, DPY))
    out = np.array(out); return {"n_windows": int(len(out)), "p5": r4(pct(out, 5)), "median": r4(pct(out, 50)), "p95": r4(pct(out, 95))} if len(out) else {"n_windows": 0}
def regime_series():
    """σ_fund and negative-funding share over the legs() anchor sequence (meta anchors with a panel row), exact device/judge definitions; BTC rv30 mapped by ts. Cached."""
    if os.path.exists(REG):
        z = np.load(REG); return {k: z[k] for k in z.files}
    M = np.load(META, allow_pickle=True); E = M["E_ts"].astype(np.int64); MEM = M["members"]
    P = np.load(PANEL, allow_pickle=True); pts = P["ts"].astype(np.int64); pw_row = {int(t): j for j, t in enumerate(pts)}; FN = P["f_fund_now"]; IV = P["f_fund_iv"]
    raw = []; neg = []; ts = []
    for i in range(len(E)):
        j = pw_row.get(int(E[i]))
        if j is None: continue
        m = MEM[i]; f = FN[j, m]; iv = IV[j, m]; ivf = np.where(np.isfinite(iv) & (iv > 0), iv, 8.0); ok = np.isfinite(f)
        raw.append(float(np.std(f[ok] * 8.0 / ivf[ok]) * 1e4) if ok.sum() >= 50 else np.nan)
        neg.append(float(((f[ok] * 8.0 / ivf[ok]) < 0).mean()) if ok.sum() >= 50 else np.nan); ts.append(int(E[i]))
    raw = np.array(raw); neg = np.array(neg); ts = np.array(ts, np.int64)
    def roll30(a):
        r = np.full(len(a), np.nan)
        for p in range(len(a)):
            w = a[max(0, p - 29):p + 1]; v = w[np.isfinite(w)]
            if len(v) >= 15: r[p] = v.mean()
        return r
    sig_roll = roll30(raw); neg_roll = roll30(neg)
    B = np.load(BTC); bmap = {int(t): float(v) for t, v in zip(B["ts"].astype(np.int64), B["rv30_ann_pct"])}; btc = np.array([bmap.get(int(t), np.nan) for t in ts])
    st, sc = causal_ter(sig_roll); nt, nc = causal_ter(neg_roll); bt, bc = causal_ter(btc)
    out = {"ts": ts, "sig_raw": raw, "sig_roll": sig_roll, "sig_ter": st, "sig_cuts": sc, "neg_raw": neg, "neg_roll": neg_roll, "neg_ter": nt, "neg_cuts": nc, "btc_rv30": btc, "btc_ter": bt, "btc_cuts": bc}
    np.savez_compressed(REG, **out); return out
def analyse(path):
    tag = os.path.basename(path).replace("w10_ablation_series_", "").replace(".npz", "")
    Z = np.load(path, allow_pickle=True); cfg = json.loads(str(Z["config_json"])); R = Z["d30_n2_c42_rec"]
    assert [str(c) for c in Z["cols"]] == COLS, "column layout changed"
    ts = R[:, C["ts"]].astype(np.int64); gt = R[:, C["gross_total"]]; ne = R[:, C["net_ex"]]
    g = ne / gt   # bps/anchor per unit gross
    days = ts // 86400; weeks = (days + 3) // 7; months = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in ts])
    out = {"tag": tag, "artifact": path, "artifact_sha256": hashlib.sha256(open(path, "rb").read()).hexdigest(), "config": cfg, "n_anchors_total": int(len(ts)),
           "first": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(ts[0]))), "last": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(ts[-1]))), "cut": time.strftime("%Y-%m-%d %H:%M", time.gmtime(CUT)),
           "units_chain": "g = net_ex/gross_total [bps/anchor per gross] -> r_L = g*L [bps/anchor NAV] -> arithmetic %/yr = mean(r_L)*2190/1e4; CAGR from Π(1+r_L/1e4); Sharpe anchor = mean/std*sqrt(2190) (L-invariant)",
           "leverages": LS, "bootstrap": {"blocks": "UTC day", "n": NB, "seed": SEED}, "maint_margin": MAINT, "windows": {}, "slices": {}}
    for wn, (lo, hi) in WIN.items():
        m = (ts >= lo) & (ts < hi)
        if m.sum() < 12: out["windows"][wn] = {"n_anchors": int(m.sum()), "skipped": True}; continue
        w = {"n_anchors": int(m.sum()), "n_days": int(len(np.unique(days[m]))), "flag": FLAG.get(wn), "from": time.strftime("%Y-%m-%d", time.gmtime(int(ts[m][0]))), "to": time.strftime("%Y-%m-%d", time.gmtime(int(ts[m][-1])))}
        gw = g[m]; tsw = ts[m]; dw = days[m]
        w["unit_book"] = {"net_ex_mean_bps_anchor": r4(ne[m].mean()), "sharpe_anchor": r4(sharpe(ne[m], APY)), "note": "unit replay book (gross_total floats, mean below); this is the caliber of the earlier RECEIPT_EX / STATE banners, NOT the executor caliber"}
        w["per_gross"] = {"mean_bps_anchor": r4(gw.mean()), "median_bps_anchor": r4(np.median(gw)), "std_bps_anchor": r4(gw.std(ddof=1)), "sharpe_anchor": r4(sharpe(gw, APY)),
                          "win_rate_anchor": r4((gw > 0).mean()), "p1_bps": r4(pct(gw, 1)), "p5_bps": r4(pct(gw, 5)), "min_bps": r4(gw.min()), "max_bps": r4(gw.max()),
                          "sum8_p5_bps": r4(pct(np.convolve(gw, np.ones(8), "valid"), 5)) if len(gw) >= 8 else None, "sum8_min_bps": r4(np.convolve(gw, np.ones(8), "valid").min()) if len(gw) >= 8 else None,
                          "arith_pct_yr_per_gross": r4(gw.mean() * APY / 1e4 * 100)}
        w["form"] = {"gross_total_mean": r4(gt[m].mean()), "nsel_mean": r4(R[m, C["nsel"]].mean()), "nmember_mean": r4(R[m, C["nmember"]].mean()), "w3_king_mean": r4(R[m, C["w3_king"]].mean()), "w3_fund_mean": r4(R[m, C["w3_fund"]].mean()),
                     "netlong_mean": r4(R[m, C["netlong"]].mean()), "fires_total": int(R[m, C["fires"]].sum()),
                     "turnover_per_gross_mean": r4((R[m, C["turnover"]] / gt[m]).mean()), "cost_ex_bps_per_gross_mean": r4((R[m, C["cost_ex"]] / gt[m]).mean()), "carry_paid_bps_per_gross_mean": r4((R[m, C["carry_ex"]] / gt[m]).mean()),
                     "pnl_ex_bps_per_gross_mean": r4((R[m, C["pnl_ex"]] / gt[m]).mean()),
                     "cost_share_of_gross_pnl": r4(R[m, C["cost_ex"]].sum() / R[m, C["pnl_ex"]].sum()) if abs(R[m, C["pnl_ex"]].sum()) > 1e-9 else None,
                     "carry_share_of_gross_pnl": r4(R[m, C["carry_ex"]].sum() / R[m, C["pnl_ex"]].sum()) if abs(R[m, C["pnl_ex"]].sum()) > 1e-9 else None,
                     "leg_king_mean": r4(R[m, C["leg_king"]].mean()), "leg_fund_mean": r4(R[m, C["leg_fund"]].mean())}
        if wn in BOOT_WINDOWS: w["boot"] = boot(gw, dw)
        w["by_L"] = {}
        for L in LS:
            r = gw * L; nav = np.cumprod(1.0 + r / 1e4)
            ud, inv = np.unique(dw, return_inverse=True); dlog = np.bincount(inv, np.log1p(r / 1e4)); dret = np.expm1(dlog)
            uw, invw = np.unique(weeks[m], return_inverse=True); wret = np.expm1(np.bincount(invw, np.log1p(r / 1e4)))
            um, invm = np.unique(months[m], return_inverse=True); mret = np.expm1(np.bincount(invm, np.log1p(r / 1e4)))
            ndays_cal = (tsw[-1] - tsw[0]) / 86400.0 + 1 / 6
            s8 = np.convolve(np.log1p(r / 1e4), np.ones(8), "valid") if len(r) >= 8 else np.array([0.0])
            mr = (1.0 + r / 1e4) / L; mr8 = np.exp(s8) / L
            d = {"arith_pct_yr": r4(r.mean() * APY / 1e4 * 100), "cagr_pct": r4(((nav[-1]) ** (365.0 / ndays_cal) - 1) * 100) if ndays_cal > 30 else None, "total_return_pct": r4((nav[-1] - 1) * 100),
                 "vol_pct_yr_anchor": r4(r.std(ddof=1) * np.sqrt(APY) / 1e4 * 100), "sharpe_daily": r4(sharpe(dret, DPY)), "sortino_daily": r4(sortino(dret, DPY)),
                 "worst_day_pct": r4(dret.min() * 100), "worst_day": time.strftime("%Y-%m-%d", time.gmtime(int(ud[np.argmin(dret)] * 86400))), "worst_week_pct": r4(wret.min() * 100), "worst_month_pct": r4(mret.min() * 100),
                 "worst_month": str(int(um[np.argmin(mret)])), "best_month_pct": r4(mret.max() * 100), "months_negative": int((mret < 0).sum()), "n_months": int(len(mret)),
                 "days_below_2pct": int((dret < -0.02).sum()), "days_below_5pct": int((dret < -0.05).sum()), "days_below_10pct": int((dret < -0.10).sum()),
                 "share_days_below_2pct": r4((dret < -0.02).mean()), "share_days_below_5pct": r4((dret < -0.05).mean()), "share_days_below_10pct": r4((dret < -0.10).mean()),
                 "win_rate_day": r4((dret > 0).mean()), "anchor_p1_pct": r4(pct(r, 1) / 100), "anchor_p5_pct": r4(pct(r, 5) / 100), "anchor_min_pct": r4(r.min() / 100),
                 "sum8_p5_pct": r4(pct(s8, 5) * 100), "sum8_min_pct": r4(s8.min() * 100), "var99_day_pct": r4(pct(dret, 1) * 100), "cvar99_day_pct": r4(dret[dret <= pct(dret, 1)].mean() * 100) if len(dret) >= 100 else None,
                 "min_margin_ratio_anchor": r4(mr.min()), "touches_maint_anchor": int((mr < MAINT).sum()), "min_margin_ratio_8anchor": r4(mr8.min()), "touches_maint_8anchor": int((mr8 < MAINT).sum()),
                 "rolling90d_sharpe": rolling_sharpe(dret, ud, lo // 86400, (hi // 86400) + 1)}
            d.update(dd_stats(nav, tsw)); w["by_L"][str(L)] = d
        out["windows"][wn] = w
    # slices over 2024->cut
    RS = regime_series(); rmap = {int(t): p for p, t in enumerate(RS["ts"])}
    mwin = (ts >= T("2024-01-01")) & (ts <= CUT); idxw = np.where(mwin)[0]
    pos = np.array([rmap.get(int(t), -1) for t in ts]); okp = pos >= 0
    nsel = R[:, C["nsel"]].astype(float); nsel_ct, nsel_cuts = causal_ter(nsel)
    series = {"sigma_fund": ("sig_roll", "sig_ter", "bps/8h, 30-anchor trailing mean"), "neg_fund_share": ("neg_roll", "neg_ter", "share of META members with 8h-equiv rate < 0, 30-anchor trailing mean"), "btc_rv30": ("btc_rv30", "btc_ter", "annualised %, 5m returns, 30 days")}
    def slice_table(vals, ter_c, ter_d, cuts_c_last, cuts_d, desc):
        res = {"definition": desc, "causal_cuts_at_window_end": cuts_c_last, "descriptive_cuts_2024_cut": [r4(cuts_d[0]), r4(cuts_d[1])], "causal": {}, "descriptive": {}}
        for kind, ter in (("causal", ter_c), ("descriptive", ter_d)):
            for t in range(3):
                mm = mwin & (ter == t)
                if mm.sum() < 12: res[kind][["low", "mid", "high"][t]] = {"n_anchors": int(mm.sum())}; continue
                gw = g[mm]; b = boot(gw, days[mm])
                res[kind][["low", "mid", "high"][t]] = {"n_anchors": int(mm.sum()), "share_of_window": r4(mm.sum() / mwin.sum()), "regime_var_mean": r4(np.nanmean(vals[mm])), "mean_bps_anchor_per_gross": r4(gw.mean()), "mean_ci95": b["mean_ci95"], "p_mean_gt0": b["p_mean_gt0"],
                                                       "sharpe_anchor": r4(sharpe(gw, APY)), "nav_pct_yr_at_2x": r4(gw.mean() * 2.0 * APY / 1e4 * 100), "worst_anchor_pct_at_2x": r4(gw.min() * 2.0 / 100), "win_rate_anchor": r4((gw > 0).mean()),
                                                       "by_year": {str(y): {"n": int((mm & (np.array([time.gmtime(int(x)).tm_year for x in ts]) == y)).sum())} for y in (2024, 2025, 2026)}}
            res[kind]["unassigned_n"] = int((mwin & (ter < 0)).sum())
        return res
    for nm, (vk, tk, desc) in series.items():
        vals = np.full(len(ts), np.nan); vals[okp] = RS[vk][pos[okp]]; terc = np.full(len(ts), -1, np.int8); terc[okp] = RS[tk][pos[okp]]
        terd, cd = desc_ter(np.where(mwin, vals, np.nan)); cuts_last = RS[vk.replace("roll", "cuts").replace("btc_rv30", "btc_cuts")][pos[idxw[-1]]] if len(idxw) else [np.nan, np.nan]
        out["slices"][nm] = slice_table(vals, terc, terd, [r4(cuts_last[0]), r4(cuts_last[1])], cd, desc)
    terd, cd = desc_ter(np.where(mwin, nsel, np.nan))
    out["slices"]["breadth_nsel"] = slice_table(nsel, nsel_ct, terd, [r4(nsel_cuts[idxw[-1]][0]), r4(nsel_cuts[idxw[-1]][1])] if len(idxw) else [None, None], cd, "nsel = tradeable names in the book (sel = finite y4 & qv4h>=2.5e5 & universe); causal expanding terciles over the rec sequence since 2022")
    # monthly table (per gross and at 2x)
    um = sorted(set(months[(ts >= T("2024-01-01")) & (ts <= CUT)].tolist())); out["monthly"] = {}
    for mo in um:
        mm = (months == mo) & (ts <= CUT); r = g[mm] * 2.0; out["monthly"][str(mo)] = {"n": int(mm.sum()), "mean_bps_anchor_per_gross": r4(g[mm].mean()), "nav_pct_at_2x": r4(np.expm1(np.log1p(r / 1e4).sum()) * 100), "sharpe_anchor": r4(sharpe(g[mm], APY))}
    um2 = sorted(set(months[(ts >= T("2024-01-01")) & (ts <= END)].tolist())); out["monthly_to_0830"] = {}   # ext2026: same table through 08-30 (2026-08 = full month to 08-30 20:00Z)
    for mo in um2:
        mm = (months == mo) & (ts <= END); r = g[mm] * 2.0; out["monthly_to_0830"][str(mo)] = {"n": int(mm.sum()), "mean_bps_anchor_per_gross": r4(g[mm].mean()), "nav_pct_at_2x": r4(np.expm1(np.log1p(r / 1e4).sum()) * 100), "sharpe_anchor": r4(sharpe(g[mm], APY))}
    return out
def txt(o):
    L = []; P = L.append
    P(f"# {o['tag']}  n={o['n_anchors_total']} {o['first']}→{o['last']}  cut {o['cut']}  sha {o['artifact_sha256'][:16]}")
    P("UNITS: " + o["units_chain"])
    P("| window | n | flag | mean bps/anchor/gross [CI95] | Sharpe anchor [CI95] | NAV %/yr arith @2/2.5/3 | CAGR @2/2.5/3 | maxDD % @2/2.5/3 | DD days | worst day % @2 | days<-2%/-5%/-10% @2 | min margin @3 |")
    P("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for wn, w in o["windows"].items():
        if w.get("skipped"): P(f"| {wn} | {w['n_anchors']} | skipped | | | | | | | | | |"); continue
        b = w.get("boot", {}); ci = b.get("mean_ci95", [None, None]); sci = b.get("sharpe_ci95", [None, None]); pg = w["per_gross"]; bl = w["by_L"]
        f = lambda k, L_=None: " / ".join(str(bl[str(x)][k]) for x in LS)
        P(f"| {wn} | {w['n_anchors']} | {w.get('flag') or ''} | {pg['mean_bps_anchor']} [{ci[0]},{ci[1]}] | {pg['sharpe_anchor']} [{sci[0]},{sci[1]}] | {f('arith_pct_yr')} | {f('cagr_pct')} | {f('maxdd_pct')} | {bl['2.0']['maxdd_span_days']}{'' if bl['2.0']['maxdd_recovered'] else '(unrec)'} | {bl['2.0']['worst_day_pct']} ({bl['2.0']['worst_day']}) | {bl['2.0']['days_below_2pct']}/{bl['2.0']['days_below_5pct']}/{bl['2.0']['days_below_10pct']} of {w['n_days']} | {bl['3.0']['min_margin_ratio_anchor']} |")
    P("\nform by window: " + json.dumps({k: v["form"] for k, v in o["windows"].items() if not v.get("skipped")}, ensure_ascii=False)[:3000])
    for nm, s in o["slices"].items():
        P(f"\nSLICE {nm} ({s['definition']}) causal cuts@end {s['causal_cuts_at_window_end']} desc cuts {s['descriptive_cuts_2024_cut']}")
        for kind in ("causal", "descriptive"):
            P(f"  {kind}: " + " | ".join(f"{k}: n={v.get('n_anchors')} var={v.get('regime_var_mean')} mean={v.get('mean_bps_anchor_per_gross')} CI={v.get('mean_ci95')} S={v.get('sharpe_anchor')} NAV%/yr@2={v.get('nav_pct_yr_at_2x')}" for k, v in s[kind].items() if isinstance(v, dict)) + f" | unassigned {s[kind]['unassigned_n']}")
    return "\n".join(L)
if __name__ == "__main__":
    print("UNITS CHAIN: g = net_ex/gross_total [bps/anchor per gross] -> r_L = g*L [bps/anchor NAV] -> %/yr = mean*2190/1e4; e.g. 1 bps/anchor per gross at L=2 = 43.8 %/yr arithmetic", flush=True)
    os.makedirs(f"{ROOT}/results", exist_ok=True)
    for p in sys.argv[1:]:
        o = analyse(p); json.dump(o, open(f"{ROOT}/results/{o['tag']}.json", "w"), indent=1, ensure_ascii=False)
        t = txt(o); open(f"{ROOT}/results/{o['tag']}.txt", "w").write(t + "\n"); print(t, flush=True)
    print("HEALTH_METRICS_DONE", flush=True)
