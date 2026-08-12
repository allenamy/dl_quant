"""DL原生输入 Phase-1 先验门 (DESIGN 93ee63c4, 判据冻结):
新原料摘要 ~28 特征(流向/笔数/单笔额/爆发度/蜡烛形/OI脉搏/多空比) 加入 160 滞后栈后,
树判官(rank-z+阳性对照) Δ ≥ +0.005 ⇒ GPU 立项; [+0.002,0.005) 弱先验报裁定; <+0.002 默认不立。
因果: 5m 序列 shift(1) + 墙钟+1h 映射 + 偏移谱守卫(w4_gate1 v3 同款)。"""
import os, sys, glob, zipfile, io
import numpy as np, pandas as pd
from concurrent.futures import ProcessPoolExecutor
M = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
OUT = f"{M}/dlnative_summaries_v1.npz"
T0, T1 = pd.Timestamp("2022-01-01"), pd.Timestamp("2026-08-10")
HGRID = pd.date_range(T0, T1, freq="1h")
def read_zip_csv(path, ncol):
    try:
        with zipfile.ZipFile(path) as z:
            raw = z.read(z.namelist()[0])
        hdr = 0 if raw[:1].isalpha() else None
        return pd.read_csv(io.BytesIO(raw), header=hdr).iloc[:, :ncol]
    except Exception:
        return None
