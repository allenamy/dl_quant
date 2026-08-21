"""#5 成本感知 serve-K 扫描 + #3 幸存者/PIT 审计 @pod(权威书构造同构, base msharpe look900, pinned king=OOS)。
serve-K: 每锚成员按 qv 取前 K∈{110,200,250,300,400} 再过流动性门; 判据(P3 残留, 冻结): 净最优 K 若非 400 且 夏普差 ≥0.10 ⇒ 建议重标 K。
PIT: 退市名 = 在面板末段(最后 60 锚)无 Y4 的名字(2026-08 前消失); 对照=剔除这些名字的全程回放(幸存者口径) vs 含退市全史(PIT 口径);
  幸存者虚增 = 夏普(剔除) − 夏普(PIT)。判据: 虚增 ≤0.15 可接受, >0.3 ⇒ 头条必须带折让。"""
import json, time, sys
import numpy as np
sys.path.insert(0, "/workspace")
from scipy.stats import rankdata
MT = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); nA = len(E_ts); NW = 829
PW = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True)
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]; R24 = PW["f_rev_24h"]; FE = PW["f_fund_ema_v1"]
SLOW = np.load("/workspace/shadow_bundle/slow_pred_pinned.npy")
Y4P = PW["Y4"]
# 退市名: 面板末 60 锚内 Y4 全 NaN 且此前有过数据
last = np.isfinite(Y4P[-60:]).any(0); ever = np.isfinite(Y4P).any(0)
DELISTED = np.where(ever & ~last)[0]
print("退市/消失名数", len(DELISTED), flush=True)
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 10: out[ok] = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
    return out
COST_B = [(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)]
def tier_of(q):
    t = np.full(len(q), 2, np.int8); t[q >= 1e6] = 1; t[q >= 5e6] = 0
    return t
def run(K=400, drop=None):
    dropset = set(drop.tolist()) if drop is not None else set()
    LR = {l: [] for l in ("king", "rev24", "fund")}; pos = {}; rec = []
    H = np.zeros(NW); p = 0
    for i in range(nA):
        j = pw_row.get(int(E_ts[i]))
        if j is None: continue
        m = np.asarray(members[i], int)
        if dropset: m = np.array([x for x in m if x not in dropset], int)
        if K < 400 and len(m) > K:
            m = np.sort(m[np.argsort(-qvk[i, m])[:K]])
        if len(m) < 50: continue
        sc = {"king": SLOW[i, m], "rev24": -R24[j, m], "fund": FE[j, m]}
        ok = np.isfinite(y4[i, m])
        for leg in LR:
            z = np.nan_to_num(xz(sc[leg])); z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0
            g = np.abs(z).sum(); LR[leg].append(float((z / g * np.nan_to_num(y4[i, m], nan=0.0)).sum() * 1e4) if g > 1e-9 else 0.0)
        if p < 900: w3 = np.array([1/3]*3)
        else:
            r = np.stack([np.array(LR[l][p-900:p]) for l in ("king", "rev24", "fund")])
            shp = np.maximum(r.mean(1) / (r.std(1) + 1e-9), 0.0); w3 = shp / shp.sum() if shp.sum() > 0 else np.array([1/3]*3)
        p += 1
        z = w3[0]*np.nan_to_num(xz(sc["king"])) + w3[1]*np.nan_to_num(xz(sc["rev24"])) + w3[2]*np.nan_to_num(xz(sc["fund"]))
        qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
        sel = ok & (qv4h >= 2.5e5)
        if sel.sum() < 80: continue
        w = np.where(sel, z, 0.0); w -= w[sel].mean(); g = np.abs(w).sum()
        if g < 1e-9: continue
        w /= g; capw = 2.5 / max(int(sel.sum()), 1); w = np.clip(w, -capw, capw); g2 = np.abs(w).sum()
        if g2 > 1e-9: w /= g2
        tgt = np.zeros(NW); tgt[m] = w
        sm = H + 0.1 * (tgt - H); trade = sm - H
        sm = np.where(np.abs(trade) < 2.5e-4, H, sm); trade = sm - H
        tr = tier_of(qv4h); tabs = np.abs(trade[m])
        cb = sum(tabs[tr == tt].sum() * (fr * mk + (1 - fr) * tk) for tt, (mk, tk, fr) in enumerate(COST_B))
        yv = np.nan_to_num(y4[i, m], nan=0.0); fnow = np.nan_to_num(FN[j, m], nan=0.0)
        ivv = IV[j, m]; ivv = np.where(np.isfinite(ivv) & (ivv > 0), ivv, 8.0)
        car = (sm[m] * fnow * (4.0 / ivv)).sum() * 1e4
        rec.append((int(E_ts[i]), float((sm[m] * yv).sum() * 1e4 - car - cb), int(sel.sum())))
        H = sm
    nets = np.array([x[1] for x in rec]); ts_ = np.array([x[0] for x in rec]); yy = np.array([time.gmtime(int(t)).tm_year for t in ts_])
    a24 = nets[yy >= 2024]
    cum = np.cumsum(a24); dd = cum - np.maximum.accumulate(cum)
    return {"net_2024on": round(float(a24.mean()), 3), "sharpe_2024on": round(float(a24.mean()/(a24.std()+1e-12)*np.sqrt(6*365)), 2),
            "maxDD_2024on": round(float(-dd.min()), 0), "sel_mean": round(float(np.mean([x[2] for x in rec])), 0),
            "by_year": {int(y): round(float(nets[yy == y].mean()), 3) for y in sorted(set(yy.tolist()))}}
out = {"serveK": {}, "pit": {}}
for K in (110, 200, 250, 300, 400):
    out["serveK"][f"K{K}"] = run(K=K); print("serveK", K, json.dumps(out["serveK"][f"K{K}"]), flush=True)
out["pit"]["PIT_all"] = out["serveK"]["K400"]
out["pit"]["survivor_only"] = run(K=400, drop=DELISTED)
out["pit"]["n_delisted"] = int(len(DELISTED))
out["pit"]["sharpe_inflation"] = round(out["pit"]["survivor_only"]["sharpe_2024on"] - out["pit"]["PIT_all"]["sharpe_2024on"], 3)
print("PIT", json.dumps(out["pit"]), flush=True)
json.dump(out, open("/workspace/serveK_pit.json", "w"), indent=1)
print("SERVEK_PIT_DONE", flush=True)
