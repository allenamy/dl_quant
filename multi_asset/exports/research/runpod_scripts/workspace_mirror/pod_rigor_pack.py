"""严谨性补测包(用户四问): A 逐腿IC(lag)衰减+滚动IC轨迹; B 融合方式OOS对决(等权/逆波/滚动maxSharpe);
C 执行三轴单变量(波动目标化/逐腿整形/z-sizing). 基准=等权三腿K400 α0.1 b2.5e-4 情景b.
"""
import json, time
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from scipy.stats import rankdata, spearmanr
MT = np.load("/workspace/data/wide_fea_v1_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
nA = len(E_ts); NW = 829
PW = np.load("/workspace/data/wide_panel_4h_v1.npz", allow_pickle=True)
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
FN = PW["f_fund_now"]; FE = PW["f_fund_ema"]; R24 = PW["f_rev_24h"]
KM = np.load("/workspace/exports_train/kcurve_meta_K400_s42.npz", allow_pickle=True)
k_ts = KM["E_ts"].astype(np.int64); k_yrs = KM["yrs"]; krow = {int(t): j for j, t in enumerate(k_ts)}
KING = None
for YV in (2023, 2024, 2025, 2026):
    p = np.load(f"/workspace/exports_train/kcurve_pred_K400_s42_{YV}.npy")
    if KING is None: KING = np.full_like(p, np.nan)
    KING[np.where(k_yrs == YV)[0]] = p[np.where(k_yrs == YV)[0]]
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    n = ok.sum()
    if n >= 10: out[ok] = rankdata(v[ok]) / max(n - 1, 1) - 0.5
    return out
def leg_scores(i):
    j = pw_row.get(int(E_ts[i])); jk = krow.get(int(E_ts[i]))
    if j is None or jk is None: return None
    m = members[i]
    return {"king": KING[jk, m], "rev24": -R24[j, m], "fund": FE[j, m]}, m
# ── A: 逐腿 IC(lag) 衰减 + 滚动半年 IC ──
print("A① 逐腿 IC(lag): 因子在锚i vs y4在锚i+lag(alpha还能吃几锚)", flush=True)
for leg in ("king", "rev24", "fund"):
    row = []
    for lag in (0, 1, 2, 6, 12, 42):
        v = []
        for i in range(0, nA - 50, 4):
            if yrs[i] < 2024: continue
            ls = leg_scores(i)
            if ls is None: continue
            sc, m = ls
            v.append(sp(sc[leg], y4[i + lag, m]))
        row.append(round(float(np.nanmean(v)), 4))
    hl = "缓" if row[0] and abs(row[3]) > abs(row[0]) * 0.5 else "陡"
    print(f"  [{leg:>5s}] lag 0/1/2/6/12/42: {row} 衰减{hl}", flush=True)
print("A② 滚动半年 IC(edge 年轻度):", flush=True)
half_map = {}
for i in range(nA):
    t = time.gmtime(int(E_ts[i]))
    half_map.setdefault((t.tm_year, 1 if t.tm_mon <= 6 else 2), []).append(i)
for leg in ("king", "rev24", "fund"):
    parts = []
    for key in sorted(half_map):
        if key[0] < 2024: continue
        v = []
        for i in half_map[key][::3]:
            ls = leg_scores(i)
            if ls is None: continue
            sc, m = ls
            v.append(sp(sc[leg], y4[i, m]))
        parts.append(f"{key[0]}H{key[1]}:{np.nanmean(v):+.3f}")
    print(f"  [{leg:>5s}] " + " ".join(parts), flush=True)
# ── 书构造与回放公共件 ──
COST_B = [(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)]
def tier_of(q):
    t = np.full(len(q), 2, np.int8); t[q >= 1e6] = 1; t[q >= 5e6] = 0
    return t
def build_targets(weight_fn, sizing="rank"):
    Wt = np.zeros((nA, NW), np.float32); okA = np.zeros(nA, bool)
    for i in range(nA):
        ls = leg_scores(i)
        if ls is None: continue
        sc, m = ls
        wk, wr, wf = weight_fn(i)
        zk = xz(sc["king"]); zr = xz(sc["rev24"]); zf = xz(sc["fund"])
        if sizing == "z":
            def zval(v):
                ok = np.isfinite(v); out = np.zeros(len(v))
                if ok.sum() > 10:
                    mu, sd = np.nanmean(v[ok]), np.nanstd(v[ok]) + 1e-12
                    out[ok] = np.clip((v[ok] - mu) / sd, -3, 3)
                return out
            zk, zr, zf = zval(sc["king"]), zval(sc["rev24"]), zval(sc["fund"])
        z = wk * np.nan_to_num(zk) + wr * np.nan_to_num(zr) + wf * np.nan_to_num(zf)
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
    return Wt, okA
def replay(Wt, okA, vol_target=False):
    H = np.zeros(NW, np.float64)
    nets, subm = [], []
    rvbuf = []
    for i in range(nA):
        if not okA[i]: continue
        tgt = Wt[i].astype(np.float64)
        scale = 1.0
        if vol_target and len(rvbuf) >= 42:
            rv = np.std(rvbuf[-42:])
            scale = min(max(0.6, (np.std(rvbuf) + 1e-9) / (rv + 1e-9)), 1.6)
        sm = H + 0.1 * (tgt * scale - H)
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
        net = float((sm[m] * yv).sum() * 1e4 - (sm[m] * fnow).sum() / 2 * 1e4 - cb)
        nets.append(net); subm.append(bool(yrs[i] >= 2025))
        rvbuf.append(float((sm[m] * yv).sum() * 1e4))
        H = sm
    nets = np.array(nets); sub = np.array(subm)
    n25 = nets[sub]
    return round(float(n25.mean()), 3), round(float(n25.mean() / (n25.std() + 1e-12) * np.sqrt(6 * 365)), 2)
# ── B: 融合方式 OOS 对决 ──
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
lr_idx = np.array(lr_idx)
LR = {k: np.array(v) for k, v in LEG_RET.items()}
def wf_weights(mode, i_pos):
    look = 900
    if i_pos < look: return (1/3, 1/3, 1/3)
    sl = slice(i_pos - look, i_pos)
    r = np.stack([LR["king"][sl], LR["rev24"][sl], LR["fund"][sl]])
    if mode == "ivol":
        iv = 1 / (r.std(1) + 1e-9); w = iv / iv.sum()
    elif mode == "msharpe":
        shp = r.mean(1) / (r.std(1) + 1e-9); shp = np.maximum(shp, 0.0)
        w = shp / shp.sum() if shp.sum() > 0 else np.array([1/3]*3)
    return tuple(w)
pos_of = {int(i): p for p, i in enumerate(lr_idx)}
for mode in ("equal", "ivol", "msharpe"):
    if mode == "equal":
        fn = lambda i: (1/3, 1/3, 1/3)
    else:
        fn = lambda i, m=mode: wf_weights(m, pos_of.get(int(i), 0))
    Wt, okA = build_targets(fn)
    net, sh = replay(Wt, okA)
    print(f"B [{mode:>8s}] 净{net} 夏普{sh}", flush=True)
# ── C: 执行三轴 ──
Wt0, okA0 = build_targets(lambda i: (1/3, 1/3, 1/3))
net, sh = replay(Wt0, okA0, vol_target=True)
print(f"C [vol目标化] 净{net} 夏普{sh} (基准3.37)", flush=True)
Wtz, okAz = build_targets(lambda i: (1/3, 1/3, 1/3), sizing="z")
net, sh = replay(Wtz, okAz)
print(f"C [z-sizing ] 净{net} 夏普{sh} (基准=rank 3.37)", flush=True)
print("RIGOR_DONE", flush=True)
