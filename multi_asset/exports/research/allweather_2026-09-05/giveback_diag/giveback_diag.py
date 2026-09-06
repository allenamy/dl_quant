#!/usr/bin/env python
"""giveback_diag.py — READ-ONLY diagnostic (team-lead 09-06 05:0xZ): base rate of large givebacks in the live-form replay and a uniform tail-lever comparison table
from ARCHIVED artifacts only (no device rerun, no new arm). Writes only under /workspace/review_scratch/allweather_trackC/giveback/.
Base = health_check main arm M1_UPIT_prod_s{42,2027}_ccal (U-PIT · m1 · FTRIM · dynamic seat · live fee tiers · accounting caliber); arm d30_n2_c42 (= live per-name stop clause), S0 = no stop.
UNITS: g = net_ex/gross_total [bps/anchor per unit gross]; NAV return at L=2 per anchor r = 2g/1e4; UTC-day equity change = Π(1+r) − 1 over the day's anchors (anchor 20:00Z belongs to its own UTC day);
  maxDD at 2× from Π(1+r); worst month = compounded month at 2×; worst k-anchor window = Π(1+r) − 1 over k consecutive anchors; thresholds −2.68% (executor cond2 investigation tier, per team-lead) and −4.0% (far line).
Side split of big-loss anchors (g ≤ −40): price P&L per name = w_k · y4_k (W = the saved sm weights, file caliber; y4 = prod meta) ⇒ long side Σ_{w>0}, short side Σ_{w<0}, in bps of gross_total;
  carry_ex and cost_ex from the rec are book-level (not per name) and are reported beside. Per-name worst 20 (anchor, name) 2024→26: w·y4·1e4/gross with side, rn8 (panel f_fund_now·8/iv, bps/8h),
  listing age (days since first observation = finite y4 or qvk>0, meta), 7-day realised vol (std of the name's y4 over the prior 42 anchors, %/4h), position share |w|/gross, y4 (%).
Tail-lever table (uniform metric from archived series): carry_layers L10/L20, Track C AGEW 0.5/1/2, C2 down-only vol-target overlays (recomputed from the base series with the archived c2 code and
  cross-checked to c2_voltarget.json), per-name stop clause (d30 vs S0 in the same artifacts). Paired Δ vs base: UTC-day-block bootstrap 2000, seed 20260905.
"""
import numpy as np, json, time, calendar, hashlib, os, sys, importlib.util
ROOT = "/workspace/review_scratch/allweather_trackC/giveback"; HC = "/workspace/review_scratch/health_check"; CL = "/workspace/review_scratch/allweather_trackC/carry_layers"; TC = "/workspace/review_scratch/allweather_trackC"
META = "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz"; PANEL = "/workspace/data/wide_panel_4h_v2ext.npz"
NB = 2000; SEED = 20260905; APY = 2190; L = 2.0; THR1 = -0.0268; THR2 = -0.04; BIG = -40.0
def T(s): return int(calendar.timegm(time.strptime(s, "%Y-%m-%d")))
CUT = T("2026-08-10") + 20 * 3600
WIN = {"2024": (T("2024-01-01"), T("2025-01-01")), "2025": (T("2025-01-01"), T("2026-01-01")), "2026->cut": (T("2026-01-01"), CUT + 1), "2026->08-30": (T("2026-01-01"), 2**40), "2024->26": (T("2024-01-01"), 2**40), "2025->26": (T("2025-01-01"), 2**40), "2024->cut": (T("2024-01-01"), CUT + 1)}
YEARS = ("2024", "2025", "2026->08-30")
COLS = ["ts", "net", "pnl", "carry", "cost", "gross_total", "gross_member", "gross_sel", "nsel", "nmember", "fires", "leg_king", "leg_rev24", "leg_fund", "w3_king", "w3_rev24", "w3_fund", "turnover", "net_ex", "pnl_ex", "carry_ex", "cost_ex", "netlong"]
C = {k: i for i, k in enumerate(COLS)}
def r4(v): return None if v is None or (isinstance(v, float) and not np.isfinite(v)) else round(float(v), 4)
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
def sharpe(x): return float(x.mean() / x.std(ddof=1) * np.sqrt(APY)) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")
def sha16(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
def daily(g, ts):
    r = L * g / 1e4; days = ts // 86400; ud, inv = np.unique(days, return_inverse=True); dl = np.bincount(inv, np.log1p(r)); return ud, np.expm1(dl)
def boot(d, ts):
    days = ts // 86400; ud, inv = np.unique(days, return_inverse=True); nd = len(ud)
    if nd < 5: return [None, None]
    s1 = np.bincount(inv, d); c = np.bincount(inv).astype(float); rng = np.random.default_rng(SEED); ii = rng.integers(0, nd, size=(NB, nd)); m = s1[ii].sum(1) / c[ii].sum(1)
    return [r4(np.percentile(m, 2.5)), r4(np.percentile(m, 97.5))]
def metrics(g, ts):
    out = {}
    for wn, (lo, hi) in WIN.items():
        m = (ts >= lo) & (ts < hi); gw = g[m]; tw = ts[m]
        if m.sum() < 12: out[wn] = {"n": int(m.sum())}; continue
        r = L * gw / 1e4; nav = np.cumprod(1 + r); dd = float((1 - nav / np.maximum.accumulate(nav)).max() * 100)
        ud, dr = daily(gw, tw); months = np.array([time.gmtime(int(d * 86400)).tm_year * 100 + time.gmtime(int(d * 86400)).tm_mon for d in ud]); um = np.unique(months); mret = np.array([np.expm1(np.log1p(dr[months == mm]).sum()) for mm in um])
        k3 = np.expm1(np.convolve(np.log1p(r), np.ones(3), "valid")); k6 = np.expm1(np.convolve(np.log1p(r), np.ones(6), "valid"))
        i3 = int(np.argmin(k3)); i6 = int(np.argmin(k6)); iw = int(np.argmin(dr))
        out[wn] = {"n": int(m.sum()), "n_days": int(len(ud)), "mean_bps_gross": r4(gw.mean()), "sharpe": r4(sharpe(gw)), "maxdd_pct_2x": r4(dd), "nav_pct_yr_2x_arith": r4(gw.mean() * 6 * 365 * 2 / 1e4 * 100),
                   "worst_month_pct_2x": r4(mret.min() * 100), "worst_month": str(int(um[np.argmin(mret)])), "days_le_268": int((dr <= THR1).sum()), "days_le_400": int((dr <= THR2).sum()), "days_le_200": int((dr <= -0.02).sum()), "worst_day_pct_2x": r4(dr.min() * 100), "worst_day": time.strftime("%Y-%m-%d", time.gmtime(int(ud[iw] * 86400))),
                   "worst3_pct_2x": r4(k3.min() * 100), "worst3_end": iso(tw[i3 + 2]), "worst6_pct_2x": r4(k6.min() * 100), "worst6_end": iso(tw[i6 + 5]), "anchors_le_40bps": int((gw <= BIG).sum()), "anchors_le_80bps": int((gw <= 2 * BIG).sum()),
                   "pct": {str(q): r4(np.percentile(gw, q)) for q in (1, 5, 25, 50, 75, 95, 99)}, "min_bps": r4(gw.min()), "max_bps": r4(gw.max())}
    return out
def load_arm(p, arm="d30_n2_c42"):
    Z = np.load(p, allow_pickle=True); assert [str(c) for c in Z["cols"]] == COLS; R = Z[f"{arm}_rec"]; cfg = json.loads(str(Z["config_json"]))
    return {"path": p, "sha16": sha16(p), "cfg": cfg, "ts": R[:, 0].astype(np.int64), "g": R[:, C["net_ex"]] / R[:, C["gross_total"]], "gt": R[:, C["gross_total"]], "R": R, "W": Z[f"{arm}_W"].astype(np.float64) if f"{arm}_W" in Z.files else None}
def delta_block(ga, gb, ts):
    out = {}
    for wn in ("2024->26", "2025->26", "2024->cut", "2024", "2025", "2026->08-30"):
        lo, hi = WIN[wn]; m = (ts >= lo) & (ts < hi); d = ga[m] - gb[m]; out[wn] = {"delta_mean": r4(d.mean()), "ci95": boot(d, ts[m])}
    return out
os.makedirs(f"{ROOT}/results", exist_ok=True)
MT = np.load(META, allow_pickle=True); mE = MT["E_ts"].astype(np.int64); Y4 = MT["y4"]; QVK = MT["qvk"]; mrow = {int(t): i for i, t in enumerate(mE)}
PW = np.load(PANEL, allow_pickle=True); SY = [str(s) for s in PW["symbols"]]; pts = PW["ts"].astype(np.int64); prow = {int(t): j for j, t in enumerate(pts)}; FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]
listed = np.isfinite(Y4) | (np.nan_to_num(QVK, nan=0.0) > 0); first = np.where(listed.any(0), listed.argmax(0), -1)
FI_PATH = "/workspace/review_scratch/crash_risk/data/fundinginfo.json"; CAP = {}; FI_META = {"path": FI_PATH, "exists": os.path.exists(FI_PATH)}
if FI_META["exists"]:
    fi = json.load(open(FI_PATH)); items = fi if isinstance(fi, list) else (fi.get("data") or fi.get("symbols") or fi.get("fundingInfo") or list(fi.values()))
    for it in items:
        if isinstance(it, dict) and "symbol" in it:
            try: CAP[it["symbol"]] = {"cap": float(it.get("adjustedFundingRateCap")), "floor": float(it.get("adjustedFundingRateFloor")), "interval_h": float(it.get("fundingIntervalHours"))}
            except Exception: pass
    FI_META.update({"n_symbols": len(CAP), "sha16": sha16(FI_PATH), "note": "current fundingInfo (cap/floor/interval as of the pull) used as a proxy for the historical cap at the event anchor — INFERRED"})
