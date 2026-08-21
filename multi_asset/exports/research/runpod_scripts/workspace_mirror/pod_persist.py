"""持续性判官(KCAL-wide): 逐锚 xsec 秩的跨锚自相关 @lag{1,6,42} — king vs LGBM82 vs slowLGBM vs 堆叠.
110 受据: king 持久 0.688 vs 树 0.559 — 宽书是否同向? 决定谁坐慢层.
"""
import json, time
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from scipy.stats import rankdata, spearmanr
MT = np.load("/workspace/data/wide_fea_v1_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
nA = len(E_ts)
KM = np.load("/workspace/exports_train/kcurve_meta_K400_s42.npz", allow_pickle=True)
k_ts = KM["E_ts"].astype(np.int64); k_yrs = KM["yrs"]; krow = {int(t): j for j, t in enumerate(k_ts)}
KING = None
for YV in (2023, 2024, 2025, 2026):
    p = np.load(f"/workspace/exports_train/kcurve_pred_K400_s42_{YV}.npy")
    if KING is None: KING = np.full_like(p, np.nan)
    KING[np.where(k_yrs == YV)[0]] = p[np.where(k_yrs == YV)[0]]
KING_A = np.full((nA, 829), np.nan, np.float32)
for i in range(nA):
    j = krow.get(int(E_ts[i]))
    if j is not None: KING_A[i] = KING[j]
PREDS = {"king_seq": KING_A,
         "lgbm82": np.load("/workspace/exports_train/bracketB_lgbm_pred.npy"),
         "stack83": np.load("/workspace/exports_train/bracketB_stack_pred.npy"),
         "slow_lgbm": np.load("/workspace/exports_train/slow_lgbm_pred.npy")}
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 50: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
out = {}
for nm, P in PREDS.items():
    row = {}
    for lag in (1, 6, 42):
        acs = []
        for i in range(0, nA - lag, 3):
            if yrs[i] < 2024: continue
            m = members[i]
            acs.append(sp(P[i, m], P[i + lag, m]))
        row[f"lag{lag}"] = round(float(np.nanmean(acs)), 3)
    out[nm] = row
    print(f"[{nm:>9s}] 秩自相关 lag1 {row['lag1']} lag6(24h) {row['lag6']} lag42(7d) {row['lag42']}", flush=True)
json.dump(out, open("/workspace/persist.json", "w"), indent=1)
print("PERSIST_DONE", flush=True)
