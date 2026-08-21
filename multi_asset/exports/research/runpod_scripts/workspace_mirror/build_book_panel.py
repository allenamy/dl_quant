"""bookDepth ±1% 带 -> 13 列小时特征, 对齐面板 ts。规格见 DESIGN_book_2026-08-07.md。

★ 因果: 小时 H-1 的 120 帧聚合后写到 ts=H 的行(与 metrics 同纪律, 整小时安全边距)。
★ 效率: 只解析 ±0.2% 两行(2/12), 提前按字节前缀过滤, 不做全量 float 转换。
★ mid: 用 klines close(独立源), 不从 book 内部反推。
"""
import glob, gzip, os, sys, time
import datetime as dt
from concurrent.futures import ProcessPoolExecutor
import numpy as np

BD = "/workspace/data/raw/bookDepth"
KL = "/workspace/data/raw/klines1h"
P = np.load("/workspace/data/panel_targets.npz", allow_pickle=True)
TS = np.asarray(P["ts"]).astype(np.int64)
SYMS = [str(s) for s in P["symbols"]]
SI = {s: i for i, s in enumerate(SYMS)}
T, N = len(TS), len(SYMS)
ROW = {int(t): i for i, t in enumerate(TS)}
LAG = 3600_000
FEAT = ["obi_mean","obi_std","obi_slope","obi_nd_gap","conc_bid","conc_ask","conc_asym",
        "cv_bid","cv_ask","cv_asym","dep_lvl","dep_chg1h","refill"]

def load_mid(sym):
    """klines close -> {hour_ms: close}"""
    out = {}
    for fp in glob.glob(f"{KL}/{sym}-2*.csv"):
        try:
            with open(fp) as f:
                for ln in f:
                    p = ln.split(",", 5)
                    if not p[0].isdigit(): continue
                    ms = int(p[0])
                    if ms > 10**14: ms //= 1000
                    out[ms] = float(p[4])
        except Exception: pass
    return out