OUT = {"fundinginfo": None, "units": "g = net_ex/gross_total bps/anchor per gross; NAV at 2x: r = 2g/1e4; UTC-day compounding; thresholds -2.68% (executor cond2 tier) and -4.0%", "base": {}, "levers": {}, "per_name": {}, "sources": {}}
BASES = {}
for s in ("42", "2027"):
    p = f"{HC}/dev_alt/probe_artifacts/w10_ablation_series_M1_UPIT_prod_s{s}_ccal.npz"; b = load_arm(p); BASES[s] = b
    assert b["cfg"]["UMASK_SCOPE"] == "m1" and b["cfg"]["FTRIM"] == "zero" and b["cfg"]["COSTB_JSON"] and b["cfg"]["W3FIX"] is None and b["cfg"]["FSEED"] == s
    ts, g, gt, W, R = b["ts"], b["g"], b["gt"], b["W"], b["R"]; met = metrics(g, ts)
    # daily series receipt (last 10 UTC days of the replay, context only — the live September anchors are NOT in the replay)
    ud, dr = daily(g, ts); last10 = [(time.strftime("%Y-%m-%d", time.gmtime(int(d * 86400))), r4(x * 100)) for d, x in zip(ud[-10:], dr[-10:])]
    # big-loss anchors: side split from W × y4
    rows = np.array([mrow[int(t)] for t in ts]); Yv = np.nan_to_num(Y4[rows], nan=0.0)
    lp = (np.where(W > 0, W, 0.0) * Yv).sum(1) * 1e4 / gt; sp_ = (np.where(W < 0, W, 0.0) * Yv).sum(1) * 1e4 / gt
    m24 = ts >= WIN["2024->26"][0]; big = m24 & (g <= BIG); nb = int(big.sum())
    side = {"n_big_anchors_2024on": nb, "share_short_side_worse": r4((sp_[big] < lp[big]).mean()) if nb else None, "mean_long_price_bps": r4(lp[big].mean()) if nb else None, "mean_short_price_bps": r4(sp_[big].mean()) if nb else None,
            "mean_carry_bps": r4((R[big, C["carry_ex"]] / gt[big]).mean()) if nb else None, "mean_cost_bps": r4((R[big, C["cost_ex"]] / gt[big]).mean()) if nb else None, "mean_g_bps": r4(g[big].mean()) if nb else None,
            "by_year": {}}
    for y, (lo, hi) in (("2024", WIN["2024"]), ("2025", WIN["2025"]), ("2026", WIN["2026->08-30"])):
        mb = big & (ts >= lo) & (ts < hi); side["by_year"][y] = {"n": int(mb.sum()), "share_short_worse": r4((sp_[mb] < lp[mb]).mean()) if mb.sum() else None, "mean_long": r4(lp[mb].mean()) if mb.sum() else None, "mean_short": r4(sp_[mb].mean()) if mb.sum() else None}
    # netlong context on big anchors and BTC-ish proxy = mean y4 of members (market move)
    mkt = np.array([np.nanmean(Y4[rows[i]]) for i in range(len(ts))]) * 1e4
    side["mean_market_y4_bps_on_big"] = r4(mkt[big].mean()) if nb else None; side["share_big_with_market_up_gt_100bps"] = r4((mkt[big] > 100).mean()) if nb else None; side["share_big_with_market_down_lt_-100bps"] = r4((mkt[big] < -100).mean()) if nb else None
    # per-name worst 20 (anchor, name) 2024->26
    P = W * Yv * 1e4 / gt[:, None]; Pm = np.where(m24[:, None], P, 0.0); flat = np.argsort(Pm.ravel())[:20]; worst = []
    for f in flat:
        i, k = divmod(int(f), P.shape[1]); j = prow.get(int(ts[i])); iv = float(IV[j, k]) if j is not None and np.isfinite(IV[j, k]) and IV[j, k] > 0 else 8.0; rn8 = float(FN[j, k]) * 8.0 / iv * 1e4 if j is not None and np.isfinite(FN[j, k]) else None
        age = (int(ts[i]) - int(mE[first[k]])) / 86400 if first[k] > 0 else None; ri = rows[i]; hist = Y4[max(0, ri - 42):ri, k]; vol = float(np.nanstd(hist) * 100) if np.isfinite(hist).sum() >= 20 else None
        h3 = Y4[max(0, ri - 18):ri, k]; du3 = float((np.prod(1 + np.nan_to_num(h3, nan=0.0)) - 1) * 100) if np.isfinite(h3).sum() >= 12 else None
        capinfo = CAP.get(SY[k]); rate_per_sett = float(FN[j, k]) if (j is not None and np.isfinite(FN[j, k])) else None
        rcap = (rate_per_sett / capinfo["cap"]) if (capinfo and rate_per_sett is not None and capinfo["cap"] > 0) else None
        worst.append({"anchor": iso(ts[i]), "symbol": SY[k], "side": "long" if W[i, k] > 0 else "short", "pnl_bps_gross": r4(P[i, k]), "pos_share_of_gross": r4(abs(W[i, k]) / gt[i]), "y4_pct": r4(Yv[i, k] * 100), "rn8_bps_8h": r4(rn8), "listing_age_days": r4(age) if age is not None else "left-censored/unknown", "vol7d_pct_per_4h": r4(vol), "du3d_pct": r4(du3), "rate_over_cap_current": r4(rcap), "cap_interval_h_current": (capinfo["interval_h"] if capinfo else None), "anchor_g_bps": r4(g[i]), "market_y4_bps": r4(mkt[i])})
    OUT["base"][f"s{s}"] = {"artifact": p, "sha16": b["sha16"], "metrics": met, "big_loss_side_split": side, "last10_utc_days_pct_2x": last10}; OUT["per_name"][f"s{s}"] = worst
    if s == "42":   # S0 vs d30 (per-name stop clause) from the same artifact
        s0 = load_arm(p, "S0"); OUT["levers"]["stop_clause_d30_vs_S0/s42"] = {"arm": "d30_n2_c42 (live per-name stop: −30% depth ×2 anchors, cooldown 42) vs S0 (no stop)", "artifact": p, "arm_metrics": met, "base_metrics(S0)": metrics(s0["g"], s0["ts"]), "delta_arm_minus_S0": delta_block(g, s0["g"], ts)}
    if s == "2027":
        s0 = load_arm(p, "S0"); OUT["levers"]["stop_clause_d30_vs_S0/s2027"] = {"arm": "d30 vs S0", "artifact": p, "arm_metrics": met, "base_metrics(S0)": metrics(s0["g"], s0["ts"]), "delta_arm_minus_S0": delta_block(g, s0["g"], ts)}
