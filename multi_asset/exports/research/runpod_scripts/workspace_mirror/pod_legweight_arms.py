"""§29 fund 集中度保险臂 @pod: A=cap50 / B=look450 / C=cap50+look450 vs 基线(900 无帽).
判据冻结(P3 §29): 夏普≥基线−0.05 且 最差月+0.5 且 2026-08≥基线−0.5; 附带 carry/权重换手读数.
书机制与 pod_extweek 逐字同构(v1 口径+carry×4/iv).
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
def run(look, cap):
    def w3_at(i):
        p = pos.get(int(i), 0)
        if p < look: return np.array([1/3]*3)
        sl = slice(p - look, p)
        r = np.stack([LRa["king"][sl], LRa["rev24"][sl], LRa["fund"][sl]])
        shp = r.mean(1) / (r.std(1) + 1e-9); shp = np.maximum(shp, 0.0)
        w = shp / shp.sum() if shp.sum() > 0 else np.array([1/3]*3)
        if cap is not None and w[2] > cap:
            ex = w[2] - cap; w[2] = cap
            oth = w[0] + w[1]
            if oth > 1e-9: w[0] += ex*w[0]/oth; w[1] += ex*w[1]/oth
            else: w[0] += ex/2; w[1] += ex/2
        return w
    H = np.zeros(NW, np.float64)
    rec = []; carr = []; wprev = None; wto = []
    for i in range(nA):
        j = pw_row.get(int(E_ts[i]))
        if j is None: continue
        m = members[i]
        sc = {"king": SLOW[i, m], "rev24": -R24[j, m], "fund": FE[j, m]}
        w3 = w3_at(i)
        if wprev is not None: wto.append(float(np.abs(w3 - wprev).sum()))
        wprev = w3
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
        carr.append(car)
        rec.append((int(E_ts[i]), float((sm[m] * yv).sum() * 1e4 - car - cb)))
        H = sm
    arr = np.array([nn for t, nn in rec if time.gmtime(t).tm_year >= 2024])
    ym = np.array([time.strftime("%Y-%m", time.gmtime(t)) for t, _ in rec])
    nets = np.array([nn for _, nn in rec])
    mo = {}
    for mth in sorted(set(ym)):
        s = ym == mth
        if s.sum() >= 50 and mth >= "2024": mo[mth] = float(nets[s].mean())
    return {"mean": round(float(arr.mean()), 3),
            "sharpe": round(float(arr.mean()/(arr.std()+1e-12)*np.sqrt(6*365)), 2),
            "worst_month": round(min(mo.values()), 2), "m2026_08": round(mo.get("2026-08", float("nan")), 2),
            "carry_mean": round(float(np.mean(carr)), 3), "w_turnover": round(float(np.mean(wto)), 4)}
res = {}
for nm, look, cap in [("base", 900, None), ("cap50", 900, 0.50), ("look450", 450, None), ("cap50_look450", 450, 0.50)]:
    res[nm] = run(look, cap)
    print(f"[{nm}] {res[nm]}", flush=True)
b = res["base"]
for nm in ("cap50", "look450", "cap50_look450"):
    r = res[nm]
    ok = (r["sharpe"] >= b["sharpe"] - 0.05 and r["worst_month"] >= b["worst_month"] + 0.5
          and r["m2026_08"] >= b["m2026_08"] - 0.5)
    res[nm]["PASS"] = bool(ok)
    print(f"  {nm}: {'PASS' if ok else 'FAIL'} (判据: 夏普≥{b['sharpe']-0.05:.2f}, 最差月≥{b['worst_month']+0.5:.2f}, 08月≥{b['m2026_08']-0.5:.2f})", flush=True)
json.dump(res, open("/workspace/legweight_arms.json", "w"), indent=1)
print("LEGWEIGHT_DONE", flush=True)
