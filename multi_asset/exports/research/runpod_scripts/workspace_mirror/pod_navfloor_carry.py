"""§24 双件 @pod: A) NAV 地板模拟(15格测量) B) carry 减分臂(γ 0.5/1.0, 判据冻结).
基线=v1iv(钉死预测 slow_pred_pinned, 全史b 2.41). 书机制与 pod_extweek 逐字同构.
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
FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]; R24 = PW["f_rev_24h"]; FE = PW["f_fund_ema_v1"]
SLOW = np.load("/workspace/shadow_bundle/slow_pred_pinned.npy")
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    n = ok.sum()
    if n >= 10: out[ok] = rankdata(v[ok]) / max(n - 1, 1) - 0.5
    return out
COST_B = [(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)]
def tier_of(q):
    t = np.full(len(q), 2, np.int8); t[q >= 1e6] = 1; t[q >= 5e6] = 0
    return t
# 腿收益 + msharpe(与 extweek 同)
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
    if p < look: return (1/3, 1/3, 1/3)
    sl = slice(p - look, p)
    r = np.stack([LRa["king"][sl], LRa["rev24"][sl], LRa["fund"][sl]])
    shp = r.mean(1) / (r.std(1) + 1e-9); shp = np.maximum(shp, 0.0)
    return tuple(shp / shp.sum() if shp.sum() > 0 else np.array([1/3]*3))

def run_book(gamma=0.0, floor_usd=0.0, nav2x=0.0):
    """gamma: carry 减分系数; floor_usd/nav2x: 地板模拟(nav2x=NAV×杠杆, 0=无地板)."""
    H = np.zeros(NW, np.float64)
    rec = []; to_int = to_exec = 0.0
    for i in range(nA):
        j = pw_row.get(int(E_ts[i]))
        if j is None: continue
        m = members[i]
        sc = {"king": SLOW[i, m], "rev24": -R24[j, m], "fund": FE[j, m]}
        wk, wr, wf = w3_at(i)
        z = wk * np.nan_to_num(xz(sc["king"])) + wr * np.nan_to_num(xz(sc["rev24"])) + wf * np.nan_to_num(xz(sc["fund"]))
        if gamma > 0:
            ivm = IV[j, m]; ivm = np.where(np.isfinite(ivm) & (ivm > 0), ivm, 8.0)
            ec = np.nan_to_num(FN[j, m], nan=0.0) * (4.0 / ivm)
            z = z - gamma * np.nan_to_num(xz(ec))
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
        if nav2x > 0:
            small = (np.abs(trade) * nav2x < floor_usd) & (np.abs(trade) > 0)
            sm = np.where(small, H, sm)
            trade = sm - H
        to_int += float(np.abs((tgt - H)).sum()); to_exec += float(np.abs(trade).sum())
        tr = tier_of(qv4h); tabs = np.abs(trade[m])
        cb = sum(tabs[tr == tt].sum() * (fr * mk + (1 - fr) * tk) for tt, (mk, tk, fr) in enumerate(COST_B))
        yv = np.nan_to_num(y4[i, m], nan=0.0)
        fnow = np.nan_to_num(FN[j, m], nan=0.0)
        ivv = IV[j, m]; ivv = np.where(np.isfinite(ivv) & (ivv > 0), ivv, 8.0)
        car = (sm[m] * fnow * (4.0 / ivv)).sum() * 1e4
        net = float((sm[m] * yv).sum() * 1e4 - car - cb)
        rec.append((int(E_ts[i]), net))
        H = sm
    out = {}
    for yr_min, tag in ((2024, "full"), (2025, "2025p")):
        arr = np.array([n for t, n in rec if time.gmtime(t).tm_year >= yr_min])
        out[tag] = {"mean": round(float(arr.mean()), 3),
                    "sharpe": round(float(arr.mean() / (arr.std() + 1e-12) * np.sqrt(6 * 365)), 2)}
    out["exec_frac"] = round(to_exec / max(to_int, 1e-9), 4)
    # 净漂移检测: 多空腿毛额不平度
    return out

res = {"base": run_book()}
print(f"[base] {res['base']}", flush=True)
for gamma in (0.5, 1.0):
    r = run_book(gamma=gamma)
    res[f"carry_g{gamma}"] = r
    print(f"[carry γ{gamma}] {r}", flush=True)
for nav in (6100, 50000, 125000, 250000, 500000):
    for fl in (5.0, 10.0, 20.0):
        r = run_book(floor_usd=fl, nav2x=nav * 2)
        res[f"floor_{nav}_{int(fl)}"] = r
        print(f"[floor NAV{nav} ${int(fl)}] 夏普{r['full']['sharpe']} 执行占比{r['exec_frac']}", flush=True)
json.dump(res, open("/workspace/navfloor_carry.json", "w"), indent=1)
print("NAVFLOOR_CARRY_DONE", flush=True)
