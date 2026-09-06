"""consistency_k1.py — K1 adjacent-month model consistency for the side-by-side reading (team-lead 09-06: K1 changes its seed every fold, 20260905+fold_index, so its
consistency includes a seed flip; KR/KC inherit the previous model and change no seed). Construction identical to train_incremental.py: per anchor in calendar month t,
Spearman between the month-t model (axisA d1_pred_age1 = K1 itself) and the month-(t-1) model (axisA d1_pred_age2) predictions; mean per month and overall (months 2024-02..2026-08).
Read-only on axisA products; writes results/consistency_k1.json here."""
import numpy as np, json, time
from scipy.stats import spearmanr
AXA = "/workspace/review_scratch/cadence_seats/axisA"
A1 = np.load(f"{AXA}/d1_pred_age1.npy"); A2 = np.load(f"{AXA}/d1_pred_age2.npy"); MT = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True)
E = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]
K1 = np.load("/workspace/review_scratch/rolling_king/slow_pred_rollm.npy"); print("age1 == K1 stitched:", bool(np.array_equal(A1, K1, equal_nan=True)))
ym = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in E])
per_month = {}; allc = []
for i in range(len(E)):
    if ym[i] < 202402: continue
    m = members[i]; a = A1[i, m]; b = A2[i, m]; ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: continue
    c = spearmanr(a[ok], b[ok])[0]; per_month.setdefault(int(ym[i]), []).append(c); allc.append(c)
pm = {k: round(float(np.mean(v)), 4) for k, v in sorted(per_month.items())}
out = {"definition": "per-anchor Spearman(model_t, model_{t-1}) on month t anchors; K1 models = axisA D1 retrain (age1 = K1 stitched bitwise); K1 seed changes every fold (20260905 + fold_index)", "per_month": pm, "mean": round(float(np.mean(allc)), 4), "min_month": min(pm, key=pm.get), "min": min(pm.values()), "n_anchors": len(allc)}
json.dump(out, open("results/consistency_k1.json", "w"), indent=1); print(json.dumps(out)); print("CONS_K1_DONE")
