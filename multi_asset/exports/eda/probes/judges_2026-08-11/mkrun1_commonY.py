"""Build the COMMON-Y backtest CSVs for the Run1-vs-production taker/maker comparison.

Caliber discipline (0B's catch): the npz "targets" are ±5σ-CLIPPED-normalized — they must NOT be
used as realized returns. The ONE common realized series for BOTH models is the production CSV's raw
y_true_ret_bps. This script:
  - denorms each month's Run1 q50 -> bps  (q50 * y_sigma + y_median) * 1e4,
  - joins ON TIMESTAMP (µs->ms) to the production CSV raw y_true_ret_bps (common nodes only),
  - writes exports/run1_commonY.csv and exports/prod_commonY.csv over the IDENTICAL node set
    (same ts+y_true+month per row; they differ ONLY in y_pred_raw) for an apples-to-apples backtest.

Verify with the build-agnostic OUTPUT audit (audit_commonY.py): node identity, prod y_true == original
CSV y_true (100%), Run1 pred == denorm(npz q50) aligned on ts. Run from the multi_asset repo root.
"""
import numpy as np, pandas as pd, os

MONTHS = ["2025_08", "2025_09", "2025_10", "2025_11", "2025_12",
          "2026_01", "2026_02", "2026_03", "2026_04", "2026_05"]
PROD_CSV = "exports/final_l01/y600_backtest_dataset.csv"
RUN1_NPZ = "experiments/d1gate/d1_%s_run1/fold_0/ema_test_preds.npz"

csv = pd.read_csv(PROD_CSV); csv = csv[csv.y_true_ret_bps != 0]
cy = dict(zip(csv.timestamp_ms.values.astype(np.int64), csv.y_true_ret_bps.values.astype(float)))
rows = []; nmiss = 0
for mk in MONTHS:
    f = RUN1_NPZ % mk
    if not os.path.exists(f):
        continue
    z = np.load(f, allow_pickle=True); pr = z["predictions"]
    q = (pr[:, 1] if pr.ndim == 2 else pr).astype(float)
    ts = z["timestamps"].astype(np.int64); ts = ts // 1000 if ts[0] > 3e12 else ts   # µs -> ms
    ysig = float(z["y_sigma"]) if "y_sigma" in z.files else 1.0
    ymed = float(z["y_median"]) if "y_median" in z.files else 0.0
    m = z["mask"].astype(bool) if "mask" in z.files else np.ones(len(q), bool)
    pred_bps = (q * ysig + ymed) * 1e4                                                # denorm -> bps
    for i in np.where(m)[0]:
        t = int(ts[i])
        if t in cy:                                                                   # common nodes; CSV RAW y
            rows.append((t, float(pred_bps[i]), cy[t], mk))
        else:
            nmiss += 1
pd.DataFrame(rows, columns=["timestamp_ms", "y_pred_raw", "y_true_ret_bps", "month"]) \
  .to_csv("exports/run1_commonY.csv", index=False)
print("run1 common-y rows:", len(rows), "| run1 nodes NOT in CSV (dropped):", nmiss)

# production restricted to the SAME common node set (identical nodes) for the apples comparison
common = set(r[0] for r in rows)
csvc = csv[csv.timestamp_ms.astype(np.int64).isin(common)]
csvc[["timestamp_ms", "y_pred_raw", "y_true_ret_bps", "month"]].to_csv("exports/prod_commonY.csv", index=False)
print("prod common-y rows:", len(csvc))
