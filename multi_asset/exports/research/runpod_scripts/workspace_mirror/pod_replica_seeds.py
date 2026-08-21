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
FN = PW["f_fund_now"]; FE = PW["f_fund_ema"]; R24 = PW["f_rev_24h"]
KM = np.load("/workspace/exports_train/kcurve_meta_K400_s42.npz", allow_pickle=True)
k_ts = KM["E_ts"].astype(np.int64); k_yrs = KM["yrs"]; krow = {int(t): j for j, t in enumerate(k_ts)}
def load_king(sd):
    P = None
    for YV in (2023, 2024, 2025, 2026):
        try:
            p = np.load(f"/workspace/exports_train/kcurve_pred_K400_s{sd}_{YV}.npy")
        except FileNotFoundError:
            return None
        if P is None: P = np.full_like(p, np.nan)
        P[np.where(k_yrs == YV)[0]] = p[np.where(k_yrs == YV)[0]]
    return P
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    n = ok.sum()
    if n >= 10: out[ok] = rankdata(v[ok]) / max(n - 1, 1) - 0.5
    return out
COST_B = [(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)]
def tier_of(q):
    t = np.full(len(q), 2, np.int8); t[q >= 1e6] = 1; t[q >= 5e6] = 0
    return t
def run(KING, wk, wr, wf):
    Wt = np.zeros((nA, NW), np.float32); okA = np.zeros(nA, bool)
    for i in range(nA):
        j = pw_row.get(int(E_ts[i]))
        if j is None: continue
        jk = krow.get(int(E_ts[i]))
        if jk is None: continue
        m = members[i]
        kg = KING[jk, m]
        z = wk * np.nan_to_num(xz(kg)) + wr * np.nan_to_num(xz(-R24[j, m])) + wf * np.nan_to_num(xz(FE[j, m]))
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
    H = np.zeros(NW, np.float64)
    nets, subm = [], []
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
            mk, tk, fr = COST_B[tt]
            cb += tabs[s_].sum() * (fr * mk + (1 - fr) * tk)
        yv = np.nan_to_num(y4[i, m], nan=0.0)
        fnow = np.nan_to_num(FN[j, m], nan=0.0)
        nets.append(float((sm[m] * yv).sum() * 1e4 - (sm[m] * fnow).sum() / 2 * 1e4 - cb))
        subm.append(bool(yrs[i] >= 2025))
        H = sm
    nets = np.array(nets); sub = np.array(subm)
    n25 = nets[sub]
    return round(float(n25.mean()), 3), round(float(n25.mean() / (n25.std() + 1e-12) * np.sqrt(6 * 365)), 2)
res = {}
for sd in (42, 2027, 3037):
    K = load_king(sd)
    if K is None:
        print(f"seed {sd}: preds 缺(2027在jpline), 跳", flush=True); continue
    net, sh = run(K, 0.45, 0.35, 0.20)
    res[f"s{sd}"] = {"net": net, "sharpe": sh}
    print(f"[在役形K400 seed{sd}] 净{net} 夏普{sh}", flush=True)
K42 = load_king(42)
for tag, (wk, wr, wf) in {"w_kingup": (0.55, 0.28, 0.17), "w_revup": (0.35, 0.45, 0.20), "w_fundup": (0.40, 0.30, 0.30), "w_equal": (0.34, 0.33, 0.33)}.items():
    net, sh = run(K42, wk, wr, wf)
    res[tag] = {"net": net, "sharpe": sh}
    print(f"[{tag} {wk}/{wr}/{wf}] 净{net} 夏普{sh}", flush=True)
json.dump(res, open("/workspace/replica_seeds.json", "w"), indent=1)
print("REPLICA_SEEDS_DONE", flush=True)
