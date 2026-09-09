"""Gate R4: full-chain accounting restatement (meta_newprod_raw replay) must reproduce the patch-table restatement (ADDENDUM 1 v3)."""
import numpy as np, sys, calendar, time
COLS = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C = {c: i for i, c in enumerate(COLS)}; CUT = calendar.timegm((2026, 8, 10, 20, 0, 0)); APY = 2190
REF = {"42": {"2022": (0.0717, 0.14, 16.95, -11.17), "2025": (0.5823, 1.02, 21.21, -4.87), "2024-26": (1.2580, 2.27, 22.60, -4.87), "full": (0.6013, 1.20, 44.77, -11.17)},
       "2027": {"2022": (0.0717, 0.14, 16.95, -11.17), "2025": (0.7097, 1.24, 18.02, -4.92), "2024-26": (1.3225, 2.38, 23.08, -4.92), "full": (0.6437, 1.28, 43.98, -11.17)}}
def stats(ts, g):
    m = ts <= CUT; t = ts[m]; x = g[m]; yr = np.array([time.gmtime(int(v)).tm_year for v in t]); o = {}
    for name, sel in [("2022", yr == 2022), ("2025", yr == 2025), ("2024-26", t >= calendar.timegm((2024, 1, 1, 0, 0, 0))), ("full", np.ones(len(t), bool))]:
        v = x[sel]; s = float(v.mean() / v.std(ddof=1) * np.sqrt(APY)); r = v / 1e4 * 2.0; nav = np.cumprod(1 + r); dd = 1 - nav / np.maximum.accumulate(nav)
        dk = t[sel] // 86400; ud, inv = np.unique(dk, return_inverse=True); dayr = np.array([np.prod(1 + r[inv == k]) - 1 for k in range(len(ud))])
        o[name] = (float(v.mean()), s, 100 * float(dd.max()), 100 * float(dayr.min()))
    return o
ok = True
for s in ("42", "2027"):
    A = np.load("/workspace/review_scratch/health_check/dev_raw/probe_artifacts/w10_ablation_series_RAW_M1_UCRYPTO_s%s.npz" % s, allow_pickle=True); R = A["d30_n2_c42_rec"]; ts = R[:, 0].astype(np.int64); g = R[:, C["net_ex"]] / R[:, C["gross_total"]]
    st = stats(ts, g); print("seed %s" % s)
    for w in ("2022", "2025", "2024-26", "full"):
        a = st[w]; b = REF[s][w]; d = (abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2]), abs(a[3] - b[3])); good = d[0] <= 0.001 and d[1] <= 0.01 and d[2] <= 0.05 and d[3] <= 0.05
        ok &= good; print("  %-8s chain %+.4f/%.2f/%.2f%%/%.2f%%  vs patch-table %+.4f/%.2f/%.2f%%/%.2f%%  -> %s" % (w, *a, *b, "OK" if good else "DIFF"))
print("GATE_R4 %s" % ("PASS" if ok else "FAIL")); sys.exit(0 if ok else 3)
