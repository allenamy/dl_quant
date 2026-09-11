"""INFRA2 step 3: re-measure XIB_LAG50 through the BITWISE device, against the round-1 (ORDINAL) build
of the identical arm. Statistic copied verbatim from judge_v4: g = net_ex/gross_total (bps/anchor per
unit gross), paired per anchor, UTC-day block bootstrap 2000 resamples, rng default_rng([20260905, k]).
The contrast substream index k is DECLARED here, and reported at two values because the CI depends on
the arm set (judge_ci_depends_on_arm_set)."""
import numpy as np, json, calendar, time, sys, os
COLS = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C = {c: i for i, c in enumerate(COLS)}; APY = 2190
J = "/workspace/uplift_2026-09-11/infra2/JHC/dev_v4/probe_artifacts"


def T(*a): return calendar.timegm(a + (0,) * (6 - len(a)))


WIN = {"full 2022-01-01→2026-08-10 20Z": (T(2022, 1, 1), T(2026, 8, 10, 20) + 1),
       "full 2022-01-01→2026-08-31 20Z": (T(2022, 1, 1), T(2026, 8, 31, 20) + 1),
       "frozen 2025-03-01→2026-08-10 20Z": (T(2025, 3, 1), T(2026, 8, 10, 20) + 1),
       "2024-01→2026-08-10 20Z": (T(2024, 1, 1), T(2026, 8, 10, 20) + 1),
       "OOF 2026-08-11→08-31 20Z": (T(2026, 8, 11), T(2026, 8, 31, 20) + 1),
       "2022": (T(2022, 1, 1), T(2023, 1, 1)), "2023": (T(2023, 1, 1), T(2024, 1, 1)),
       "2024": (T(2024, 1, 1), T(2025, 1, 1)), "2025": (T(2025, 1, 1), T(2026, 1, 1)),
       "2026→08-10 20Z": (T(2026, 1, 1), T(2026, 8, 10, 20) + 1)}
PRIMARY = "frozen 2025-03-01→2026-08-10 20Z"; FULL = "full 2022-01-01→2026-08-10 20Z"


def load(arm, seat, s):
    A = np.load(f"{J}/w10_ablation_series_V4_{arm}_{seat}_s{s}.npz", allow_pickle=True)
    R = np.asarray(A["d30_n2_c42_rec"], float)
    return np.round(R[:, 0]).astype(np.int64), R[:, C["net_ex"]] / R[:, C["gross_total"]], R


def boot(v, days, k, B=2000):
    rng = np.random.default_rng([20260905, k])
    ud, inv = np.unique(days, return_inverse=True); nd = len(ud)
    if nd < 3: return (float("nan"),) * 3
    S = np.bincount(inv, weights=v, minlength=nd); N = np.bincount(inv, minlength=nd)
    idx = rng.integers(0, nd, size=(B, nd)); mn = S[idx].sum(1) / N[idx].sum(1)
    return float(np.percentile(mn, 2.5)), float(np.percentile(mn, 97.5)), float((mn > 0).mean())


def bonf(v, days, k, K=68, B=20000):
    rng = np.random.default_rng([20260905, k])
    ud, inv = np.unique(days, return_inverse=True); nd = len(ud)
    S = np.bincount(inv, weights=v, minlength=nd); N = np.bincount(inv, minlength=nd)
    idx = rng.integers(0, nd, size=(B, nd)); mn = S[idx].sum(1) / N[idx].sum(1)
    return float(np.percentile(mn, 100 * (0.05 / K) / 2))


def sh(v): return float(v.mean() / v.std(ddof=1) * np.sqrt(APY)) if len(v) > 2 and v.std(ddof=1) > 0 else float("nan")


