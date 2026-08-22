"""F7 · Binance 永续 metrics(5-min: OI / OI 价值 / 大户账户多空比 / 大户持仓多空比 / 全体账户多空比 / 主动买卖量比)流式提取器(本机后台; §A-1 B 级项, 不在今日 S1 装置内)。
目的: P1-P4 的 400 全宇宙判决需要 wide_metrics_ch(140 名)之外的 ~580 名; 每日文件 ~30KB × ~1M ⇒ 不落原始 zip, 只保留每小时最后一条 5-min 记录(小时末状态)。
输出: <out>/<sym>.npz: days(YYYYMMDD int), X(n_days, 24, 6) float32 [sum_open_interest, sum_open_interest_value, count_toptrader_long_short_ratio, sum_toptrader_long_short_ratio, count_long_short_ratio, sum_taker_long_short_vol_ratio], tmin(n_days,24) int16(该小时末记录的分钟, 便于核对陈旧); _done.json 可续。
范围: u400_union_symbols.json 每名 [max(first,2022-01), min(last,2026-06)] 整月; 可用 --skip <json> 跳过已有 140 名。
用法: python3 local_metrics_stream.py <out_dir> [nproc] [skip_symbols_json]
只读公共数据(data.binance.vision), 不碰 share/实盘。
"""
import sys, os, io, json, time, socket, zipfile, urllib.request, urllib.error, datetime as dt
from multiprocessing import Pool
import numpy as np
socket.setdefaulttimeout(60)
OUT = sys.argv[1]; NT = int(sys.argv[2]) if len(sys.argv) > 2 else 12
SKIP = set(json.load(open(sys.argv[3]))) if len(sys.argv) > 3 else set()
os.makedirs(OUT, exist_ok=True)
U = json.load(open("u400_union_symbols.json"))
COLS = ["sum_open_interest", "sum_open_interest_value", "count_toptrader_long_short_ratio", "sum_toptrader_long_short_ratio", "count_long_short_ratio", "sum_taker_long_short_vol_ratio"]
def ym2d(ym): y, m = map(int, ym.split("-")); return dt.date(y, m, 1)
def month_end(d): return (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
done_p = f"{OUT}/_done.json"; done = json.load(open(done_p)) if os.path.exists(done_p) else {}
def one_day(args):
    sym, day = args
    u = f"https://data.binance.vision/data/futures/um/daily/metrics/{sym}/{sym}-metrics-{day.isoformat()}.zip"
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
        ts = pd.to_datetime(df["create_time"]); df = df.assign(hh=ts.dt.hour.values, mm=ts.dt.minute.values).sort_values(["hh", "mm"])
        last = df.groupby("hh").tail(1).set_index("hh")
        X = np.full((24, 6), np.nan, np.float32); TM = np.full(24, -1, np.int16)
        for h, row in last.iterrows():
            h = int(h)
            if 0 <= h <= 23:
                X[h] = [float(row[c]) if c in row and pd.notna(row[c]) else np.nan for c in COLS]; TM[h] = int(row["mm"])
        return day, (X, TM)
    except Exception:
        return day, "err"
def one_sym(sym):
    if sym in done: return sym, done[sym]
    a = max(ym2d(U["first"][sym]), dt.date(2022, 1, 1)); b = min(ym2d(U["last"][sym]), dt.date(2026, 6, 1))
    if b < a: done[sym] = {"days": 0, "note": "out of range"}; return sym, done[sym]
    b = month_end(b); days = [a + dt.timedelta(days=k) for k in range((b - a).days + 1)]
    res = {}; n404 = 0; nerr = 0
    with Pool(NT) as pool:
        for day, r in pool.imap_unordered(one_day, [(sym, d) for d in days], chunksize=8):
            if r is None: n404 += 1
            elif r == "err": nerr += 1
            else: res[day] = r
    if res:
        ds = sorted(res); X = np.stack([res[d][0] for d in ds]); TM = np.stack([res[d][1] for d in ds])
        np.savez_compressed(f"{OUT}/{sym}.npz", days=np.array([int(d.strftime("%Y%m%d")) for d in ds]), X=X, tmin=TM, cols=np.array(COLS))
    done[sym] = {"days": len(res), "n404": n404, "nerr": nerr, "range": [a.isoformat(), b.isoformat()]}
    json.dump(done, open(done_p, "w"), indent=0)
    return sym, done[sym]
if __name__ == "__main__":
    t0 = time.time(); syms = [s for s in sorted(U["symbols"], key=lambda s: -U["n_anchor_member"][s]) if s not in SKIP]
    print("symbols to pull", len(syms), "skip", len(SKIP), flush=True)
    for k, s in enumerate(syms):
        sym, info = one_sym(s)
        print(k, "/", len(syms), sym, info, round(time.time() - t0), "s", flush=True)
    print("ALL DONE", round(time.time() - t0), "s", flush=True)
