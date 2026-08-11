import os, numpy as np, datetime as dt
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
months = ["2025_08","2025_09","2025_10","2025_11","2025_12","2026_01","2026_02","2026_03","2026_04","2026_05"]
US = 1_000_000
print(f"{'month':8} {'ema_test_preds path':52} {'N':>6} {'mask_ok':>7} {'test_span (UTC days)':30}")
paths = {}
for m in months:
    od = f"{MA}/experiments/d1gate/d1_{m}_run1/fold_0"
    ema = f"{od}/ema_test_preds.npz"; best = f"{od}/test_preds.npz"
    if not os.path.exists(ema):
        print(f"{m:8} MISSING {ema}"); continue
    z = np.load(ema, allow_pickle=True)
    n = len(z["predictions"]); mk = int(z["mask"].sum()) if "mask" in z.files else n
    ts = z["timestamps"].astype(np.int64)
    d0 = dt.datetime.utcfromtimestamp(ts.min()//US).date(); d1 = dt.datetime.utcfromtimestamp(ts.max()//US).date()
    rel = ema.replace(MA + "/", "")
    print(f"{m:8} {rel:52} {n:>6} {mk:>7} {str(d0)}..{str(d1)}")
    paths[m] = (ema, best)
print("\n=== keys in a sample (caliber structure) ===")
z = np.load(paths['2026_01'][0], allow_pickle=True)
print("  ", {k: (z[k].shape, str(z[k].dtype)) for k in z.files})
print("\n=== production CSV rows (for caliber compare) ===")
csv = f"{MA}/exports/final_l01/y600_backtest_dataset.csv"
print("  exists:", os.path.exists(csv))
if os.path.exists(csv):
    import csv as csvmod
    with open(csv) as f:
        head = f.readline().strip()
        nrows = sum(1 for _ in f)
    print(f"  header: {head[:120]}")
    print(f"  data rows: {nrows}")
