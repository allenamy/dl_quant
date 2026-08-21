"""P3 v3: 归因驱动迭代 — ①carry 收割腿(空高funding) ②成本感知 serve-K{150,250,400} ③组合书(堆叠+zoo慢+carry).
整形冻结在 v2 胜格(α0.2 b2.5e-4); 双成本情景; 判据同 §5.
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
F6 = {k: PW[k] for k in ["f_vol_7d", "f_range_24h", "f_mom_7d", "f_fund_ema"]}
STACK = np.load("/workspace/exports_train/bracketB_stack_pred.npy")
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    n = ok.sum()
    if n >= 10: out[ok] = rankdata(v[ok]) / max(n - 1, 1) - 0.5
    return out
COST = {"b": [(-0.25, 5.0, 0.85), (2.0, 6.0, 0.70), (3.0, 8.0, 0.50)],
        "c": [(1.0, 6.0, 0.75), (4.0, 8.0, 0.55), (8.0, 10.0, 0.35)]}
def tier_of(qv4h):
    t = np.full(len(qv4h), 2, np.int8); t[qv4h >= 1e6] = 1; t[qv4h >= 5e6] = 0
    return t
CAP_MULT = 2.5; AL = 0.2; BD = 2.5e-4
WCOMBOS = [("stack", 1.0, 0.0, 0.0), ("s6z2c2", 0.6, 0.2, 0.2), ("s5z3c2", 0.5, 0.3, 0.2),
           ("s4z3c3", 0.4, 0.3, 0.3), ("s6c4", 0.6, 0.0, 0.4), ("s7z3", 0.7, 0.3, 0.0),
           ("carry", 0.0, 0.0, 1.0)]
KS = (150, 250, 400)
fx2526 = yrs >= 2025
out = {}
for wnm, w1, w2, w3 in WCOMBOS:
    for K in KS:
        Wt = np.zeros((nA, NW), np.float32); okA = np.zeros(nA, bool)
        for i in range(nA):
            j = pw_row.get(int(E_ts[i]))
            if j is None: continue
            m = members[i]
            s1 = xz(STACK[i, m])
            z = np.zeros(len(m))
            for k, sg in (("f_vol_7d", -1), ("f_range_24h", -1), ("f_mom_7d", -1), ("f_fund_ema", +1)):
                z += sg * np.nan_to_num(xz(F6[k][j, m]))
            s2_ = xz(z)
            s3_ = xz(-np.nan_to_num(FN[j, m], nan=0.0))
            sc = w1 * np.nan_to_num(s1) + w2 * np.nan_to_num(s2_) + w3 * np.nan_to_num(s3_)
            ok = np.isfinite(y4[i, m])
            qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
            g1 = qv4h >= 2.5e5
            sel = ok & g1
            if sel.sum() < 80: continue
            if sel.sum() > K:
                ord_ = np.argsort(-qv4h)
                kk = np.zeros(len(m), bool); cnt = 0
                for idx in ord_:
                    if sel[idx]: kk[idx] = True; cnt += 1
                    if cnt >= K: break
                sel = kk
            w = np.where(sel, sc, 0.0)
            w = w - w[sel].mean()
            g = np.abs(w).sum()
            if g < 1e-9: continue
            w = w / g
            capw = CAP_MULT / max(sel.sum(), 1)
            w = np.clip(w, -capw, capw)
            g2 = np.abs(w).sum()
            if g2 > 1e-9: w = w / g2
            Wt[i, m] = w; okA[i] = True
        H = np.zeros(NW, np.float64)
        rets, carrys, cb_, cc_, tos = [], [], [], [], []
        subm = []
        for i in range(nA):
            if not okA[i]: continue
            tgt = Wt[i].astype(np.float64)
            sm = H + AL * (tgt - H)
            trade = sm - H
            sm = np.where(np.abs(trade) < BD, H, sm)
            trade = sm - H
            j = pw_row[int(E_ts[i])]
            m = members[i]
            qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
            tr = tier_of(qv4h); tabs = np.abs(trade[m])
            cb = cc = 0.0
            for tt in range(3):
                s_ = tr == tt
                mk, tk, fr = COST["b"][tt]; cb += tabs[s_].sum() * (fr * mk + (1 - fr) * tk)
                mk, tk, fr = COST["c"][tt]; cc += tabs[s_].sum() * (fr * mk + (1 - fr) * tk)
            yv = np.nan_to_num(y4[i, m], nan=0.0)
            rets.append(float((sm[m] * yv).sum() * 1e4))
            fnow = np.nan_to_num(FN[j, m], nan=0.0)
            carrys.append(float(-(sm[m] * fnow).sum() / 2 * 1e4))
            cb_.append(cb); cc_.append(cc); tos.append(float(tabs.sum()))
            subm.append(bool(fx2526[i]))
            H = sm
        rets = np.array(rets); carrys = np.array(carrys)
        cb_ = np.array(cb_); cc_ = np.array(cc_); sub = np.array(subm)
        for scen, cost_arr in (("b", cb_), ("c", cc_)):
            net = rets + carrys - cost_arr
            n25 = net[sub]
            sh = float(n25.mean() / (n25.std() + 1e-12) * np.sqrt(6 * 365))
            rec = {"net": round(float(n25.mean()), 3), "sharpe": round(sh, 2),
                   "gross": round(float(rets[sub].mean()), 3), "carry": round(float(carrys[sub].mean()), 3),
                   "cost": round(float(cost_arr[sub].mean()), 3), "to": round(float(np.array(tos)[sub].mean()), 4)}
            out[f"{wnm}_K{K}_{scen}"] = rec
            print(f"[{wnm} K{K} {scen}] 毛{rec['gross']} carry{rec['carry']} 成本{rec['cost']} => 净{rec['net']} 夏普{rec['sharpe']} 换手{rec['to']}", flush=True)
json.dump(out, open("/workspace/replay_wide_v3.json", "w"), indent=1)
best_b = max((k for k in out if k.endswith("_b")), key=lambda k: out[k]["sharpe"])
print(f"最优(b): {best_b} 夏普 {out[best_b]['sharpe']}", flush=True)
print("REPLAY3_DONE", flush=True)
