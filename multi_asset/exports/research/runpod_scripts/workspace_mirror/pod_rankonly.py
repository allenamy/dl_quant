"""§30 rank-only 消融 @pod: 78 列 → 40 列(38 秩 + fund 2), 双跑, 判据冻结(P3 §30).
基线折 IC = 0.0574/0.0617/0.0571(钉死 booster 世代).
"""
import json, time
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from scipy.stats import rankdata, spearmanr
FEA = np.load("/workspace/data/wide_fea_v2ext.npy")
MT = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]
names = [str(n) for n in MT["names"]]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
nA = len(E_ts)
slow_keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
rank_keep = [k for k in slow_keep if names[k].endswith("_r") or names[k] in ("fund_ema", "fund_now")]
print(f"rank-only 列数 {len(rank_keep)} (基线 {len(slow_keep)})", flush=True)
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
    rows_X.append(FEA[i, m[ok]][:, rank_keep].astype(np.float32))
    rows_y.append(rr.astype(np.float32)); rows_a.append(np.full(ok.sum(), i, np.int32))
X = np.concatenate(rows_X); Y = np.concatenate(rows_y); A = np.concatenate(rows_a)
YRA = yrs[A]
import lightgbm as lgb
BASE = {"2024": 0.0574, "2025": 0.0617, "2026": 0.0571}
res = {"base": BASE, "runs": []}
for run in (1, 2):
    ic_by = {}
    for YV in (2024, 2025, 2026):
        tr = YRA < YV; te = YRA == YV
        if te.sum() == 0: continue
        g = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63,
                              subsample=0.8, colsample_bytree=0.8, n_jobs=100, verbose=-1).fit(X[tr], Y[tr])
        pv = g.predict(X[te]); a_te = A[te]
        ics = []
        for a in np.unique(a_te):
            s_ = a_te == a; m = members[a]; okm = np.isfinite(y4[a, m])
            ics.append(sp(pv[s_], y4[a, m][okm]))
        ic_by[str(YV)] = round(float(np.nanmean(ics)), 4)
    d = {y: round(ic_by[y] - BASE[y], 4) for y in ic_by}
    res["runs"].append({"ic": ic_by, "delta": d})
    print(f"[run{run}] rank-only IC {ic_by} Δ {d}", flush=True)
d1, d2 = (res["runs"][0]["delta"], res["runs"][1]["delta"]) if len(res["runs"]) == 2 else (res["runs"][0]["delta"],)*2
all_small = all(abs(d1[y]) < 0.002 and abs(d2[y]) < 0.002 for y in d1)
any_big = any(abs(d1[y]) >= 0.005 and abs(d2[y]) >= 0.005 for y in d1)
res["verdict"] = "VALUE_COLS_NEGLIGIBLE" if all_small else ("VALUE_COLS_REAL" if any_big else "MIDBAND")
print(f"VERDICT {res['verdict']}", flush=True)
json.dump(res, open("/workspace/rankonly.json", "w"), indent=1)
print("RANKONLY_DONE", flush=True)
