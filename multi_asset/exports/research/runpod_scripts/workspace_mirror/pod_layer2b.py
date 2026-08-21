"""逐层书臂: 快层 = 快特征LGBM 训练在慢层残差上(逐锚 rank(y4) 对 rank(slow_pred) OLS 残差);
书 = 慢书(α0.1整形) + λ×快书(α1不整形, 小预算), λ∈{0, .1, .2, .3}; 三成本情景.
在役"逐层学残差+各层自带换手预算"结构的宽书移植.
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
SLOW = np.load("/workspace/exports_train/slow_lgbm_pred.npy")
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    n = ok.sum()
    if n >= 10: out[ok] = rankdata(v[ok]) / max(n - 1, 1) - 0.5
    return out
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
# 快层目标: 逐锚 rank(y4) 残差 vs rank(slow)
rows_X, rows_y, rows_a = [], [], []
for i in range(nA):
    m = members[i]
    yv = y4[i, m]; ok = np.isfinite(yv)
    if ok.sum() < 50: continue
    sl = SLOW[i, m[ok]]
    yr_ = rankdata(yv[ok]) / max(ok.sum() - 1, 1) - 0.5
    if np.isfinite(sl).sum() >= 30:
        sz = np.nan_to_num(xz(sl))
        beta = float((yr_ * sz).sum() / ((sz * sz).sum() + 1e-9))
        tgt = yr_ - beta * sz
    else:
        tgt = yr_
    rows_X.append(FEA[i, m[ok]].astype(np.float32))
    rows_y.append(tgt.astype(np.float32)); rows_a.append(np.full(ok.sum(), i, np.int32))
X = np.concatenate(rows_X); Y = np.concatenate(rows_y); A = np.concatenate(rows_a)
YRA = yrs[A]
import lightgbm as lgb
FAST = np.full((nA, NW), np.nan, np.float32)
for YV in (2024, 2025, 2026):
    tr = YRA < YV; te = YRA == YV
    if te.sum() == 0: continue
    gbm = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63,
                            subsample=0.8, colsample_bytree=0.8, n_jobs=100, verbose=-1).fit(X[tr], Y[tr])
    pv = gbm.predict(X[te]); a_te = A[te]
    for a in np.unique(a_te):
        sel = a_te == a
        m = members[a]; okm = np.isfinite(y4[a, m])
        FAST[a, m[okm]] = pv[sel]
    print(f"[{YV}] fast-layer 训毕", flush=True)
np.save("/workspace/exports_train/layer2_fast_pred.npy", FAST)
# 组书: 慢书 H_s(α0.1, b2.5e-4) + λ 快书 H_f(α1, b0)
PW = np.load("/workspace/data/wide_panel_4h_v1.npz", allow_pickle=True)
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
FN = PW["f_fund_now"]
COST = {"a": [(-0.25, 5.0, 0.85)] * 3,
        "b": [(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)],
        "c": [(1.0, 6.0, 0.75), (4.0, 8.0, 0.55), (8.0, 10.0, 0.35)]}
def tier_of(qv4h):
    t = np.full(len(qv4h), 2, np.int8); t[qv4h >= 1e6] = 1; t[qv4h >= 5e6] = 0
    return t
CAP = 2.5
def build_w(P):
    Wt = np.zeros((nA, NW), np.float32); okA = np.zeros(nA, bool)
    for i in range(nA):
        j = pw_row.get(int(E_ts[i]))
        if j is None: continue
        m = members[i]
        s = P[i, m]
        ok = np.isfinite(s) & np.isfinite(y4[i, m])
        qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
        sel = ok & (qv4h >= 2.5e5)
        if sel.sum() < 80: continue
        z = xz(np.where(sel, s, np.nan))
        w = np.nan_to_num(z); w -= w[sel].mean()
        g = np.abs(w).sum()
        if g < 1e-9: continue
        w /= g
        capw = CAP / max(sel.sum(), 1)
        w = np.clip(w, -capw, capw)
        g2 = np.abs(w).sum()
        if g2 > 1e-9: w /= g2
        Wt[i, m] = w; okA[i] = True
    return Wt, okA
Ws, okS = build_w(SLOW); Wf, okF = build_w(FAST)
fx2526 = yrs >= 2025
out = {}
for lam in (0.0, 0.1, 0.2, 0.3):
    Hs = np.zeros(NW, np.float64); Hf = np.zeros(NW, np.float64)
    rets, carrys, costs, tos, subm = [], [], {"a": [], "b": [], "c": []}, [], []
    for i in range(nA):
        if not okS[i]: continue
        tgt_s = Ws[i].astype(np.float64)
        sm_s = Hs + 0.1 * (tgt_s - Hs)
        tr_s = sm_s - Hs
        sm_s = np.where(np.abs(tr_s) < 2.5e-4, Hs, sm_s)
        sm_f = Wf[i].astype(np.float64) if (okF[i] and lam > 0) else Hf
        pos = sm_s + lam * sm_f
        prev = Hs + lam * Hf
        trade = pos - prev
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
        gross_l1 = np.abs(pos[m]).sum()
        scale = 1.0 / max(gross_l1, 1e-9)
        rets.append(float((pos[m] * yv).sum() * 1e4 * scale))
        fnow = np.nan_to_num(FN[j, m], nan=0.0)
        carrys.append(float(-(pos[m] * fnow).sum() / 2 * 1e4 * scale))
        for scen in ("a", "b", "c"): costs[scen][-1] *= scale
        tos.append(float(tabs.sum() * scale)); subm.append(bool(fx2526[i]))
        Hs = sm_s; Hf = sm_f
    rets = np.array(rets); carrys = np.array(carrys); sub = np.array(subm)
    for scen in ("a", "b", "c"):
        ca = np.array(costs[scen])
        net = rets + carrys - ca
        n25 = net[sub]
        sh = float(n25.mean() / (n25.std() + 1e-12) * np.sqrt(6 * 365))
        key = f"lam{lam}_{scen}"
        out[key] = {"net": round(float(n25.mean()), 3), "sharpe": round(sh, 2),
                    "gross": round(float(rets[sub].mean()), 3), "cost": round(float(ca[sub].mean()), 3),
                    "to": round(float(np.array(tos)[sub].mean()), 4)}
        print(f"[层书 λ{lam} {scen}] 毛{out[key]['gross']} 成本{out[key]['cost']} => 净{out[key]['net']} 夏普{out[key]['sharpe']} 换手{out[key]['to']}", flush=True)
json.dump(out, open("/workspace/layer2_bprime.json", "w"), indent=1)
print("LAYER2_DONE", flush=True)
