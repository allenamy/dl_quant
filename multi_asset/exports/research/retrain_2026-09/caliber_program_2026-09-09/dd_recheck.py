"""E-0909-C recheck: every maxDD I published used cumsum/NAV drawdown WITHOUT the window start. Recompute both ways for the
published arms/windows and report old vs corrected. (bps dd on g; NAV dd at 2x with a prepended 1.0)"""
import numpy as np, calendar, time
COLS = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C = {c: i for i, c in enumerate(COLS)}; CUT = calendar.timegm((2026, 8, 10, 20, 0, 0))
def T(*a): return calendar.timegm(a + (0,) * (6 - len(a)))
W = {"2022": (T(2022,1,1), T(2023,1,1)), "2023": (T(2023,1,1), T(2024,1,1)), "2024": (T(2024,1,1), T(2025,1,1)), "2025": (T(2025,1,1), T(2026,1,1)), "2026<=cut": (T(2026,1,1), CUT+1), "frozen": (T(2025,3,1), CUT+1), "2024-26": (T(2024,1,1), CUT+1), "full": (0, CUT+1)}
def dd_old(v): c = np.cumsum(v); return float(np.max(np.maximum.accumulate(c) - c))
def dd_new(v): c = np.concatenate([[0.0], np.cumsum(v)]); return float(np.max(np.maximum.accumulate(c) - c))
def nav_old(v): r = v / 1e4 * 2; n = np.cumprod(1 + r); return 100 * float(np.max(1 - n / np.maximum.accumulate(n)))
def nav_new(v): r = v / 1e4 * 2; n = np.concatenate([[1.0], np.cumprod(1 + r)]); return 100 * float(np.max(1 - n / np.maximum.accumulate(n)))
ARMS = {"G_FIX7_UCRYPTO (ADD4 CRYPTO)": "/workspace/review_scratch/allweather_trackB/replay/dev_alt/probe_artifacts/w10_ablation_series_G_FIX7_UCRYPTO.npz",
        "G_mE1cX7_R0_spl42 (ADD4 BASE)": "/workspace/review_scratch/allweather_trackB/replay/dev_alt/probe_artifacts/w10_ablation_series_G_mE1cX7_R0_spl42.npz",
        "M1_UCRYPTO_prod_s42 (ADD6)": "/workspace/review_scratch/health_check/dev_alt/probe_artifacts/w10_ablation_series_M1_UCRYPTO_prod_s42_ccal.npz",
        "M1_UCRYPTO_prod_s2027 (ADD6)": "/workspace/review_scratch/health_check/dev_alt/probe_artifacts/w10_ablation_series_M1_UCRYPTO_prod_s2027_ccal.npz",
        "HF2_FIX7_UCRYPTO_s42 (round2)": "/workspace/review_scratch/health_check/dev_hf2/probe_artifacts/w10_ablation_series_HF2_FIX7_UCRYPTO_s42.npz"}
for name, p in ARMS.items():
    A = np.load(p, allow_pickle=True); R = A["d30_n2_c42_rec"]; ts = R[:, 0].astype(np.int64); g = R[:, C["net_ex"]] / R[:, C["gross_total"]]
    print("== %s ==" % name); chg = []
    for w, (lo, hi) in W.items():
        m = (ts >= lo) & (ts < hi); v = g[m]
        if m.sum() == 0: continue
        a, b, c_, d_ = dd_old(v), dd_new(v), nav_old(v), nav_new(v)
        flag = "" if (abs(a - b) < 1e-9 and abs(c_ - d_) < 1e-9) else "  <-- CHANGED"
        print("  %-10s n %5d | bps maxDD old %8.1f new %8.1f | NAV@2x maxDD old %6.2f%% new %6.2f%%%s" % (w, m.sum(), a, b, c_, d_, flag))
