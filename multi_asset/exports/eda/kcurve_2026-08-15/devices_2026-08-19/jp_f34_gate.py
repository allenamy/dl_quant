"""门 F-A(族级, 设计稿 §1.4 冻结): base78 + {F1 | F2}(锚内秩形态) vs 冻结基线, 三折双跑.
判: 三折均值 Δ ≥ +0.003 且 2026 折 ≥ 0 ⇒ 族过; 否则族杀.
env: FEA_IN META_IN F34_IN OUT_JSON
"""
import json, time, os
import numpy as np
from scipy.stats import rankdata, spearmanr
import lightgbm as lgb

FEA = np.load(os.environ["FEA_IN"], mmap_mode="r")
MT = np.load(os.environ["META_IN"], allow_pickle=True)
F12 = np.load(os.environ["F34_IN"], mmap_mode="r")
F12C = [str(c) for c in np.load(os.environ["F34_IN"].replace(".npy", "_cols.npy"))]
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]
names = [str(n) for n in MT["names"]]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
slow_keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
FAM = {"F3": [F12C.index(c) for c in ("vr3_60", "trendr2_30", "dist_hi_30", "dist_hi_90", "updays_30")],
       "F4": [F12C.index(c) for c in ("beta_btc_30", "idio_share_30", "corr_mkt_30")]}
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
def xrank(v):  # 锚内秩 [-0.5, 0.5], NaN→0(中位)
    out = np.zeros(len(v), np.float32); ok = np.isfinite(v)
    if ok.sum() > 1: out[ok] = rankdata(v[ok]) / (ok.sum() - 1) - 0.5
    return out
rows_X, rows_F, rows_y, rows_a = [], [], [], []
for i in range(len(E_ts)):
    m = members[i]; yv = y4[i, m]; ok = np.isfinite(yv)
    if ok.sum() < 50: continue
    rr = rankdata(yv[ok]) / max(ok.sum() - 1, 1) - 0.5
    rows_X.append(np.asarray(FEA[i, m[ok]][:, slow_keep], dtype=np.float32))
    fv = np.asarray(F12[i, m[ok]], dtype=np.float32)
    rows_F.append(np.column_stack([xrank(fv[:, j]) for j in range(fv.shape[1])]))
    rows_y.append(rr.astype(np.float32)); rows_a.append(np.full(ok.sum(), i, np.int32))
XB = np.concatenate(rows_X); XF = np.concatenate(rows_F)
Y = np.concatenate(rows_y); A = np.concatenate(rows_a); YRA = yrs[A]
del rows_X, rows_F
print(f"rows {len(Y)} base {XB.shape[1]} f12 {XF.shape[1]}", flush=True)
BASE = {"2024": 0.0530, "2025": 0.0550, "2026": 0.0545}
def fold_ics(X, seed):
    out = {}
    for YV in (2024, 2025, 2026):
        tr = YRA < YV; te = YRA == YV
        if te.sum() == 0: continue
        g = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8,
                              colsample_bytree=0.8, n_jobs=24, verbose=-1, random_state=seed).fit(X[tr], Y[tr])
        pv = g.predict(X[te]); a_te = A[te]; ics = []
        for a in np.unique(a_te):
            s_ = a_te == a; mm = members[a]; okm = np.isfinite(y4[a, mm])
            ics.append(sp(pv[s_], y4[a, mm][okm]))
        out[str(YV)] = round(float(np.nanmean(ics)), 4)
    return out
res = {"base_frozen": BASE, "families": {}}
for fam, idx in FAM.items():
    XA = np.column_stack([XB, XF[:, idx]])
    runs = []
    for seed in (0, 1):
        ic = fold_ics(XA, seed)
        d = {y: round(ic[y] - BASE[y], 4) for y in ic}
        avg = round(float(np.mean(list(d.values()))), 4)
        runs.append({"ic": ic, "delta": d, "avg_delta": avg})
        print(f"[{fam} run{seed}] {ic} Δavg {avg:+.4f}", flush=True)
    ok = all(r["avg_delta"] >= 0.003 and r["delta"]["2026"] >= 0 for r in runs)
    res["families"][fam] = {"runs": runs, "verdict": "PASS_TO_FB" if ok else "FAMILY_KILLED"}
    print(f"{fam} VERDICT {res['families'][fam]['verdict']}", flush=True)
json.dump(res, open(os.environ.get("OUT_JSON", "f12_gate.json"), "w"), indent=1)
print("F12_GATE_DONE", flush=True)
