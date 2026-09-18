#!/usr/bin/env python3
"""FP3-R evaluation (PREREG §2–§3): baseline record vs overlay variant records, same engine, same accounting (net_ex = the evaluation caliber).
v2 (R7B-R1): every book quantity is taken from the ACCOUNTED book HR (post-reshape, post-overlay) — the same book the returns are computed on; turnover = Σ|ΔHR|. Per variant: per-year g, daily Sharpe, maxDD@L (per-anchor compounding), worst day, days ≤ −2.68% and ≤ −4% at L=2 (UTC-day NAV path), turnover ratio,
breadth-top-decile bucket g (breadth = causal member EW 24h return, computed here from the meta y4 exactly as the overlay does) and the paired Δ vs
baseline with a UTC-day block bootstrap CI95 over W_ALPHA and KING_LIVE. Gates G1/G2/G3 evaluated as frozen. usage: overlay_eval.py <probe_dir> <king_meta.npz> <out.json>"""
import glob, json, os, sys, time, hashlib, collections, numpy as np
PD, META, OUT = sys.argv[1:4]; L = 2.0; WA0, UB, KL0 = 1656547200, 1788120000, 1704067200; DELTA = 0.05
PREFIX = os.environ.get("ARM_PREFIX", "V4_A0_dyn_s42")          # arm/seed under evaluation (R3 replication: V4_A1_dyn_s42, V4_A0_dyn_s2027)
BUCKET = os.environ.get("BUCKET", "breadth")                    # "breadth" = causal trailing-24h breadth top decile (PREREG R); "changed" = anchors where the variant's accounted book differs from baseline (= its own trigger set; PREREG R6 G3)
CONTROL = os.environ.get("CONTROL_TAG")                         # PREREG R6 G4: a variant tag whose numbers every other variant is compared against (unconditional same-average-leverage control)
ONLY = os.environ.get("ONLY_PREFIX")                            # evaluate only variant tags starting with this (e.g. "r6")
def load(tag):
    z = np.load(f"{PD}/w10_ablation_series_{PREFIX}_{tag}.npz", allow_pickle=True); C = [str(c) for c in z["cols"]]; rec = np.asarray(z["d30_n2_c42_rec"], float)
    ts = rec[:, C.index("ts")].astype(np.int64); g = rec[:, C.index("net_ex")] / np.where(rec[:, C.index("gross_total")] > 0, rec[:, C.index("gross_total")], np.nan)
    HR = np.asarray(z["d30_n2_c42_HR"], np.float32); W = np.asarray(z["d30_n2_c42_W"], np.float32)     # HR = accounted book (what pnl/carry/cost_ex are computed on); W = target book
    to = np.concatenate([[np.nan], np.abs(np.diff(np.nan_to_num(HR), axis=0)).sum(1)])                  # executor-caliber turnover = Σ|ΔHR| (the same book the returns are on)
    return ts, g, to, json.loads(str(z["config_json"])).get("OVERLAY", "?"), HR, W
M = np.load(META, allow_pickle=True); E = M["E_ts"].astype(np.int64); y4 = np.asarray(M["y4"], float); MEM = M["members"]
ts0, g0, to0, _, W0, T0 = load("OVLnone"); pos = {int(t): i for i, t in enumerate(E)}   # W0 = accounted book of the baseline; T0 = its target book
# causal breadth per book anchor (rows i-6..i-1 of y4 over members), then top decile flag using the expanding history (as the overlay sees it)
B = np.full(len(ts0), np.nan)
for k, t in enumerate(ts0):
    i = pos.get(int(t))
    if i is None or i < 6: continue
    m = np.asarray(MEM[i]).astype(int); seg = y4[i - 6:i][:, m]; B[k] = np.where(np.isfinite(seg), seg, 0.0).mean(1).sum()
top = np.zeros(len(ts0), bool); hist = []
for k in range(len(ts0)):
    b = B[k]
    if np.isfinite(b):
        if len(hist) >= 200 and b >= np.quantile(hist, 0.90): top[k] = True
        hist.append(b)
day = np.array([time.strftime("%Y%m%d", time.gmtime(int(t))) for t in ts0]); year = np.array([d[:4] for d in day])
def stats(g, mask):
    x = np.nan_to_num(g[mask]); d = day[mask]; ud, inv = np.unique(d, return_inverse=True); nav = np.ones(len(ud)); 
    daily = np.array([np.prod(1 + L * x[inv == k] * 1e-4) - 1 for k in range(len(ud))])
    path = np.cumprod(1 + L * x * 1e-4); mdd = float((path / np.maximum.accumulate(path) - 1).min()) if len(path) else np.nan
    return {"n": int(mask.sum()), "g": float(x.mean()), "sharpe_daily": float(daily.mean() / daily.std(ddof=1) * np.sqrt(365)) if len(daily) > 2 and daily.std(ddof=1) > 0 else None, "maxdd_L": mdd, "worst_day": float(daily.min()), "days_le_m2p68": int((daily <= -0.0268).sum()), "days_le_m4": int((daily <= -0.04).sum()), "n_days": len(daily)}
