"""OI/metrics 特征面板: 解析 wide_multisrc/metrics 日度zip(5m行) → 逐锚特征 → wide_oi_v1.npz.
特征: oi_val_log / oi_chg_24h / oi_chg_7d / lsr_top / lsr_all / taker_ratio_24h(锚时刻最近读数与窗口均值).
并行: 按币多进程(64 workers).
"""
import os, io, csv, glob, json, time, zipfile, hashlib
import numpy as np
from multiprocessing import Pool
import sys; sys.path.insert(0, "/workspace")
MT = np.load("/workspace/data/wide_fea_v1_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64)
Z = np.load("/workspace/data/wide_panel_4h_v1.npz", allow_pickle=True)
syms = [str(s) for s in Z["symbols"]]
sidx = {s: j for j, s in enumerate(syms)}
nA = len(E_ts); NW = len(syms)
def parse_sym(s):
    d = f"/workspace/wide_multisrc/metrics/{s}"
    if not os.path.isdir(d): return s, None
    ts_l, oi_l, lt_l, la_l, tk_l = [], [], [], [], []
    for zp in sorted(glob.glob(d + "/*.zip")):
        try:
            zf = zipfile.ZipFile(zp)
            with zf.open(zf.namelist()[0]) as fh:
                rd = csv.reader(io.TextIOWrapper(fh))
                hdr = next(rd)
                ci = {c: k for k, c in enumerate(hdr)}
                for row in rd:
                    try:
                        t = row[ci.get("create_time", 0)]
                        tt = int(time.mktime(time.strptime(t[:19], "%Y-%m-%d %H:%M:%S"))) if "-" in t else int(t) // 1000
                        oiv = float(row[ci["sum_open_interest_value"]])
                        ltop = float(row[ci["sum_toptrader_long_short_ratio"]])
                        lall = float(row[ci["count_long_short_ratio"]])
                        tkr = float(row[ci["sum_taker_long_short_vol_ratio"]])
                        ts_l.append(tt); oi_l.append(oiv); lt_l.append(ltop); la_l.append(lall); tk_l.append(tkr)
                    except Exception:
                        continue
        except Exception:
            continue
    if not ts_l: return s, None
    o = np.argsort(ts_l)
    return s, (np.array(ts_l)[o], np.array(oi_l)[o], np.array(lt_l)[o], np.array(la_l)[o], np.array(tk_l)[o])
F = {k: np.full((nA, NW), np.nan, np.float32) for k in
     ("oi_val_log", "oi_chg_24h", "oi_chg_7d", "lsr_top", "lsr_all", "taker_ratio_24h")}
symdirs = [os.path.basename(p) for p in glob.glob("/workspace/wide_multisrc/metrics/*")]
print(f"{len(symdirs)} 币目录", flush=True)
t0 = time.time()
with Pool(64) as pool:
    for k, (s, data) in enumerate(pool.imap_unordered(parse_sym, symdirs)):
        if data is None: continue
        ts_a, oi, lt, la, tk = data
        j = sidx.get(s)
        if j is None: continue
        pos = np.searchsorted(ts_a, E_ts, side="right") - 1
        ok = pos >= 0
        stale = np.zeros(nA, bool)
        stale[ok] = (E_ts[ok] - ts_a[pos[ok]]) > 6 * 3600
        ok = ok & ~stale
        with np.errstate(divide="ignore", invalid="ignore"):
            F["oi_val_log"][ok, j] = np.log1p(oi[pos[ok]])
            p24 = np.searchsorted(ts_a, E_ts - 86400, side="right") - 1
            p7d = np.searchsorted(ts_a, E_ts - 7 * 86400, side="right") - 1
            ok24 = ok & (p24 >= 0); ok7 = ok & (p7d >= 0)
            F["oi_chg_24h"][ok24, j] = np.log(np.maximum(oi[pos[ok24]], 1) / np.maximum(oi[p24[ok24]], 1))
            F["oi_chg_7d"][ok7, j] = np.log(np.maximum(oi[pos[ok7]], 1) / np.maximum(oi[p7d[ok7]], 1))
            F["lsr_top"][ok, j] = lt[pos[ok]]
            F["lsr_all"][ok, j] = la[pos[ok]]
            # taker 24h 均值
            for i in np.where(ok24)[0]:
                a0, a1 = p24[i], pos[i]
                if a1 > a0: F["taker_ratio_24h"][i, j] = float(np.nanmean(tk[a0:a1]))
        if k % 50 == 0: print(f"{k}/{len(symdirs)} ({time.time()-t0:.0f}s)", flush=True)
out = "/workspace/data/wide_oi_v1.npz"
np.savez_compressed(out, ts=E_ts, symbols=np.array(syms), **{("f_" + k): v for k, v in F.items()})
h = hashlib.sha256(open(out, "rb").read()).hexdigest()[:16]
cov = float(np.isfinite(F["oi_val_log"]).any(0).sum())
print(f"OI_PANEL_DONE 覆盖 {cov:.0f} 币 SHA {h}", flush=True)
