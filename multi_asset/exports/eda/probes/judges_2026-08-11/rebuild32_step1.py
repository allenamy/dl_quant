"""32ch 自建 · 第一步: klines 日 CSV + fundingRate 月 CSV -> OHLCV 面板(对齐 panel_targets 网格)。

★ 不重建 MEMBER/目标 —— panel_targets.npz 里的 MEMBER110/YR4/YR24/CL* 是生产面板原件,
  重建它们只会引入不一致。本脚本只产 OHLCV+FUND 原料; 因子公式由【原版】wide_factory 算
  (零转写风险), 装配由第二步做。
输出: /workspace/data/ohlcv_grid.npz {OPEN,HIGH,LOW,CLOSE,VOL,QVOL,FUND_RATE (T,N)}
"""
import glob, os, sys
import datetime as dt
from concurrent.futures import ProcessPoolExecutor
import numpy as np

P = np.load("/workspace/data/panel_targets.npz", allow_pickle=True)
TS = np.asarray(P["ts"]).astype(np.int64)
SYMS = [str(s) for s in P["symbols"]]
SI = {s: i for i, s in enumerate(SYMS)}
T, N = len(TS), len(SYMS)
ROW = {int(t): i for i, t in enumerate(TS)}
KDIR = "/workspace/data/raw/klines1h"
FDIR = "/workspace/data/raw/fundingRate"

def one_sym(sym):
    """该币全部日文件 -> (行号, 6 列) 列表 + funding (ts,rate) 列表。"""
    o = []
    for fp in sorted(glob.glob(os.path.join(KDIR, f"{sym}-2*.csv"))):
        try:
            with open(fp) as f:
                first = f.readline()
                if not first: continue
                lines = ([] if first[0].isdigit() else []) if False else None
        except Exception:
            continue
        try:
            with open(fp) as f:
                for ln in f:
                    p = ln.rstrip("\n").split(",")
                    if len(p) < 11 or not p[0].isdigit(): continue
                    ms = int(p[0])
                    # 归档既有 ms 也有 us 时间戳(2025+ 部分文件) — 归一到 ms
                    if ms > 10**14: ms //= 1000
                    i = ROW.get(ms)
                    if i is None: continue
                    o.append((i, float(p[1]), float(p[2]), float(p[3]),
                              float(p[4]), float(p[5]), float(p[7])))
        except Exception:
            continue
    fr = []
    for fp in sorted(glob.glob(os.path.join(FDIR, f"{sym}-2*.csv"))):
        try:
            with open(fp) as f:
                for ln in f:
                    p = ln.rstrip("\n").split(",")
                    if len(p) < 3: continue
                    try: ms = int(p[0]); r = float(p[2])
                    except ValueError: continue
                    if ms > 10**14: ms //= 1000
                    fr.append((ms, r))
        except Exception:
            continue
    return sym, o, fr

if __name__ == "__main__":
    import time
    t0 = time.time()
    A = {k: np.full((T, N), np.nan, np.float32)
         for k in ("OPEN", "HIGH", "LOW", "CLOSE", "VOL", "QVOL")}
    FUND = np.full((T, N), np.nan, np.float32)     # 结算点上的 rate, 后续 EMA 在第二步
    with ProcessPoolExecutor(max_workers=14) as ex:
        for k, (sym, rows, fr) in enumerate(ex.map(one_sym, SYMS)):
            j = SI[sym]
            for i, op, hi, lo, cl, vo, qv in rows:
                A["OPEN"][i, j] = op; A["HIGH"][i, j] = hi; A["LOW"][i, j] = lo
                A["CLOSE"][i, j] = cl; A["VOL"][i, j] = vo; A["QVOL"][i, j] = qv
            for ms, r in fr:
                # funding 结算戳落到【它之后】最近的整点行(严格 ≥ 结算时刻 ⇒ 因果)
                h = ms - (ms % 3600000)
                i = ROW.get(h if ms % 3600000 == 0 else h + 3600000)
                if i is not None: FUND[i, j] = r
            if (k + 1) % 20 == 0:
                print(f"  {k+1}/{N}  {(time.time()-t0)/60:.1f}min", flush=True)
    fill = np.isfinite(A["CLOSE"]).mean()
    print(f"CLOSE 填充率 {fill:.3f}  (panel MEMBER110 率 {P['MEMBER110'].mean():.3f})")
    np.savez_compressed("/workspace/data/ohlcv_grid.npz", ts=TS,
                        symbols=np.array(SYMS, object), FUND_RATE=FUND, **A)
    print(f"saved ohlcv_grid.npz  {(time.time()-t0)/60:.1f}min")
