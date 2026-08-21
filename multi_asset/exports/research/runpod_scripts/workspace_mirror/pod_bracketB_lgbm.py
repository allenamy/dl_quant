"""B梯队臂①: LGBM 满弹药(wide_fea_v1 82特征) 年度walk-forward, 参数沿A梯队固定不搜.
口径: 逐锚 spear(pred, y4) 全体 + 固定锚2025-26(与 film2 0.0645 同口径可比).
"""
import json, time
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from scipy.stats import rankdata, spearmanr
FEA = np.load("/workspace/data/wide_fea_v1.npy")
M = np.load("/workspace/data/wide_fea_v1_meta.npz", allow_pickle=True)
E_ts = M["E_ts"].astype(np.int64); members = M["members"]; y4 = M["y4"]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
nA = len(E_ts)
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
rows_X, rows_y, rows_a = [], [], []
for i in range(nA):
    m = members[i]
    yv = y4[i, m]
    ok = np.isfinite(yv)
    if ok.sum() < 50: continue
    rr = rankdata(yv[ok]) / max(ok.sum() - 1, 1) - 0.5
    rows_X.append(FEA[i, m[ok]].astype(np.float32))
    rows_y.append(rr.astype(np.float32))
    rows_a.append(np.full(ok.sum(), i, np.int32))
X = np.concatenate(rows_X); Y = np.concatenate(rows_y); A = np.concatenate(rows_a)
YRA = yrs[A]
print(f"样本 {X.shape}", flush=True)
import lightgbm as lgb
res = {}
PRED = np.full((nA, 829), np.nan, np.float32)
for YV in (2024, 2025, 2026):
    tr = YRA < YV; te = YRA == YV
    if te.sum() == 0: continue
    t0 = time.time()
    gbm = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63,
                            subsample=0.8, colsample_bytree=0.8, n_jobs=100, verbose=-1).fit(X[tr], Y[tr])
    pv = gbm.predict(X[te])
    a_te = A[te]
    ics = []
    for a in np.unique(a_te):
        sel = a_te == a
        if sel.sum() < 40: continue
        m = members[a]
        okm = np.isfinite(y4[a, m])
        PRED[a, m[okm]] = pv[sel]
        ics.append(sp(pv[sel], y4[a, m[okm]]))
    res[str(YV)] = float(np.nanmean(ics))
    print(f"[{YV}] lgbm IC {res[str(YV)]:+.4f} ({time.time()-t0:.0f}s)", flush=True)
res["mean"] = float(np.mean([v for k, v in res.items() if k != "mean"]))
# 固定锚 2025-26 口径(成员≥360)
fx = [i for i in range(nA) if yrs[i] >= 2025 and len(members[i]) >= 360 and np.isfinite(PRED[i]).sum() >= 300]
fics = [sp(PRED[i, members[i]], y4[i, members[i]]) for i in fx]
res["fixed_2025_26"] = float(np.nanmean(fics)); res["n_fixed"] = len(fx)
np.save("/workspace/exports_train/bracketB_lgbm_pred.npy", PRED)
json.dump(res, open("/workspace/bracketB_lgbm.json", "w"), indent=1)
print(f"LGBM 均值 {res['mean']:+.4f} | 固定锚2025-26 {res['fixed_2025_26']:+.4f}(n{res['n_fixed']}) vs film2 +0.0645", flush=True)
print("BRACKETB_LGBM_DONE", flush=True)
