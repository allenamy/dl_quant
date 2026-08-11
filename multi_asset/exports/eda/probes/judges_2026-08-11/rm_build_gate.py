"""实现矩通道 RM1-5 构建 + G1 同款门 (PREREG 34165637 冻结)
构建: 5m close → 24h 窗方向性矩; 整点采样 shift(1)(≤t−5m); 输出临时 npz 后立即进同一门装置。
门与对齐: 复用 w4_gate1 v3 逻辑(+1h 墙钟映射 + 偏移谱红断言)。"""
import os, sys, glob, zipfile, io
import numpy as np, pandas as pd
from concurrent.futures import ProcessPoolExecutor
M = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
OUT = f"{M}/rm_channels_v1.npz"
T0, T1 = pd.Timestamp("2022-01-01"), pd.Timestamp("2026-08-10")
HGRID = pd.date_range(T0, T1, freq="1h")
def read_zip_csv(path):
    try:
        with zipfile.ZipFile(path) as z:
            raw = z.read(z.namelist()[0])
        first = raw[:60].decode("utf-8", "ignore")
        return pd.read_csv(io.BytesIO(raw), header=0 if first[0].isalpha() else None)
    except Exception:
        return None
def build(sym):
    kdir = f"{M}/w4_klines5m/{sym}"
    if not os.path.isdir(kdir): return sym, None
    kls = []
    for f in sorted(glob.glob(f"{kdir}/*.zip")):
        d = read_zip_csv(f)
        if d is None or len(d) == 0: continue
        d = d.iloc[:, :5]; d.columns = ["open_time", "o", "h", "l", "c"]
        kls.append(d[["open_time", "c"]])
    if not kls: return sym, None
    kk = pd.concat(kls)
    kk["ts"] = pd.to_datetime(kk.open_time.astype(np.int64), unit="ms") + pd.Timedelta("5min")
    kk = kk.drop_duplicates("ts").set_index("ts").sort_index()
    idx = pd.date_range(kk.index[0], kk.index[-1], freq="5min")
    c = kk.c.reindex(idx)
    r = c.pct_change(fill_method=None)
    r2 = r**2
    sig = r.rolling(288, min_periods=100).std()
    dn2 = r2.where(r < 0, 0.0); up2 = r2.where(r > 0, 0.0)
    s_dn = dn2.rolling(288, min_periods=100).sum(); s_all = r2.rolling(288, min_periods=100).sum()
    F = pd.DataFrame(index=idx)
    F["rm1"] = s_dn/(s_all+1e-12) - 0.5
    mx_up = r.clip(lower=0).rolling(288, min_periods=100).max()
    mx_dn = (-r.clip(upper=0)).rolling(288, min_periods=100).max()
    F["rm2"] = (mx_up - mx_dn)/(sig+1e-12)
    bigdn = (r < -4*sig)
    last = pd.Series(idx.where(bigdn), index=idx).ffill()
    F["rm3"] = ((idx.to_series() - last).dt.total_seconds()/3600).clip(upper=24).fillna(24)
    jump = r2.where(r.abs() > 4*sig, 0.0)
    F["rm4"] = jump.rolling(288, min_periods=100).sum()/(s_all+1e-12)
    q95 = r.abs().rolling(288, min_periods=100).quantile(0.95)
    med = r.abs().rolling(288, min_periods=100).median()
    F["rm5"] = q95/(med+1e-12)
    return sym, F.shift(1).reindex(HGRID).to_numpy(dtype=np.float32)
syms = sorted(os.listdir(f"{M}/w4_klines5m"))
res = {}
with ProcessPoolExecutor(max_workers=8) as ex:
    for i, (s, arr) in enumerate(ex.map(build, syms)):
        res[s] = arr
        if (i+1) % 30 == 0: print(f"{i+1}/{len(syms)}", flush=True)
good = [s for s in syms if res.get(s) is not None]
np.savez_compressed(OUT, ts=HGRID.astype("int64")//10**9, symbols=np.array(good),
                    feats=np.array(["rm1", "rm2", "rm3", "rm4", "rm5"]),
                    data=np.stack([res[s] for s in good], axis=1))