# --- tail-lever table from archived artifacts
ARMS = [("carry_layers", "L10", "carry_layers L HI+10 (long carry hurdle)", f"{CL}/dev_alt/probe_artifacts/w10_ablation_series_L10_prod_s{{s}}.npz", f"{CL}/dev_alt/probe_artifacts/w10_ablation_series_B0_prod_s{{s}}.npz"),
        ("carry_layers", "L20", "carry_layers L HI+20", f"{CL}/dev_alt/probe_artifacts/w10_ablation_series_L20_prod_s{{s}}.npz", f"{CL}/dev_alt/probe_artifacts/w10_ablation_series_B0_prod_s{{s}}.npz"),
        ("trackC", "A05", "Track C C1 AGEW 0.5", f"{TC}/dev_alt/probe_artifacts/w10_ablation_series_A05_prod_s{{s}}.npz", f"{TC}/dev_alt/probe_artifacts/w10_ablation_series_A0_prod_s{{s}}.npz"),
        ("trackC", "A10", "Track C C1 AGEW 1.0", f"{TC}/dev_alt/probe_artifacts/w10_ablation_series_A10_prod_s{{s}}.npz", f"{TC}/dev_alt/probe_artifacts/w10_ablation_series_A0_prod_s{{s}}.npz"),
        ("trackC", "A20", "Track C C1 AGEW 2.0", f"{TC}/dev_alt/probe_artifacts/w10_ablation_series_A20_prod_s{{s}}.npz", f"{TC}/dev_alt/probe_artifacts/w10_ablation_series_A0_prod_s{{s}}.npz")]
