"""Pure hole-fix effect on the book (reviewer item 3): HF2 (corrected cache) − REFAUG (original cache, SAME F10 coverage) paired on
08-11→08-30 20Z, day-block bootstrap 2000 seed 20260905; drawdown from the window start (E-0909-C)."""
import numpy as np, calendar, time, json, sys
COLS = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C = {c: i for i, c in enumerate(COLS)}; APY = 2190
def T(*a): return calendar.timegm(a + (0,) * (6 - len(a)))
W = {"ext 08-11→08-30 20Z (120)": (T(2026,8,11), T(2026,8,30,20)+1), "  pre-hole 08-11 (6)": (T(2026,8,11), T(2026,8,11,20)+1), "  hole 08-12→08-24 04Z (74)": (T(2026,8,12), T(2026,8,24,4)+1), "  post 08-24 08Z→08-30 (40)": (T(2026,8,24,8), T(2026,8,30,20)+1)}
rng = np.random.default_rng(20260905)
def boot(v, days):
    ud, inv = np.unique(days, return_inverse=True); nd = len(ud)
    if nd < 3: return (float("nan"), float("nan"), float("nan"))
    S = np.bincount(inv, weights=v, minlength=nd); N = np.bincount(inv, minlength=nd); idx = rng.integers(0, nd, size=(2000, nd)); mn = S[idx].sum(1) / N[idx].sum(1)
    return float(np.percentile(mn, 2.5)), float(np.percentile(mn, 97.5)), float((mn > 0).mean())
def dd(v): c = np.concatenate([[0.0], np.cumsum(v)]); return float(np.max(np.maximum.accumulate(c) - c))
H = "/workspace/review_scratch/health_check"; out = {}
for s in ("42", "2027"):
    A = np.load("%s/dev_refaug/probe_artifacts/w10_ablation_series_REFAUG_FIX7_UCRYPTO_s%s.npz" % (H, s), allow_pickle=True)["d30_n2_c42_rec"]
    B = np.load("%s/dev_hf2/probe_artifacts/w10_ablation_series_HF2_FIX7_UCRYPTO_s%s.npz" % (H, s), allow_pickle=True)["d30_n2_c42_rec"]
    ta, tb = A[:, 0].astype(np.int64), B[:, 0].astype(np.int64); com, ia, ib = np.intersect1d(ta, tb, return_indices=True)
    ga = (A[:, C["net_ex"]] / A[:, C["gross_total"]])[ia]; gb = (B[:, C["net_ex"]] / B[:, C["gross_total"]])[ib]; ts = com
    print("\n== seed %s: REFAUG anchors %d, HF2 %d, common %d ==" % (s, len(ta), len(tb), len(com)))
    print("%-30s %5s %10s %10s %10s %22s %6s | %9s %9s" % ("window", "n", "REFAUG", "HF2", "Δ(HF2−REF)", "CI95(Δ)", "P>0", "DD_REF", "DD_HF2"))
    for w, (lo, hi) in W.items():
        m = (ts >= lo) & (ts < hi); d = (gb - ga)[m]; lo_, hi_, p = boot(d, ts[m] // 86400)
        out["%s|%s" % (s, w.strip())] = {"n": int(m.sum()), "ref": float(ga[m].mean()), "hf2": float(gb[m].mean()), "delta": float(d.mean()), "ci95": [lo_, hi_], "p_gt0": p, "dd_ref": dd(ga[m]), "dd_hf2": dd(gb[m])}
        print("%-30s %5d %+10.4f %+10.4f %+10.4f [%+8.4f,%+8.4f] %6.3f | %9.1f %9.1f" % (w, m.sum(), ga[m].mean(), gb[m].mean(), d.mean(), lo_, hi_, p, dd(ga[m]), dd(gb[m])))
    pre = ts <= T(2026,8,10,20); print("  sanity: <= 08-10 20Z paired diff maxabs %.3e over %d anchors (must be 0)" % (np.abs((gb - ga)[pre]).max(), int(pre.sum())))
json.dump(out, open("/workspace/review_scratch/hf2_infer/JUDGE_REFAUG.json", "w"), indent=1)
