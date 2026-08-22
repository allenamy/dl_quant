#!/usr/bin/env python
"""F7 · 永续/现货 1h 面板构建器 @jpline(2026-08-22, Session 6737834a-F7; PREREG a262418 §P6)。
输入(只读): w3lane/wide1h_csv/<perp_sym>/<ym>.zip(829 名永续 1h 月度 zip, data.binance.vision), w3lane/spot1h_csv/<spot_sym>/<ym>.zip(现货 1h),
          probe_artifacts/f7/f7_spot_map.json(永续→现货映射), pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz(symbols 顺序)。
输出: probe_artifacts/f7/{perp1h_panel.npz, spot1h_panel.npz}: ts(小时, 秒), symbols(829, 永续顺序), close/qv(quote volume)/tbq(taker buy quote)/cnt(trades) float32 (n_hours×829)。
列(Binance kline csv): open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore; 2025+ 部分文件 open_time 为微秒(16 位)→ 归一为毫秒。
用法: python f7_build_1h_panels.py [perp|spot|both]
"""
import os, sys, io, json, time, zipfile, hashlib, numpy as np
from multiprocessing import Pool
W3 = "/mnt/storage/private/work_hsy/w3lane"; B = "/mnt/storage/private/work_hsy/pod_backup_2026-08-21"; F7 = "/mnt/storage/private/work_hsy/probe_artifacts/f7"
T0 = 1635724800   # 2021-11-01 00:00Z
T1 = 1785452400   # 2026-07-31 23:00Z
HOURS = np.arange(T0, T1 + 1, 3600, dtype=np.int64); NH = len(HOURS)
SYMS = [str(s) for s in np.load(f"{B}/wide_panel_4h_hist_v2.npz", allow_pickle=True)["symbols"]]
MAP = json.load(open(f"{F7}/f7_spot_map.json"))["map"]
which = sys.argv[1] if len(sys.argv) > 1 else "both"

def parse_dir(d):
    """returns dict hour_ts -> (close, qv, tbq, cnt) arrays aligned to HOURS (NaN where absent), plus n files, n rows"""
    cl = np.full(NH, np.nan, np.float32); qv = np.full(NH, np.nan, np.float32); tb = np.full(NH, np.nan, np.float32); ct = np.full(NH, np.nan, np.float32)
    if not os.path.isdir(d): return cl, qv, tb, ct, 0, 0
    nf = 0; nr = 0
    for f in sorted(os.listdir(d)):
        if not f.endswith(".zip"): continue
        p = f"{d}/{f}"
        if os.path.getsize(p) < 100: continue
        try:
            z = zipfile.ZipFile(p); nm = z.namelist()[0]; raw = z.read(nm).decode("utf-8", "ignore")
        except Exception:
            continue
        nf += 1
        for line in raw.split("\n"):
            if not line or line.startswith("open_time"): continue
            parts = line.split(",")
            if len(parts) < 11: continue
            try:
                ot = int(parts[0])
                if ot > 10 ** 14: ot //= 1000          # microseconds -> ms
                ot //= 1000                             # ms -> s
                if ot < T0 or ot > T1 or (ot % 3600) != 0: continue
                i = (ot - T0) // 3600
                cl[i] = float(parts[4]); qv[i] = float(parts[7]); ct[i] = float(parts[8]); tb[i] = float(parts[10]); nr += 1
            except Exception:
                continue
    return cl, qv, tb, ct, nf, nr

def work_perp(k):
    s = SYMS[k]; cl, qv, tb, ct, nf, nr = parse_dir(f"{W3}/wide1h_csv/{s}"); return k, cl, qv, tb, ct, nf, nr
def work_spot(k):
    s = SYMS[k]; sp = MAP.get(s)
    if not sp: return k, None, None, None, None, 0, 0
    cl, qv, tb, ct, nf, nr = parse_dir(f"{W3}/spot1h_csv/{sp}"); return k, cl, qv, tb, ct, nf, nr

def build(kind):
    t0 = time.time(); fn = work_perp if kind == "perp" else work_spot
    CL = np.full((NH, len(SYMS)), np.nan, np.float32); QV = CL.copy(); TB = CL.copy(); CT = CL.copy(); meta = {}
    with Pool(24) as pool:
        for j, (k, cl, qv, tb, ct, nf, nr) in enumerate(pool.imap_unordered(fn, range(len(SYMS)), chunksize=4)):
            if cl is not None: CL[:, k] = cl; QV[:, k] = qv; TB[:, k] = tb; CT[:, k] = ct
            meta[SYMS[k]] = {"files": nf, "rows": nr}
            if j % 100 == 0: print(kind, j, "/", len(SYMS), round(time.time() - t0), "s", flush=True)
    out = f"{F7}/{kind}1h_panel.npz"
    np.savez_compressed(out, ts=HOURS, symbols=np.array(SYMS), close=CL, qv=QV, tbq=TB, cnt=CT, meta=json.dumps(meta))
    nsym = sum(1 for v in meta.values() if v["rows"] > 0)
    print(f"{kind}: symbols with data {nsym}/{len(SYMS)}, rows {sum(v['rows'] for v in meta.values())}, finite close frac {np.isfinite(CL).mean():.4f}, saved {out} {round(time.time()-t0)}s", flush=True)

if __name__ == "__main__":
    if which in ("perp", "both"): build("perp")
    if which in ("spot", "both"): build("spot")
