"""PREREG_v4 §2.5 judge (frozen §4 of PREREG_king_clip_label_ablation, verbatim rules; AMENDMENT 1 item 5: RAW accounting => recorded g, no clip correction).
Arms on the dev_v4 tree: A0 (v3 king + in-service F10 yearly OOS), A1 (king v4 + F10 v4 RAW/FIX7), A2 (king v4 + F10 v4 CLIP/FIX7), A3 (king v4 + in-service F10).
g = net_ex/gross_total [bps/anchor per gross]; frozen window 2025-03-01 -> 2026-08-10 20Z; UTC-day block bootstrap 2000; base seed 20260905 with a
per-contrast sub-stream (judge_ci_depends_on_arm_set): rng = default_rng([20260905, contrast_index]). Verdict per (contrast, seat) over both seeds:
(A) point>0 and CI lower>0 on both; (B) CI upper<0 on both; (C) otherwise UNDECIDED (never 'non-inferior'). Levels: full-cycle yearly table (negative years explicit,
maxDD includes the window start (E-0909-C), worst UTC day, worst calendar month), extension window 08-11->08-30 and 08-31 reported separately.
Reproduction check first (#20): A0 dyn vs the published RAW_M1_UCRYPTO arm (dev_raw: v3 king + in-service F10, RAW accounting on _ext+patch)."""
import numpy as np, json, calendar, time, os, sys
HC = "/workspace/review_scratch/health_check"
COLS = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C = {c: i for i, c in enumerate(COLS)}; APY = 2190
def T(*a): return calendar.timegm(a + (0,) * (6 - len(a)))
FROZEN = (T(2025, 3, 1), T(2026, 8, 10, 20) + 1); EXT = (T(2025, 3, 1), T(2026, 8, 31, 20) + 1)   # AMENDMENT 4: extended window = secondary reading (verdict stays on FROZEN)
WIN = {"2022": (T(2022, 1, 1), T(2023, 1, 1)), "2023": (T(2023, 1, 1), T(2024, 1, 1)), "2024": (T(2024, 1, 1), T(2025, 1, 1)), "2025": (T(2025, 1, 1), T(2026, 1, 1)), "2026→08-10 20Z": (T(2026, 1, 1), T(2026, 8, 10, 20) + 1),
       "frozen 2025-03-01→2026-08-10 20Z": FROZEN, "2024-01→2026-08-10 20Z": (T(2024, 1, 1), T(2026, 8, 10, 20) + 1), "ext 08-11→08-30 20Z": (T(2026, 8, 11), T(2026, 8, 30, 20) + 1), "08-31 (6)": (T(2026, 8, 31), T(2026, 9, 1)),
       "2026→08-31 20Z (all)": (T(2026, 1, 1), T(2026, 8, 31, 20) + 1), "EXTENDED 2025-03-01→2026-08-31 20Z": EXT, "2024-01→2026-08-31 20Z": (T(2024, 1, 1), T(2026, 8, 31, 20) + 1)}
def load(path):
    A = np.load(path, allow_pickle=True); R = A["d30_n2_c42_rec"]; ts = R[:, 0].astype(np.int64); g = R[:, C["net_ex"]] / R[:, C["gross_total"]]
    return ts, g, R
def boot(v, days, rng):
    ud, inv = np.unique(days, return_inverse=True); nd = len(ud)
    if nd < 3: return (float("nan"), float("nan"), float("nan"))
    S = np.bincount(inv, weights=v, minlength=nd); N = np.bincount(inv, minlength=nd); idx = rng.integers(0, nd, size=(2000, nd)); mn = S[idx].sum(1) / N[idx].sum(1)
    return float(np.percentile(mn, 2.5)), float(np.percentile(mn, 97.5)), float((mn > 0).mean())
