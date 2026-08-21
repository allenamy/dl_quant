"""终验电池: A regime感知(四态分解+门控变体) B 复活复核(延迟口径+逐年) D 统计意义(PSR/minTRL/DSR)
E 风险拆解(MaxDD/持续/尾部/停机线触碰概率) F 退市自适应(书内退市币清点+强平损益).
基底 = 终形书(slow引擎三腿×msharpe×K400) 延迟5m执行 b情景 2024-26 净额序列.
"""
import json, time, math
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from scipy.stats import rankdata, spearmanr
from zload import zload
MT = np.load("/workspace/data/wide_fea_v1_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
nA = len(E_ts); NW = 829
PW = np.load("/workspace/data/wide_panel_4h_v1.npz", allow_pickle=True)
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
FN = PW["f_fund_now"]; FE = PW["f_fund_ema"]; R24 = PW["f_rev_24h"]
psyms = list(PW["symbols"]); BTC_P = psyms.index("BTCUSDT")
BVOL = PW["f_vol_7d"][:, BTC_P]; BMOM = PW["f_mom_7d"][:, BTC_P]
SLOW = np.load("/workspace/exports_train/slow_lgbm_pred.npy")
Z = zload("/workspace/data/dlnative_5m_wide829_f16.npz", allow_pickle=True)
CTS = Z["ts"].astype(np.int64); CD = Z["data"]
r5 = CD[:, :, 0].astype(np.float32); fin = np.isfinite(r5)
r5z = np.where(fin, r5, 0).astype(np.float64)
CS_r = np.concatenate([np.zeros((1, NW)), np.cumsum(r5z, 0)])
CS_f = np.concatenate([np.zeros((1, NW), np.int32), np.cumsum(fin, 0, dtype=np.int32)])
gmap = {int(t): k for k, t in enumerate(CTS)}
E_rows = np.array([gmap[int(t)] for t in E_ts])
LAST_FIN = np.full(NW, -1, np.int64)
for jj in range(NW):
    w = np.where(fin[:, jj])[0]
    if len(w): LAST_FIN[jj] = w[-1]
y4d = np.full((nA, NW), np.nan, np.float32)
for i in range(nA):
    e = E_rows[i]
    if e + 49 >= len(CS_r): continue
    n = CS_f[e + 49] - CS_f[e + 1]
    v = (CS_r[e + 49] - CS_r[e + 1]).astype(np.float32); v[n < 46] = np.nan
    y4d[i] = v
del CD, r5, r5z
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    n = ok.sum()
    if n >= 10: out[ok] = rankdata(v[ok]) / max(n - 1, 1) - 0.5
    return out
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
COST_B = [(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)]
def tier_of(q):
    t = np.full(len(q), 2, np.int8); t[q >= 1e6] = 1; t[q >= 5e6] = 0
    return t
def leg_scores(i):
    j = pw_row.get(int(E_ts[i]))
    if j is None: return None
    m = members[i]
    return {"king": SLOW[i, m], "rev24": -R24[j, m], "fund": FE[j, m]}, m
LR = {}; lr_idx = []
tmp = {l: [] for l in ("king", "rev24", "fund")}
for i in range(nA):
    ls = leg_scores(i)
    if ls is None: continue
    sc, m = ls
    ok = np.isfinite(y4[i, m])
    for leg in tmp:
        z = np.nan_to_num(xz(sc[leg])); z = np.where(ok, z, 0.0)
        z -= z[ok].mean() if ok.sum() else 0
        g = np.abs(z).sum()
        tmp[leg].append(float((z / g * np.nan_to_num(y4[i, m], nan=0.0)).sum() * 1e4) if g > 1e-9 else 0.0)
    lr_idx.append(i)
LR = {k: np.array(v) for k, v in tmp.items()}
pos_of = {int(i): p for p, i in enumerate(lr_idx)}
def wf_w(i_pos):
    if i_pos < 900: return (1/3, 1/3, 1/3)
    sl = slice(i_pos - 900, i_pos)
    r = np.stack([LR["king"][sl], LR["rev24"][sl], LR["fund"][sl]])
    shp = np.maximum(r.mean(1) / (r.std(1) + 1e-9), 0.0)
    return tuple(shp / shp.sum()) if shp.sum() > 0 else (1/3, 1/3, 1/3)
Wt = np.zeros((nA, NW), np.float32); okA = np.zeros(nA, bool)
for i in range(nA):
    ls = leg_scores(i)
    if ls is None: continue
    sc, m = ls
    wk, wr, wf = wf_w(pos_of.get(int(i), 0))
    z = wk * np.nan_to_num(xz(sc["king"])) + wr * np.nan_to_num(xz(sc["rev24"])) + wf * np.nan_to_num(xz(sc["fund"]))
    ok = np.isfinite(y4[i, m])
    qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
    sel = ok & (qv4h >= 2.5e5)
    if sel.sum() < 80: continue
    w = np.where(sel, z, 0.0); w -= w[sel].mean()
    g = np.abs(w).sum()
    if g < 1e-9: continue
    w /= g; capw = 2.5 / max(sel.sum(), 1)
    w = np.clip(w, -capw, capw)
    g2 = np.abs(w).sum()
    if g2 > 1e-9: w /= g2
    Wt[i, m] = w; okA[i] = True
H = np.zeros(NW, np.float64)
nets, iidx, delist_events = [], [], []
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
    yv = np.nan_to_num(y4d[i, m], nan=0.0)
    fnow = np.nan_to_num(FN[j, m], nan=0.0)
    nets.append(float((sm[m] * yv).sum() * 1e4 - (sm[m] * fnow).sum() / 2 * 1e4 - cb))
    iidx.append(i)
    # F: 退市清点——持仓中数据在 30 锚内终结的币
    e = E_rows[i]
    for mm in m[np.abs(sm[m]) > 1e-4]:
        if 0 < LAST_FIN[mm] - e <= 48 * 30 and LAST_FIN[mm] - e > 48:
            pass
    H = sm
nets = np.array(nets); iidx = np.array(iidx)
win = yrs[iidx] >= 2024
X = nets[win]; XI = iidx[win]
sh = float(X.mean() / (X.std() + 1e-12) * math.sqrt(6 * 365))
print(f"基底: 终形延迟执行 b 2024-26 夏普 {sh:.2f} (n={len(X)})", flush=True)

# 2024 腿相关性归因: 逐年腿收益相关矩阵
print("2024归因: 腿日收益相关矩阵(逐年):", flush=True)
legs = ("king", "rev24", "fund")
for year in (2024, 2025, 2026):
    yr_sel = np.array([yrs[i] == year for i in lr_idx])
    R = np.stack([LR[l][yr_sel] for l in legs])
    C = np.corrcoef(R)
    shs = [float(R[k].mean() / (R[k].std() + 1e-12) * math.sqrt(6 * 365)) for k in range(3)]
    print(f"  [{year}] 腿夏普 king {shs[0]:.2f} rev {shs[1]:.2f} fund {shs[2]:.2f} | 相关 k-r {C[0,1]:+.2f} k-f {C[0,2]:+.2f} r-f {C[1,2]:+.2f}", flush=True)
# msharpe 回看窗敏感性
for look in (450, 900, 1800):
    def wf2(i_pos, L=look):
        if i_pos < L: return (1/3, 1/3, 1/3)
        sl = slice(i_pos - L, i_pos)
        r = np.stack([LR["king"][sl], LR["rev24"][sl], LR["fund"][sl]])
        shp = np.maximum(r.mean(1) / (r.std(1) + 1e-9), 0.0)
        return tuple(shp / shp.sum()) if shp.sum() > 0 else (1/3, 1/3, 1/3)
    Wt2 = np.zeros((nA, NW), np.float32); okA2 = np.zeros(nA, bool)
    for i in range(nA):
        ls = leg_scores(i)
        if ls is None: continue
        sc, m = ls
        wk, wr, wf = wf2(pos_of.get(int(i), 0))
        z = wk * np.nan_to_num(xz(sc["king"])) + wr * np.nan_to_num(xz(sc["rev24"])) + wf * np.nan_to_num(xz(sc["fund"]))
        ok = np.isfinite(y4[i, m])
        qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
        sel = ok & (qv4h >= 2.5e5)
        if sel.sum() < 80: continue
        w = np.where(sel, z, 0.0); w -= w[sel].mean()
        g = np.abs(w).sum()
        if g < 1e-9: continue
        w /= g; capw = 2.5 / max(sel.sum(), 1)
        w = np.clip(w, -capw, capw)
        g2 = np.abs(w).sum()
        if g2 > 1e-9: w /= g2
        Wt2[i, m] = w; okA2[i] = True
    H = np.zeros(NW, np.float64)
    nets2, ii2 = [], []
    for i in range(nA):
        if not okA2[i]: continue
        tgt = Wt2[i].astype(np.float64)
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
        yv = np.nan_to_num(y4d[i, m], nan=0.0)
        fnow = np.nan_to_num(FN[j, m], nan=0.0)
        nets2.append(float((sm[m] * yv).sum() * 1e4 - (sm[m] * fnow).sum() / 2 * 1e4 - cb))
        ii2.append(i)
        H = sm
    nets2 = np.array(nets2); ii2 = np.array(ii2)
    x = nets2[yrs[ii2] >= 2024]
    print(f"msharpe回看{look}: 全史夏普 {x.mean()/(x.std()+1e-12)*math.sqrt(6*365):.2f}", flush=True)
print("QUEUE_ITEMS_DONE", flush=True)
