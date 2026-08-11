import numpy as np, glob, csv, os
MONTHS=["2025_08","2025_09","2025_10","2025_11","2025_12","2026_01","2026_02","2026_03","2026_04","2026_05"]
rows=[]
for mk in MONTHS:
    f="experiments/d1gate/d1_%s_run1/fold_0/ema_test_preds.npz"%mk
    if not os.path.exists(f): print("MISS",mk); continue
    z=np.load(f,allow_pickle=True); pr=z["predictions"]; q=(pr[:,1] if pr.ndim==2 else pr)
    y=z["targets"].astype(float); ts=z["timestamps"].astype(np.int64); ts=ts//1000 if ts[0]>3e12 else ts
    ysig=float(z["y_sigma"]) if "y_sigma" in z.files else 1.0; ymed=float(z["y_median"]) if "y_median" in z.files else 0.0
    m=z["mask"].astype(bool) if "mask" in z.files else np.ones(len(y),bool)
    for i in np.where(m)[0]:
        rows.append((int(ts[i]), float(q[i]), (float(y[i])*ysig+ymed)*1e4, mk))
with open("exports/run1_backtest.csv","w",newline="") as o:
    w=csv.writer(o); w.writerow(["timestamp_ms","y_pred_raw","y_true_ret_bps","month"]); w.writerows(rows)
print("wrote",len(rows),"rows; months:",sorted(set(r[3] for r in rows)))
