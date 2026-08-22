"""F7 门(两臂, 事前计 2 测): ① F7 单族(10列) vs 基线; ② F7∪ALL35 全融合(45列) vs 基线.
判据同族门: Δavg ≥ +0.003 双跑且 2026 折 ≥ 0.
env: FEA_IN META_IN F7_IN F12_IN F34_IN F6_IN F5_IN OUT_JSON
"""
import json, time, os
import numpy as np
from scipy.stats import rankdata, spearmanr
import lightgbm as lgb
FEA = np.load(os.environ["FEA_IN"], mmap_mode="r")
MT = np.load(os.environ["META_IN"], allow_pickle=True)
F7 = np.load(os.environ["F7_IN"], mmap_mode="r")
FS = [np.load(os.environ[k], mmap_mode="r") for k in ("F12_IN", "F34_IN", "F6_IN", "F5_IN")]
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]
names = [str(n) for n in MT["names"]]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
slow_keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
def xrank(v):
    out = np.zeros(len(v), np.float32); ok = np.isfinite(v)
    if ok.sum() > 1: out[ok] = rankdata(v[ok]) / (ok.sum() - 1) - 0.5
    return out
rows_X, rows_7, rows_O, rows_y, rows_a = [], [], [], [], []
for i in range(len(E_ts)):
    m = members[i]; yv = y4[i, m]; ok = np.isfinite(yv)
    if ok.sum() < 50: continue
    rr = rankdata(yv[ok]) / max(ok.sum() - 1, 1) - 0.5
    rows_X.append(np.asarray(FEA[i, m[ok]][:, slow_keep], dtype=np.float32))
    f7 = np.asarray(F7[i, m[ok]], dtype=np.float32)
    rows_7.append(np.column_stack([xrank(f7[:, j]) for j in range(f7.shape[1])]))
    fo = np.column_stack([np.asarray(F[i, m[ok]], dtype=np.float32) for F in FS])
    rows_O.append(np.column_stack([xrank(fo[:, j]) for j in range(fo.shape[1])]))
    rows_y.append(rr.astype(np.float32)); rows_a.append(np.full(ok.sum(), i, np.int32))
XB = np.concatenate(rows_X); X7 = np.concatenate(rows_7); XO = np.concatenate(rows_O)
Y = np.concatenate(rows_y); A = np.concatenate(rows_a); YRA = yrs[A]
del rows_X, rows_7, rows_O
print(f"rows {len(Y)} f7 {X7.shape[1]} old35 {XO.shape[1]}", flush=True)
BASE = {"2024": 0.0530, "2025": 0.0550, "2026": 0.0545}
def fold_ics(X, seed):
    out = {}
    for YV in (2024, 2025, 2026):
        tr = YRA < YV; te = YRA == YV
        g = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8,
                              colsample_bytree=0.8, n_jobs=24, verbose=-1, random_state=seed).fit(X[tr], Y[tr])
        pv = g.predict(X[te]); a_te = A[te]; ics = []
        for a in np.unique(a_te):
            s_ = a_te == a; mm = members[a]; okm = np.isfinite(y4[a, mm])
            ics.append(sp(pv[s_], y4[a, mm][okm]))
        out[str(YV)] = round(float(np.nanmean(ics)), 4)
    return out
res = {"base_frozen": BASE, "arms": {}}
for arm, X in (("F7", np.column_stack([XB, X7])), ("F7_ALL45", np.column_stack([XB, X7, XO]))):
    runs = []
    for seed in (0, 1):
        ic = fold_ics(X, seed)
        d = {y: round(ic[y] - BASE[y], 4) for y in ic}
        avg = round(float(np.mean(list(d.values()))), 4)
        runs.append({"ic": ic, "delta": d, "avg_delta": avg})
        print(f"[{arm} s{seed}] {ic} Δavg {avg:+.4f}", flush=True)
    ok = all(r["avg_delta"] >= 0.003 and r["delta"]["2026"] >= 0 for r in runs)
    res["arms"][arm] = {"runs": runs, "verdict": "PASS" if ok else "KILLED"}
    print(f"{arm} VERDICT {res['arms'][arm]['verdict']}", flush=True)
json.dump(res, open(os.environ.get("OUT_JSON", "f7_gate.json"), "w"), indent=1)
print("F7_GATE_DONE", flush=True)