def build(sym):
    kdir, mdir = f"{M}/w4_klines5m/{sym}", f"{M}/wide_metrics_raw/{sym}"
    if not os.path.isdir(kdir): return sym, None
    ks = []
    for f in sorted(glob.glob(f"{kdir}/*.zip")):
        d = read_zip_csv(f, 11)
        if d is None or len(d) == 0: continue
        d.columns = ["open_time","o","h","l","c","v","close_time","qv","cnt","tbv","tbqv"][:d.shape[1]]
        ks.append(d)
    if not ks: return sym, None
    k = pd.concat(ks)
    k["ts"] = pd.to_datetime(k.open_time.astype(np.int64), unit="ms") + pd.Timedelta("5min")
    k = k.drop_duplicates("ts").set_index("ts").sort_index()
    idx = pd.date_range(k.index[0], k.index[-1], freq="5min")
    k = k.reindex(idx)
    ret = k.c.pct_change(fill_method=None)
    rng_ = (k.h-k.l)/k.c
    cpos = ((k.c-k.l)/(k.h-k.l)).clip(0,1)
    tbf = (k.tbqv/k.qv).clip(0,1)
    sgn_flow = (2*tbf-1)*k.qv
    avg_sz = k.qv/k.cnt.replace(0,np.nan)
    F = pd.DataFrame(index=idx)
    for w, tag in ((48,"4h"),(288,"24h")):
        F[f"tbf_{tag}"] = tbf.rolling(w,min_periods=w//3).mean()
        F[f"flow_{tag}"] = sgn_flow.rolling(w,min_periods=w//3).sum()/k.qv.rolling(w,min_periods=w//3).sum()
        F[f"cnt_{tag}"] = np.log1p(k.cnt.rolling(w,min_periods=w//3).sum())
        F[f"asz_{tag}"] = np.log(avg_sz.rolling(w,min_periods=w//3).mean())
        F[f"burst_{tag}"] = k.qv.rolling(w,min_periods=w//3).max()/k.qv.rolling(w,min_periods=w//3).sum()
        F[f"cpos_{tag}"] = cpos.rolling(w,min_periods=w//3).mean()
        F[f"chop_{tag}"] = rng_.rolling(w,min_periods=w//3).sum()/ (k.c.pct_change(w).abs()+1e-4)
    F["tbf_trend"] = F.tbf_4h - tbf.rolling(288,min_periods=96).mean()
    F["asz_z7d"] = (F.asz_4h - F.asz_4h.rolling(2016,min_periods=500).mean())/(F.asz_4h.rolling(2016,min_periods=500).std()+1e-9)
    # metrics(OI/多空比)
    if os.path.isdir(mdir):
        ms = []
        for f in sorted(glob.glob(f"{mdir}/*.zip")):
            d = read_zip_csv(f, 8)
            if d is None or len(d) == 0 or d.shape[1] < 8: continue
            d.columns = ["create_time","symbol","oi","oiv","cttls","sttls","cls","stlsv"]
            ms.append(d[["create_time","oiv","sttls","stlsv"]])
        if ms:
            mm = pd.concat(ms)
            mm["ts"] = pd.to_datetime(mm.create_time)
            mm = mm.drop_duplicates("ts").set_index("ts").sort_index().reindex(idx)
            doi = mm.oiv.diff()/mm.oiv.shift(1)
            for w, tag in ((48,"4h"),(288,"24h")):
                F[f"doi_{tag}"] = doi.rolling(w,min_periods=w//3).sum()
            F["oi_px_div"] = doi.rolling(288,min_periods=96).sum()*np.sign(-k.c.pct_change(288))
            F["ttls_chg"] = mm.sttls.diff(48)
            F["tkls_24h"] = mm.stlsv.rolling(288,min_periods=96).mean()
    return sym, F.shift(1).reindex(HGRID).to_numpy(dtype=np.float32), list(F.columns)
syms = sorted(os.listdir(f"{M}/w4_klines5m"))
cols_ref = None; res = {}
with ProcessPoolExecutor(max_workers=8) as ex:
    for i, out in enumerate(ex.map(build, syms)):
        if len(out) == 3:
            s, arr, cols = out; res[s] = arr; cols_ref = cols
        else:
            res[out[0]] = None
        if (i+1) % 30 == 0: print(f"{i+1}/{len(syms)}", flush=True)
good = [s for s in syms if res.get(s) is not None]
NF = len(cols_ref)
np.savez_compressed(OUT, ts=HGRID.astype("int64")//10**9, symbols=np.array(good),
                    feats=np.array(cols_ref), data=np.stack([res[s] for s in good], axis=1))
print(f"summaries built: {len(good)} 币 × {NF} 特征", flush=True)
# ── 树判官(v4 harness) ──
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
from scipy.stats import rankdata, spearmanr
import lightgbm as lgb
import engine.replay_fullhist as RF
PANEL = MA + "/exports/wide_dl_full_corrfund_causal_v1.npz"
src = RF.get_src(PANEL, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N; n = len(a)
C = src.CH.shape[2]; LAGS = [0,1,3,6,24]; F0 = C*len(LAGS)
Z = np.load(OUT, allow_pickle=True)
ts2row = {int(t): i for i, t in enumerate(Z["ts"])}
sym2col = {s: j for j, s in enumerate(list(Z["symbols"]))}
SYMS = [str(s) for s in src.symbols]
col_of = np.array([sym2col.get(s, -1) for s in SYMS])
anchor_epoch = (src.ts[np.asarray(a, dtype=np.int64)] // 1000 + 3600).astype(np.int64)
rows = np.array([ts2row.get(int(e), -1) for e in anchor_epoch])
assert (rows >= 0).mean() > 0.95
X = np.full((n, N, F0+NF), np.nan, dtype=np.float32)
Y = np.full((n, N), np.nan, dtype=np.float32)
KING = np.full((n, N), np.nan, dtype=np.float32)
held_k = np.full(N, np.nan)
zd = Z["data"]
for i, t in enumerate(a):
    ti = int(t); m = np.asarray(src.tradeable(ti))
    if m.dtype == bool: m = np.where(m)[0]
    if i == 0 or ti % 8 == 0:
        v = np.full(N, np.nan); v[m] = src.king[ti, m]; held_k = v
    KING[i] = held_k; Y[i, m] = src.Y4[ti, m]
    for li, L in enumerate(LAGS):
        if ti-L >= 0: X[i, m, li*C:(li+1)*C] = src.CH[ti-L, m, :]
    if rows[i] >= 0:
        okc = col_of >= 0
        X[i, okc, F0:] = zd[rows[i]][col_of[okc], :]
YRZ = np.full_like(Y, np.nan)
for i in range(n):
    ok = np.isfinite(Y[i])
    if ok.sum() >= 10:
        r_ = rankdata(Y[i, ok]); YRZ[i, ok] = (r_-(ok.sum()+1)/2)/max(ok.sum()-1,1)
yrs = np.array(yr)
def spear(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    return spearmanr(x[ok], y[ok]).correlation if ok.sum() >= 10 else np.nan
PAR = dict(objective="regression", num_leaves=63, learning_rate=0.03, min_data_in_leaf=200,
           feature_fraction=0.7, bagging_fraction=0.8, bagging_freq=1, verbosity=-1, num_threads=8)
res2 = {"base": {}, "aug": {}, "C": {}}
for Yv in (2023, 2024, 2025, 2026):
    tr = np.where(yrs < Yv)[0][::2]; te = np.where(yrs == Yv)[0]
    def flat(idx, cols):
        xs, ys = [], []
        for i in idx:
            ok = np.isfinite(YRZ[i]); xs.append(X[i, ok][:, cols]); ys.append(YRZ[i, ok])
        return np.concatenate(xs), np.concatenate(ys)
    for tag, cols in (("C", None), ("base", list(range(F0))), ("aug", list(range(F0+NF)))):
        if tag == "C":
            xs, ys = [], []
            for i in tr:
                ok = np.isfinite(YRZ[i]) & np.isfinite(KING[i])
                xs.append(KING[i, ok][:, None]); ys.append(YRZ[i, ok])
            mdl = lgb.train(dict(PAR, num_leaves=31), lgb.Dataset(np.concatenate(xs), np.concatenate(ys)), num_boost_round=200)
            P = np.full((n, N), np.nan, np.float32)
            for i in te:
                ok = np.isfinite(Y[i]) & np.isfinite(KING[i]); P[i, ok] = mdl.predict(KING[i, ok][:, None])
        else:
            Xtr, ytr = flat(tr, cols)
            mdl = lgb.train(PAR, lgb.Dataset(Xtr, ytr), num_boost_round=300)
            P = np.full((n, N), np.nan, np.float32)
            for i in te:
                ok = np.isfinite(Y[i]); P[i, ok] = mdl.predict(X[i, ok][:, cols])
        res2[tag][Yv] = float(np.nanmean([spear(P[i], Y[i]) for i in te]))
    print(f"{Yv}: C {res2['C'][Yv]:+.4f} base {res2['base'][Yv]:+.4f} aug {res2['aug'][Yv]:+.4f}", flush=True)
king_ic = np.mean([float(np.nanmean([spear(KING[i], Y[i]) for i in np.where(yrs==Yv)[0]])) for Yv in (2023,2024,2025,2026)])
cc = np.mean(list(res2["C"].values())); bb = np.mean(list(res2["base"].values())); aa = np.mean(list(res2["aug"].values()))
dv = [res2["aug"][y_]-res2["base"][y_] for y_ in (2023,2024,2025,2026)]
print(f"\n阳性对照复原率 {cc/king_ic*100:.0f}% ({'有效' if cc>=0.9*king_ic else '无效, 下述不可判'})")
print(f"base(现32特征滞后栈) {bb:+.4f} | aug(+新原料摘要{NF}个) {aa:+.4f} | Δ逐年 {[round(x,4) for x in dv]} 均值 {np.mean(dv):+.4f}")
d = np.mean(dv)
print("判: " + ("★Δ≥+0.005 ⇒ GPU 战役立项理由充分" if d>=0.005 else
      "弱先验 ⇒ 报用户裁定" if d>=0.002 else "Δ<+0.002 ⇒ 默认不立项(摘要摸不到 ⇒ 只剩纯模式赌注)"))
print("PHASE1_DONE", flush=True)
