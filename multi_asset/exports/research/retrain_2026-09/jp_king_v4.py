"""门V4-king @jpline(PREREG addendum §A): king booster 同参重训, 折 IC vs pod 侧 |Δ|≤0.004。
训练数学 = pod_export_bundle_v3.py §①逐字(keep 过滤/秩目标/LGBM 参数/逐锚 spearman)。
基准(pod 侧受据): fold24 +0.0548 / fold25 +0.0630 / ic26 +0.0584。
用法: python jp_king_v4.py <fea.npy> <meta.npz>
"""
import sys, time, json
import numpy as np
from scipy.stats import rankdata, spearmanr

FEA = np.load(sys.argv[1], mmap_mode="r")
MT = np.load(sys.argv[2], allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]
names = [str(n) for n in MT["names"]]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
nA = len(E_ts)
keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
rows_X, rows_y, rows_a = [], [], []
for i in range(nA):
    m = members[i]
    yv = y4[i, m]; ok = np.isfinite(yv)
    if ok.sum() < 50: continue
    rr = rankdata(yv[ok]) / max(ok.sum() - 1, 1) - 0.5
    rows_X.append(np.asarray(FEA[i])[m[ok]][:, keep].astype(np.float32))
    rows_y.append(rr.astype(np.float32)); rows_a.append(np.full(ok.sum(), i, np.int32))
X = np.concatenate(rows_X); Y = np.concatenate(rows_y); A = np.concatenate(rows_a)
YRA = yrs[A]
import lightgbm as lgb
POD = {"2024": 0.0548, "2025": 0.0630, "2026": 0.0584}
res = {}
for YV in (2024, 2025, 2026):
    tr = YRA < YV; te = YRA == YV
    g = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63,
                          subsample=0.8, colsample_bytree=0.8, n_jobs=48, verbose=-1).fit(X[tr], Y[tr])
    pv = g.predict(X[te]); a_te = A[te]
    ics = []
    for a in np.unique(a_te):
        s_ = a_te == a; m = members[a]; okm = np.isfinite(y4[a, m])
        ics.append(sp(pv[s_], y4[a, m[okm]]))
    ic = float(np.nanmean(ics)); d = ic - POD[str(YV)]
    res[YV] = (ic, d)
    print(f"V4 king fold {YV}: jpline IC {ic:+.4f} pod {POD[str(YV)]:+.4f} Δ{d:+.4f} {'OK' if abs(d)<=0.004 else 'FAIL'}", flush=True)
ok = all(abs(d) <= 0.004 for _, d in res.values())
print("V4_KING", "PASS" if ok else "FAIL", flush=True)
sys.exit(0 if ok else 3)
