"""守卫红归因 @pod(2026-09-01): v3 replay 夏普 1.92 vs 带 2.42±0.15 → 两仪器对账。
① 逐字重算 v3 三腿收益序列(= pod_export_bundle_v3.py §② 同代码), 与八月 bundle leg_returns.npz 按 ts 对齐:
   逐腿 corr / mean Δ 分年 —— 分歧起点 = 归因方向(全史散开=装置口径; 尾部集中=窗口真实行情)。
② v1iv 书 replay 分年净/夏普(2024/2025/2026/08-15后子窗), 定位夏普 1.92 的构成。
只读, 不改任何判据。
"""
import json, time
import numpy as np
from scipy.stats import rankdata

MT = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True)
PRED = np.load("/workspace/shadow_bundle_v3/slow_pred_pinned.npy")
import os
PW = np.load(os.environ.get("RECON_PANEL", "/workspace/data/wide_panel_4h_v2ext.npz"), allow_pickle=True)
AUG = np.load("/workspace/aug_leg_returns.npz", allow_pickle=True)

E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]
nA = len(E_ts); NW = y4.shape[1]
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]; R24 = PW["f_rev_24h"]; FE = PW["f_fund_ema_v1"]

def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    n = ok.sum()
    if n >= 10: out[ok] = rankdata(v[ok]) / max(n - 1, 1) - 0.5
    return out

LR = {leg: [] for leg in ("king", "rev24", "fund")}
idx = []
for i in range(nA):
    j = pw_row.get(int(E_ts[i]))
    if j is None: continue
    m = members[i]
    sc = {"king": PRED[i, m], "rev24": -R24[j, m], "fund": FE[j, m]}
    ok = np.isfinite(y4[i, m])
    for leg in LR:
        z = np.nan_to_num(xz(sc[leg]))
        z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0
        g = np.abs(z).sum()
        LR[leg].append(float((z / g * np.nan_to_num(y4[i, m], nan=0.0)).sum() * 1e4) if g > 1e-9 else 0.0)
    idx.append(i)
LRa = {k: np.array(v) for k, v in LR.items()}
ts_v3 = E_ts[np.array(idx)]

# ── ① 与八月对齐 ──
a_ts = AUG["ts"].astype(np.int64)
a_row = {int(t): i for i, t in enumerate(a_ts)}
common = [(a_row[int(t)], p) for p, t in enumerate(ts_v3) if int(t) in a_row]
ia = np.array([c[0] for c in common]); iv3 = np.array([c[1] for c in common])
yrs_c = np.array([time.gmtime(int(t)).tm_year for t in ts_v3[iv3]])
print(f"对齐锚 {len(ia)} (八月 {len(a_ts)} / v3 {len(ts_v3)})", flush=True)
for leg in ("king", "rev24", "fund"):
    va = AUG[leg][ia]; vb = LRa[leg][iv3]
    c = float(np.corrcoef(va, vb)[0, 1])
    print(f"[{leg}] 全体 corr {c:.6f} meanΔ {float(np.mean(vb-va)):+.4f}", flush=True)
    for y in (2024, 2025, 2026):
        s = yrs_c == y
        if s.sum() < 50: continue
        cy = float(np.corrcoef(va[s], vb[s])[0, 1])
        print(f"   {y}: corr {cy:.6f} meanΔ {float(np.mean(vb[s]-va[s])):+.4f} |maxΔ| {float(np.abs(vb[s]-va[s]).max()):.3f}", flush=True)

# ── ② v1iv 书 replay 分年(逐字同导出装置) ──
pos = {int(i): p for p, i in enumerate(idx)}
def msharpe_w(i_pos):
    if i_pos < 900: return (1/3, 1/3, 1/3)
    sl = slice(i_pos - 900, i_pos)
    r = np.stack([LRa["king"][sl], LRa["rev24"][sl], LRa["fund"][sl]])
    shp = r.mean(1) / (r.std(1) + 1e-9); shp = np.maximum(shp, 0.0)
    return tuple(shp / shp.sum() if shp.sum() > 0 else np.array([1/3]*3))
COST_B = [(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)]
def tier_of(q):
    t = np.full(len(q), 2, np.int8); t[q >= 1e6] = 1; t[q >= 5e6] = 0
    return t
H = np.zeros(NW, np.float64); rec = []
for i in range(nA):
    j = pw_row.get(int(E_ts[i]))
    if j is None: continue
    m = members[i]
    sc = {"king": PRED[i, m], "rev24": -R24[j, m], "fund": FE[j, m]}
    wk, wr, wf = msharpe_w(pos.get(int(i), 0))
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
    tgt = np.zeros(NW); tgt[m] = w
    sm = H + 0.1 * (tgt - H)
    trade = sm - H
    sm = np.where(np.abs(trade) < 2.5e-4, H, sm)
    trade = sm - H
    trm = tier_of(qv4h); tabs = np.abs(trade[m])
    cb = sum(tabs[trm == tt].sum() * (fr * mk + (1 - fr) * tk) for tt, (mk, tk, fr) in enumerate(COST_B))
    yv = np.nan_to_num(y4[i, m], nan=0.0)
    fnow = np.nan_to_num(FN[j, m], nan=0.0)
    ivv = IV[j, m]; ivv = np.where(np.isfinite(ivv) & (ivv > 0), ivv, 8.0)
    car = (sm[m] * fnow * (4.0 / ivv)).sum() * 1e4
    net = float((sm[m] * yv).sum() * 1e4 - car - cb)
    rec.append((int(E_ts[i]), net, float((sm[m] * yv).sum() * 1e4), car, cb))
    H = sm
R = np.array([(t, n, g_, c_, b_) for t, n, g_, c_, b_ in rec])
yrsR = np.array([time.gmtime(int(t)).tm_year for t in R[:, 0]])
AN = 6 * 365
def line(tag, s):
    a = R[s]
    if len(a) < 30: print(f"{tag}: n<30", flush=True); return
    sh = a[:, 1].mean() / (a[:, 1].std() + 1e-12) * np.sqrt(AN)
    print(f"{tag}: n {len(a)} 净{a[:,1].mean():+.3f} 毛{a[:,2].mean():+.3f} carry{a[:,3].mean():+.3f} cost{a[:,4].mean():.3f} 夏普{sh:.2f}", flush=True)
line("2024", yrsR == 2024); line("2025", yrsR == 2025); line("2026", yrsR == 2026)
line("2024+全体", yrsR >= 2024)
cut = 1786752000  # 2026-08-15
line("2026≤08-15", (yrsR == 2026) & (R[:, 0] <= cut))
line("08-15后新尾", R[:, 0] > cut)
print("RECON_DONE", flush=True)
