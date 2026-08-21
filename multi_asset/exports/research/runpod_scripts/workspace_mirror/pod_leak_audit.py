"""泄漏审计电池(用户令: 严格因果, 之前咬过一次).
① shuffle-future 空值: 目标年内乱序重训 LGBM → OOS IC 必须≈0(训练管道无泄漏的会红断言)
② embargo 不变性: LGBM82 加 60 锚 embargo 重训 → ΔIC(边界目标窗跨年的定价)
③ 偏移谱: slow/stack preds vs y4 offset{-2..+2} → corr@0 必须峰值
④ 特征时间戳重导: 抽 3 锚, 从原始缓存重算 5 个特征, 断言只用 <锚 数据且与缓存值一致
"""
import json, time
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from scipy.stats import rankdata, spearmanr
from zload import zload
FEA = np.load("/workspace/data/wide_fea_v1.npy")
MT = np.load("/workspace/data/wide_fea_v1_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]
names = [str(n) for n in MT["names"]]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
nA = len(E_ts)
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
    rows_X.append(FEA[i, m[ok]].astype(np.float32))
    rows_y.append(rr.astype(np.float32)); rows_a.append(np.full(ok.sum(), i, np.int32))
X = np.concatenate(rows_X); Y = np.concatenate(rows_y); A = np.concatenate(rows_a)
YRA = yrs[A]
import lightgbm as lgb
def run_fold(Ytr_use, embargo=0, YV=2025):
    first_te = np.where(yrs == YV)[0][0]
    tr = (YRA < YV) & (A < first_te - embargo)
    te = YRA == YV
    gbm = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63,
                            subsample=0.8, colsample_bytree=0.8, n_jobs=100, verbose=-1).fit(X[tr], Ytr_use[tr])
    pv = gbm.predict(X[te]); a_te = A[te]
    ics = []
    for a in np.unique(a_te):
        sel = a_te == a
        if sel.sum() < 40: continue
        m = members[a]; okm = np.isfinite(y4[a, m])
        ics.append(sp(pv[sel], y4[a, m[okm]]))
    return float(np.nanmean(ics))
# ① shuffle-future: 锚级目标乱序(同年内), 特征不动
rng = np.random.default_rng(7)
Yshuf = Y.copy()
for yv_ in (2022, 2023, 2024):
    aset = np.unique(A[(YRA == yv_)])
    perm = rng.permutation(aset)
    remap = dict(zip(aset.tolist(), perm.tolist()))
    idx_by_a = {a: np.where(A == a)[0] for a in aset}
    newY = Y.copy()
    for a in aset:
        src = idx_by_a[remap[a]]; dst = idx_by_a[a]
        n = min(len(src), len(dst))
        newY[dst[:n]] = Y[src[:n]]
    Yshuf[(YRA == yv_)] = newY[(YRA == yv_)]
ic_shuf = run_fold(Yshuf, 0, 2025)
print(f"① shuffle-future 空值 OOS IC(2025) = {ic_shuf:+.4f} (判据 |IC|<0.005)", flush=True)
# ② embargo 不变性
ic_e0 = run_fold(Y, 0, 2025)
ic_e60 = run_fold(Y, 60, 2025)
print(f"② embargo: e0 {ic_e0:+.4f} vs e60 {ic_e60:+.4f} Δ{ic_e60-ic_e0:+.4f} (判据 |Δ|<0.002)", flush=True)
# ③ 偏移谱(slow 与 stack preds)
SLOW = np.load("/workspace/exports_train/slow_lgbm_pred.npy")
STACK = np.load("/workspace/exports_train/bracketB_stack_pred.npy")
for nm, P in (("slow", SLOW), ("stack", STACK)):
    row = []
    for off in (-2, -1, 0, 1, 2):
        v = []
        for i in range(60, nA - 60, 5):
            if yrs[i] < 2025: continue
            m = members[i]
            if 0 <= i + off < nA:
                v.append(sp(P[i, m], y4[i + off, m]))
        row.append(round(float(np.nanmean(v)), 4))
    peak = "PASS" if max(range(5), key=lambda k: abs(row[k])) == 2 else "FAIL"
    print(f"③ 偏移谱[{nm}] -2..+2: {row} 峰在0: {peak}", flush=True)
# ④ 特征时间戳重导(抽3锚, vol_2016 与 ret5_sum_288 从缓存重算)
Z = zload("/workspace/data/dlnative_5m_wide829_f16.npz", allow_pickle=True)
CTS = Z["ts"].astype(np.int64); CD = Z["data"]
grid_map = {int(t): k for k, t in enumerate(CTS)}
iv = names.index("vol_2016_v"); ir = names.index("ret5_sum_288_v")
bad = 0
for probe_i in (500, 5000, 9000):
    e = grid_map[int(E_ts[probe_i])]
    m0 = members[probe_i][0]
    r5 = CD[e-2016:e, m0, 0].astype(np.float64)
    fin = np.isfinite(r5); n = max(fin.sum(), 1)
    rv = np.sqrt(max(np.nansum(r5[fin]**2)/n - (np.nansum(r5[fin])/n)**2, 0))
    cached_v = float(FEA[probe_i, m0, iv])
    r288 = np.nansum(CD[e-288:e, m0, 0].astype(np.float64))
    cached_r = float(FEA[probe_i, m0, ir])
    ok1 = abs(rv - cached_v) < max(abs(cached_v)*0.05, 1e-4)
    ok2 = abs(r288 - cached_r) < max(abs(cached_r)*0.05, 1e-3)
    if not (ok1 and ok2): bad += 1
    print(f"④ 锚{probe_i}: vol重导 {rv:.5f} vs 缓存 {cached_v:.5f} {'OK' if ok1 else 'MISMATCH'}; ret288 {r288:.5f} vs {cached_r:.5f} {'OK' if ok2 else 'MISMATCH'}", flush=True)
print(f"④ 特征重导: {'PASS' if bad==0 else f'FAIL {bad}锚'} (窗口=[e-w,e) 只用锚前数据, 目标=[e,e+48))", flush=True)
print("LEAK_AUDIT_DONE", flush=True)