print(f"built {OUT} n={len(good)}", flush=True)
# ── 门(w4_gate1 v3 同逻辑) ──
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
from scipy.stats import rankdata, spearmanr
import legs as LG
import engine.replay_fullhist as RF
WB = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}; C1, C2 = 4.137, 6.23; ANN = np.sqrt(6*365)
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N; n = len(a)
FI, RVI = src.fund_idx, src.ch.index("rvol_24h")
SYMS = [str(s) for s in src.symbols]
Z = np.load(OUT, allow_pickle=True)
zts = Z["ts"]; zsyms = list(Z["symbols"]); zfeats = list(Z["feats"]); zd = Z["data"]
ts2row = {int(t): i for i, t in enumerate(zts)}
sym2col = {s: j for j, s in enumerate(zsyms)}
col_of = np.array([sym2col.get(s, -1) for s in SYMS])
anchor_epoch = (src.ts[np.asarray(a, dtype=np.int64)] // 1000 + 3600).astype(np.int64)
rows = np.array([ts2row.get(int(e), -1) for e in anchor_epoch])
assert (rows >= 0).mean() > 0.95, f"映射命中 {(rows>=0).mean():.1%}"
def feat_panel(fi):
    X = np.full((n, N), np.nan, dtype=np.float32)
    ok = (rows >= 0)[:, None] & (col_of >= 0)[None, :]
    X[:] = zd[np.where(rows >= 0, rows, 0)][:, np.where(col_of >= 0, col_of, 0), fi]
    X[~ok] = np.nan
    return X
def madz(X):
    df = pd.DataFrame(X)
    med = df.rolling(180, min_periods=60).median().shift(1)
    mad = (df - med).abs().rolling(180, min_periods=60).median().shift(1)
    return ((df - med)/(1.4826*mad + 1e-12)).clip(-3, 3).to_numpy()
CAND = {f"RM{k+1}": madz(feat_panel(k)) for k in range(5)}
RAW1 = feat_panel(0)
held = {"k": np.full(N, np.nan), "s": np.full(N, np.nan), "f": np.full(N, np.nan)}
COMP, MSK, RET, RV, KL, SL, FL, RVOL = [], [], [], [], [], [], [], []
for i, t in enumerate(a):
    ti = int(t); m = np.asarray(src.tradeable(ti))
    if m.dtype == bool: m = np.where(m)[0]
    if i == 0 or ti % 8 == 0:
        v = np.full(N, np.nan); v[m] = src.king[ti, m]; held["k"] = v.copy()
    if i == 0 or ti % 24 == 0:
        v = np.full(N, np.nan); v[m] = src.s2[ti, m]; held["s"] = v.copy()
    if i == 0 or ti % 8 == 0:
        v = np.full(N, np.nan); v[m] = src.CH[ti, m, FI]; held["f"] = v.copy()
    rv = src.CH[ti, m, RVI].astype(float)
    r = LG.compose_book(held["k"][m], held["s"][m], held["f"][m], np.ones(len(m)),
                        weights=WB, rvol=rv, risk_budget=RB)
    w = np.full(N, np.nan); w[m] = np.asarray(r["target_w"], float)
    rvw = np.full(N, np.nan); rvw[m] = rv
    COMP.append(w); MSK.append(m); RET.append(src.Y4[ti, m].astype(float)); RV.append(rv)
    KL.append(held["k"].copy()); SL.append(held["s"].copy()); FL.append(held["f"].copy()); RVOL.append(rvw)
def xz(v):
    ok = np.isfinite(v)
    if ok.sum() < 10: return v
    r_ = np.full_like(v, np.nan)
    r_[ok] = (rankdata(v[ok]) - (ok.sum()+1)/2)/max(ok.sum()-1, 1)
    return r_
def spear(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    return spearmanr(x[ok], y[ok]).correlation if ok.sum() >= 10 else np.nan
yrs = np.array(yr)
DELTAS = [-0.2, -0.1, -0.05, 0.05, 0.1, 0.2]
print("== S1 筛 ==", flush=True)
survivors = []
for nm, Xz in CAND.items():
    ic_gain = np.full((n, len(DELTAS)), np.nan); cors = []; rvcors = []
    for i in range(n):
        m = MSK[i]; y = RET[i]
        cz = xz(COMP[i][m]); fz = Xz[i][m]
        b = spear(cz, y)
        for j, d in enumerate(DELTAS):
            ic_gain[i, j] = spear(cz + d*np.nan_to_num(fz), y) - b
        ok = np.isfinite(fz)
        if ok.sum() > 20:
            for L, tag in ((KL[i][m], "k"), (SL[i][m], "s"), (FL[i][m], "f")):
                okk = ok & np.isfinite(L)
                if okk.sum() > 20: cors.append((tag, np.corrcoef(fz[okk], L[okk])[0, 1]))
            okr = ok & np.isfinite(RVOL[i][m])
            if okr.sum() > 20: rvcors.append(np.corrcoef(fz[okr], RVOL[i][m][okr])[0, 1])
    gains = []
    for Y in (2023, 2024, 2025, 2026):
        tr = yrs < Y; te = yrs == Y
        jstar = int(np.nanargmax(np.nanmean(ic_gain[tr], axis=0)))
        gains.append((Y, DELTAS[jstar], float(np.nanmean(ic_gain[te, jstar]))))
    avg = float(np.mean([g[2] for g in gains])); allpos = all(g[2] >= 0 for g in gains)
    cdf = pd.DataFrame(cors, columns=["leg", "c"]).groupby("leg").c.mean()
    maxc = float(cdf.abs().max()) if len(cdf) else 0.0
    rvc = float(np.nanmean(rvcors)) if rvcors else np.nan
    passed = avg >= 0.003 and allpos and maxc < 0.6
    print(f"  {nm}: 平均Δic {avg:+.4f} 逐年{[(g[0],g[1],round(g[2],4)) for g in gains]} "
          f"maxLegCorr {maxc:+.2f} rvolCorr {rvc:+.2f} {'★过筛' if passed else 'fail'}", flush=True)
    if passed: survivors.append((nm, Xz, gains))
print(f"\n== S2 净(幸存者 {len(survivors)}) ==", flush=True)
def run_book(extra=None, w4=0.0):
    state = None; prev = np.zeros(N)
    pnl = np.zeros(n); trn = np.zeros(n)
    for i in range(n):
        m = MSK[i]
        if extra is None:
            tgt0 = COMP[i][m]
        else:
            sc = 1 - w4
            W_ = {"king": WB["king"]*sc, "s2": WB["s2"]*sc, "funding": WB["funding"]*sc, "size": w4}
            r = LG.compose_book(KL[i][m], SL[i][m], FL[i][m], np.nan_to_num(extra[i][m]),
                                weights=W_, rvol=RV[i], risk_budget=RB)
            tgt0 = np.asarray(r["target_w"], float)
        out = LG.apply_harvest_ema(tgt0, [SYMS[j] for j in m], state, 0.05)
        state = out["state"]; tgt = np.asarray(out["target_w"], float)
        w = prev.copy(); w[[j for j in range(N) if j not in set(m)]] = 0.0
        delta = tgt - w[m]; T = np.abs(delta) > 0.002
        wm = w[m].copy(); wm[T] = tgt[T]
        if T.any(): wm[T] -= wm.sum()/T.sum()
        w[m] = wm
        y = RET[i]; ok = np.isfinite(y)
        pnl[i] = float(np.nansum(w[m][ok]*y[ok]))*1e4
        trn[i] = float(np.abs(w-prev).sum()); prev = w
    return pnl, trn
def boot(d, nb=2000, bl=5):
    rng = np.random.default_rng(41); L = len(d); k = int(np.ceil(L/bl)); o = np.empty(nb)
    for q in range(nb):
        st = rng.integers(0, max(L-bl, 1), size=k)
        ix = (st[:, None]+np.arange(bl)[None, :]).ravel()[:L]; ix = ix[ix < L]
        o[q] = d[ix].mean()
    return float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))