for fam, tag, label, ap, bp in ARMS:
    for s in ("42", "2027"):
        a = load_arm(ap.format(s=s)); b = load_arm(bp.format(s=s)); assert np.array_equal(a["ts"], b["ts"]) and np.array_equal(b["g"], BASES[s]["g"]), (tag, s, "base not bitwise HC main")
        OUT["levers"][f"{tag}/s{s}"] = {"arm": label, "artifact": a["path"], "sha16": a["sha16"], "base_artifact": b["path"], "arm_metrics": metrics(a["g"], a["ts"]), "delta_vs_base": delta_block(a["g"], b["g"], a["ts"])}
VC = "/workspace/review_scratch/tail_aware_sizing/dev_alt/probe_artifacts"
for gam in ("0.5", "1.0"):
    for s in ("42", "2027"):
        a = load_arm(f"{VC}/w10_ablation_series_VC_prod_g{gam}_s{s}.npz"); b = load_arm(f"{VC}/w10_ablation_series_VC_prod_g0_s{s}.npz"); assert np.array_equal(a["ts"], b["ts"]) and np.array_equal(b["g"], BASES[s]["g"]), ("VC base not bitwise HC main", s)
        OUT["levers"][f"VC_g{gam}/s{s}"] = {"arm": f"tail_aware_sizing per-name vol cap γ={gam} (|w| ≤ capw·min(1,(σ_med/σ)^γ))", "artifact": a["path"], "sha16": a["sha16"], "base_artifact": b["path"], "arm_metrics": metrics(a["g"], a["ts"]), "delta_vs_base": delta_block(a["g"], b["g"], a["ts"])}