def levels(ts, g, R):
    out = {}
    for w, (lo, hi) in WIN.items():
        m = (ts >= lo) & (ts < hi)
        if not m.any(): continue
        v = g[m]; c = np.concatenate([[0.0], np.cumsum(v)]); dd = float(np.max(np.maximum.accumulate(c) - c))
        days = ts[m] // 86400; ud, inv = np.unique(days, return_inverse=True); dsum = np.bincount(inv, weights=v); mon = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in ts[m]]); um, im = np.unique(mon, return_inverse=True); msum = np.bincount(im, weights=v)
        out[w] = {"n": int(m.sum()), "mean_bps": float(v.mean()), "sharpe": float(v.mean() / v.std(ddof=1) * np.sqrt(APY)) if m.sum() > 2 and v.std(ddof=1) > 0 else float("nan"), "maxdd_bps": dd,
                  "worst_day_bps": float(dsum.min()), "worst_day": time.strftime("%F", time.gmtime(int(ud[dsum.argmin()]) * 86400)), "worst_month_bps": float(msum.min()), "worst_month": str(um[msum.argmin()]),
                  "n_neg_months": int((msum < 0).sum()), "n_months": int(len(um)), "gross_total_mean": float(R[m, C["gross_total"]].mean()), "nsel_mean": float(R[m, C["nsel"]].mean()), "w3_king_mean": float(R[m, C["w3_king"]].mean()), "turnover_mean": float(R[m, C["turnover"]].mean()),
                  "annual_pct_per_gross": float(v.mean() * APY / 1e4 * 100), "negative_year": bool(v.sum() < 0)}
    return out
ARMS = {}; missing = []
for arm in ("A0", "A0p", "A1", "A1s", "A2", "A3"):
    for seat in ("dyn", "fix"):
        for s in ("42", "2027"):
            p = f"{HC}/dev_v4/probe_artifacts/w10_ablation_series_V4_{arm}_{seat}_s{s}.npz"
            if os.path.exists(p): ARMS[(arm, seat, s)] = load(p)
            else: missing.append(f"{arm}_{seat}_s{s}")
print("arms loaded:", sorted("_".join(k) for k in ARMS), "| missing:", missing)
out = {"arms": sorted("_".join(k) for k in ARMS), "missing": missing, "levels": {}, "contrasts": {}, "verdicts": {}, "reproduction": {}}
# --- reproduction check first (#20): A0 dyn vs published RAW_M1_UCRYPTO (dev_raw), frozen window
for arm0 in ("A0p", "A0"):   # A0p = same F10 vintage as the published RAW_M1 arm (port_w10 08-22 preds aligned to the v4 axis) -> the like-for-like reproduction; A0 = in-service 09-01 vintage
  for s in ("42", "2027"):
    p = f"{HC}/dev_raw/probe_artifacts/w10_ablation_series_RAW_M1_UCRYPTO_s{s}.npz"
    if (arm0, "dyn", s) in ARMS and os.path.exists(p):
        t0, g0, _ = ARMS[(arm0, "dyn", s)]; t1, g1, _ = load(p); com = np.intersect1d(t0, t1); i0 = np.searchsorted(t0, com); i1 = np.searchsorted(t1, com); m = (com >= FROZEN[0]) & (com < FROZEN[1])
        d = g0[i0][m] - g1[i1][m]; m26 = (com >= T(2026, 1, 1)) & (com < FROZEN[1]); d26 = g0[i0][m26] - g1[i1][m26]
        out["reproduction"][f"{arm0}_dyn_s{s}_vs_RAW_M1"] = {"n": int(m.sum()), "arm_mean": float(g0[i0][m].mean()), "RAW_M1_mean": float(g1[i1][m].mean()), "paired_mean": float(d.mean()), "paired_maxabs": float(np.abs(d).max()), "share_exact": float(np.mean(np.abs(d) < 1e-9)), "share_lt_1e-3": float(np.mean(np.abs(d) < 1e-3)), "paired_maxabs_2026": float(np.abs(d26).max())}
        print(f"REPRO {arm0} dyn s{s} vs RAW_M1 (frozen): {g0[i0][m].mean():+.4f} vs {g1[i1][m].mean():+.4f} | paired Δ {d.mean():+.4f} max|Δ| {np.abs(d).max():.4f} share<1e-3 {np.mean(np.abs(d) < 1e-3):.3f} | 2026 max|Δ| {np.abs(d26).max():.4f}")
# --- levels
print("\n== LEVELS (bps/anchor per gross; annual % per gross = mean*2190/1e4; at 2.0x gross multiply by 2) ==")
for k, (ts, g, R) in sorted(ARMS.items()):
    L = levels(ts, g, R); out["levels"]["_".join(k)] = L
    print(f"\n-- {'_'.join(k)} --"); print("%-34s %5s %8s %6s %8s %9s %11s %9s %11s %6s %6s %5s" % ("window", "n", "bps/anch", "Shp", "ann%/g", "maxDD", "worst day", "wd bps", "worst month", "negM", "w3k", "NEG"))
    for w, r in L.items(): print("%-34s %5d %+8.4f %6.2f %+8.2f %9.1f %11s %+9.1f %11s %3d/%2d %6.3f %5s" % (w, r["n"], r["mean_bps"], r["sharpe"], r["annual_pct_per_gross"], r["maxdd_bps"], r["worst_day"], r["worst_day_bps"], r["worst_month"], r["n_neg_months"], r["n_months"], r["w3_king_mean"], "NEG" if r["negative_year"] else ""))
