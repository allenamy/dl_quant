"""F7 · Binance 永续 bookDepth(±1..5% 档名义深度, ~30s 快照)流式提取器(本机后台; §A-4 B 级项, 不在今日 S1 装置内)。
每个 (symbol, day) 日 zip(~440KB)下载到内存(进程池, 每日一任务) → pandas 按小时聚合(各档 notional 的小时均值 + 小时内最后一个快照)→ 丢弃原文件(本机仅 36GB 余, 不落原始 zip)。
输出: <out>/<sym>.npz: days(YYYYMMDD int), H(n_days, 24, 10, 2) float32 [mean, last] for levels [-5,-4,-3,-2,-1,1,2,3,4,5] (notional, USDT), nsnap(n_days,24) int16; 进度文件 _done.json 可续。
范围: u400_union_symbols.json 每名 [max(first,2023-01), min(last,2026-06)] 整月。
用法: python3 local_bookdepth_stream.py <out_dir> [nthreads]
只读公共数据(data.binance.vision), 不碰 share/实盘。
"""
import sys, os, io, json, time, socket, zipfile, urllib.request, urllib.error, datetime as dt
from multiprocessing import Pool
import numpy as np
socket.setdefaulttimeout(60)
OUT = sys.argv[1]; NT = int(sys.argv[2]) if len(sys.argv) > 2 else 24
os.makedirs(OUT, exist_ok=True)
U = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "f7_u400_union_symbols.json")) if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "f7_u400_union_symbols.json")) else open("u400_union_symbols.json"))
LEV = [-5, -4, -3, -2, -1, 1, 2, 3, 4, 5]; LI = {l: i for i, l in enumerate(LEV)}
def ym2d(ym): y, m = map(int, ym.split("-")); return dt.date(y, m, 1)
def month_end(d): return (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
done_p = f"{OUT}/_done.json"; done = json.load(open(done_p)) if os.path.exists(done_p) else {}
def one_day(args):
    sym, day = args
    u = f"https://data.binance.vision/data/futures/um/daily/bookDepth/{sym}/{sym}-bookDepth-{day.isoformat()}.zip"
    raw = None
    for att in range(4):
        try:
            with urllib.request.urlopen(u) as r: raw = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code == 404: return day, None
            time.sleep(1 + att)
        except Exception:
            time.sleep(1 + att)
    if raw is None: return day, "err"
    try:
        import pandas as pd
        z = zipfile.ZipFile(io.BytesIO(raw)); df = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])))
        df = df[df["percentage"].isin(LEV)]
        hh = df["timestamp"].str.slice(11, 13).astype(int); df = df.assign(hh=hh)
        g = df.groupby(["hh", "percentage"])["notional"].agg(["mean", "last", "count"])
        M = np.full((24, 10), np.nan, np.float32); L = np.full((24, 10), np.nan, np.float32); C = np.zeros((24, 10), np.int16)
        for (h, lv), row in g.iterrows():
            j = LI[int(lv)]; M[h, j] = row["mean"]; L[h, j] = row["last"]; C[h, j] = min(int(row["count"]), 32000)
        return day, (M, L, C[:, 0])
    except Exception:
        return day, "err"
def one_sym(sym):
    if sym in done: return sym, done[sym]
    a = max(ym2d(U["first"][sym]), dt.date(2023, 1, 1)); b = min(ym2d(U["last"][sym]), dt.date(2026, 6, 1))
    if b < a: done[sym] = {"days": 0, "note": "out of range"}; return sym, done[sym]
    b = month_end(b); days = [a + dt.timedelta(days=k) for k in range((b - a).days + 1)]
    res = {}; n404 = 0; nerr = 0
    with Pool(NT) as pool:
        for day, r in pool.imap_unordered(one_day, [(sym, d) for d in days], chunksize=8):
            if r is None: n404 += 1
            elif r == "err": nerr += 1
            else: res[day] = r
    if res:
        ds = sorted(res); H = np.stack([np.stack([res[d][0], res[d][1]], -1) for d in ds]); NS = np.stack([res[d][2] for d in ds])
        np.savez_compressed(f"{OUT}/{sym}.npz", days=np.array([int(d.strftime("%Y%m%d")) for d in ds]), H=H, nsnap=NS, levels=np.array(LEV))
    done[sym] = {"days": len(res), "n404": n404, "nerr": nerr, "range": [a.isoformat(), b.isoformat()]}
    json.dump(done, open(done_p, "w"), indent=0)
    return sym, done[sym]
if __name__ == "__main__":
    t0 = time.time(); syms = U["symbols"]
    # majors/long-lived first (most U400 anchor-membership)
    syms = sorted(syms, key=lambda s: -U["n_anchor_member"][s])
    for k, s in enumerate(syms):
        sym, info = one_sym(s)
        print(k, "/", len(syms), sym, info, round(time.time() - t0), "s", flush=True)
    print("ALL DONE", round(time.time() - t0), "s", flush=True)