# C2 overlays recomputed from the base series with the archived code; cross-check to archived json levels
spec = importlib.util.spec_from_file_location("c2", f"{TC}/c2_voltarget.py"); c2 = importlib.util.module_from_spec(spec); spec.loader.exec_module(c2)
c2j = json.load(open(f"{TC}/c2/c2_voltarget.json"))
for s in ("42", "2027"):
    g = BASES[s]["g"]; ts = BASES[s]["ts"]
    for q in (0.5, 0.65, 0.8):
        ins, sym, sig, star = c2.gates(g, q); x, drag = c2.overlay(g, ins); arch = c2j["cells"][f"prod/s{s}"]["arms"][f"ins_q{q:.2f}"]["levels"]
        chk = {w: (r4(x[(ts >= WIN[w if w != "2024->26" else "2024->cut"][0]) & (ts < WIN[w if w != "2024->26" else "2024->cut"][1])].mean()), arch[w]["mean"]) for w in ("2024", "2025", "2024->26")}   # archived 2024->26 ends at the cut
        assert all(abs(a_ - b_) < 1e-3 for a_, b_ in chk.values()), ("C2 recompute mismatch", s, q, chk)
        OUT["levers"][f"C2_ins_q{q:.2f}/s{s}"] = {"arm": f"Track C C2 down-only vol target q={q:.2f} (paper overlay, cost 3.92 bps/unit gross moved)", "artifact": f"{TC}/c2/c2_voltarget.json (levels cross-checked: {chk})", "arm_metrics": metrics(x, ts), "delta_vs_base": delta_block(x, g, ts)}
