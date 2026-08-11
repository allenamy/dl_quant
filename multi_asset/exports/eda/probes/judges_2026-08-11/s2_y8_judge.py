"""S-2 判官 · y8 原生 king @ 8h 持有 vs y4 king — 生产书装置配对(判官入库, y24 案家规)
==== 冻结判据(先于数字) ====
装置: 生产 3 腿书(deepsmooth 同源: compose→EMA α.05→带.002), king 8h 保持, 9821 锚;
唯一变量 = king 预测源: y8 复合(rb32_lam0_yr8_{s42,s2027}) vs y4 复合(gate1/rb32_lam0_yr4_s42_pod)。
两侧皆 5 折研究 OOS 复合(6头 z-rank 均值) —— 不与 prodfold newgen 混代(champion_dir 陷阱)。
判据: Δ净@4.137 日块CI95 下界>0 且 @6.23≥0 且逐年≥4/5 且夏普不降 —— 双 y8 种子【分别】给数,
同向才算候选(y8 s42 是模型级低离群 0.0458, 预写在案)。
口径声明: y8 训练面板=pm32_hz(与正典 corr 0.99999896), y4=正典 0731 —— 微差已声明;
绝对水平不代表生产(研究折复合 vs prodfold), 只读配对 Δ。"""
import sys, glob, json
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import numpy as np
from scipy.stats import rankdata
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
import legs as LG
import engine.replay_fullhist as RF

KREF = f"{PD}/king_pred_newgen.npz"
kref = np.load(KREF, allow_pickle=True)
NROW, NCOL = kref["king_pred"].shape
ARMS = {"y8_s42": f"{PD}/y8_seeds/rb32_lam0_yr8_s42",
        "y8_s2027": f"{PD}/y8_seeds/rb32_lam0_yr8_s2027",
        "y4_ctrl": f"{PD}/gate1/rb32_lam0_yr4_s42_pod"}

def zr_row(v):
    o = np.full_like(v, np.nan, np.float64); m = np.isfinite(v)
    if m.sum() < 20: return o
    r = rankdata(v[m]); o[m] = (r - r.mean()) / (r.std() + 1e-12); return o

def stitch(path):
    acc = np.full((NROW, NCOL), np.nan, np.float64)
    for f in sorted(glob.glob(f"{path}/fold_*_head_scores.npz")):
        d = np.load(f); sc, rows = d["scores"], d["te_rows"]
        keep = rows[rows < NROW]
        for i, rr in enumerate(keep):
            hz = np.stack([zr_row(sc[rr, :, h]) for h in range(sc.shape[2])])
            with np.errstate(all="ignore"):
                acc[rr] = np.nanmean(hz, 0)
    last = None; age = 99          # ffill ≤23 小时行: 补到全小时格, 由书装置在其锚点取样
    for i in range(NROW):
        if np.isfinite(acc[i]).any(): last = acc[i].copy(); age = 0
        elif last is not None and age < 23: acc[i] = last; age += 1
    return acc

panels = {}
cover = None
for name, path in ARMS.items():
    acc = stitch(path)
    fin = np.isfinite(acc).any(1)
    print(f"[{name}] 覆盖 {int(fin.sum())}", flush=True)
    if cover is None: cover = fin
    cover = cover & fin
for name in panels or ARMS:
    pass
for name, path in ARMS.items():
    acc = stitch(path); acc[~cover] = np.nan
    np.savez(f"/tmp/s2j_{name}.npz", king_pred=acc.astype(np.float32), ts=kref["ts"])
print(f"[共同覆盖] {int(cover.sum())} 行", flush=True)

W = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}; C1, C2 = 4.137, 6.23; ANN = np.sqrt(6*365); BW = 0.002

def book_run(king_path):
    RF._SRC, RF._SRC_KEY = None, None
    src = RF.get_src(None, king_path, f"{PD}/s2_pred_newgen.npz")
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
    return pnl, trn, yr

def boot(d, nb=3000, bl=5):
    rng = np.random.default_rng(99); L = len(d); k = int(np.ceil(L/bl)); o = np.empty(nb)
    for q in range(nb):
        st = rng.integers(0, max(L-bl, 1), size=k)
        ix = (st[:, None]+np.arange(bl)[None, :]).ravel()[:L]; ix = ix[ix < L]
        o[q] = d[ix].mean()
    return float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))

import pandas as pd
res = {}
p0, t0, yr = book_run("/tmp/s2j_y4_ctrl.npz"); n0 = p0-t0*C1
print(f"y4_ctrl 书: 毛 {p0.mean():+.3f} 换手 {t0.mean():.4f} 净 {n0.mean():+.3f} "
      f"夏普 {n0.mean()/n0.std(ddof=1)*ANN:+.2f}", flush=True)
for nm in ("y8_s42", "y8_s2027"):
    p, t, _ = book_run(f"/tmp/s2j_{nm}.npz")
    net = p-t*C1; d = net-n0; lo, hi = boot(d)
    d2 = (p-t*C2)-(p0-t0*C2)
    dfy = pd.DataFrame({"y": yr, "d": d}).groupby("y").d.mean()
    sh = net.mean()/net.std(ddof=1)*ANN; sh0 = n0.mean()/n0.std(ddof=1)*ANN
    ok_ = "★PASS" if (lo > 0 and d2.mean() >= 0 and (dfy >= 0).sum() >= 4 and sh >= sh0) else "fail"
    res[nm] = dict(net=round(net.mean(),4), dnet=round(d.mean(),4), ci=[round(lo,4),round(hi,4)],
                   yrs=int((dfy>=0).sum()), sharpe=round(sh,3),
                   by_year={str(k): round(v,3) for k,v in dfy.items()})
    print(f"{nm}: 净 {net.mean():+.3f} Δ {d.mean():+.4f} CI[{lo:+.4f},{hi:+.4f}] "
          f"逐年{int((dfy>=0).sum())}/5 夏普 {sh:+.2f} {ok_}", flush=True)
json.dump(res, open(f"{PD}/s2_y8_verdict.json", "w"), indent=1)
print("S2Y8_DONE")
