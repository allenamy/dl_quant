"""GAP#3 (2026-09-04): worst calendar month of net_ex (arm d30_n2_c42) for every port + alt (Pi-caliber) series.
Units: net_ex = bps/anchor per unit NAV of the book (as recorded by w10_universe.py); month sum = bps of NAV-book;
/ g (annual mean gross_total) / 100 = % of gross; x2 = % NAV at gross_mult 2.0 (in-service). Also month-own-gross variant.
Reads only; writes only /workspace/review_scratch/gap_3/worst_months.json"""
import numpy as np, json, time, glob, os, sys
files = {}
for f in sorted(glob.glob("/workspace/port_w10/probe_artifacts/w10_ablation_series_pod_*.npz")):
    files[os.path.basename(f)[len("w10_ablation_series_"):-4]] = f
for f in sorted(glob.glob("/workspace/review_scratch/refute_C6_2/altrun/*/probe_artifacts/w10_ablation_series_alt_*.npz")):
    files[os.path.basename(f)[len("w10_ablation_series_"):-4]] = f
for f in sorted(glob.glob("/workspace/review_scratch/refute_C6_1/*/probe_artifacts/w10_ablation_series_*.npz")) + sorted(glob.glob("/workspace/review_scratch/refute_C6_1/*/*/probe_artifacts/w10_ablation_series_*.npz")):
    files["C6_1/" + os.path.basename(f)[len("w10_ablation_series_"):-4]] = f
res = {}
for tag, f in files.items():
    z = np.load(f, allow_pickle=True); cols = [str(c) for c in z["cols"]]; c = {n: k for k, n in enumerate(cols)}
    R = z["d30_n2_c42_rec"]; cfg = json.loads(str(z["config_json"]))
    ts = R[:, c["ts"]].astype(np.int64); net = R[:, c["net_ex"]]; gt = R[:, c["gross_total"]]
    yr = np.array([time.gmtime(int(t)).tm_year for t in ts]); ym = np.array([time.strftime("%Y-%m", time.gmtime(int(t))) for t in ts])
    C = {k: cfg.get(k) for k in ("CAL", "W3FIX", "MEMBERS_TOPN", "TRADE_TOPN", "FTRIM", "KMOD_F10", "FSEED")}
    out = {"file": f, "cfg": C, "n": int(len(ts))}
    months = {m: {"sum_bps_nav": float(net[ym == m].sum()), "n": int((ym == m).sum()), "gross_mean": float(gt[ym == m].mean())} for m in sorted(set(ym.tolist()))}
    out["months"] = months
    for lab, s in (("2024", yr == 2024), ("2025", yr == 2025), ("2026", yr == 2026), ("2024on", yr >= 2024)):
        if s.sum() == 0: continue
        g = float(gt[s].mean())
        ms = {m: v for m, v in months.items() if (int(m[:4]) >= 2024 if lab == "2024on" else int(m[:4]) == int(lab))}
        wm = min(ms, key=lambda m: ms[m]["sum_bps_nav"]); v = ms[wm]["sum_bps_nav"]; gm = ms[wm]["gross_mean"]
        out[lab] = dict(worst_month=wm, worst_bps_nav=round(v, 1), gross_year=round(g, 4), gross_month=round(gm, 4),
                        pct_gross_yearg=round(v / g / 100, 2), pct_nav_2x_yearg=round(2 * v / g / 100, 2),
                        pct_gross_monthg=round(v / gm / 100, 2), pct_nav_2x_monthg=round(2 * v / gm / 100, 2))
    res[tag] = out
    print("== %s  CAL=%s W3FIX=%s FTRIM=%s M=%s T=%s K=%s seed=%s n=%d" % (tag, C["CAL"], C["W3FIX"], C["FTRIM"], C["MEMBERS_TOPN"], C["TRADE_TOPN"], C["KMOD_F10"], C["FSEED"], out["n"]))
    for lab in ("2024", "2025", "2026", "2024on"):
        if lab in out:
            o = out[lab]
            print("   %-7s worst %s %+8.1f bps NAV-book | g_year %.3f -> %+6.2f%% gross, 2x %+6.2f%% NAV | g_month %.3f -> %+6.2f%% gross, 2x %+6.2f%% NAV" % (
                lab, o["worst_month"], o["worst_bps_nav"], o["gross_year"], o["pct_gross_yearg"], o["pct_nav_2x_yearg"], o["gross_month"], o["pct_gross_monthg"], o["pct_nav_2x_monthg"]))
json.dump(res, open("/workspace/review_scratch/gap_3/worst_months.json", "w"), indent=1)
# appendix: full monthly series (bps NAV-book) 2024on for headline runs, Σ-simple vs Π
for tag in ("pod_live_w3fix_callog_s42", "alt_newprod_w3fix", "alt_newsum_w3fix", "pod_live_w3fix_calsimple_s42", "pod_live_callog_s42", "alt_newprod_dyn", "alt_newsum_dyn", "pod_live_calsimple_s42"):
    if tag in res:
        print("MONTHLY %s: " % tag + " ".join("%s:%+.0f" % (m, v["sum_bps_nav"]) for m, v in res[tag]["months"].items() if int(m[:4]) >= 2024))
print("FILES:")
for k, v in files.items(): print("  %s -> %s" % (k, v))
print("WORST_MONTHS_DONE")
