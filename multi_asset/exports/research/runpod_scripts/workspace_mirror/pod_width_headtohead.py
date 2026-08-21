"""同引擎宽度正面对决(离线终审核心件): 同一打分器族×同一成本模型, serve-110 书 vs serve-400 书.
打分器: slow_lgbm(慢书主角)+stack83(快书参照); 整形 α0.1 b2.5e-4; 三成本情景.
回答: "加宽本身在净口径是否赚钱"——消掉跨引擎口径风险的最小装置.
"""
import json, time
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from scipy.stats import rankdata
MT = np.load("/workspace/data/wide_fea_v1_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
nA = len(E_ts); NW = 829
PW = np.load("/workspace/data/wide_panel_4h_v1.npz", allow_pickle=True)
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
FN = PW["f_fund_now"]
SC = {"slow": np.load("/workspace/exports_train/slow_lgbm_pred.npy"),
      "stack": np.load("/workspace/exports_train/bracketB_stack_pred.npy")}
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    n = ok.sum()
    if n >= 10: out[ok] = rankdata(v[ok]) / max(n - 1, 1) - 0.5
    return out
COST = {"a": [(-0.25, 5.0, 0.85)] * 3,
        "b": [(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)],
        "c": [(1.0, 6.0, 0.75), (4.0, 8.0, 0.55), (8.0, 10.0, 0.35)]}
def tier_of(qv4h):
    t = np.full(len(qv4h), 2, np.int8); t[qv4h >= 1e6] = 1; t[qv4h >= 5e6] = 0
    return t
fx = yrs >= 2025
out = {}
for snm, P in SC.items():
    for K in (110, 400):
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
            if sel.sum() > K:
                ord_ = np.argsort(-qv4h)
                kk = np.zeros(len(m), bool); cnt = 0
                for idx in ord_:
                    if sel[idx]: kk[idx] = True; cnt += 1
                    if cnt >= K: break
                sel = kk
            z = xz(np.where(sel, s, np.nan))
            w = np.nan_to_num(z); w -= w[sel].mean()
            g = np.abs(w).sum()
            if g < 1e-9: continue
            w /= g
            capw = 2.5 / max(sel.sum(), 1)
            w = np.clip(w, -capw, capw)
            g2 = np.abs(w).sum()
            if g2 > 1e-9: w /= g2
            Wt[i, m] = w; okA[i] = True
        H = np.zeros(NW, np.float64)
        rets, carrys, costs, subm = [], [], {"a": [], "b": [], "c": []}, []
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
            subm.append(bool(fx[i]))
            H = sm
        rets = np.array(rets); carrys = np.array(carrys); sub = np.array(subm)
        for scen in ("a", "b", "c"):
            ca = np.array(costs[scen])
            net = rets + carrys - ca
            n25 = net[sub]
            sh = float(n25.mean() / (n25.std() + 1e-12) * np.sqrt(6 * 365))
            out[f"{snm}_K{K}_{scen}"] = {"net": round(float(n25.mean()), 3), "sharpe": round(sh, 2)}
            print(f"[{snm} K{K} {scen}] 净{out[f'{snm}_K{K}_{scen}']['net']} 夏普{sh:.2f}", flush=True)
json.dump(out, open("/workspace/width_h2h.json", "w"), indent=1)
print("H2H_DONE", flush=True)
