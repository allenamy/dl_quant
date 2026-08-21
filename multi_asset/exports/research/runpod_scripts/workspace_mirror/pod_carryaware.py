"""carry-aware msharpe 单臂(P3 §22 判据冻结先于跑): 腿收益含各腿自身 carry, 权重学习器可见.
基线对照 = v1iv(全史b 2.42 / 2025+ 3.26). 其余全部与 pod_extweek.py 逐字同构.
"""
import json, time
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from scipy.stats import rankdata
MT = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
nA = len(E_ts); NW = 829
PW = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True)
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]; R24 = PW["f_rev_24h"]
FE = PW["f_fund_ema_v1"]
SLOW = np.load("/workspace/exports_train/slow_lgbm_pred_ext.npy")
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    n = ok.sum()
    if n >= 10: out[ok] = rankdata(v[ok]) / max(n - 1, 1) - 0.5
    return out
COST = {"b": [(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)],
        "c": [(1.0, 6.0, 0.75), (4.0, 8.0, 0.55), (8.0, 10.0, 0.35)]}
def tier_of(q):
    t = np.full(len(q), 2, np.int8); t[q >= 1e6] = 1; t[q >= 5e6] = 0
    return t
def leg_scores(i):
    j = pw_row.get(int(E_ts[i]))
    if j is None: return None
    m = members[i]
    return {"king": SLOW[i, m], "rev24": -R24[j, m], "fund": FE[j, m]}, m, j
# 腿收益: 含各腿自身 carry
LR = {leg: [] for leg in ("king", "rev24", "fund")}
idx = []
for i in range(nA):
    ls = leg_scores(i)
    if ls is None: continue
    sc, m, j = ls
    ok = np.isfinite(y4[i, m])
    fnow = np.nan_to_num(FN[j, m], nan=0.0)
    ivv = IV[j, m]; ivv = np.where(np.isfinite(ivv) & (ivv > 0), ivv, 8.0)
    for leg in LR:
        z = np.nan_to_num(xz(sc[leg]))
        z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0
        g = np.abs(z).sum()
        if g > 1e-9:
            zn = z / g
            r = float((zn * np.nan_to_num(y4[i, m], nan=0.0)).sum() * 1e4 - (zn * fnow * (4.0 / ivv)).sum() * 1e4)
        else:
            r = 0.0
        LR[leg].append(r)
    idx.append(i)
LR = {k: np.array(v) for k, v in LR.items()}
pos = {int(i): p for p, i in enumerate(idx)}
def msharpe_w(i_pos):
    look = 900
    if i_pos < look: return (1/3, 1/3, 1/3)
    sl = slice(i_pos - look, i_pos)
    r = np.stack([LR["king"][sl], LR["rev24"][sl], LR["fund"][sl]])
    shp = r.mean(1) / (r.std(1) + 1e-9); shp = np.maximum(shp, 0.0)
    w = shp / shp.sum() if shp.sum() > 0 else np.array([1/3]*3)
    return tuple(w)
Wt = np.zeros((nA, NW), np.float32); okA = np.zeros(nA, bool)
for i in range(nA):
    ls = leg_scores(i)
    if ls is None: continue
    sc, m, j = ls
    wk, wr, wf = msharpe_w(pos.get(int(i), 0))
    z = wk * np.nan_to_num(xz(sc["king"])) + wr * np.nan_to_num(xz(sc["rev24"])) + wf * np.nan_to_num(xz(sc["fund"]))
    ok = np.isfinite(y4[i, m])
    qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
    sel = ok & (qv4h >= 2.5e5)
    if sel.sum() < 80: continue
    w = np.where(sel, z, 0.0); w -= w[sel].mean()
    g = np.abs(w).sum()
    if g < 1e-9: continue
    w /= g
    capw = 2.5 / max(sel.sum(), 1)
    w = np.clip(w, -capw, capw)
    g2 = np.abs(w).sum()
    if g2 > 1e-9: w /= g2
    Wt[i, m] = w; okA[i] = True
res = {}
for scen in ("b", "c"):
    H = np.zeros(NW, np.float64)
    rec = []
    for i in range(nA):
        if not okA[i]: continue
        tgt = Wt[i].astype(np.float64)
        sm = H + 0.1 * (tgt - H)
        trade = sm - H
        sm = np.where(np.abs(trade) < 2.5e-4, H, sm)
        trade = sm - H
        j = pw_row[int(E_ts[i])]
        m = members[i]
        qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
        tr = tier_of(qv4h); tabs = np.abs(trade[m])
        cb = 0.0
        for tt in range(3):
            s_ = tr == tt
            mk, tk, fr = COST[scen][tt]
            cb += tabs[s_].sum() * (fr * mk + (1 - fr) * tk)
        yv = np.nan_to_num(y4[i, m], nan=0.0)
        fnow = np.nan_to_num(FN[j, m], nan=0.0)
        ivv = IV[j, m]; ivv = np.where(np.isfinite(ivv) & (ivv > 0), ivv, 8.0)
        car = (sm[m] * fnow * (4.0 / ivv)).sum() * 1e4
        net = float((sm[m] * yv).sum() * 1e4 - car - cb)
        rec.append((int(E_ts[i]), net))
        H = sm
    for yr_min, tag in ((2024, "full"), (2025, "2025p")):
        arr = np.array([n for t, n in rec if time.gmtime(t).tm_year >= yr_min])
        sh = float(arr.mean() / (arr.std() + 1e-12) * np.sqrt(6 * 365))
        res[f"{scen}_{tag}"] = {"n": len(arr), "mean_bps": round(float(arr.mean()), 3), "sharpe": round(sh, 2)}
        print(f"[carry-aware {scen} {tag}] 净{res[f'{scen}_{tag}']['mean_bps']} 夏普{res[f'{scen}_{tag}']['sharpe']}", flush=True)
json.dump(res, open("/workspace/carryaware.json", "w"), indent=1)
print("CARRYAWARE_DONE", flush=True)
