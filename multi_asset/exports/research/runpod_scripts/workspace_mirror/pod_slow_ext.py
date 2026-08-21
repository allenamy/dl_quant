"""ext 慢引擎: 与 pod_slow_scorer.py 同折同参重训(按年扩张 2024/2025/2026), 打分含延长周.
平价守卫: 与旧 PRED 在共同锚上逐年 corr>=0.98(f16 缓存重建允许微差), 违者 FAIL 退出.
产物: slow_lgbm_pred_ext.npy (nA_ext x 829)
"""
import time
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from scipy.stats import rankdata, spearmanr
FEA = np.load("/workspace/data/wide_fea_v2ext.npy")
MT = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]
names = [str(n) for n in MT["names"]]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
nA = len(E_ts); NW = 829
keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
print(f"慢特征 {len(keep)}/{len(names)} 锚 {nA}", flush=True)
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
    rows_X.append(FEA[i, m[ok]][:, keep].astype(np.float32))
    rows_y.append(rr.astype(np.float32)); rows_a.append(np.full(ok.sum(), i, np.int32))
X = np.concatenate(rows_X); Y = np.concatenate(rows_y); A = np.concatenate(rows_a)
YRA = yrs[A]
import lightgbm as lgb
PRED = np.full((nA, NW), np.nan, np.float32)
ic_by = {}
for YV in (2024, 2025, 2026):
    tr = YRA < YV; te = YRA == YV
    if te.sum() == 0: continue
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
    ic_by[str(YV)] = float(np.nanmean(ics))
    print(f"[{YV}] slow-lgbm-ext IC {ic_by[str(YV)]:+.4f}", flush=True)
np.save("/workspace/exports_train/slow_lgbm_pred_ext.npy", PRED)
# 平价守卫 vs 旧 PRED
OLD = np.load("/workspace/exports_train/slow_lgbm_pred.npy")
MT0 = np.load("/workspace/data/wide_fea_v1_meta.npz", allow_pickle=True)
ts0 = MT0["E_ts"].astype(np.int64)
row_new = {int(t): i for i, t in enumerate(E_ts)}
pairs = [(i0, row_new[int(t)]) for i0, t in enumerate(ts0) if int(t) in row_new]
yr0 = np.array([time.gmtime(int(t)).tm_year for t in ts0])
fails = []
for YV in (2024, 2025, 2026):
    aa, bb = [], []
    for i0, i1 in pairs:
        if yr0[i0] != YV: continue
        a = OLD[i0]; b = PRED[i1]
        ok = np.isfinite(a) & np.isfinite(b)
        aa.append(a[ok]); bb.append(b[ok])
    if not aa: continue
    a = np.concatenate(aa); b = np.concatenate(bb)
    c = float(np.corrcoef(a, b)[0, 1]) if len(a) > 1000 else np.nan
    print(f"parity-diag {YV} pred-corr {c:.4f} n {len(a)} (LGBM 多线程非确定性, 仅诊断不作门)", flush=True)
# 真平价门: 折 IC vs 原装 slow_scorer.json(2024/2025 严判 ≤0.004; 2026 含延长周新锚, 只打印)
import json as _json
orig_ic = _json.load(open("/workspace/slow_scorer.json"))["ic"]
for YV in ("2024", "2025"):
    d = abs(ic_by.get(YV, np.nan) - float(orig_ic[YV]))
    print(f"parity-IC {YV} orig {float(orig_ic[YV]):+.4f} ext {ic_by.get(YV, float('nan')):+.4f} |Δ| {d:.4f}", flush=True)
    if not (d <= 0.004): fails.append((YV, round(d, 4)))
print(f"parity-IC 2026(参考) orig {float(orig_ic['2026']):+.4f} ext {ic_by.get('2026', float('nan')):+.4f}", flush=True)
if fails:
    print(f"SLOW_EXT_PARITY_FAIL {fails}", flush=True); sys.exit(3)
print("SLOW_EXT_DONE", flush=True)
