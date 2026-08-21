"""慢引擎逐年扩张 OOS 折 @pod(2020 起训练): YV∈{2022..2026}, train=yrs<YV. 与 pod_slow_hist_judge 同参同特征(去 ret5_sum_48/288).
产物: /workspace/exports_train/slow_pred_hist_oos.npy (锚×829, OOS), + fold IC 收据 json。"""
import json, time, os
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from scipy.stats import rankdata, spearmanr
FEA = np.load(os.environ.get("FEA_IN", "/workspace/data/wide_fea_hist.npy"), mmap_mode="r")
MT = np.load(os.environ.get("META_IN", "/workspace/data/wide_fea_hist_meta.npz"), allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; names = [str(n) for n in MT["names"]]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); nA = len(E_ts); NW = 829
keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
print(f"锚 {nA} 年分布 {dict(zip(*np.unique(yrs, return_counts=True)))} 特征 {len(keep)}", flush=True)
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
rows_X, rows_y, rows_a = [], [], []
for i in range(nA):
    m = members[i]; yv = y4[i, m]; ok = np.isfinite(yv)
    if ok.sum() < 50: continue
    rr = rankdata(yv[ok]) / max(ok.sum() - 1, 1) - 0.5
    rows_X.append(np.asarray(FEA[i, m[ok]][:, keep], np.float32)); rows_y.append(rr.astype(np.float32)); rows_a.append(np.full(ok.sum(), i, np.int32))
X = np.concatenate(rows_X); Y = np.concatenate(rows_y); A = np.concatenate(rows_a); YRA = yrs[A]
print("X", X.shape, flush=True)
import lightgbm as lgb
PRED = np.full((nA, NW), np.nan, np.float32); ic_by = {}
for YV in (2022, 2023, 2024, 2025, 2026):
    tr = YRA < YV; te = YRA == YV
    if te.sum() == 0 or tr.sum() < 20000: print(f"skip {YV} tr={int(tr.sum())}", flush=True); continue
    g = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8, colsample_bytree=0.8, n_jobs=-1, verbose=-1).fit(X[tr], Y[tr])
    pv = g.predict(X[te]); a_te = A[te]; ics = []
    for a in np.unique(a_te):
        s_ = a_te == a; m = members[a]; okm = np.isfinite(y4[a, m])
        PRED[a, m[okm]] = pv[s_]; ics.append(sp(pv[s_], y4[a, m][okm]))
    ic_by[str(YV)] = round(float(np.nanmean(ics)), 4)
    print(f"fold {YV}: train_rows {int(tr.sum())} IC {ic_by[str(YV)]}", flush=True)
np.save("/workspace/exports_train/slow_pred_hist_oos.npy", PRED)
json.dump({"ic_by_year": ic_by, "base_ic_2024_26": {"2024": 0.0574, "2025": 0.0617, "2026": 0.0571}}, open("/workspace/slow_hist_folds.json", "w"), indent=1)
print("FOLDS_DONE", ic_by, flush=True)
