"""metrics 原始 CSV -> 小时特征张量, 对齐面板 ts 网格。

★ 因果性(本文件唯一不可协商的设计):
  面板 ts[i] 是小时【起点】。第 i 行的特征只允许用 **ts[i] 之前** 已经存在的数据。
  故本脚本把【小时 H-1 的帧】聚合后写到 ts=H 的行 —— 整整一小时的安全边距。
  不做 lag0 版本: 有了两个版本就一定会有人挑那个数字更好的, 而 ch31 正是这么进来的。
  OI / 多空比是高度持久量, 1 小时滞后的信息损失极小, 换来的是无歧义的因果性。

★ 输出后必须过的门(由 gate_metrics.py 独立执行, 不在本文件里自评):
  G1 |IC vs 未来 24h| < 0.15   G2 单特征 |IC| > 0.01   G3 participation ratio 必须上升
"""
import glob, os, sys, time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import datetime as dt
import numpy as np

MET = "/workspace/data/raw/metrics"
P = np.load("/workspace/data/panel_targets.npz", allow_pickle=True)
TS = np.asarray(P["ts"]).astype(np.int64)
SYMS = [str(s) for s in P["symbols"]]
SI = {s: i for i, s in enumerate(SYMS)}
T, N = len(TS), len(SYMS)
HOUR = {int(t): i for i, t in enumerate(TS)}
COLS = ["oi", "oi_val", "tt_cnt_ls", "tt_sum_ls", "all_cnt_ls", "taker_ls"]
FEAT = [f"{c}_{d}" for c in COLS for d in ("mean", "std", "slope")] + \
       ["oi_chg1h", "oi_chg24h", "oi_val_chg1h"]
LAG_MS = 3600_000          # ★ 一小时滞后

def one(fp):
    """返回 [(row_index, sym_index, 21 个特征值)]。"""
    base = os.path.basename(fp)[:-4]
    sym = base.rsplit("-", 3)[0]
    j = SI.get(sym)
    if j is None:
        return []
    buck = defaultdict(list)
    try:
        with open(fp) as f:
            next(f)
            for ln in f:
                p = ln.rstrip("\n").split(",")
                if len(p) < 8:
                    continue
                try:
                    ms = int(dt.datetime.strptime(p[0], "%Y-%m-%d %H:%M:%S")
                             .replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
                    v = [float(p[2]), float(p[3]), float(p[4]),
                         float(p[5]), float(p[6]), float(p[7])]
                except ValueError:
                    continue
                # ★ 该小时的帧 -> 写到【下一小时】的行
                buck[ms - (ms % 3600_000) + LAG_MS].append(v)
    except Exception:
        return []
    out = []
    for h, rows in buck.items():
        i = HOUR.get(h)
        if i is None or len(rows) < 3:
            continue
        a = np.asarray(rows, float)
        q = max(1, len(a) // 3)
        f = np.empty(21, np.float32)
        for c in range(6):
            v = a[:, c]
            f[c*3], f[c*3+1] = v.mean(), v.std()
            f[c*3+2] = v[-q:].mean() - v[:q].mean()     # 组内斜率(不跨小时)
        f[18] = f[19] = f[20] = np.nan
        out.append((i, j, f))
    return out

if __name__ == "__main__":
    files = sorted(glob.glob(os.path.join(MET, "*.csv")))
    print(f"面板 {T:,} 小时 × {N} 币; metrics 文件 {len(files):,}", flush=True)
    X = np.full((T, N, 21), np.nan, np.float32)
    t0, done = time.time(), 0
    with ProcessPoolExecutor(max_workers=14) as ex:
        for res in ex.map(one, files, chunksize=64):
            for i, j, f in res:
                X[i, j] = f
            done += 1
            if done % 20000 == 0:
                print(f"  {done:,}/{len(files):,}  {(time.time()-t0)/60:.1f}min", flush=True)
    # 变化率: 严格用已滞后的序列做差 ⇒ 仍然因果
    with np.errstate(invalid="ignore", divide="ignore"):
        oi, oiv = X[:, :, 0], X[:, :, 3]
        X[1:, :, 18] = np.log(oi[1:] / oi[:-1])
        X[24:, :, 19] = np.log(oi[24:] / oi[:-24])
        X[1:, :, 20] = np.log(oiv[1:] / oiv[:-1])
    X[~np.isfinite(X)] = np.nan
    fill = np.isfinite(X[:, :, 0]).mean()
    print(f"填充率 {fill:.3f}   用时 {(time.time()-t0)/60:.1f}min")
    for k, nm in enumerate(FEAT):
        v = X[:, :, k][np.isfinite(X[:, :, k])]
        print(f"  {nm:14s} n={len(v):>10,}  中位 {np.median(v):+.4g}" if len(v) else f"  {nm:14s} 全空")
    np.savez_compressed("/workspace/data/metrics_hourly.npz",
                        X=X, ts=TS, symbols=np.array(SYMS, object),
                        feats=np.array(FEAT, object), lag_ms=LAG_MS)
    print("saved /workspace/data/metrics_hourly.npz")
