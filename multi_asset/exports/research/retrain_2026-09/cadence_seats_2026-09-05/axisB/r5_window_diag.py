"""r5_window_diag.py — diagnostic (not an arm): for R5 anchors in 2025->26 (and 2024), replicate the causal same-tercile window selection from the saved
σ_fund series and report, per current tercile: n anchors, share of the selected 900-anchor window that lies before 2024-01-01 (king leg has no predictions there),
mean age of the window (anchors), mean R5 vs R0 king seat at those anchors, and mean paired Δ net_ex. Read-only; prints only."""
import numpy as np, time, calendar, sys
NM = ["low", "mid", "high"]; ROOT = "/workspace/review_scratch/cadence_seats/axisB"; T24 = calendar.timegm((2024, 1, 1, 0, 0, 0)); T25 = calendar.timegm((2025, 1, 1, 0, 0, 0))
for king, cal, d in (("rollm", "log", "dev"), ("rollm", "prod", "dev_alt"), ("pinned", "log", "dev")):
    A = np.load(f"{ROOT}/{d}/probe_artifacts/w10_ablation_series_R5_{king}_{cal}_s42.npz", allow_pickle=True); B = np.load(f"{ROOT}/{d}/probe_artifacts/w10_ablation_series_R0_{king}_{cal}_s42.npz", allow_pickle=True)
    cols = [str(c) for c in A["cols"]]; RA = A["d30_n2_c42_rec"]; RB = B["d30_n2_c42_rec"]; assert np.array_equal(RA[:, 0], RB[:, 0])
    ts_rec = RA[:, 0].astype(np.int64); wk5 = RA[:, cols.index("w3_king")]; wk0 = RB[:, cols.index("w3_king")]; dnet = RA[:, cols.index("net_ex")] - RB[:, cols.index("net_ex")]
    rmap = {int(t): i for i, t in enumerate(ts_rec)}
    lts = A["axisb_legs_ts"].astype(np.int64); roll = A["axisb_sigma_roll"]; TER = A["axisb_regime_tercile"].astype(int); FB = A["axisb_regime_fallback"].astype(int)
    for lo, hi, nm in ((T25, 1 << 62, "2025->26"), (T24, T25, "2024")):
        agg = {t: [] for t in range(3)}
        for p in range(900, len(lts)):
            if not (lo <= lts[p] < hi) or FB[p] != 0: continue
            hist = roll[:p]; fin = np.isfinite(hist); q1, q2 = np.percentile(hist[fin], [100.0 / 3, 200.0 / 3])
            th = np.where(hist <= q1, 0, np.where(hist <= q2, 1, 2)); th[~fin] = -1; tc = TER[p]; same = np.where(th == tc)[0]; sel = same[-900:]
            i = rmap.get(int(lts[p]))
            if i is None: continue
            agg[tc].append((float((lts[sel] < T24).mean()), float((p - sel).mean()), float(wk5[i]), float(wk0[i]), float(dnet[i]), float(q1), float(q2)))
        print(f"{king} {cal} {nm}: " + " | ".join(f"{NM[t]} n={len(v)} pre2024_share={np.mean([x[0] for x in v]):.3f} mean_age={np.mean([x[1] for x in v]):.0f} w_king R5/R0={np.mean([x[2] for x in v]):.3f}/{np.mean([x[3] for x in v]):.3f} Δnet={np.mean([x[4] for x in v]):+.3f} cuts~{np.mean([x[5] for x in v]):.2f}/{np.mean([x[6] for x in v]):.2f}" for t, v in agg.items() if v))
