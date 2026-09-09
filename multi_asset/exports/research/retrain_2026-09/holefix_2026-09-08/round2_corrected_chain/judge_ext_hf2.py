"""PREREG_holefix §4 extension-window reading (frozen): no gate, no candidate. Levels only, segments separated.
g = net_ex/gross_total [bps/anchor per gross]; UTC-day block bootstrap 2000, seed 20260905; Sharpe anchor = mean/std*sqrt(2190).
Windows: frozen main 2025-03-01 -> 2026-08-10 20Z (sanity: must equal the old-input reference bitwise, reported by B1');
extension 2026-08-11 00Z -> 08-30 20Z (120 anchors) = pre-hole 08-11 (6) + hole 08-12 00Z..08-24 04Z (74) + post 08-24 08Z..08-30 20Z (40); plus 08-31 00Z (1)."""
import numpy as np, sys, calendar, time, json
COLS = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C = {c: i for i, c in enumerate(COLS)}; APY = 2190
def T(*a): return calendar.timegm(a + (0,) * (6 - len(a)))
W = {"frozen 2025-03-01→08-10 20Z": (T(2025, 3, 1), T(2026, 8, 10, 20) + 1), "ext 08-11→08-30 20Z (120)": (T(2026, 8, 11), T(2026, 8, 30, 20) + 1),
     "  pre-hole 08-11 (6)": (T(2026, 8, 11), T(2026, 8, 11, 20) + 1), "  hole 08-12 00Z→08-24 04Z (74)": (T(2026, 8, 12), T(2026, 8, 24, 4) + 1),
     "  post 08-24 08Z→08-30 20Z (40)": (T(2026, 8, 24, 8), T(2026, 8, 30, 20) + 1), "  08-31 00Z (1)": (T(2026, 8, 31), T(2026, 8, 31) + 1),
     "2026-01-01→08-30 20Z": (T(2026, 1, 1), T(2026, 8, 30, 20) + 1)}
rng = np.random.default_rng(20260905)
def boot(v, days):
    ud, inv = np.unique(days, return_inverse=True); nd = len(ud)
    if nd < 3: return (float("nan"), float("nan"))
    S = np.bincount(inv, weights=v, minlength=nd); N = np.bincount(inv, minlength=nd); idx = rng.integers(0, nd, size=(2000, nd)); mn = S[idx].sum(1) / N[idx].sum(1)
    return float(np.percentile(mn, 2.5)), float(np.percentile(mn, 97.5))
out = {}
for tag in sys.argv[1:]:
    A = np.load(tag, allow_pickle=True); R = A["d30_n2_c42_rec"]; ts = R[:, 0].astype(np.int64)
    g = R[:, C["net_ex"]] / R[:, C["gross_total"]]; gt = R[:, C["gross_total"]]; nsel = R[:, C["nsel"]]; w3k = R[:, C["w3_king"]]
    name = tag.split("w10_ablation_series_")[-1].replace(".npz", ""); out[name] = {}
    print("\n== %s == anchors %d, last %s" % (name, len(ts), time.strftime("%F %H:%MZ", time.gmtime(ts[-1]))))
    print("%-36s %5s %9s %7s %8s %20s %9s %6s %7s" % ("window", "n", "bps/anch", "Sharpe", "maxDD", "CI95(mean)", "gross_tot", "nsel", "w3_king"))
    for w, (lo, hi) in W.items():
        m = (ts >= lo) & (ts < hi); v = g[m]
        if m.sum() == 0: print("%-36s %5d" % (w, 0)); continue
        s = float(v.mean() / v.std(ddof=1) * np.sqrt(APY)) if len(v) > 2 and v.std(ddof=1) > 0 else float("nan")
        c = np.cumsum(v); dd = float(np.max(np.maximum.accumulate(c) - c)) if len(v) else 0.0
        lo_, hi_ = boot(v, ts[m] // 86400)
        out[name][w] = {"n": int(m.sum()), "mean": float(v.mean()), "sharpe": s, "maxdd_bps": dd, "ci95": [lo_, hi_], "gross_total_mean": float(gt[m].mean()), "nsel_mean": float(nsel[m].mean()), "w3_king_mean": float(w3k[m].mean())}
        print("%-36s %5d %+9.4f %7.2f %8.1f [%+8.4f,%+8.4f] %9.4f %6.1f %7.3f" % (w, m.sum(), v.mean(), s, dd, lo_, hi_, gt[m].mean(), nsel[m].mean(), w3k[m].mean()))
json.dump(out, open("/workspace/review_scratch/hf2_infer/JUDGE_EXT.json", "w"), indent=1)