OUT["fundinginfo"] = FI_META
json.dump(OUT, open(f"{ROOT}/results/giveback.json", "w"), indent=1, ensure_ascii=False)
# --- tables
Lm = []; P = Lm.append
P("## ① Base rate — health_check main arm (U-PIT·m1·FTRIM·dynamic seat·live fees·accounting caliber), arm d30_n2_c42; g bps/anchor per gross; NAV at 2×")
P("| seed | window | n anchors / days | mean g | Sharpe | maxDD 2× | worst month 2× | days ≤−2.68% | ≤−4.0% | ≤−2% | worst day 2× | worst 3-anchor 2× (end) | worst 6-anchor 2× (end) | anchors ≤−40 / ≤−80 bps | g pct 1/5/50/95/99 | min / max |")
P("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for s in ("42", "2027"):
    met = OUT["base"][f"s{s}"]["metrics"]
    for w in ("2024", "2025", "2026->cut", "2026->08-30", "2024->26", "2025->26"):
        m = met[w]; P(f"| s{s} | {w} | {m['n']} / {m['n_days']} | {m['mean_bps_gross']:+.3f} | {m['sharpe']:.2f} | {m['maxdd_pct_2x']:.1f}% | {m['worst_month_pct_2x']:+.1f}% ({m['worst_month']}) | {m['days_le_268']} | {m['days_le_400']} | {m['days_le_200']} | {m['worst_day_pct_2x']:+.2f}% ({m['worst_day']}) | {m['worst3_pct_2x']:+.2f}% ({m['worst3_end']}) | {m['worst6_pct_2x']:+.2f}% ({m['worst6_end']}) | {m['anchors_le_40bps']} / {m['anchors_le_80bps']} | {m['pct']['1']:+.1f}/{m['pct']['5']:+.1f}/{m['pct']['50']:+.2f}/{m['pct']['95']:+.1f}/{m['pct']['99']:+.1f} | {m['min_bps']:+.1f} / {m['max_bps']:+.1f} |")
P("\n## ① Big-loss anchors (g ≤ −40 bps/gross, 2024→26): side split of PRICE P&L from W×y4 (bps of gross); carry/cost are book-level")
P("| seed | n big | share short side worse | mean long price | mean short price | mean carry | mean cost | mean g | market mean y4 on big (bps) | share market up >+100 bps | share market down <−100 | by year n / share short worse / mean long / mean short |")
P("|---|---|---|---|---|---|---|---|---|---|---|---|")
for s in ("42", "2027"):
    d = OUT["base"][f"s{s}"]["big_loss_side_split"]; by = " · ".join(f"{y}: {v['n']} / {v['share_short_worse']} / {v['mean_long']} / {v['mean_short']}" for y, v in d["by_year"].items())
    P(f"| s{s} | {d['n_big_anchors_2024on']} | {d['share_short_side_worse']} | {d['mean_long_price_bps']} | {d['mean_short_price_bps']} | {d['mean_carry_bps']} | {d['mean_cost_bps']} | {d['mean_g_bps']} | {d['mean_market_y4_bps_on_big']} | {d['share_big_with_market_up_gt_100bps']} | {d['share_big_with_market_down_lt_-100bps']} | {by} |")
P("\nLast 10 UTC days of the replay at 2× (context only; live September anchors are not in the replay): " + "; ".join(f"s{s}: " + ", ".join(f"{d} {x:+.2f}%" for d, x in OUT["base"][f"s{s}"]["last10_utc_days_pct_2x"]) for s in ("42", "2027")))
P("\n## ② Tail levers — uniform metric from archived series (prod caliber; Δ = arm − base per gross, UTC-day-block bootstrap CI95; days ≤−2.68% per window at 2×)")
P("| lever | seed | Δ 2024→26 [CI] | Δ 2025→26 [CI] | Δ 2024 / 2025 / 2026 | maxDD 2× base → arm (2024→26) | worst month base → arm | days ≤−2.68% base → arm (24→26; 2024/2025/2026) | Sharpe base → arm 2024 / 2025 / 2026 |")
P("|---|---|---|---|---|---|---|---|---|")
for key, v in OUT["levers"].items():
    s = key.split("/")[-1][1:] if "/s" in key else "42"; bm = OUT["base"][f"s{s}"]["metrics"] if "stop_clause" not in key else v["base_metrics(S0)"]; am = v["arm_metrics"]; dl = v["delta_arm_minus_S0"] if "stop_clause" in key else v["delta_vs_base"]
    f = lambda w: f"{dl[w]['delta_mean']:+.3f} [{dl[w]['ci95'][0]:+.3f},{dl[w]['ci95'][1]:+.3f}]"
    P(f"| {v['arm']} | s{s} | {f('2024->26')} | {f('2025->26')} | {dl['2024']['delta_mean']:+.3f} / {dl['2025']['delta_mean']:+.3f} / {dl['2026->08-30']['delta_mean']:+.3f} | {bm['2024->26']['maxdd_pct_2x']:.1f}% → {am['2024->26']['maxdd_pct_2x']:.1f}% | {bm['2024->26']['worst_month_pct_2x']:+.1f}% ({bm['2024->26']['worst_month']}) → {am['2024->26']['worst_month_pct_2x']:+.1f}% ({am['2024->26']['worst_month']}) | {bm['2024->26']['days_le_268']} → {am['2024->26']['days_le_268']} ({bm['2024']['days_le_268']}/{bm['2025']['days_le_268']}/{bm['2026->08-30']['days_le_268']} → {am['2024']['days_le_268']}/{am['2025']['days_le_268']}/{am['2026->08-30']['days_le_268']}) | {bm['2024']['sharpe']:.2f}/{bm['2025']['sharpe']:.2f}/{bm['2026->08-30']['sharpe']:.2f} → {am['2024']['sharpe']:.2f}/{am['2025']['sharpe']:.2f}/{am['2026->08-30']['sharpe']:.2f} |")
P("\n## ③ Per-name worst 20 (anchor, name) price P&L 2024→26, bps of gross (W×y4 from the saved weights; side; rn8 bps/8h; listing age days; 7-day realised vol %/4h; position share; y4 %; anchor g; market mean y4)")
for s in ("42", "2027"):
    P(f"\n**seed {s}**\n"); P("| # | anchor (UTC) | name | side | P&L bps/gross | pos share | y4 % | rn8 bps/8h | age d | vol7d %/4h | du 3d % | rate/cap (current cap, interval) | anchor g | market y4 bps |"); P("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for i, w in enumerate(OUT["per_name"][f"s{s}"]): P(f"| {i+1} | {w['anchor']} | {w['symbol']} | {w['side']} | {w['pnl_bps_gross']:+.1f} | {w['pos_share_of_gross']:.4f} | {w['y4_pct']:+.1f} | {w['rn8_bps_8h']} | {w['listing_age_days']} | {w['vol7d_pct_per_4h']} | {w['du3d_pct']} | {w['rate_over_cap_current']} ({w['cap_interval_h_current']}h) | {w['anchor_g_bps']:+.1f} | {w['market_y4_bps']:+.0f} |")
open(f"{ROOT}/results/giveback_tables.md", "w").write("\n".join(Lm) + "\n"); print("\n".join(Lm)); print("GIVEBACK_DONE")
