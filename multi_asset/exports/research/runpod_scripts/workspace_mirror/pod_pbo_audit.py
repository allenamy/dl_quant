"""PBO/过拟合审计(用户令): 整形网格 α×b 的"最优格"CSCV 检验 + 通缩夏普.
方法: 慢书 5α×4b=20格, 存逐锚净额序列(2024-2026); CSCV: 12时间块, C(12,6)=924组合抽64,
IS选最优格→OOS排名分位; PBO = P(OOS排名<中位). 另报最优格通缩夏普(试验数=20).
"""
import json, time, itertools
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
SLOW = np.load("/workspace/exports_train/slow_lgbm_pred.npy")
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    n = ok.sum()
    if n >= 10: out[ok] = rankdata(v[ok]) / max(n - 1, 1) - 0.5
    return out
COST_B = [(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)]
def tier_of(q):
    t = np.full(len(q), 2, np.int8); t[q >= 1e6] = 1; t[q >= 5e6] = 0
    return t
Wt = np.zeros((nA, NW), np.float32); okA = np.zeros(nA, bool)
for i in range(nA):
    j = pw_row.get(int(E_ts[i]))
    if j is None: continue
    m = members[i]
    s = SLOW[i, m]
    ok = np.isfinite(s) & np.isfinite(y4[i, m])
    qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
    sel = ok & (qv4h >= 2.5e5)
    if sel.sum() < 80: continue
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
GRID = [(al, bd) for al in (1.0, 0.3, 0.2, 0.1, 0.05) for bd in (0.0, 1e-4, 2.5e-4, 5e-4)]
NETS = {}
idx_list = None
for al, bd in GRID:
    H = np.zeros(NW, np.float64)
    nets, idxs = [], []
    for i in range(nA):
        if not okA[i]: continue
        if yrs[i] < 2024:
            tgt = Wt[i].astype(np.float64)
            sm = H + al * (tgt - H); tr_ = sm - H
            H = np.where(np.abs(tr_) < bd, H, sm)
            continue
        tgt = Wt[i].astype(np.float64)
        sm = H + al * (tgt - H)
        trade = sm - H
        sm = np.where(np.abs(trade) < bd, H, sm)
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
        idxs.append(i)
        H = sm
    NETS[(al, bd)] = np.array(nets)
    if idx_list is None: idx_list = np.array(idxs)
n = len(idx_list)
blocks = np.array_split(np.arange(n), 12)
def sharpe(x):
    return float(x.mean() / (x.std() + 1e-12) * np.sqrt(6 * 365))
combos = list(itertools.combinations(range(12), 6))
rng = np.random.default_rng(7)
sel_combos = [combos[k] for k in rng.choice(len(combos), 64, replace=False)]
pbo_bad = 0; oos_ranks = []
for cset in sel_combos:
    is_idx = np.concatenate([blocks[b] for b in cset])
    oos_idx = np.concatenate([blocks[b] for b in range(12) if b not in cset])
    is_sh = {g: sharpe(NETS[g][is_idx]) for g in GRID}
    best = max(GRID, key=lambda g: is_sh[g])
    oos_sh = {g: sharpe(NETS[g][oos_idx]) for g in GRID}
    rank = sum(1 for g in GRID if oos_sh[g] < oos_sh[best]) / (len(GRID) - 1)
    oos_ranks.append(rank)
    if rank < 0.5: pbo_bad += 1
pbo = pbo_bad / len(sel_combos)
full_sh = {g: sharpe(NETS[g]) for g in GRID}
best_full = max(GRID, key=lambda g: full_sh[g])
sh_arr = np.array(list(full_sh.values()))
import math
N_tr = len(GRID)
emax = (1 - 0.5772) * 2 ** 0.5 * math.sqrt(2 * math.log(N_tr)) / math.sqrt(2 * math.log(N_tr)) if False else None
sh0 = float(np.sqrt(np.var(sh_arr)) * ((1 - 0.5772156649) * (2 * math.log(N_tr)) ** 0.5 + 0.5772156649 * (2 * math.log(N_tr * math.e)) ** 0.5 * 0 + (2 * math.log(N_tr)) ** 0.5 * 0))
sh0 = float(np.std(sh_arr) * (2 * math.log(N_tr)) ** 0.5)
T_obs = len(idx_list)
best_sh = full_sh[best_full]
dsr_z = (best_sh / math.sqrt(6*365) - sh0 / math.sqrt(6*365)) * math.sqrt(T_obs)
print(f"CSCV-PBO(慢书 20格, 64组合): PBO = {pbo:.2%} (判据 <50%, 良好<20%)", flush=True)
print(f"OOS排名分位 均值 {np.mean(oos_ranks):.2f}(1=最优)", flush=True)
print(f"全窗最优格 {best_full}: 夏普 {best_sh:.2f}; 试验数{N_tr}期望极值折让 {sh0:.2f} ⇒ 通缩后 ~{best_sh - sh0:.2f}", flush=True)
print(f"DSR z ≈ {dsr_z:.1f}", flush=True)
json.dump({"pbo": pbo, "oos_rank_mean": float(np.mean(oos_ranks)),
           "best": list(best_full), "best_sharpe": best_sh, "deflate": sh0}, open("/workspace/pbo_audit.json", "w"), indent=1)
print("PBO_AUDIT_DONE", flush=True)
