"""ALL45 滞后安慰剂(泄漏审计 §8-8): 45 新列全部取【42 锚(7天)前】的值注入, 基线不动.
判读(封于跑前): 安慰剂 Δavg ≈ 0(|Δ|<0.001) ⇒ +0.0029 时间锁定为真; ≈+0.002 ⇒ 列数伪影, 终审值作废.
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
SHIFT = 42
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
def xrank(v):
    out = np.zeros(len(v), np.float32); ok = np.isfinite(v)
    if ok.sum() > 1: out[ok] = rankdata(v[ok]) / (ok.sum() - 1) - 0.5
    return out
rows_X, rows_P, rows_y, rows_a = [], [], [], []
for i in range(len(E_ts)):
    m = members[i]; yv = y4[i, m]; ok = np.isfinite(yv)
    if ok.sum() < 50: continue
    j = max(i - SHIFT, 0)
    rr = rankdata(yv[ok]) / max(ok.sum() - 1, 1) - 0.5
    rows_X.append(np.asarray(FEA[i, m[ok]][:, slow_keep], dtype=np.float32))
    f7 = np.asarray(F7[j, m[ok]], dtype=np.float32)
    fo = np.column_stack([np.asarray(F[j, m[ok]], dtype=np.float32) for F in FS])
    fv = np.column_stack([f7, fo])
    rows_P.append(np.column_stack([xrank(fv[:, k]) for k in range(fv.shape[1])]))
    rows_y.append(rr.astype(np.float32)); rows_a.append(np.full(ok.sum(), i, np.int32))
XB = np.concatenate(rows_X); XP = np.concatenate(rows_P)
Y = np.concatenate(rows_y); A = np.concatenate(rows_a); YRA = yrs[A]
del rows_X, rows_P
print(f"rows {len(Y)} placebo45 shift {SHIFT}", flush=True)
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
BASE = {"2024": 0.0530, "2025": 0.0550, "2026": 0.0545}
res = {"runs": []}
for seed in (0, 1):
    ic = fold_ics(np.column_stack([XB, XP]), seed)
    d = {y: round(ic[y] - BASE[y], 4) for y in ic}
    avg = round(float(np.mean(list(d.values()))), 4)
    res["runs"].append({"ic": ic, "delta": d, "avg_delta": avg})
    print(f"[PLACEBO45 s{seed}] {ic} Δavg {avg:+.4f}", flush=True)
json.dump(res, open(os.environ.get("OUT_JSON", "arb_placebo.json"), "w"), indent=1)
print("PLACEBO_DONE", flush=True)
