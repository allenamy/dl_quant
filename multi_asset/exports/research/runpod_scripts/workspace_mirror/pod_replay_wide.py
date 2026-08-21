"""P3 宽回放引擎 v1(设计冻结: DESIGN_wide_replay_P3_2026-08-16).
四打分器 × 双成本情景(b基准/c保守) × 换手网格(EMA α × 带 b), 分tier成本+成交率+funding carry.
单位: 毛敞口=1 的 bps/锚; 夏普=年化(6锚/日×365). 判据见设计稿 §5.
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
KM = np.load("/workspace/exports_train/kcurve_meta_K400_s42.npz", allow_pickle=True)
k_ts = KM["E_ts"].astype(np.int64); k_yrs = KM["yrs"]; krow = {int(t): j for j, t in enumerate(k_ts)}
def load_king():
    P = None
    for YV in (2023, 2024, 2025, 2026):
        p = np.load(f"/workspace/exports_train/kcurve_pred_K400_s42_{YV}.npy")
        if P is None: P = np.full_like(p, np.nan)
        P[np.where(k_yrs == YV)[0]] = p[np.where(k_yrs == YV)[0]]
    return P
KING = load_king()
STACK = np.load("/workspace/exports_train/bracketB_stack_pred.npy")
LGBM = np.load("/workspace/exports_train/bracketB_lgbm_pred.npy")
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    n = ok.sum()
    if n >= 10: out[ok] = rankdata(v[ok]) / max(n - 1, 1) - 0.5
    return out
# 打分器字典: 逐锚返回成员分数
def sc_stack(i, j, m): return STACK[i, m]
def sc_lgbm(i, j, m): return LGBM[i, m]
def sc_king(i, j, m):
    jk = krow.get(int(E_ts[i]))
    return KING[jk, m] if jk is not None else np.full(len(m), np.nan)
def sc_zooslow(i, j, m):
    z = np.zeros(len(m))
    for k, s in (("f_vol_7d", -1), ("f_range_24h", -1), ("f_mom_7d", -1), ("f_fund_ema", +1)):
        z += s * np.nan_to_num(xz(F6[k][j, m]))
    return z
SCORERS = {"stack83": sc_stack, "lgbm82": sc_lgbm, "king_seq": sc_king, "zoo_slow": sc_zooslow}
# tier: exp(qvk)≈单5m bar 均quote量 → ×48=4h量. T1≥$5M, T2 1-5M, T3<1M
def tier_of(qv4h):
    t = np.full(len(qv4h), 2, np.int8)
    t[qv4h >= 1e6] = 1
    t[qv4h >= 5e6] = 0
    return t
COST = {  # (maker成本bps/侧, taker回退bps/侧, fill率) per tier, 情景 b 基准 / c 保守
    "b": [( -0.25, 5.0, 0.85), (2.0, 6.0, 0.70), (3.0, 8.0, 0.50)],
    "c": [( 1.0,  6.0, 0.75), (4.0, 8.0, 0.55), (8.0, 10.0, 0.35)],
}
CAP_MULT = 2.5
ALPHAS = (0.03, 0.05, 0.1, 0.2, 1.0)
BANDS = (0.0, 0.001, 0.002)
fx2526 = yrs >= 2025
out = {}
for snm, fn in SCORERS.items():
    # 预算目标权重序列(打分与守门与整形无关, 先算)
    Wt = np.zeros((nA, NW), np.float32)
    okA = np.zeros(nA, bool)
    for i in range(nA):
        j = pw_row.get(int(E_ts[i]))
        if j is None: continue
        m = members[i]
        s = fn(i, j, m)
        ok = np.isfinite(s) & np.isfinite(y4[i, m])
        if ok.sum() < 100: continue
        qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
        g1 = qv4h >= 2.5e5
        sel = ok & g1
        if sel.sum() < 80: continue
        z = xz(np.where(sel, s, np.nan))
        w = np.nan_to_num(z)
        w = w - w[sel].mean()
        gross = np.abs(w).sum()
        if gross < 1e-9: continue
        w = w / gross
        capw = CAP_MULT / max(sel.sum(), 1)
        w = np.clip(w, -capw, capw)
        g2 = np.abs(w).sum()
        if g2 > 1e-9: w = w / g2
        Wt[i, m] = w
        okA[i] = True
    # 换手整形网格
    best = None
    for al in ALPHAS:
        for bd in BANDS:
            H = np.zeros(NW, np.float64)
            rets, carrys, costs_b, costs_c, tos = [], [], [], [], []
            for i in range(nA):
                if not okA[i]:
                    continue
                tgt = Wt[i].astype(np.float64)
                sm = H + al * (tgt - H)
                trade = sm - H
                small = np.abs(trade) < bd
                sm = np.where(small, H, sm)
                trade = sm - H
                j = pw_row[int(E_ts[i])]
                m = members[i]
                qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
                tr = tier_of(qv4h)
                tabs = np.abs(trade[m])
                cb = cc = 0.0
                for tt in range(3):
                    sel = tr == tt
                    mk, tk, fr = COST["b"][tt]
                    cb += tabs[sel].sum() * (fr * mk + (1 - fr) * tk)
                    mk, tk, fr = COST["c"][tt]
                    cc += tabs[sel].sum() * (fr * mk + (1 - fr) * tk)
                yv = np.nan_to_num(y4[i, m], nan=0.0)
                rets.append(float((sm[m] * yv).sum() * 1e4))
                fnow = np.nan_to_num(FN[j, m], nan=0.0)
                carrys.append(float(-(sm[m] * fnow).sum() / 2 * 1e4))
                costs_b.append(cb); costs_c.append(cc)
                tos.append(float(tabs.sum()))
                H = sm
            rets = np.array(rets); carrys = np.array(carrys)
            cb_ = np.array(costs_b); cc_ = np.array(costs_c); tos = np.array(tos)
            sub = np.array([fx2526[i] for i in range(nA) if okA[i]])
            for scen, cost_arr in (("b", cb_), ("c", cc_)):
                net = rets + carrys - cost_arr
                n25 = net[sub]
                sh = float(n25.mean() / (n25.std() + 1e-12) * np.sqrt(6 * 365))
                rec = {"alpha": al, "band": bd, "scen": scen,
                       "net_bps": round(float(n25.mean()), 3), "sharpe": round(sh, 2),
                       "gross_bps": round(float(rets[sub].mean()), 3),
                       "carry_bps": round(float(carrys[sub].mean()), 3),
                       "cost_bps": round(float(cost_arr[sub].mean()), 3),
                       "to": round(float(tos[sub].mean()), 4)}
                key = (snm, scen)
                if best is None: best = {}
                if key not in best or rec["sharpe"] > best[key]["sharpe"]:
                    best[key] = rec
    for (snm2, scen), rec in best.items():
        out[f"{snm2}_{scen}"] = rec
        print(f"[{snm2} 情景{scen}] α{rec['alpha']} b{rec['band']}: 毛{rec['gross_bps']} carry{rec['carry_bps']} "
              f"成本{rec['cost_bps']} => 净{rec['net_bps']}bps/锚 夏普{rec['sharpe']} 换手{rec['to']}", flush=True)
json.dump(out, open("/workspace/replay_wide_v1.json", "w"), indent=1)
print("REPLAY_DONE", flush=True)
