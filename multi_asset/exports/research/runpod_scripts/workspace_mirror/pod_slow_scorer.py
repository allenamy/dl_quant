"""慢打分器臂: LGBM82 剔快特征(窗<864 的 ret/秩列)→ 慢 LGBM → 直接回放(整形网格小扫).
诊断依据: P3 v3 — 快alpha×薄币成本错配; 目标: 换手0.03-0.05 下净额/夏普.
"""
import json, time
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from scipy.stats import rankdata, spearmanr
FEA = np.load("/workspace/data/wide_fea_v1.npy")
MT = np.load("/workspace/data/wide_fea_v1_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]
names = [str(n) for n in MT["names"]]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
nA = len(E_ts); NW = 829
# 慢特征列: 剔除窗 48/288 的 ret5_sum 与其秩(快反转), 保留其余(vol/range/cpos/qv/cnt/asz/tbf 全窗 + ret 864+)
keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
print(f"慢特征 {len(keep)}/{len(names)}", flush=True)
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
    print(f"[{YV}] slow-lgbm IC {ic_by[str(YV)]:+.4f}", flush=True)
np.save("/workspace/exports_train/slow_lgbm_pred.npy", PRED)
# 回放(与 v2 引擎同构, 打分器=慢LGBM, 整形小网格)
PW = np.load("/workspace/data/wide_panel_4h_v1.npz", allow_pickle=True)
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
FN = PW["f_fund_now"]
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    n = ok.sum()
    if n >= 10: out[ok] = rankdata(v[ok]) / max(n - 1, 1) - 0.5
    return out
COST = {"b": [(-0.25, 5.0, 0.85), (2.0, 6.0, 0.70), (3.0, 8.0, 0.50)],
        "c": [(1.0, 6.0, 0.75), (4.0, 8.0, 0.55), (8.0, 10.0, 0.35)],
        "a": [(-0.25, 5.0, 0.85), (-0.25, 5.0, 0.85), (-0.25, 5.0, 0.85)]}
def tier_of(qv4h):
    t = np.full(len(qv4h), 2, np.int8); t[qv4h >= 1e6] = 1; t[qv4h >= 5e6] = 0
    return t
CAP_MULT = 2.5
fx2526 = yrs >= 2025
Wt = np.zeros((nA, NW), np.float32); okA = np.zeros(nA, bool)
for i in range(nA):
    j = pw_row.get(int(E_ts[i]))
    if j is None: continue
    m = members[i]
    s = PRED[i, m]
    ok = np.isfinite(s) & np.isfinite(y4[i, m])
    qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
    sel = ok & (qv4h >= 2.5e5)
    if sel.sum() < 80: continue
    z = xz(np.where(sel, s, np.nan))
    w = np.nan_to_num(z); w = w - w[sel].mean()
    g = np.abs(w).sum()
    if g < 1e-9: continue
    w = w / g
    capw = CAP_MULT / max(sel.sum(), 1)
    w = np.clip(w, -capw, capw)
    g2 = np.abs(w).sum()
    if g2 > 1e-9: w = w / g2
    Wt[i, m] = w; okA[i] = True
out = {"ic": ic_by}
for al in (1.0, 0.3, 0.2, 0.1):
    for bd in (0.0, 2.5e-4):
        H = np.zeros(NW, np.float64)
        rets, carrys, costs, tos, subm = [], [], {"a": [], "b": [], "c": []}, [], []
        for i in range(nA):
            if not okA[i]: continue
            tgt = Wt[i].astype(np.float64)
            sm = H + al * (tgt - H)
            trade = sm - H
            sm = np.where(np.abs(trade) < bd, H, sm)
            trade = sm - H
            j = pw_row[int(E_ts[i])]
            m = members[i]
            qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
            tr = tier_of(qv4h); tabs = np.abs(trade[m])
            for scen in ("a", "b", "c"):
                cx = 0.0
                for tt in range(3):
                    s_ = tr == tt
                    mk, tk, fr = COST[scen][tt]
                    cx += tabs[s_].sum() * (fr * mk + (1 - fr) * tk)
                costs[scen].append(cx)
            yv = np.nan_to_num(y4[i, m], nan=0.0)
            rets.append(float((sm[m] * yv).sum() * 1e4))
            fnow = np.nan_to_num(FN[j, m], nan=0.0)
            carrys.append(float(-(sm[m] * fnow).sum() / 2 * 1e4))
            tos.append(float(tabs.sum())); subm.append(bool(fx2526[i]))
            H = sm
        rets = np.array(rets); carrys = np.array(carrys); sub = np.array(subm)
        for scen in ("a", "b", "c"):
            ca = np.array(costs[scen])
            net = rets + carrys - ca
            n25 = net[sub]
            sh = float(n25.mean() / (n25.std() + 1e-12) * np.sqrt(6 * 365))
            key = f"al{al}_bd{bd}_{scen}"
            out[key] = {"net": round(float(n25.mean()), 3), "sharpe": round(sh, 2),
                        "gross": round(float(rets[sub].mean()), 3), "cost": round(float(ca[sub].mean()), 3),
                        "to": round(float(np.array(tos)[sub].mean()), 4)}
            print(f"[慢书 α{al} b{bd} {scen}] 毛{out[key]['gross']} 成本{out[key]['cost']} => 净{out[key]['net']} 夏普{out[key]['sharpe']} 换手{out[key]['to']}", flush=True)
json.dump(out, open("/workspace/slow_scorer.json", "w"), indent=1)
print("SLOW_DONE", flush=True)