# --- contrasts (frozen), per-contrast RNG sub-stream
CON = [("A1", "A0"), ("A2", "A0"), ("A3", "A0"), ("A1", "A2"), ("A1", "A3"), ("A1s", "A0"), ("A1s", "A1")]
print("\n== CONTRASTS (frozen 2025-03-01→2026-08-10 20Z; paired per anchor; UTC-day block bootstrap 2000; rng [20260905, k]) ==")
print("%-10s %-4s %-5s %9s %22s %6s | %s" % ("contrast", "seat", "seed", "Δ bps", "CI95", "P>0", "levels base -> arm"))
for ci, (a, b) in enumerate(CON):
    for seat in ("dyn", "fix"):
        for s in ("42", "2027"):
            if (a, seat, s) not in ARMS or (b, seat, s) not in ARMS: continue
            ta, ga, _ = ARMS[(a, seat, s)]; tb, gb, _ = ARMS[(b, seat, s)]; assert np.array_equal(ta, tb), "axis mismatch"
            m = (ta >= FROZEN[0]) & (ta < FROZEN[1]); d = (ga - gb)[m]; rng = np.random.default_rng([20260905, ci]); lo, hi, p = boot(d, ta[m] // 86400, rng)
            out["contrasts"][f"{a}-{b}|{seat}|s{s}"] = {"delta": float(d.mean()), "ci95": [lo, hi], "p_gt0": p, "n": int(m.sum()), "level_base": float(gb[m].mean()), "level_arm": float(ga[m].mean()), "rng": [20260905, ci]}
            print("%-10s %-4s %-5s %+9.4f [%+8.4f,%+8.4f] %6.3f | %+7.4f -> %+7.4f" % (f"{a}-{b}", seat, s, d.mean(), lo, hi, p, gb[m].mean(), ga[m].mean()))
print("\n== SECONDARY (AMENDMENT 4): same contrasts on the EXTENDED window 2025-03-01→2026-08-31 20Z (repaired August included; 126 more anchors; NOT the verdict window) ==")
out["contrasts_extended"] = {}
for ci, (a, b) in enumerate(CON):
    for seat in ("dyn", "fix"):
        for s in ("42", "2027"):
            if (a, seat, s) not in ARMS or (b, seat, s) not in ARMS: continue
            ta, ga, _ = ARMS[(a, seat, s)]; tb, gb, _ = ARMS[(b, seat, s)]; m = (ta >= EXT[0]) & (ta < EXT[1]); d = (ga - gb)[m]; rng = np.random.default_rng([20260905, 100 + ci]); lo, hi, p = boot(d, ta[m] // 86400, rng)
            out["contrasts_extended"][f"{a}-{b}|{seat}|s{s}"] = {"delta": float(d.mean()), "ci95": [lo, hi], "p_gt0": p, "n": int(m.sum()), "level_base": float(gb[m].mean()), "level_arm": float(ga[m].mean()), "rng": [20260905, 100 + ci]}
            print("%-10s %-4s %-5s %+9.4f [%+8.4f,%+8.4f] %6.3f | %+7.4f -> %+7.4f  (n=%d)" % (f"{a}-{b}", seat, s, d.mean(), lo, hi, p, gb[m].mean(), ga[m].mean(), m.sum()))
print("\n== VERDICTS (frozen §4: (A) both seeds point>0 & CI lower>0; (B) both CI upper<0; (C) otherwise UNDECIDED = '未过否决线', never '不劣') ==")
for a, b in CON:
    for seat in ("dyn", "fix"):
        r = [out["contrasts"].get(f"{a}-{b}|{seat}|s{s}") for s in ("42", "2027")]
        if any(x is None for x in r): continue
        v = "(A) PROMOTE" if all(x["delta"] > 0 and x["ci95"][0] > 0 for x in r) else ("(B) REJECT" if all(x["ci95"][1] < 0 for x in r) else "(C) UNDECIDED")
        out["verdicts"][f"{a}-{b}|{seat}"] = v; print(f"  {a}-{b:3s} {seat}: {v}")
out["utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()); os.makedirs("/workspace/review_scratch/v4_gates", exist_ok=True); json.dump(out, open("/workspace/review_scratch/v4_gates/JUDGE_v4.json", "w"), indent=1); print("JUDGE_V4_DONE")
