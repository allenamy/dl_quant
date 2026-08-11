"""W4 特征构建器 v1 (PREREG 75a09de2 菜单 F1-F5 的原料层)
输入: wide_metrics_raw(OI 5m USD) + w4_klines5m(5m OHLCV)
输出: exports/w4_liq_proxy_v1.npz — [T小时 × N × 7] raw 特征(归一在门装置侧做)
  通道: F1_4h F1_24h(下杀瀑布额) F2_4h F2_24h(挤空额) F3(距瀑布小时, cap24) F4(24h不平衡) ret24(F5用)
因果: 特征在整点 t 取 5m 序列 shift(1) 的值 ⇒ 只用 create_time/close ≤ t−5m (track-2 同款滞后)。
阈值实现注记(prereg §3 "自身30d q05"): 逐日 q05 → 30日滚动均值 → shift(1日); 与逐bin滚动分位等价且可算。
首 symbol (BTCUSDT) QC 模式: 打印 join率/瀑布率/阈值量级, join<80% 或瀑布率∉[1%,15%] 则 abort。"""
import os, sys, glob, zipfile, io
import numpy as np, pandas as pd
from concurrent.futures import ProcessPoolExecutor
M = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
OUT = f"{M}/w4_liq_proxy_v1.npz"
T0, T1 = pd.Timestamp("2022-01-01"), pd.Timestamp("2026-08-10")
HGRID = pd.date_range(T0, T1, freq="1h")
def read_zip_csv(path):
    try:
        with zipfile.ZipFile(path) as z:
            name = z.namelist()[0]
            raw = z.read(name)
        first = raw[:60].decode("utf-8", "ignore")
        hdr = 0 if first[0].isalpha() else None
        return pd.read_csv(io.BytesIO(raw), header=hdr)
    except Exception:
        return None
def build_symbol(sym, qc=False):
    mdir, kdir = f"{M}/wide_metrics_raw/{sym}", f"{M}/w4_klines5m/{sym}"
    if not (os.path.isdir(mdir) and os.path.isdir(kdir)): return sym, None
    mets = []
    for f in sorted(glob.glob(f"{mdir}/*.zip")):
        d = read_zip_csv(f)
        if d is None or len(d) == 0: continue
        if d.shape[1] < 4: continue
        d.columns = ["create_time", "symbol", "oi", "oiv"] + list(d.columns[4:])
        mets.append(d[["create_time", "oiv"]])
    if not mets: return sym, None
    mm = pd.concat(mets)
    mm["ts"] = pd.to_datetime(mm.create_time)
    mm = mm.drop_duplicates("ts").set_index("ts").sort_index()
    kls = []
    for f in sorted(glob.glob(f"{kdir}/*.zip")):
        d = read_zip_csv(f)
        if d is None or len(d) == 0: continue
        d = d.iloc[:, :7]
        d.columns = ["open_time", "o", "h", "l", "c", "v", "close_time"]
        kls.append(d[["open_time", "c"]])
    if not kls: return sym, None
    kk = pd.concat(kls)
    kk["ts"] = pd.to_datetime(kk.open_time.astype(np.int64), unit="ms") + pd.Timedelta("5min")
    kk = kk.drop_duplicates("ts").set_index("ts").sort_index()
    df = pd.DataFrame(index=pd.date_range(max(mm.index[0], kk.index[0]),
                                          min(mm.index[-1], kk.index[-1]), freq="5min"))
    df["oiv"] = mm.oiv.reindex(df.index)
    df["c"] = kk.c.reindex(df.index)
    join_rate = float(df.oiv.notna().mean())
    df["doi"] = df.oiv.diff()
    df["ret5"] = df.c.pct_change()
    dq = df.doi.resample("1D").quantile(0.05)
    thr = dq.rolling(30, min_periods=10).mean().shift(1)
    df["thr"] = thr.reindex(df.index.floor("1D")).to_numpy()
    casc = df.doi < df.thr
    dn = casc & (df.ret5 < 0); up = casc & (df.ret5 > 0)
    mag = df.doi.abs()
    dnm = mag.where(dn, 0.0); upm = mag.where(up, 0.0)
    F = pd.DataFrame(index=df.index)
    F["f1_4"] = dnm.rolling(48, min_periods=1).sum()
    F["f1_24"] = dnm.rolling(288, min_periods=1).sum()
    F["f2_4"] = upm.rolling(48, min_periods=1).sum()
    F["f2_24"] = upm.rolling(288, min_periods=1).sum()
    last_casc = pd.Series(df.index.where(casc | dn | up), index=df.index).ffill()
    F["f3"] = ((df.index.to_series() - last_casc).dt.total_seconds() / 3600).clip(upper=24).fillna(24)
    F["f4"] = (F.f1_24 - F.f2_24) / (F.f1_24 + F.f2_24 + 1e4)
    F["ret24"] = df.c.pct_change(288)
    Fh = F.shift(1).reindex(HGRID)
    casc_rate = float((dn | up).mean())
    if qc:
        print(f"[QC {sym}] 5m行 {len(df)} join率 {join_rate:.1%} 瀑布率 {casc_rate:.2%} "
              f"thr中位 {np.nanmedian(df.thr)/1e6:.2f}M f1_24中位 {np.nanmedian(F.f1_24)/1e6:.1f}M "
              f"非零f1_4占比 {(F.f1_4>0).mean():.1%}", flush=True)
        assert join_rate > 0.8, "QC FAIL: metrics join <80%"
        assert 0.01 < casc_rate < 0.15, f"QC FAIL: 瀑布率 {casc_rate:.2%} 出合理域"
    return sym, Fh.to_numpy(dtype=np.float32)
syms = sorted(os.listdir(f"{M}/wide_metrics_raw"))
print(f"symbols={len(syms)} grid={len(HGRID)}h", flush=True)
_, btc = build_symbol("BTCUSDT", qc=True)
results = {"BTCUSDT": btc}
todo = [s for s in syms if s != "BTCUSDT"]
with ProcessPoolExecutor(max_workers=8) as ex:
    for i, (s, arr) in enumerate(ex.map(build_symbol, todo)):
        results[s] = arr
        if (i + 1) % 20 == 0: print(f"{i+1}/{len(todo)}", flush=True)
good = [s for s in syms if results.get(s) is not None]
data = np.stack([results[s] for s in good], axis=1)
np.savez_compressed(OUT, ts=HGRID.astype("int64") // 10**9, symbols=np.array(good),
                    feats=np.array(["f1_4", "f1_24", "f2_4", "f2_24", "f3", "f4", "ret24"]),
                    data=data)
print(f"saved {OUT} shape={data.shape} symbols_ok={len(good)}/{len(syms)}", flush=True)
print("W4_FEATURES_DONE", flush=True)
