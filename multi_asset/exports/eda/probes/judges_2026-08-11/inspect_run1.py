import numpy as np, pandas as pd, os
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
MONTHS = ["2025_08","2025_09","2025_10","2025_11","2025_12","2026_01","2026_02","2026_03","2026_04","2026_05"]

prod = pd.read_csv(f"{MA}/exports/final_l01/y600_backtest_dataset.csv")
print("PROD CSV cols:", list(prod.columns), "rows:", len(prod))
print("  has month col:", "month" in prod.columns, "| y!=0 rows:", int((prod.y_true_ret_bps!=0).sum()))
cy = dict(zip(prod.timestamp_ms.values.astype(np.int64), prod.y_true_ret_bps.values.astype(float)))
print("  prod unique ts:", prod.timestamp_ms.nunique())

# one npz structure
z = np.load(f"{MA}/experiments/d1gate/d1_2025_10_run1/fold_0/ema_test_preds.npz", allow_pickle=True)
print("\nNPZ keys:", z.files)
print("  predictions shape:", z["predictions"].shape, "| targets shape:", z["targets"].shape)
ts = z["timestamps"]; print("  ts dtype:", ts.dtype, "ts[0]:", ts[0], "(µs if ~1.7e15)")
print("  y_sigma:", float(z["y_sigma"]) if "y_sigma" in z.files else "NA", "y_median:", float(z["y_median"]) if "y_median" in z.files else "NA")
print("  mask sum:", int(z["mask"].sum()) if "mask" in z.files else "no mask", "/ n:", len(z["targets"]))

print("\nPER-MONTH coverage (Run1 valid nodes vs prod-CSV raw-y join):")
print(f"{'month':>8s} {'n_total':>8s} {'n_valid':>8s} {'n_ytrue':>8s} {'ytrue%':>7s} {'days':>5s} {'ts_start':>12s}")
tot_valid = tot_ytrue = 0
for mk in MONTHS:
    f = f"{MA}/experiments/d1gate/d1_{mk}_run1/fold_0/ema_test_preds.npz"
    if not os.path.exists(f):
        print(f"{mk:>8s}  MISSING"); continue
    z = np.load(f, allow_pickle=True)
    n = len(z["targets"]); m = z["mask"].astype(bool) if "mask" in z.files else np.ones(n, bool)
    ts = z["timestamps"].astype(np.int64); ts_ms = ts//1000 if ts[0] > 3e12 else ts
    tv = ts_ms[m]
    has_y = np.array([int(t) in cy for t in tv])
    days = len(np.unique(tv // 86400000))
    nv, ny = int(m.sum()), int(has_y.sum())
    tot_valid += nv; tot_ytrue += ny
    print(f"{mk:>8s} {n:8d} {nv:8d} {ny:8d} {100*ny/max(nv,1):6.1f}% {days:5d} {int(tv.min()):12d}")
print(f"{'TOTAL':>8s} {'':>8s} {tot_valid:8d} {tot_ytrue:8d} {100*tot_ytrue/max(tot_valid,1):6.1f}%")
