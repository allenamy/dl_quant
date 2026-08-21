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
# ── A: regime 四态分解 + 门控变体 ──
bv = BVOL[[pw_row[int(E_ts[i])] for i in XI]]
bm = BMOM[[pw_row[int(E_ts[i])] for i in XI]]
vol_hi = bv >= np.nanmedian(bv); mom_up = bm >= 0
print("A regime 四态(BTC波动×趋势):", flush=True)
for vl, vname in ((True, "高波"), (False, "低波")):
    for ml, mname in ((True, "涨"), (False, "跌")):
        s_ = (vol_hi == vl) & (mom_up == ml)
        x = X[s_]
        print(f"  [{vname}{mname}] n{ s_.sum()} 夏普 {x.mean()/(x.std()+1e-12)*math.sqrt(6*365):.2f} 净{x.mean():.3f}", flush=True)
worst = min([(X[(vol_hi==vl)&(mom_up==ml)].mean()/(X[(vol_hi==vl)&(mom_up==ml)].std()+1e-12)) for vl in (0,1) for ml in (0,1)])
gate = ~((vol_hi == True) & (mom_up == False))
xg = np.where(gate, X, X * 0.5)
shg = float(xg.mean() / (xg.std() + 1e-12) * math.sqrt(6 * 365))
print(f"A 门控变体(最差态减半gross): 夏普 {shg:.2f} vs 基底 {sh:.2f} ⇒ {'有益' if shg > sh + 0.1 else '无益(择时死先验维持)'}", flush=True)
# ── B: 复活复核(延迟口径, 逐年) ──
print("B 复活复核(rev24 因子 IC, 延迟口径):", flush=True)
for year in (2024, 2025, 2026):
    for tlab, K in (("liq110", 110), ("wide400", 400)):
        v = []
        for i in range(0, nA, 4):
            if yrs[i] != year: continue
            j = pw_row.get(int(E_ts[i]))
            if j is None: continue
            m = members[i]
            qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
            ord_ = np.argsort(-qv4h)[:K]
            v.append(sp(-R24[j, m[ord_]], y4d[i, m[ord_]]))
        print(f"  [{year} {tlab}] {np.nanmean(v):+.4f}", flush=True)
# ── D: 统计意义 ──
T = len(X); sr_a = X.mean() / (X.std() + 1e-12)
g3 = float(((X - X.mean()) ** 3).mean() / X.std() ** 3)
g4 = float(((X - X.mean()) ** 4).mean() / X.std() ** 4)
bench = 1.46 / math.sqrt(6 * 365)
psr = 0.5 * (1 + math.erf(((sr_a - bench) * math.sqrt(T - 1)) / math.sqrt(max(1 - g3 * sr_a + (g4 - 1) / 4 * sr_a ** 2, 1e-9)) / math.sqrt(2)))
print(f"D 统计: n={T}锚 偏度{g3:.2f} 峰度{g4:.1f} | PSR(>在役1.46) = {psr:.4f}", flush=True)
NTR = 20
sd_tr = 0.3 / math.sqrt(6 * 365)
emax = sd_tr * ((1 - 0.5772) * math.sqrt(2 * math.log(NTR)) + 0.5772 * math.sqrt(2 * math.log(NTR * math.e)))
dsr = 0.5 * (1 + math.erf(((sr_a - bench - emax) * math.sqrt(T - 1)) / math.sqrt(max(1 - g3 * sr_a + (g4 - 1) / 4 * sr_a ** 2, 1e-9)) / math.sqrt(2)))
print(f"D DSR(20试验税后 vs 在役) = {dsr:.4f}", flush=True)
# ── E: 风险拆解 ──
cum = np.cumsum(X) / 1e4
peak = np.maximum.accumulate(cum)
dd = cum - peak
mdd = float(dd.min())
ddur = 0; cur = 0
for d in dd:
    cur = cur + 1 if d < 0 else 0
    ddur = max(ddur, cur)
daily = np.array([X[k:k+6].sum() for k in range(0, len(X) - 6, 6)])
var5 = float(np.percentile(daily, 5)); es5 = float(daily[daily <= var5].mean())
print(f"E 风险: MaxDD {mdd*100:.2f}%(毛敞口单位) 最长水下 {ddur}锚({ddur/6:.0f}天) 日VaR5 {var5:.1f}bps ES {es5:.1f}bps 最差日 {daily.min():.1f}bps", flush=True)
lev = 3
rng = np.random.default_rng(7)
touch = 0
for _ in range(2000):
    bs = rng.choice(daily, 365)
    c = np.cumsum(bs) * lev / 1e4
    p = np.maximum.accumulate(np.concatenate([[0], c]))[1:]
    if (c - p).min() < -0.25: touch += 1
print(f"E 3×杠杆下年触 −25% 停机线概率(日bootstrap) ≈ {touch/2000:.1%}", flush=True)
# ── F: 退市自适应 ──
del_hits = []
for k, i in enumerate(XI):
    e = E_rows[i]
    m = members[i]
    for mm in m:
        lf = LAST_FIN[mm]
        if e < lf <= e + 48 and abs(Wt[i, mm]) > 1e-4:
            del_hits.append((int(i), psyms[mm], float(Wt[i, mm])))
print(f"F 退市清点: 回放期书内持仓币在锚后4h内数据终结事件 {len(del_hits)} 次(样例 {del_hits[:5]})", flush=True)
print("FINAL_BATTERY_DONE", flush=True)