def paired_ci(d, mask, B_=2000, seed=0):
    x = np.nan_to_num(d[mask]); dd = day[mask]; ud, inv = np.unique(dd, return_inverse=True); nd = len(ud); rng = np.random.default_rng(seed)
    sums = np.bincount(inv, weights=x, minlength=nd); cnts = np.bincount(inv, minlength=nd); boots = []
    for _ in range(B_):
        idx = rng.integers(0, nd, nd); boots.append(sums[idx].sum() / max(1, cnts[idx].sum()))
    return float(x.mean()), [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]
WA = (ts0 >= WA0) & (ts0 <= UB); KL = (ts0 >= KL0) & (ts0 <= UB)
out = {"device": "overlay_eval.py", "self_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest(), "utc": time.strftime("%FT%TZ", time.gmtime()), "L": L, "delta": DELTA, "baseline": {"W_ALPHA": stats(g0, WA), "KING_LIVE": stats(g0, KL), "by_year": {y: stats(g0, WA & (year == y)) for y in sorted(set(year[WA]))}, "top_decile_breadth": {"n": int((WA & top).sum()), "g": float(np.nan_to_num(g0[WA & top]).mean())}, "turnover_mean": float(np.nanmean(to0[WA])), "max_abs_accounted_weight": float(np.nanmax(np.abs(W0))), "accounted_over_target_gross": float(np.nanmean(np.abs(np.nan_to_num(W0)).sum(1) / np.maximum(np.abs(np.nan_to_num(T0)).sum(1), 1e-9)))}, "variants": {}}
for p in sorted(glob.glob(f"{PD}/w10_ablation_series_{PREFIX}_OVL_*.npz")):
    tag = os.path.basename(p).split("_OVL_")[1][:-4]
    if "d30_n2_c42_HR" not in np.load(p, allow_pickle=True).files: out.setdefault("skipped_no_HR", []).append(tag); continue   # produced by the pre-relocation engine (exploratory r5): not comparable, not evaluated
    if ONLY and not tag.startswith(ONLY): continue
    ts, g, to, spec, W1, T1 = load("OVL_" + tag); assert np.array_equal(ts, ts0), tag
    dW = np.abs(np.nan_to_num(W1) - np.nan_to_num(W0)).sum(1); wired = {"anchors_changed": int((dW > 1e-9).sum()), "frac_changed": float((dW > 1e-9).mean()), "mean_L1_dW_over_gross": float(np.nanmean(dW / np.maximum(np.abs(np.nan_to_num(W0)).sum(1), 1e-9))),
             "accounted_over_target_gross": float(np.nanmean(np.abs(np.nan_to_num(W1)).sum(1) / np.maximum(np.abs(np.nan_to_num(T1)).sum(1), 1e-9))), "target_book_unchanged": bool(np.array_equal(np.nan_to_num(T1), np.nan_to_num(T0))),
             "max_abs_accounted_weight": float(np.nanmax(np.abs(W1))), "net_over_gross_max": float(np.nanmax(np.abs(np.nan_to_num(W1).sum(1)) / np.maximum(np.abs(np.nan_to_num(W1)).sum(1), 1e-9)))}
    d = g - g0; dW, ciW = paired_ci(d, WA); dK, ciK = paired_ci(d, KL)
    bucket = (WA & top) if BUCKET == "breadth" else (WA & (dW > 1e-9)) if False else (WA & (np.abs(np.nan_to_num(W1) - np.nan_to_num(W0)).sum(1) > 1e-9))
    if BUCKET == "breadth": bucket = WA & top
    dT, ciT = paired_ci(d, bucket) if bucket.sum() > 10 else (float("nan"), [float("nan"), float("nan")])
    sW, sK = stats(g, WA), stats(g, KL); by = {y: stats(g, WA & (year == y)) for y in sorted(set(year[WA]))}; b0 = out["baseline"]
    worst_year_sharpe = min(v["sharpe_daily"] for v in by.values() if v["sharpe_daily"] is not None); worst_year_sharpe0 = min(v["sharpe_daily"] for v in b0["by_year"].values() if v["sharpe_daily"] is not None)
    G1 = ciW[0] > -DELTA; G2 = (worst_year_sharpe >= worst_year_sharpe0 - 1e-9) and ((sW["maxdd_L"] - b0["W_ALPHA"]["maxdd_L"] >= 0.05) or (sW["days_le_m4"] <= b0["W_ALPHA"]["days_le_m4"] // 2)) and (sW["days_le_m2p68"] <= b0["W_ALPHA"]["days_le_m2p68"]); G3 = bool(np.isfinite(ciT[0]) and ciT[0] > 0)
    out["variants"][tag] = {"spec": spec, "W_ALPHA": sW, "KING_LIVE": sK, "by_year": by, "top_decile_breadth": {"n": int((WA & top).sum()), "g": float(np.nan_to_num(g[WA & top]).mean())}, "bucket": {"mode": BUCKET, "n": int(bucket.sum()), "g_variant": float(np.nan_to_num(g[bucket]).mean()) if bucket.sum() else None, "g_baseline": float(np.nan_to_num(g0[bucket]).mean()) if bucket.sum() else None}, "turnover_ratio": float(np.nanmean(to[WA]) / np.nanmean(to0[WA])), "wired": wired,
                            "delta": {"W_ALPHA": [dW, ciW], "KING_LIVE": [dK, ciK], "top_decile_breadth": [dT, ciT]}, "gates": {"G1_not_worse_delta": G1, "G2_maximin": G2, "G3_top_decile": G3, "ALL": bool(G1 and G2 and G3)}, "worst_year_sharpe": worst_year_sharpe}
out["baseline"]["worst_year_sharpe"] = worst_year_sharpe0
if CONTROL and CONTROL in out["variants"]:
    c = out["variants"][CONTROL]["W_ALPHA"]; cg = out["variants"][CONTROL]["gates"]
    for tag, v in out["variants"].items():
        if tag == CONTROL: continue
        w = v["W_ALPHA"]; better = {"maxdd": w["maxdd_L"] > c["maxdd_L"], "days_le_m4": w["days_le_m4"] < c["days_le_m4"], "days_le_m2p68": w["days_le_m2p68"] <= c["days_le_m2p68"], "delta_lower_bound": v["delta"]["W_ALPHA"][1][0] > out["variants"][CONTROL]["delta"]["W_ALPHA"][1][0], "worst_year_sharpe": v["worst_year_sharpe"] >= out["variants"][CONTROL]["worst_year_sharpe"]}
        v["gates"]["G4_vs_control"] = better; v["gates"]["G4"] = bool(better["maxdd"] and better["days_le_m4"]); v["gates"]["ALL"] = bool(v["gates"]["ALL"] and v["gates"]["G4"])
    out["control_tag"] = CONTROL
json.dump(out, open(OUT, "w"), indent=1)
b = out["baseline"]; print("baseline W_ALPHA", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in b["W_ALPHA"].items()}, "| top-decile g", round(b["top_decile_breadth"]["g"], 3), "n", b["top_decile_breadth"]["n"], "| worst-year sharpe", round(worst_year_sharpe0, 2))
for tag, v in out["variants"].items():
    w = v["W_ALPHA"]; print(f"{tag:22s} g {w['g']:+.3f} (Δ {v['delta']['W_ALPHA'][0]:+.3f} [{v['delta']['W_ALPHA'][1][0]:+.3f},{v['delta']['W_ALPHA'][1][1]:+.3f}]) sh {w['sharpe_daily']:.2f} maxdd {w['maxdd_L']:.3f} worst {w['worst_day']:.4f} d≤-2.68% {w['days_le_m2p68']} d≤-4% {w['days_le_m4']} | bucket({v['bucket']['mode']},n={v['bucket']['n']}) Δ {v['delta']['top_decile_breadth'][0]:+.3f} [{v['delta']['top_decile_breadth'][1][0]:+.3f},{v['delta']['top_decile_breadth'][1][1]:+.3f}] | turn×{v['turnover_ratio']:.2f} | changed {v['wired']['frac_changed']:.2%} L1 {v['wired']['mean_L1_dW_over_gross']:.3%} acc/tgt gross {v['wired']['accounted_over_target_gross']:.3f} max|w| {v['wired']['max_abs_accounted_weight']:.4f} |net|/gross≤{v['wired']['net_over_gross_max']:.1e} | worst-yr sh {v['worst_year_sharpe']:.2f} | G1 {v['gates']['G1_not_worse_delta']} G2 {v['gates']['G2_maximin']} G3 {v['gates']['G3_top_decile']} G4 {v['gates'].get('G4', '-')}")
