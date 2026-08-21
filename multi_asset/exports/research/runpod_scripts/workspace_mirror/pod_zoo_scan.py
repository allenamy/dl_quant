"""宽书 zoo S1 全谱扫 + A 梯队(面板口径模型对决) @pod CPU.
输入: /workspace/data/wide_panel_4h_v1.npz(829 币含退市, 13+2 因子列)
① zoo: 每因子逐锚 xsec rank-IC(vs Y4), 全体/K110/K400 三口径 + 逐年 + 最坏年 — 回答"110 失效因子是否在宽书复活"(干净版)
② A 梯队: 同弹药(全部因子 xsec-z)下 Ridge vs LGBM, 年度 walk-forward, 逐锚 rank-IC
   注意: 本梯队=面板口径, 与 film2(5m序列口径 0.0645@K400)非公平对比, 只作梯队内排序; 公平对决=B 梯队(同 5m 弹药).
产物: /workspace/zoo_scan.json
"""
import json, time
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from scipy.stats import rankdata, spearmanr
P = np.load("/workspace/data/wide_panel_4h_v1.npz", allow_pickle=True)
ts = P["ts"].astype(np.int64); syms = list(P["symbols"]); elig = P["elig"]
Y4 = P["Y4"]; NW = Y4.shape[1]
fnames = [k for k in P.files if k.startswith("f_")]
F = {k: P[k] for k in fnames}
yrs = np.array([time.gmtime(int(t)).tm_year for t in ts])
nT = len(ts)
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok])
    return r.correlation if hasattr(r, "correlation") else r[0]
# 量能列用于 K 子集(与装置同键: 尾随7日量能 ~ f_volq 不是水平; 用 amihud 反推不行 → 直接用 f 值重建: 面板没存 qvm ⇒ 用 f_vol_7d? 不对. 退而求其次: 每锚按 f_amihud_24h 升序≈流动性降序? amihud 小=流动. 稳妥: 用 24h 量能 qv24 重建: F 没存 qv24 ⇒ 用 volq_ratio*7d/7... 放弃重建, K 子集按 f_amihud_24h 升序取前 K(流动性代理, 标注口径)
LIQ = F.get("f_amihud_24h")
res_zoo = {}
sample = range(0, nT, 2)
for k in sorted(F):
    accA, acc110, acc400 = [], [], []
    by_year = {}
    for i in sample:
        if yrs[i] < 2023: continue
        m = np.where(elig[i] & np.isfinite(Y4[i]) & np.isfinite(F[k][i]))[0]
        if len(m) < 60: continue
        v = sp(F[k][i, m], Y4[i, m])
        accA.append(v); by_year.setdefault(int(yrs[i]), []).append(v)
        if LIQ is not None and np.isfinite(LIQ[i, m]).sum() > 100:
            order = m[np.argsort(LIQ[i, m])]
            if len(order) >= 100: acc110.append(sp(F[k][i, order[:110]], Y4[i, order[:110]]))
            if len(order) >= 360: acc400.append(sp(F[k][i, order[:400]], Y4[i, order[:400]]))
    a = np.array(accA)
    res_zoo[k] = {
        "ic": float(np.nanmean(a)), "t": float(np.nanmean(a) / (np.nanstd(a) / np.sqrt(np.isfinite(a).sum()) + 1e-12)),
        "ic_liq110": float(np.nanmean(acc110)) if acc110 else None,
        "ic_wide400": float(np.nanmean(acc400)) if acc400 else None,
        "by_year": {str(y): round(float(np.nanmean(v)), 4) for y, v in sorted(by_year.items())},
    }
    print(f"[zoo] {k:>16s} IC {res_zoo[k]['ic']:+.4f} t {res_zoo[k]['t']:+5.1f} "
          f"liq110 {res_zoo[k]['ic_liq110'] if res_zoo[k]['ic_liq110'] is None else round(res_zoo[k]['ic_liq110'],4)} "
          f"wide400 {res_zoo[k]['ic_wide400'] if res_zoo[k]['ic_wide400'] is None else round(res_zoo[k]['ic_wide400'],4)} "
          f"{res_zoo[k]['by_year']}", flush=True)
# ---- A 梯队: Ridge vs LGBM 同弹药 ----
feat_keys = sorted(F)
def xsec_z(v):
    out = np.full_like(v, np.nan)
    r = rankdata(v, nan_policy="omit")
    n = np.isfinite(v).sum()
    if n < 10: return out
    out[np.isfinite(v)] = (r[np.isfinite(v)] - (n + 1) / 2) / max(n - 1, 1)
    return out
rows, cols_i, cols_y, cols_yr = [], [], [], []
X_list, y_list, an_list, yr_list = [], [], [], []
for i in range(0, nT, 2):
    if yrs[i] < 2023: continue
    m = np.where(elig[i] & np.isfinite(Y4[i]))[0]
    if len(m) < 60: continue
    feats = []
    for k in feat_keys:
        z = np.full(NW, np.nan, np.float32); z[m] = 0
        vv = F[k][i, m]
        zz = xsec_z(vv)
        feats.append(zz)
    Xa = np.stack(feats, 1)
    ok = np.isfinite(Xa).all(1)
    if ok.sum() < 60: continue
    ya = xsec_z(Y4[i, m])
    X_list.append(Xa[ok]); y_list.append(ya[ok])
    an_list.append(np.full(ok.sum(), i)); yr_list.append(np.full(ok.sum(), yrs[i]))
X = np.concatenate(X_list); Y = np.concatenate(y_list)
AN = np.concatenate(an_list); YR = np.concatenate(yr_list)
print(f"A梯队样本 {X.shape}", flush=True)
res_A = {}
from sklearn.linear_model import Ridge
import lightgbm as lgb
for YV in (2024, 2025, 2026):
    tr = YR < YV; te = YR == YV
    if te.sum() == 0 or tr.sum() < 5000: continue
    an_te = AN[te]
    rid = Ridge(alpha=10.0).fit(X[tr], Y[tr])
    pr = rid.predict(X[te])
    gbm = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63,
                            subsample=0.8, colsample_bytree=0.8, n_jobs=64, verbose=-1).fit(X[tr], Y[tr])
    pg = gbm.predict(X[te])
    for nm, pv in (("ridge", pr), ("lgbm", pg)):
        ics = []
        for a in np.unique(an_te):
            sel = an_te == a
            if sel.sum() < 40: continue
            ics.append(sp(pv[sel], Y[te][sel]))
        res_A.setdefault(nm, {})[str(YV)] = float(np.nanmean(ics))
    print(f"[A] {YV}: ridge {res_A['ridge'][str(YV)]:+.4f}  lgbm {res_A['lgbm'][str(YV)]:+.4f}", flush=True)
for nm in res_A:
    res_A[nm]["mean"] = float(np.mean([v for k, v in res_A[nm].items() if k != "mean"]))
json.dump({"zoo": res_zoo, "bracketA": res_A}, open("/workspace/zoo_scan.json", "w"), indent=1)
print(f"A梯队均值: ridge {res_A.get('ridge',{}).get('mean')} lgbm {res_A.get('lgbm',{}).get('mean')}", flush=True)
print("ZOO_SCAN_DONE", flush=True)
