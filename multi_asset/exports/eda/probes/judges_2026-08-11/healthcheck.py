"""体检双仪器(诊断, 无采纳门, 口径全声明):
A. 当前在役栈(EMA.05+带.002)逐年绝对表: 净/夏普/换手/毛, 9821 锚 @4.137 与 @6.23
B. 因子衰减曲线: 5 折 walk-forward 的 OOS 逐月 IC 按【距训练截止月数】对齐平均
   (对象=y4 冠军臂 gate1/rb32_lam0_yr4_s42_pod, 6头z均值复合, member 内横截面 spearman)
   —— 若 IC 随月龄下降斜率显著为负 ⇒ 衰减是真的, 给出半衰期估计; 平 ⇒ 陈旧性不是主敌"""
import sys, glob, json
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import numpy as np, pandas as pd
from scipy.stats import rankdata, spearmanr
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
import legs as LG
import engine.replay_fullhist as RF

# ---- A. 在役栈逐年绝对 ----
W = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}; C1, C2 = 4.137, 6.23; ANN = np.sqrt(6*365); BW = 0.002
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N; n = len(a)
FI, RVI = src.fund_idx, src.ch.index("rvol_24h")
SYMS = [str(s) for s in src.symbols]
TGT, MSK, RET = [], [], []
held = {"k": np.full(N, np.nan), "s": np.full(N, np.nan), "f": np.full(N, np.nan)}
for i, t in enumerate(a):
    ti = int(t); m = np.asarray(src.tradeable(ti))
    if m.dtype == bool: m = np.where(m)[0]
    if i == 0 or ti % 8 == 0:
        v = np.full(N, np.nan); v[m] = src.king[ti, m]; held["k"] = v
    if i == 0 or ti % 24 == 0:
        v = np.full(N, np.nan); v[m] = src.s2[ti, m]; held["s"] = v
    if i == 0 or ti % 8 == 0:
        v = np.full(N, np.nan); v[m] = src.CH[ti, m, FI]; held["f"] = v
    r = LG.compose_book(held["k"][m], held["s"][m], held["f"][m], np.ones(len(m)),
                        weights=W, rvol=src.CH[ti, m, RVI].astype(float), risk_budget=RB)
    w = np.full(N, 0.0); w[m] = np.asarray(r["target_w"], float)
    TGT.append(w); MSK.append(m); RET.append(src.Y4[ti, m].astype(float))
state = None; prev = np.zeros(N)
pnl = np.zeros(n); trn = np.zeros(n)
for i in range(n):
    m = MSK[i]; syms = [SYMS[j] for j in m]
    out = LG.apply_harvest_ema(TGT[i][m], syms, state, 0.05)
    state = out["state"]
    tgt = np.asarray(out["target_w"], float)
    w = prev.copy(); w[[j for j in range(N) if j not in set(m)]] = 0.0
    delta = tgt - w[m]
    T = np.abs(delta) > BW
    wm = w[m].copy(); wm[T] = tgt[T]
    if T.any(): wm[T] -= wm.sum()/T.sum()
    w[m] = wm
    y = RET[i]; ok = np.isfinite(y)
    pnl[i] = float(np.nansum(w[m][ok]*y[ok]))*1e4
    trn[i] = float(np.abs(w-prev).sum()); prev = w
df = pd.DataFrame({"y": yr, "g": pnl, "t": trn})
df["n1"] = df.g - df.t*C1; df["n2"] = df.g - df.t*C2
print("A. 在役栈逐年绝对(9821 锚):")
for y, gdf in df.groupby("y"):
    sh = gdf.n1.mean()/gdf.n1.std(ddof=1)*ANN
    print(f"  {y}: 毛 {gdf.g.mean():+.3f} 换手 {gdf.t.mean():.4f} 净@4.137 {gdf.n1.mean():+.3f} "
          f"夏普 {sh:+.2f} 净@6.23 {gdf.n2.mean():+.3f} n={len(gdf)}")
sh_all = df.n1.mean()/df.n1.std(ddof=1)*ANN
print(f"  全期: 净 {df.n1.mean():+.3f} 夏普 {sh_all:+.2f} | 2026切片单独看上表")

# ---- B. 衰减曲线 ----
kref = np.load(f"{PD}/king_pred_newgen.npz", allow_pickle=True)
NROW, NCOL = kref["king_pred"].shape
P = np.load(f"{MA}/exports/wide_dl_full_corrfund_causal_0731.npz", allow_pickle=True)
Y4, MEM, ts = P["Y4"], P["MEMBER110"], P["ts"]
tss = ts//1000 if ts[1]-ts[0] >= 3600*1000 else ts
def zr_row(v):
    o = np.full_like(v, np.nan, np.float64); m = np.isfinite(v)
    if m.sum() < 20: return o
    r = rankdata(v[m]); o[m] = (r - r.mean()) / (r.std() + 1e-12); return o
decay = {}
for f in sorted(glob.glob(f"{PD}/gate1/rb32_lam0_yr4_s42_pod/fold_*_head_scores.npz")):
    d = np.load(f); sc, rows = d["scores"], d["te_rows"]
    keep = rows[rows < NROW]
    t0 = tss[keep.min()]                       # 该折测试起点 ≈ 训练截止
    for rr in keep:
        m = np.isfinite(sc[rr, :, 0]) & MEM[rr].astype(bool) & np.isfinite(Y4[rr])
        if m.sum() < 30: continue
        hz = np.stack([zr_row(sc[rr, :, h]) for h in range(sc.shape[2])])
        with np.errstate(all="ignore"):
            comp = np.nanmean(hz, 0)
        mm = m & np.isfinite(comp)
        if mm.sum() < 30: continue
        ic = spearmanr(comp[mm], Y4[rr][mm]).statistic
        mo = int((tss[rr] - t0) // (30*86400))
        decay.setdefault(mo, []).append(ic)
print("\nB. 衰减曲线: OOS IC vs 距训练截止月数(5 折对齐平均, y4 冠军臂):")
xs, ys, ns = [], [], []
for mo in sorted(decay):
    v = np.array(decay[mo])
    if len(v) < 100: continue
    xs.append(mo); ys.append(float(v.mean())); ns.append(len(v))
    print(f"  月{mo:2d}: IC {v.mean():+.4f} (se {v.std(ddof=1)/np.sqrt(len(v)):.4f}, n={len(v)})")
if len(xs) >= 4:
    sl, b0 = np.polyfit(xs, ys, 1)
    print(f"  线性斜率 {sl:+.5f}/月 (起点 {b0:.4f}) ⇒ "
          f"{'半衰期 ≈ %.0f 月' % (b0/(-2*sl)) if sl < 0 else '无衰减(斜率非负)'}")
json.dump({"by_year": {str(y): dict(net=round(g.n1.mean(),4),
           sharpe=round(g.n1.mean()/g.n1.std(ddof=1)*ANN,3)) for y,g in df.groupby('y')},
           "decay": {str(k): round(float(np.mean(v)),4) for k,v in sorted(decay.items()) if len(v)>=100}},
          open(f"{PD}/healthcheck.json", "w"), indent=1)
print("HEALTHCHECK_DONE")
