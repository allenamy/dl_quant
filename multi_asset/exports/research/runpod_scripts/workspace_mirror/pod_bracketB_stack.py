"""B梯队终装候选: LGBM 83特征 = 82 + king(s42) pred 逐锚秩z. 同折同参; 判 vs LGBM82 0.0690 门+0.003.
附: K2W 固定锚2025-26口径补算.
"""
import json, time
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from scipy.stats import rankdata, spearmanr
FEA = np.load("/workspace/data/wide_fea_v1.npy")
MT = np.load("/workspace/data/wide_fea_v1_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
nA = len(E_ts)
KM = np.load("/workspace/exports_train/kcurve_meta_K400_s42.npz", allow_pickle=True)
k_ts = KM["E_ts"].astype(np.int64); k_yrs = KM["yrs"]
krow = {int(t): j for j, t in enumerate(k_ts)}
def load_king():
    P = None
    for YV in (2023, 2024, 2025, 2026):
        p = np.load(f"/workspace/exports_train/kcurve_pred_K400_s42_{YV}.npy")
        if P is None: P = np.full_like(p, np.nan)
        P[np.where(k_yrs == YV)[0]] = p[np.where(k_yrs == YV)[0]]
    return P
KP = load_king()
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
# K2W 固定锚补算
K2P = None
for YV in (2023, 2024, 2025, 2026):
    p = np.load(f"/workspace/exports_train/k2w_s42_pred_{YV}.npy")
    if K2P is None: K2P = np.full_like(p, np.nan)
    K2P[np.where(yrs == YV)[0]] = p[np.where(yrs == YV)[0]]
fx = [i for i in range(nA) if yrs[i] >= 2025 and len(members[i]) >= 360]
k2fix = float(np.nanmean([sp(K2P[i, members[i]], y4[i, members[i]]) for i in fx]))
print(f"K2W 固定锚2025-26 {k2fix:+.4f}(n{len(fx)})", flush=True)
# 堆叠特征
rows_X, rows_y, rows_a = [], [], []
n_kingok = 0
for i in range(nA):
    m = members[i]
    yv = y4[i, m]; ok = np.isfinite(yv)
    if ok.sum() < 50: continue
    j = krow.get(int(E_ts[i]))
    kz = np.zeros(ok.sum(), np.float32)
    if j is not None:
        kp = KP[j, m[ok]]
        okk = np.isfinite(kp)
        if okk.sum() >= 10:
            kz[okk] = (rankdata(kp[okk]) / max(okk.sum() - 1, 1) - 0.5).astype(np.float32)
            n_kingok += 1
    rr = rankdata(yv[ok]) / max(ok.sum() - 1, 1) - 0.5
    rows_X.append(np.concatenate([FEA[i, m[ok]].astype(np.float32), kz[:, None]], 1))
    rows_y.append(rr.astype(np.float32)); rows_a.append(np.full(ok.sum(), i, np.int32))
X = np.concatenate(rows_X); Y = np.concatenate(rows_y); A = np.concatenate(rows_a)
print(f"样本 {X.shape} king可用锚 {n_kingok}", flush=True)
import lightgbm as lgb
YRA = yrs[A]
res = {}
PRED = np.full((nA, 829), np.nan, np.float32)
for YV in (2024, 2025, 2026):
    tr = YRA < YV; te = YRA == YV
    if te.sum() == 0: continue
    t0 = time.time()
    gbm = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63,
                            subsample=0.8, colsample_bytree=0.8, n_jobs=100, verbose=-1).fit(X[tr], Y[tr])
    pv = gbm.predict(X[te]); a_te = A[te]
    ics = []
    for a in np.unique(a_te):
        sel = a_te == a
        if sel.sum() < 40: continue
        m = members[a]; okm = np.isfinite(y4[a, m])
        PRED[a, m[okm]] = pv[sel]
        ics.append(sp(pv[sel], y4[a, m[okm]]))
    res[str(YV)] = float(np.nanmean(ics))
    print(f"[{YV}] stack IC {res[str(YV)]:+.4f} ({time.time()-t0:.0f}s)", flush=True)
res["mean"] = float(np.mean([v for k, v in res.items() if k != "mean"]))
sics = [sp(PRED[i, members[i]], y4[i, members[i]]) for i in fx]
res["fixed_2025_26"] = float(np.nanmean(sics)); res["k2w_fixed"] = k2fix
np.save("/workspace/exports_train/bracketB_stack_pred.npy", PRED)
json.dump(res, open("/workspace/bracketB_stack.json", "w"), indent=1)
print(f"STACK 均值 {res['mean']:+.4f} | 固定锚 {res['fixed_2025_26']:+.4f} vs LGBM82 +0.0690 / film2 +0.0645", flush=True)
print("STACK_DONE", flush=True)
