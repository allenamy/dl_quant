"""§28 采纳准备 @pod: 生产配方(pod_export_shadow_bundle ①)原样, 仅训练集换为 2020 起 hist 特征 →
slow2026_hist.txt booster + 钉定预测 + 2026 IC 核对. 产物入 /workspace/shadow_bundle_hist/ (不碰在用 bundle).
★ 特征列序守卫: hist meta names 必须与 v2ext meta names(config keep_names 之源)逐位一致, 否则按名重排."""
import json, time, os, sys
import numpy as np
from scipy.stats import rankdata, spearmanr
OUT = "/workspace/shadow_bundle_hist"; os.makedirs(OUT, exist_ok=True)
FEA = np.load("/workspace/data/wide_fea_hist.npy", mmap_mode="r")
MT = np.load("/workspace/data/wide_fea_hist_meta.npz", allow_pickle=True)
MT2 = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True)
names = [str(n) for n in MT["names"]]; names2 = [str(n) for n in MT2["names"]]
keep2 = [k for k, nm in enumerate(names2) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
keep_names = [names2[k] for k in keep2]
pos = {nm: k for k, nm in enumerate(names)}
missing = [nm for nm in keep_names if nm not in pos]
assert not missing, f"hist 特征缺列: {missing[:5]}"
keep = [pos[nm] for nm in keep_names]          # 按 v2ext 列序取 hist 列 ⇒ booster 列序与生产一致
print("列序守卫: 逐位同序" if keep == sorted(keep) and [names[k] for k in keep] == keep_names else "列序守卫: 已按名重排", flush=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); nA = len(E_ts); NW = 829
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
print("X", X.shape, "年分布", {int(y): int((YRA == y).sum()) for y in np.unique(YRA)}, flush=True)
import lightgbm as lgb
tr = YRA < 2026; te = YRA == 2026
gbm = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8, colsample_bytree=0.8, n_jobs=-1, verbose=-1).fit(X[tr], Y[tr])
gbm.booster_.save_model(f"{OUT}/slow2026_hist.txt")
PRED = np.full((nA, NW), np.nan, np.float32)
for YV in (2022, 2023, 2024, 2025):
    tr_ = YRA < YV; te_ = YRA == YV
    if tr_.sum() < 20000: continue
    g2 = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8, colsample_bytree=0.8, n_jobs=-1, verbose=-1).fit(X[tr_], Y[tr_])
    pv = g2.predict(X[te_]); a_te = A[te_]
    for a in np.unique(a_te):
        sel = a_te == a; m = members[a]; okm = np.isfinite(y4[a, m]); PRED[a, m[okm]] = pv[sel]
pv = gbm.predict(X[te]); a_te = A[te]; ics = []
for a in np.unique(a_te):
    sel = a_te == a; m = members[a]; okm = np.isfinite(y4[a, m]); PRED[a, m[okm]] = pv[sel]; ics.append(sp(pv[sel], y4[a, m][okm]))
ic26 = float(np.nanmean(ics))
np.save(f"{OUT}/slow_pred_pinned_hist.npy", PRED)
import hashlib
sha = hashlib.sha256(open(f"{OUT}/slow2026_hist.txt", "rb").read()).hexdigest()
json.dump({"ic2026": round(ic26, 4), "ref_hist_fold_2026": 0.058, "ref_prod_pinned_2026": 0.0571, "train_rows": int(tr.sum()),
           "keep_names": keep_names, "booster_sha256": sha, "note": "§28 ADOPT_FOR_V2 采纳准备; 未部署; 需影子平价+用户裁定"},
          open(f"{OUT}/RETRAIN_HIST.json", "w"), indent=1)
print(f"RETRAIN_HIST_DONE ic2026 {ic26:+.4f} (hist fold ref 0.058 / prod 0.0571) sha {sha[:12]}", flush=True)
