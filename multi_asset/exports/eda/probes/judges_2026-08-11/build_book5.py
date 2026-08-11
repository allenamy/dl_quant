"""book v2: 五带×两侧结构化面板。输出 (T,N,22): share_mean/std × (5,2) + dep_lvl + dep_chg1h。
带序 level0=±1% ... level4=±5%(有序空间轴)。因果滞后 1h。格式跨年兼容("-1"/"-1.00")。"""
import glob, gzip, os, time
import datetime as dt
from concurrent.futures import ProcessPoolExecutor
import numpy as np

BD = "/workspace/data/raw/bookDepth"
P = np.load("/workspace/data/panel_targets.npz", allow_pickle=True)
TS = np.asarray(P["ts"]).astype(np.int64)
SYMS = [str(s) for s in P["symbols"]]
SI = {s: i for i, s in enumerate(SYMS)}
T, N = len(TS), len(SYMS)
ROW = {int(t): i for i, t in enumerate(TS)}
LAG = 3600_000
LV = {"-1":(0,0),"-1.00":(0,0),"-2":(1,0),"-2.00":(1,0),"-3":(2,0),"-3.00":(2,0),
      "-4":(3,0),"-4.00":(3,0),"-5":(4,0),"-5.00":(4,0),
      "1":(0,1),"1.00":(0,1),"2":(1,1),"2.00":(1,1),"3":(2,1),"3.00":(2,1),
      "4":(3,1),"4.00":(3,1),"5":(4,1),"5.00":(4,1)}

def one_sym(sym):
    j = SI.get(sym)
    if j is None: return None
    acc = {}
    for fp in sorted(glob.glob(f"{BD}/{sym}-2*.csv.gz")):
        try:
            with gzip.open(fp, "rt") as f:
                f.readline()
                cur = None; frame = np.zeros((5, 2))
                got = 0
                for ln in f:
                    i1 = ln.find(","); i2 = ln.find(",", i1+1)
                    lv = LV.get(ln[i1+1:i2])
                    if lv is None: continue
                    tstr = ln[:i1]
                    if tstr != cur:
                        if cur is not None and got >= 8:
                            h = int(dt.datetime.strptime(cur, "%Y-%m-%d %H:%M:%S")
                                    .replace(tzinfo=dt.timezone.utc).timestamp()) // 3600 * 3600000
                            acc.setdefault(h, []).append(frame.copy())
                        cur = tstr; frame[:] = 0; got = 0
                    i3 = ln.find(",", i2+1)
                    frame[lv[0], lv[1]] = float(ln[i2+1:i3]); got += 1
                if cur is not None and got >= 8:
                    h = int(dt.datetime.strptime(cur, "%Y-%m-%d %H:%M:%S")
                            .replace(tzinfo=dt.timezone.utc).timestamp()) // 3600 * 3600000
                    acc.setdefault(h, []).append(frame.copy())
        except Exception:
            continue
    if not acc: return None
    hrs = sorted(acc)
    meds = {}
    out = []
    for h in hrs:
        a = np.asarray(acc[h])              # (F,5,2) 帧×带×侧, 累计深度
        if len(a) < 20: continue
        # 累计→逐带增量(带是累计定义: ±2% 含 ±1%): diff 沿 level 轴
        inc = a.copy()
        inc[:, 1:, :] = a[:, 1:, :] - a[:, :-1, :]
        tot = a[:, 4, :].sum(-1)            # 全带双侧
        m = float(np.median(tot))
        meds[h] = m
        out.append((h, inc, m))
    res = []
    hs = [o[0] for o in out]; ms = [o[2] for o in out]
    for k, (h, inc, mv) in enumerate(out):
        lo = max(0, k - 720)
        base = float(np.median(ms[lo:k+1]))
        if base <= 0: continue
        share = inc / base                   # (F,5,2) 尺度无关
        f = np.empty(22, np.float32)
        f[:10] = share.mean(0).ravel()       # share_mean (5×2)
        f[10:20] = share.std(0).ravel()      # share_std  (5×2)
        f[20] = np.log(max(mv, 1e-12) / base)
        f[21] = (np.log(mv / ms[k-1]) if k > 0 and ms[k-1] > 0 and hs[k]-hs[k-1] == 3600000 else np.nan)
        i = ROW.get(h + LAG)
        if i is not None: res.append((i, j, f))
    return res

if __name__ == "__main__":
    t0 = time.time()
    have = sorted({os.path.basename(f).rsplit("-", 3)[0] for f in glob.glob(f"{BD}/*.csv.gz")})
    todo = [s for s in have if s in SI]
    print(f"币 {len(todo)}  面板 {T:,}h", flush=True)
    X = np.full((T, N, 22), np.nan, np.float32)
    done = 0
    with ProcessPoolExecutor(max_workers=14) as ex:
        for r in ex.map(one_sym, todo):
            done += 1
            if r:
                for i, j, f in r: X[i, j] = f
            if done % 20 == 0: print(f"  {done}/{len(todo)} {(time.time()-t0)/60:.1f}min", flush=True)
    print(f"填充 {np.isfinite(X[:,:,0]).mean():.4f}  {(time.time()-t0)/60:.1f}min")
    FEAT = [f"sh_m_L{l}{'ba'[s]}" for l in range(5) for s in (0,1)] + \
           [f"sh_s_L{l}{'ba'[s]}" for l in range(5) for s in (0,1)] + ["dep_lvl","dep_chg1h"]
    np.savez_compressed("/workspace/data/book5_hourly.npz", X=X, ts=TS,
                        symbols=np.array(SYMS, object), feats=np.array(FEAT, object), lag_ms=LAG)
    print("saved book5_hourly.npz")
