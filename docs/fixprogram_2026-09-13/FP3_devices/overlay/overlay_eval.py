#!/usr/bin/env python3
"""FP3-R evaluation (PREREG §2–§3): baseline record vs overlay variant records, same engine, same accounting (net_ex = the evaluation caliber).
Per variant: per-year g, daily Sharpe, maxDD@L (per-anchor compounding), worst day, days ≤ −2.68% and ≤ −4% at L=2 (UTC-day NAV path), turnover ratio,
breadth-top-decile bucket g (breadth = causal member EW 24h return, computed here from the meta y4 exactly as the overlay does) and the paired Δ vs
baseline with a UTC-day block bootstrap CI95 over W_ALPHA and KING_LIVE. Gates G1/G2/G3 evaluated as frozen. usage: overlay_eval.py <probe_dir> <king_meta.npz> <out.json>"""
import glob, json, os, sys, time, hashlib, collections, numpy as np
PD, META, OUT = sys.argv[1:4]; L = 2.0; WA0, UB, KL0 = 1656547200, 1788120000, 1704067200; DELTA = 0.05
def load(tag):
    z = np.load(f"{PD}/w10_ablation_series_V4_A0_dyn_s42_{tag}.npz", allow_pickle=True); C = [str(c) for c in z["cols"]]; rec = np.asarray(z["d30_n2_c42_rec"], float)
    ts = rec[:, C.index("ts")].astype(np.int64); g = rec[:, C.index("net_ex")] / np.where(rec[:, C.index("gross_total")] > 0, rec[:, C.index("gross_total")], np.nan); to = rec[:, C.index("turnover")]
    return ts, g, to, json.loads(str(z["config_json"])).get("OVERLAY", "?")
M = np.load(META, allow_pickle=True); E = M["E_ts"].astype(np.int64); y4 = np.asarray(M["y4"], float); MEM = M["members"]
ts0, g0, to0, _ = load("OVLnone"); pos = {int(t): i for i, t in enumerate(E)}
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
out = {"device": "overlay_eval.py", "self_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest(), "utc": time.strftime("%FT%TZ", time.gmtime()), "L": L, "delta": DELTA, "baseline": {"W_ALPHA": stats(g0, WA), "KING_LIVE": stats(g0, KL), "by_year": {y: stats(g0, WA & (year == y)) for y in sorted(set(year[WA]))}, "top_decile_breadth": {"n": int((WA & top).sum()), "g": float(np.nan_to_num(g0[WA & top]).mean())}, "turnover_mean": float(np.nanmean(to0[WA]))}, "variants": {}}
for p in sorted(glob.glob(f"{PD}/w10_ablation_series_V4_A0_dyn_s42_OVL_*.npz")):
    tag = os.path.basename(p).split("_OVL_")[1][:-4]; ts, g, to, spec = load("OVL_" + tag); assert np.array_equal(ts, ts0), tag
    d = g - g0; dW, ciW = paired_ci(d, WA); dK, ciK = paired_ci(d, KL); dT, ciT = paired_ci(d, WA & top)
    sW, sK = stats(g, WA), stats(g, KL); by = {y: stats(g, WA & (year == y)) for y in sorted(set(year[WA]))}; b0 = out["baseline"]
    worst_year_sharpe = min(v["sharpe_daily"] for v in by.values() if v["sharpe_daily"] is not None); worst_year_sharpe0 = min(v["sharpe_daily"] for v in b0["by_year"].values() if v["sharpe_daily"] is not None)
    G1 = ciW[0] > -DELTA; G2 = (worst_year_sharpe >= worst_year_sharpe0 - 1e-9) and ((sW["maxdd_L"] - b0["W_ALPHA"]["maxdd_L"] >= 0.05) or (sW["days_le_m4"] <= b0["W_ALPHA"]["days_le_m4"] // 2)) and (sW["days_le_m2p68"] <= b0["W_ALPHA"]["days_le_m2p68"]); G3 = ciT[0] > 0
    out["variants"][tag] = {"spec": spec, "W_ALPHA": sW, "KING_LIVE": sK, "by_year": by, "top_decile_breadth": {"n": int((WA & top).sum()), "g": float(np.nan_to_num(g[WA & top]).mean())}, "turnover_ratio": float(np.nanmean(to[WA]) / np.nanmean(to0[WA])),
                            "delta": {"W_ALPHA": [dW, ciW], "KING_LIVE": [dK, ciK], "top_decile_breadth": [dT, ciT]}, "gates": {"G1_not_worse_delta": G1, "G2_maximin": G2, "G3_top_decile": G3, "ALL": bool(G1 and G2 and G3)}, "worst_year_sharpe": worst_year_sharpe}
out["baseline"]["worst_year_sharpe"] = worst_year_sharpe0
json.dump(out, open(OUT, "w"), indent=1)
b = out["baseline"]; print("baseline W_ALPHA", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in b["W_ALPHA"].items()}, "| top-decile g", round(b["top_decile_breadth"]["g"], 3), "n", b["top_decile_breadth"]["n"], "| worst-year sharpe", round(worst_year_sharpe0, 2))
for tag, v in out["variants"].items():
    w = v["W_ALPHA"]; print(f"{tag:22s} g {w['g']:+.3f} (Δ {v['delta']['W_ALPHA'][0]:+.3f} [{v['delta']['W_ALPHA'][1][0]:+.3f},{v['delta']['W_ALPHA'][1][1]:+.3f}]) sh {w['sharpe_daily']:.2f} maxdd {w['maxdd_L']:.3f} worst {w['worst_day']:.4f} d≤-2.68% {w['days_le_m2p68']} d≤-4% {w['days_le_m4']} | top-dec Δ {v['delta']['top_decile_breadth'][0]:+.3f} [{v['delta']['top_decile_breadth'][1][0]:+.3f},{v['delta']['top_decile_breadth'][1][1]:+.3f}] | turn×{v['turnover_ratio']:.2f} | worst-yr sh {v['worst_year_sharpe']:.2f} | G1 {v['gates']['G1_not_worse_delta']} G2 {v['gates']['G2_maximin']} G3 {v['gates']['G3_top_decile']}")
