"""挑战电池(用户质疑 4.3 过高): A 延迟一根5m执行(杀反弹伪影) B 全史窗+NW年化+净额自相关
C 未成交=丢仓位下界 D rev腿分层定位(反弹诊断). 终形=slow引擎三腿×msharpe×K400.
"""
import json, time
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from scipy.stats import rankdata
from zload import zload
MT = np.load("/workspace/data/wide_fea_v1_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
nA = len(E_ts); NW = 829
PW = np.load("/workspace/data/wide_panel_4h_v1.npz", allow_pickle=True)
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
FN = PW["f_fund_now"]; FE = PW["f_fund_ema"]; R24 = PW["f_rev_24h"]
SLOW = np.load("/workspace/exports_train/slow_lgbm_pred.npy")
# 延迟执行目标: y4_delay = 缓存重算 [e+1, e+49) 的 48bar 和(晚一根 5m 入场)
Z = zload("/workspace/data/dlnative_5m_wide829_f16.npz", allow_pickle=True)
CTS = Z["ts"].astype(np.int64); CD = Z["data"]
r5 = CD[:, :, 0].astype(np.float32)
fin = np.isfinite(r5)
r5z = np.where(fin, r5, 0).astype(np.float64)
CS_r = np.concatenate([np.zeros((1, NW)), np.cumsum(r5z, 0)])
CS_f = np.concatenate([np.zeros((1, NW), np.int32), np.cumsum(fin, 0, dtype=np.int32)])
gmap = {int(t): k for k, t in enumerate(CTS)}
E_rows = np.array([gmap[int(t)] for t in E_ts])
y4d = np.full((nA, NW), np.nan, np.float32)
for i in range(nA):
    e = E_rows[i]
    if e + 49 >= len(CS_r): continue
    n = CS_f[e + 49] - CS_f[e + 1]
    v = (CS_r[e + 49] - CS_r[e + 1]).astype(np.float32)
    v[n < 46] = np.nan
    y4d[i] = v
del CD, r5, r5z, fin, CS_r, CS_f
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
    return {"king": SLOW[i, m], "rev24": -R24[j, m], "fund": FE[j, m]}, m
LEG_RET = {leg: [] for leg in ("king", "rev24", "fund")}
lr_idx = []
for i in range(nA):
    ls = leg_scores(i)
    if ls is None: continue
    sc, m = ls
    ok = np.isfinite(y4[i, m])
    for leg in LEG_RET:
        z = np.nan_to_num(xz(sc[leg]))
        z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0
        g = np.abs(z).sum()
        LEG_RET[leg].append(float((z / g * np.nan_to_num(y4[i, m], nan=0.0)).sum() * 1e4) if g > 1e-9 else 0.0)
    lr_idx.append(i)
LR = {k: np.array(v) for k, v in LEG_RET.items()}
pos_of = {int(i): p for p, i in enumerate(lr_idx)}
def wf_w(i_pos):
    if i_pos < 900: return (1/3, 1/3, 1/3)
    sl = slice(i_pos - 900, i_pos)
    r = np.stack([LR["king"][sl], LR["rev24"][sl], LR["fund"][sl]])
    shp = r.mean(1) / (r.std(1) + 1e-9); shp = np.maximum(shp, 0.0)
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
    w /= g
    capw = 2.5 / max(sel.sum(), 1)
    w = np.clip(w, -capw, capw)
    g2 = np.abs(w).sum()
    if g2 > 1e-9: w /= g2
    Wt[i, m] = w; okA[i] = True
def replay(Ymat, scen, lost_alpha=False):
    H = np.zeros(NW, np.float64)
    nets, iidx = [], []
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
        eff = sm.copy()
        for tt in range(3):
            s_ = tr == tt
            mk, tk, fr = COST[scen][tt]
            if lost_alpha:
                cb += tabs[s_].sum() * (fr * mk)
                mcol = m[s_]
                eff[mcol] = H[mcol] + fr * (sm[mcol] - H[mcol])
            else:
                cb += tabs[s_].sum() * (fr * mk + (1 - fr) * tk)
        pos_use = eff if lost_alpha else sm
        yv = np.nan_to_num(Ymat[i, m], nan=0.0)
        fnow = np.nan_to_num(FN[j, m], nan=0.0)
        nets.append(float((pos_use[m] * yv).sum() * 1e4 - (pos_use[m] * fnow).sum() / 2 * 1e4 - cb))
        iidx.append(i)
        H = pos_use if lost_alpha else sm
    return np.array(nets), np.array(iidx)
def report(nets, iidx, tag):
    for win, lab in ((yrs[iidx] >= 2025, "2025-26"), (yrs[iidx] >= 2024, "2024-26")):
        x = nets[win]
        sh = float(x.mean() / (x.std() + 1e-12) * np.sqrt(6 * 365))
        ac1 = float(np.corrcoef(x[:-1], x[1:])[0, 1])
        nw = sh / np.sqrt(max(1 + 2 * ac1, 0.2))
        print(f"[{tag} {lab}] 夏普 {sh:.2f} | 净额自相关lag1 {ac1:+.3f} | NW校正夏普 {nw:.2f}", flush=True)
n0, i0 = replay(y4, "b")
report(n0, i0, "A0 基线(锚执行)b")
n1, i1 = replay(y4d, "b")
report(n1, i1, "A1 延迟5m执行 b")
n1c, i1c = replay(y4d, "c")
report(n1c, i1c, "A1 延迟5m c")
n2, i2 = replay(y4d, "c", lost_alpha=True)
report(n2, i2, "C 延迟+未成交丢仓 c(下界)")
# D: rev 腿分层(反弹定位): rev-only 书在 T1 vs T2/T3 子集
print("D rev24 单腿 IC 分层(反弹诊断, 延迟前后):", flush=True)
for lab, Ym in (("锚执行", y4), ("延迟5m", y4d)):
    for tlab, lo, hi in (("T1(>=5M)", 5e6, 1e18), ("T2/3(<5M)", 0, 5e6)):
        v = []
        for i in range(0, nA, 4):
            if yrs[i] < 2024: continue
            ls = leg_scores(i)
            if ls is None: continue
            sc, m = ls
            qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
            sel = (qv4h >= lo) & (qv4h < hi) & np.isfinite(Ym[i, m]) & np.isfinite(sc["rev24"])
            if sel.sum() < 30: continue
            from scipy.stats import spearmanr
            r = spearmanr(sc["rev24"][sel], Ym[i, m][sel])
            v.append(r.correlation if hasattr(r, "correlation") else r[0])
        print(f"  [{lab} {tlab}] rev24 IC {np.nanmean(v):+.4f}", flush=True)
print("CHALLENGE_DONE", flush=True)
