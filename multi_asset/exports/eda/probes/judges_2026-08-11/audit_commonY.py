"""Audit 0C's common-y data-prep by verifying the OUTPUT CSVs (build-script-agnostic).
A. node identity: run1 & prod CSVs share ts+y_true+month per-row, differ only in pred.
B. prod y_true == original production CSV y_true (common realized series).
C. run1 pred = denorm(q50)*1e4 from the matching d1_<m>_run1 npz, aligned on timestamp
   (proves correct denorm AND pred↔ts alignment, no misjoin)."""
import numpy as np, pandas as pd
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
r = pd.read_csv(f"{MA}/exports/run1_commonY.csv")
p = pd.read_csv(f"{MA}/exports/prod_commonY.csv")
prod0 = pd.read_csv(f"{MA}/exports/final_l01/y600_backtest_dataset.csv")
print(f"rows: run1={len(r)} prod={len(p)} orig_prod={len(prod0)}")

# A. node identity (same order assumed; verify)
same_ts = np.array_equal(r.timestamp_ms.values, p.timestamp_ms.values)
same_y  = np.allclose(r.y_true_ret_bps.values, p.y_true_ret_bps.values, atol=1e-6)
same_mon= np.array_equal(r.month.values, p.month.values)
pred_diff = not np.allclose(r.y_pred_raw.values, p.y_pred_raw.values)
print(f"A. node identity: same_ts={same_ts} same_y_true={same_y} same_month={same_mon} | pred DIFFERS={pred_diff}")
print(f"   ts strictly increasing (chrono)? {bool(np.all(np.diff(r.timestamp_ms.values)>=0))}; unique ts? {r.timestamp_ms.nunique()==len(r)}")

# B. prod y_true vs ORIGINAL production CSV (join on ts)
mp = prod0.set_index("timestamp_ms")["y_true_ret_bps"]
join = p.timestamp_ms.map(mp)
covered = join.notna().mean()
ymatch = np.allclose(join.dropna().values, p.y_true_ret_bps.values[join.notna().values], atol=1e-4)
print(f"B. prod y_true vs orig-prod: {covered*100:.1f}% ts covered, y_true match={ymatch}")

# C. run1 pred denorm+alignment vs the d1_<m>_run1 npz (spot-check 2 months x 4 ts)
print("C. run1 pred = denorm(npz q50)*1e4, aligned on ts:")
for m in ["2025_08", "2026_01"]:
    z = np.load(f"{MA}/experiments/d1gate/d1_{m}_run1/fold_0/ema_test_preds.npz", allow_pickle=True)
    q = z["predictions"][:,1].astype(float); ts_us = z["timestamps"].astype(np.int64)
    ysig=float(z["y_sigma"]); ymed=float(z["y_median"])
    denorm_bps = (q*ysig+ymed)*1e4
    npz_ms = ts_us//1000
    lut = dict(zip(npz_ms, denorm_bps))
    sub = r[r.month==m]
    idxs = np.linspace(0, len(sub)-1, 4).astype(int)
    ok=True; details=[]
    for ii in idxs:
        row = sub.iloc[ii]; tms=int(row.timestamp_ms); got=float(row.y_pred_raw)
        exp = lut.get(tms, None)
        hit = (exp is not None and abs(got-exp)<1e-4)
        ok &= hit; details.append(f"ts={tms} csv={got:+.4f} npz_denorm={('%.4f'%exp) if exp is not None else 'NOMATCH'} {'ok' if hit else 'MISMATCH'}")
    print(f"   {m}: {'PASS' if ok else 'FAIL'}")
    for dd in details: print(f"      {dd}")
