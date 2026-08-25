#!/usr/bin/env python3
"""um_metrics 面板化: 每符号 1330 日 zip -> (T5,6) f32 npz, 全局 5m 网格对齐.
★ 泄漏纪律: 存储为 create_time 原始戳; meta.availability 声明"ts 值最早在 ts+300s 可用",
特征构造侧一律 +1 bar 时移. 输出 /mnt/storage/private/work_hsy/um_panel/<SYM>.npz"""
import os, io, zipfile, csv, datetime as dt
import numpy as np
from concurrent.futures import ProcessPoolExecutor

D = "/mnt/storage/private/work_hsy/um_metrics"
O = "/mnt/storage/private/work_hsy/um_panel"
os.makedirs(O, exist_ok=True)
T0 = dt.datetime(2023, 1, 1)
NT = ((dt.datetime(2026, 8, 23) - T0).days) * 288
COLS = ["sum_open_interest", "sum_open_interest_value", "sum_toptrader_long_short_ratio",
        "count_toptrader_long_short_ratio", "count_long_short_ratio", "sum_taker_long_short_vol_ratio"]

files = os.listdir(D)
by_sym = {}
for f in files:
    if f.endswith(".zip"):
        s = f.rsplit("-", 3)[0]
        by_sym.setdefault(s, []).append(f)

def do_sym(s):
    out = f"{O}/{s}.npz"
    if os.path.exists(out):
        return (s, -1)
    X = np.full((NT, 6), np.nan, np.float32)
    n = 0
    for f in sorted(by_sym[s]):
        try:
            with zipfile.ZipFile(f"{D}/{f}") as z:
                raw = z.read(z.namelist()[0]).decode()
        except Exception:
            continue
        rd = csv.reader(io.StringIO(raw))
        hdr = next(rd)
        try:
            ix = [hdr.index(c) for c in COLS]
            it = hdr.index("create_time")
        except ValueError:
            continue
        for row in rd:
            try:
                t = dt.datetime.strptime(row[it][:16], "%Y-%m-%d %H:%M")
                k = int((t - T0).total_seconds() // 300)
                if 0 <= k < NT:
                    X[k] = [float(row[i]) if row[i] else np.nan for i in ix]
                    n += 1
            except Exception:
                continue
    np.savez_compressed(out, X=X, cols=np.array(COLS),
                        meta=np.array([f"grid=5m t0=2023-01-01 NT={NT}",
                                       "availability: value at ts usable only >= ts+300s (+1 bar shift at feature build)"]))
    return (s, n)

if __name__ == "__main__":
    syms = sorted(by_sym)
    print(f"syms {len(syms)} NT {NT}", flush=True)
    with ProcessPoolExecutor(8) as ex:
        for i, (s, n) in enumerate(ex.map(do_sym, syms)):
            if (i + 1) % 50 == 0 or n < 0:
                print(f"[{i+1}/{len(syms)}] {s} rows={n}", flush=True)
    print("PANEL_DONE", flush=True)