OUT = {}
print("=== LEVELS: g bps/anchor per unit gross (net-of-fee, RAW accounting, CAL=log) ===")
print("%-34s %-10s %-5s %5s %9s %7s %8s" % ("window", "arm", "seed", "n", "bps/anch", "Sharpe", "SE(Shp)"))
for w in WIN:
    lo, hi = WIN[w]
    for arm in ("A0", "XIBOLD50", "XIBLAG50"):
        for s in ("42", "2027"):
            ts, g, R = load(arm, "dyn", s); m = (ts >= lo) & (ts < hi)
            if not m.any(): continue
            OUT.setdefault(w, {})[f"{arm}_dyn_s{s}"] = {"n": int(m.sum()), "mean_bps": float(g[m].mean()), "sharpe": sh(g[m]),
                                                        "se_sharpe": float(np.sqrt(APY / m.sum())),
                                                        "annual_pct_per_gross": float(g[m].mean() * APY / 1e4 * 100)}
            print("%-34s %-10s %-5s %5d %+9.4f %7.2f %8.2f" % (w, arm, s, m.sum(), g[m].mean(), sh(g[m]), np.sqrt(APY / m.sum())))
print()
print("=== PAIRED CONTRAST vs A0 (same anchors, both seats, both seeds; block bootstrap 2000, rng [20260905,k]) ===")
print("%-34s %-10s %-4s %-5s %2s %+9s %24s %6s %10s" % ("window", "arm", "seat", "seed", "k", "dg", "CI95", "P>0", "BONF68lo"))
for w in (PRIMARY, FULL, "full 2022-01-01→2026-08-31 20Z", "2024-01→2026-08-10 20Z", "OOF 2026-08-11→08-31 20Z"):
    lo, hi = WIN[w]
    for arm in ("XIBOLD50", "XIBLAG50"):
        for seat in ("dyn", "fix"):
            for s in ("42", "2027"):
                ta, ga, _ = load(arm, seat, s); tb, gb, _ = load("A0", seat, s)
                com, ia, ib = np.intersect1d(ta, tb, return_indices=True)   # fix-seat arms drop 1 anchor (reported below); pair on the shared set
                dropped = sorted(set(tb.tolist()) - set(ta.tolist()))
                ta = com; ga = ga[ia]; gb = gb[ib]
                m = (ta >= lo) & (ta < hi); d = (ga - gb)[m]
                for k in (0, 9):
                    cl, ch, p = boot(d, ta[m] // 86400, k)
                    bl = bonf(d, ta[m] // 86400, k) if w in (PRIMARY, FULL) else float("nan")
                    OUT.setdefault("contrast_" + w, {})[f"{arm}-A0|{seat}|s{s}|k{k}"] = {
                        "delta": float(d.mean()), "ci95": [cl, ch], "p_gt0": p, "bonf68_lo": bl, "n": int(m.sum()),
                        "anchors_dropped_vs_A0": [time.strftime("%F %HZ", time.gmtime(int(x))) for x in dropped]}
                    print("%-34s %-10s %-4s %-5s %2d %+9.4f [%+9.4f,%+9.4f] %6.3f %+10.4f" % (w, arm, seat, s, k, d.mean(), cl, ch, p, bl))
print()
print("=== CORRELATION of arm g to A0 g (full cycle) and OLD vs NEW build ===")
ts, ga, _ = load("XIBLAG50", "dyn", "42"); _, g0, _ = load("A0", "dyn", "42"); _, go, _ = load("XIBOLD50", "dyn", "42")
lo, hi = WIN[FULL]; m = (ts >= lo) & (ts < hi)
cc = {"corr(XIBLAG50,A0) full": float(np.corrcoef(ga[m], g0[m])[0, 1]),
      "corr(XIBOLD50,A0) full": float(np.corrcoef(go[m], g0[m])[0, 1]),
      "corr(new,old) full": float(np.corrcoef(ga[m], go[m])[0, 1]),
      "mean|g_new - g_old| full": float(np.abs(ga[m] - go[m]).mean()),
      "max|g_new - g_old| full": float(np.abs(ga[m] - go[m]).max()),
      "d(mean g) new-old full": float((ga[m] - go[m]).mean())}
for k, v in cc.items(): print("  %-32s %+0.6f" % (k, v))
OUT["correlations"] = cc
json.dump(OUT, open("/workspace/uplift_2026-09-11/infra2/RESULT_xib_bitwise.json", "w"), indent=1)
print("MEASURE_DONE")