p0, t0 = run_book(); n0 = p0-t0*C1; sh0 = n0.mean()/n0.std(ddof=1)*ANN
print(f"基线: 净 {n0.mean():+.3f} 夏普 {sh0:+.2f}", flush=True)
for nm, Xz, gains in survivors:
    sgn = np.sign(np.median([g[1] for g in gains]))
    for w4 in (0.05, 0.10):
        p, t = run_book(extra=[sgn*Xz[i] for i in range(n)], w4=w4)
        net = p-t*C1; d = net-n0; lo, hi = boot(d)
        d2 = (p-t*C2).mean()-(p0-t0*C2).mean()
        dfy = pd.DataFrame({"y": yrs, "d": d}).groupby("y").d.mean()
        sh = net.mean()/net.std(ddof=1)*ANN
        ok_ = "★PASS" if (lo > 0 and d2 >= 0 and (dfy >= 0).sum() >= 4 and sh >= sh0) else "fail"
        print(f"  {nm} w={w4} sign={int(sgn)}: Δ净 {d.mean():+.4f} CI[{lo:+.4f},{hi:+.4f}] "
              f"@6.23 {d2:+.4f} 逐年{int((dfy>=0).sum())}/5 夏普 {sh:+.2f} {ok_}", flush=True)
print("RM_DONE", flush=True)
