"""INSTRUMENT-2 / GATE B step 3: what the candidate windows do to the standing verdicts.
Statistic replicated from judge_v4.py: g = net_ex/gross_total; paired per-anchor d = g_arm - g_A0;
UTC-day block bootstrap 2000; rng = numpy.default_rng([20260905, contrast_index]).
Verdict rule replicated: (A) point>0 AND CI-lower>0 on BOTH seeds; (B) CI-upper<0 on both; else (C) UNDECIDED.
E-0911-A: every window except 'FROZEN_as_judged' DROPS the first LOOK=900 anchors of the shared axis.
judge_v4.py and ELIGIBILITY_CONTRACT.json are NOT modified; this is a read-only replica.
"""
import numpy as np, json, calendar
HC = "/workspace/review_scratch/health_check"; U = "/workspace/uplift_2026-09-11"
COLS = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C = {c: i for i, c in enumerate(COLS)}
def T(*a): return calendar.timegm(a + (0,) * (6 - len(a)))
def load(p, key="d30_n2_c42_rec"):
    A = np.load(p, allow_pickle=True)
    R = A[key] if key in A.files else A["rec"]
    ts = np.round(R[:, 0]).astype(np.int64)
    return ts, R[:, C["net_ex"]] / R[:, C["gross_total"]]
def boot(d, days, k, K):
    ud, inv = np.unique(days, return_inverse=True); nd = len(ud)
    S = np.bincount(inv, weights=d, minlength=nd); N = np.bincount(inv, minlength=nd)
    rng = np.random.default_rng([20260905, k])
    idx = rng.integers(0, nd, size=(2000, nd)); mn = S[idx].sum(1) / N[idx].sum(1)
    a = 0.05 / K
    return (float(d.mean()), float(np.percentile(mn, 2.5)), float(np.percentile(mn, 97.5)),
            float(np.percentile(mn, 100 * a / 2)), float(np.percentile(mn, 100 * (1 - a / 2))), float((mn > 0).mean()))
HI = T(2026, 8, 10, 20) + 1
A0 = {(seat, s): load(f"{HC}/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_{seat}_s{s}.npz") for seat in ("dyn", "fix") for s in (42, 2027)}
XIB = {(seat, s): load(f"{U}/infra2/arms/w10_ablation_series_V4_XIBLAG50_{seat}_s{s}.npz") for seat in ("dyn", "fix") for s in (42, 2027)}
ts0 = A0[("dyn", 42)][0]
WARM = 900; warm_ts = int(ts0[WARM])
WIN = {
 "FROZEN_as_judged_2025-03-01..2026-08-10": (T(2025, 3, 1), HI, False),
 "FROZEN_postwarm(identical, warm<start)":  (T(2025, 3, 1), HI, True),
 "2024on_postwarm":                         (T(2024, 1, 1), HI, True),
 "F23_postwarm":                            (T(2023, 1, 1), HI, True),
 "FULLCYCLE_postwarm(PROPOSED PRIMARY)":    (warm_ts, HI, True),
}
K_DECLARED = 4     # the four candidate windows enumerated in PREREG_windows BEFORE any arm was re-judged
out = {"_meta": {"warm_cut_ts": warm_ts, "WARM": WARM, "K_declared_windows": K_DECLARED,
                 "statistic": "paired per-anchor d=g_arm-g_A0, UTC-day block bootstrap 2000, rng default_rng([20260905,k])"}}
ci = 0
print("%-42s %-4s %-5s %6s %8s %19s %19s %7s" % ("window", "seat", "seed", "n", "mean_d", "CI95", "BONF(K=%d)" % K_DECLARED, "P(>0)"))
for wn, (lo, hi, pw) in WIN.items():
    out[wn] = {}
    for seat in ("dyn", "fix"):
        for s in (42, 2027):
            ta, ga = XIB[(seat, s)]; tb, gb = A0[(seat, s)]
            com = np.intersect1d(ta, tb); ia = np.searchsorted(ta, com); ib = np.searchsorted(tb, com)
            dd = ga[ia] - gb[ib]
            m = (com >= lo) & (com < hi)
            if pw: m &= (com >= warm_ts)
            d = dd[m]; ci += 1
            mu, l, u, bl, bu, p = boot(d, com[m] // 86400, ci, K_DECLARED)
            out[wn][f"{seat}_s{s}"] = dict(n=int(m.sum()), mean=round(mu, 4), ci95=[round(l, 4), round(u, 4)],
                                           bonf=[round(bl, 4), round(bu, 4)], p_gt0=round(p, 4))
            print("%-42s %-4s %-5s %6d %+8.4f  [%+8.4f,%+8.4f] [%+8.4f,%+8.4f] %7.4f" % (wn, seat, s, m.sum(), mu, l, u, bl, bu, p))
    v = out[wn]
    for seat in ("dyn", "fix"):
        c = [v[f"{seat}_s{s}"] for s in (42, 2027)]
        ver = "(A) PASS" if all(x["mean"] > 0 and x["ci95"][0] > 0 for x in c) else \
              "(B) FAIL" if all(x["ci95"][1] < 0 for x in c) else "(C) UNDECIDED"
        verb = "(A) PASS" if all(x["mean"] > 0 and x["bonf"][0] > 0 for x in c) else \
               "(B) FAIL" if all(x["bonf"][1] < 0 for x in c) else "(C) UNDECIDED"
        out[wn][f"VERDICT_{seat}_CI95"] = ver; out[wn][f"VERDICT_{seat}_BONF"] = verb
        print("      -> VERDICT %s seat: CI95 %s | BONF(K=%d) %s" % (seat, ver, K_DECLARED, verb))
json.dump(out, open(U + "/r3_gates/rejudge_windows.json", "w"), indent=1)
print("wrote", U + "/r3_gates/rejudge_windows.json")
