"""§28 回溯终判 @pod: 扩轴(2020起)特征上重训慢引擎(双跑)→ 折 IC 门 → 书级 v1iv 门.
判据冻结(P3 §28): 三折平均 ≥−0.001 且 2024 折 ≥+0.002 且 书级Δ全史(b) ≥+0.05 且 双跑全过.
基线: 折 IC 0.0574/0.0617/0.0571, 书级 2.42. 搭车臂(1h 步长)另跑不混判.
"""
import json, time, os
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from scipy.stats import rankdata, spearmanr
FEA = np.load(os.environ.get("FEA_IN", "/workspace/data/wide_fea_hist.npy"))
MT = np.load(os.environ.get("META_IN", "/workspace/data/wide_fea_hist_meta.npz"), allow_pickle=True)
PANEL = os.environ.get("PANEL_IN", "/workspace/data/wide_panel_4h_hist.npz")
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]
names = [str(n) for n in MT["names"]]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
nA = len(E_ts); NW = 829
keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
n_small = int(((yrs <= 2021)).sum())
print(f"锚 {nA}(其中 2020-21 新增 {n_small}) 慢特征 {len(keep)}", flush=True)
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
BASE_IC = {"2024": 0.0574, "2025": 0.0617, "2026": 0.0571}
res = {"base_ic": BASE_IC, "runs": [], "n_new_anchors": n_small}
best_pred = None
for run in (1, 2):
    PRED = np.full((nA, NW), np.nan, np.float32)
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
            PRED[a, m[okm]] = pv[s_]
            ics.append(sp(pv[s_], y4[a, m][okm]))
        ic_by[str(YV)] = round(float(np.nanmean(ics)), 4)
    d = {y: round(ic_by[y] - BASE_IC[y], 4) for y in ic_by}
    ok_ic = (np.mean(list(d.values())) >= -0.001) and (d["2024"] >= 0.002)
    res["runs"].append({"ic": ic_by, "delta": d, "ic_gate": bool(ok_ic)})
    print(f"[run{run}] hist IC {ic_by} Δ {d} 门 {'过' if ok_ic else '不过'}", flush=True)
    if run == 1: best_pred = PRED
ic_double = all(r["ic_gate"] for r in res["runs"])
res["ic_gate_double"] = bool(ic_double)
# 书级(仅在 IC 门过时跑, 省时; 不过也跑一次供归因)
PW = np.load(PANEL, allow_pickle=True)
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]; R24 = PW["f_rev_24h"]; FE = PW["f_fund_ema_v1"]
SLOW = best_pred
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 10: out[ok] = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
    return out
COST_B = [(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)]
def tier_of(q):
    t = np.full(len(q), 2, np.int8); t[q >= 1e6] = 1; t[q >= 5e6] = 0
    return t
LR = {leg: [] for leg in ("king", "rev24", "fund")}
idx = []
for i in range(nA):
    j = pw_row.get(int(E_ts[i]))
    if j is None: continue
    m = members[i]
    sc = {"king": SLOW[i, m], "rev24": -R24[j, m], "fund": FE[j, m]}
    ok = np.isfinite(y4[i, m])
    for leg in LR:
        z = np.nan_to_num(xz(sc[leg]))
        z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0
        g = np.abs(z).sum()
        LR[leg].append(float((z / g * np.nan_to_num(y4[i, m], nan=0.0)).sum() * 1e4) if g > 1e-9 else 0.0)
    idx.append(i)
LRa = {k: np.array(v) for k, v in LR.items()}
pos = {int(i): p for p, i in enumerate(idx)}
def w3_at(i):
    p = pos.get(int(i), 0); look = 900
    if p < look: return np.array([1/3]*3)
    sl = slice(p - look, p)
    r = np.stack([LRa["king"][sl], LRa["rev24"][sl], LRa["fund"][sl]])
    shp = r.mean(1) / (r.std(1) + 1e-9); shp = np.maximum(shp, 0.0)
    return shp / shp.sum() if shp.sum() > 0 else np.array([1/3]*3)
H = np.zeros(NW, np.float64)
rec = []
for i in range(nA):
    j = pw_row.get(int(E_ts[i]))
    if j is None: continue
    m = members[i]
    sc = {"king": SLOW[i, m], "rev24": -R24[j, m], "fund": FE[j, m]}
    w3 = w3_at(i)
    z = w3[0]*np.nan_to_num(xz(sc["king"])) + w3[1]*np.nan_to_num(xz(sc["rev24"])) + w3[2]*np.nan_to_num(xz(sc["fund"]))
    ok = np.isfinite(y4[i, m])
    qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
    sel = ok & (qv4h >= 2.5e5)
    if sel.sum() < 80: continue
    w = np.where(sel, z, 0.0); w -= w[sel].mean()
    g = np.abs(w).sum()
    if g < 1e-9: continue
    w /= g
    capw = 2.5 / max(int(sel.sum()), 1)
    w = np.clip(w, -capw, capw)
    g2 = np.abs(w).sum()
    if g2 > 1e-9: w /= g2
    tgt = np.zeros(NW); tgt[m] = w
    sm = H + 0.1 * (tgt - H)
    trade = sm - H
    sm = np.where(np.abs(trade) < 2.5e-4, H, sm)
    trade = sm - H
    tr = tier_of(qv4h); tabs = np.abs(trade[m])
    cb = sum(tabs[tr == tt].sum() * (fr * mk + (1 - fr) * tk) for tt, (mk, tk, fr) in enumerate(COST_B))
    yv = np.nan_to_num(y4[i, m], nan=0.0)
    fnow = np.nan_to_num(FN[j, m], nan=0.0)
    ivv = IV[j, m]; ivv = np.where(np.isfinite(ivv) & (ivv > 0), ivv, 8.0)
    car = (sm[m] * fnow * (4.0 / ivv)).sum() * 1e4
    rec.append((int(E_ts[i]), float((sm[m] * yv).sum() * 1e4 - car - cb)))
    H = sm
arr = np.array([nn for t, nn in rec if time.gmtime(t).tm_year >= 2024])
sh = float(arr.mean()/(arr.std()+1e-12)*np.sqrt(6*365))
res["book_full_b"] = {"mean": round(float(arr.mean()), 3), "sharpe": round(sh, 2)}
book_gate = sh >= 2.42 + 0.05
res["book_gate"] = bool(book_gate)
res["VERDICT"] = "ADOPT_FOR_V2" if (ic_double and book_gate) else "HIST_AXIS_CLOSED"
print(f"书级全史(b) 夏普 {sh:.2f} (门 ≥2.47) | IC双跑 {'过' if ic_double else '不过'} | 终判 {res['VERDICT']}", flush=True)
json.dump(res, open("/workspace/hist_judge.json", "w"), indent=1)
print("HIST_JUDGE_DONE", flush=True)