def one_sym(sym):
    j = SI.get(sym)
    if j is None: return None
    mid = load_mid(sym)
    # hour_ms -> lists
    acc = {}
    for fp in sorted(glob.glob(f"{BD}/{sym}-2*.csv.gz") + glob.glob(f"{BD}/{sym}-2*.csv")):
        try:
            op = gzip.open(fp, "rt") if fp.endswith(".gz") else open(fp)
            with op as f:
                f.readline()
                cur_ts = None; bd = ad = bn = an = None
                for ln in f:
                    # 只要 ±0.20 两行: 提前字节过滤
                    i1 = ln.find(",")
                    if i1 < 0: continue
                    i2 = ln.find(",", i1 + 1)
                    band = ln[i1+1:i2]
                    # ★ 带选择 = ±1%(不是 ±0.2%)。实测: ±0.2 带 2026-02 才被交易所加入,
                    #   仅 6 个月历史; ±1% 全史 2023-01 起 3.6 年, 实盘 126/128 币可服务
                    #   (仅 BTC/ETH 的 REST 1000 档够不到 ±1%, 这两币书特征留空)。
                    #   格式跨年漂移: 早期 "-1", 2026-02 起 "-1.00" —— 两种都收。
                    if band == "-1" or band == "-1.00":
                        side = 0
                    elif band == "1" or band == "1.00":
                        side = 1
                    else:
                        continue
                    tstr = ln[:i1]
                    if tstr != cur_ts:
                        if cur_ts is not None and bd is not None and ad is not None:
                            h = int(dt.datetime.strptime(cur_ts, "%Y-%m-%d %H:%M:%S")
                                    .replace(tzinfo=dt.timezone.utc).timestamp()) // 3600 * 3600000
                            acc.setdefault(h, []).append((bd, ad, bn, an))
                        cur_ts = tstr; bd = ad = bn = an = None
                    i3 = ln.find(",", i2 + 1)
                    d = float(ln[i2+1:i3]); nn = float(ln[i3+1:].rstrip())
                    if side == 0: bd, bn = d, nn
                    else: ad, an = d, nn
                if cur_ts is not None and bd is not None and ad is not None:
                    h = int(dt.datetime.strptime(cur_ts, "%Y-%m-%d %H:%M:%S")
                            .replace(tzinfo=dt.timezone.utc).timestamp()) // 3600 * 3600000
                    acc.setdefault(h, []).append((bd, ad, bn, an))
        except Exception:
            continue
    if not acc: return None
    hrs = sorted(acc)
    tot_by_hr = {}
    out = []
    for h in hrs:
        a = np.asarray(acc[h], float)
        if len(a) < 20: continue
        bd, ad, bn, an = a[:,0], a[:,1], a[:,2], a[:,3]
        tot = bd + ad
        tot_by_hr[h] = float(np.median(tot))
        obi = (bd - ad) / np.maximum(tot, 1e-12)
        obin = (bn - an) / np.maximum(bn + an, 1e-12)
        q = max(1, len(a)//3)
        m = mid.get(h)
        f = np.full(13, np.nan)
        f[0] = obi.mean(); f[1] = obi.std(); f[2] = obi[-q:].mean() - obi[:q].mean()
        f[3] = obin.mean() - obi.mean()
        if m and m > 0:
            wb = bn / np.maximum(bd, 1e-12); wa = an / np.maximum(ad, 1e-12)
            f[4] = float(np.mean((m - wb) / m) * 1e4); f[5] = float(np.mean((wa - m) / m) * 1e4)
            f[6] = f[5] - f[4]
        f[7] = bd.std() / max(bd.mean(), 1e-12); f[8] = ad.std() / max(ad.mean(), 1e-12)
        if f[7] > 1e-9 and f[8] > 1e-9: f[9] = float(np.log(f[8] / f[7]))
        dd = np.diff(tot); nz = dd != 0
        f[12] = float((dd > 0).sum() / max(nz.sum(), 1))
        out.append((h, f, float(np.median(tot))))
    # 自归一: 30d 滚动中位数(因果, 只用过去)
    hs = [o[0] for o in out]; med = [o[2] for o in out]
    res = []
    for k, (h, f, mv) in enumerate(out):
        lo = max(0, k - 720)
        base = np.median(med[lo:k+1])
        if base > 0 and mv > 0: f[10] = float(np.log(mv / base))
        if k > 0 and med[k-1] > 0 and mv > 0 and hs[k] - hs[k-1] == 3600000:
            f[11] = float(np.log(mv / med[k-1]))
        i = ROW.get(h + LAG)
        if i is not None: res.append((i, j, f.astype(np.float32)))
    return res

if __name__ == "__main__":
    t0 = time.time()
    have = sorted({os.path.basename(f).rsplit("-", 3)[0]
                   for f in glob.glob(f"{BD}/*.csv.gz") + glob.glob(f"{BD}/*.csv")})
    todo = [s for s in have if s in SI]
    print(f"币 {len(todo)}/{N}  面板 {T:,}h", flush=True)
    X = np.full((T, N, 13), np.nan, np.float32)
    done = 0
    with ProcessPoolExecutor(max_workers=14) as ex:
        for r in ex.map(one_sym, todo):
            done += 1
            if r:
                for i, j, f in r: X[i, j] = f
            if done % 20 == 0:
                print(f"  {done}/{len(todo)}  {(time.time()-t0)/60:.1f}min", flush=True)
    fill = np.isfinite(X[:, :, 0]).mean()
    print(f"填充率 {fill:.4f}  用时 {(time.time()-t0)/60:.1f}min")
    for k, nm in enumerate(FEAT):
        v = X[:, :, k][np.isfinite(X[:, :, k])]
        print(f"  {nm:12s} n={len(v):>9,}  中位 {np.median(v):+.5g}" if len(v) else f"  {nm:12s} 全空")
    np.savez_compressed("/workspace/data/book1p_hourly.npz", X=X, ts=TS,
                        symbols=np.array(SYMS, object), feats=np.array(FEAT, object), lag_ms=LAG)
    print("saved /workspace/data/book1p_hourly.npz")
