"""L2 全局流动性状态臂(设计 §2.2): BTC 书状态 18 列作【组尺度状态列】(声明性例外: 不做锚内秩,
fund_ema 先例)广播给全体成员行. 门同 F-A: Δavg ≥ +0.003 双跑且 2026 折 ≥ 0.
只在 LOB 覆盖锚上判(2023-01..2026-05-31), 基线在同一限定集上重算 — 两臂对称.
env: FEA_IN META_IN LOB_IN OUT_JSON
"""
import json, time, os
import numpy as np
from scipy.stats import rankdata, spearmanr
import lightgbm as lgb
FEA = np.load(os.environ["FEA_IN"], mmap_mode="r")
MT = np.load(os.environ["META_IN"], allow_pickle=True)
L = np.load(os.environ["LOB_IN"])
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]
names = [str(n) for n in MT["names"]]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
slow_keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
lts = L["ts_min"].astype(np.int64); lf = L["feat"].astype(np.float64)
o = np.argsort(lts); lts, lf = lts[o], lf[o]
lcum = np.vstack([np.zeros((1, lf.shape[1])), np.nancumsum(np.where(np.isfinite(lf), lf, 0), 0)])
lcnt = np.vstack([np.zeros((1, lf.shape[1])), np.cumsum(np.isfinite(lf), 0)])
amin = E_ts // 60
G = np.full((len(E_ts), 18), np.nan, np.float32); cov = np.zeros(len(E_ts), bool)
for j, W in enumerate((60, 1440)):
    hi = np.searchsorted(lts, amin, side="right"); lo = np.searchsorted(lts, amin - W, side="right")
    s = lcum[hi] - lcum[lo]; n = lcnt[hi] - lcnt[lo]
    G[:, j*9:(j+1)*9] = np.where(n >= W * 0.5, s / np.maximum(n, 1), np.nan)
    if W == 1440: cov = n[:, 0] >= 720
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
rows_X, rows_G, rows_y, rows_a = [], [], [], []
for i in range(len(E_ts)):
    if not cov[i]: continue
    m = members[i]; yv = y4[i, m]; ok = np.isfinite(yv)
    if ok.sum() < 50: continue
    rr = rankdata(yv[ok]) / max(ok.sum() - 1, 1) - 0.5
    rows_X.append(np.asarray(FEA[i, m[ok]][:, slow_keep], dtype=np.float32))
    rows_G.append(np.repeat(G[i][None, :], ok.sum(), 0))
    rows_y.append(rr.astype(np.float32)); rows_a.append(np.full(ok.sum(), i, np.int32))
XB = np.concatenate(rows_X); XG = np.concatenate(rows_G)
Y = np.concatenate(rows_y); A = np.concatenate(rows_a); YRA = yrs[A]
del rows_X, rows_G
print(f"rows {len(Y)} 覆盖锚 {cov.sum()}", flush=True)
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
res = {"note": "限定集=LOB覆盖锚(2023-01..2026-05-31); 基线同集重算", "runs": []}
for seed in (0, 1):
    b = fold_ics(XB, seed); a = fold_ics(np.column_stack([XB, XG]), seed)
    d = {y: round(a[y] - b[y], 4) for y in b}
    avg = round(float(np.mean(list(d.values()))), 4)
    res["runs"].append({"base": b, "l2g": a, "delta": d, "avg_delta": avg})
    print(f"[s{seed}] base {b} l2g {a} Δ {d} avg {avg:+.4f}", flush=True)
ok = all(r["avg_delta"] >= 0.003 and r["delta"]["2026"] >= 0 for r in res["runs"])
res["VERDICT"] = "PASS_TO_FB" if ok else "L2G_KILLED"
print(f"VERDICT {res['VERDICT']}", flush=True)
json.dump(res, open(os.environ.get("OUT_JSON", "l2_gate.json"), "w"), indent=1)
print("L2_GATE_DONE", flush=True)
