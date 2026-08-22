"""F7 · 本机版现货 1h kline 下载器(线程池; 与 jp_spot1h_pull.py 同法同落盘结构; 之后 rsync 到 jpline w3lane/spot1h_csv)."""
import sys, os, time, json, socket, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
socket.setdefaulttimeout(30)
base = sys.argv[1]; y0m, y1m = sys.argv[2], sys.argv[3]; NT = int(sys.argv[4]) if len(sys.argv) > 4 else 32
MAP = json.load(open("f7_spot_map.json"))["map"]
def months(a, b):
    ya, ma = map(int, a.split('-')); yb, mb = map(int, b.split('-')); out = []
    while (ya, ma) <= (yb, mb):
        out.append(f'{ya}-{ma:02d}'); ma += 1
        if ma > 12: ma = 1; ya += 1
    return out
ms = months(y0m, y1m); syms = sorted(set(v for v in MAP.values() if v))
os.makedirs(base, exist_ok=True)
jobs = [(s, ym) for s in syms for ym in ms]
def one(j):
    s, ym = j; d = f'{base}/{s}'; os.makedirs(d, exist_ok=True); p = f'{d}/{ym}.zip'
    if os.path.exists(p) and os.path.getsize(p) > 100: return s, ym, "have"
    u = f'https://data.binance.vision/data/spot/monthly/klines/{s}/1h/{s}-1h-{ym}.zip'
    for att in range(4):
        try:
            urllib.request.urlretrieve(u, p); return s, ym, "got"
        except urllib.error.HTTPError as e:
            if os.path.exists(p): os.remove(p)
            if e.code == 404: return s, ym, "404"
            time.sleep(1 + att)
        except Exception:
            if os.path.exists(p): os.remove(p)
            time.sleep(1 + att)
    return s, ym, "err"
t0 = time.time(); cnt = {"have": 0, "got": 0, "404": 0, "err": 0}; rep = {}
print("symbols", len(syms), "months", len(ms), "jobs", len(jobs), "threads", NT, flush=True)
with ThreadPoolExecutor(NT) as ex:
    futs = [ex.submit(one, j) for j in jobs]
    for k, f in enumerate(as_completed(futs)):
        s, ym, st = f.result(); cnt[st] += 1; rep.setdefault(s, {}).setdefault(st, []).append(ym)
        if k % 2000 == 0: print(k, cnt, round(time.time() - t0), "s", flush=True)
json.dump({"counts": cnt, "per_symbol": {s: {k: sorted(v) for k, v in d.items()} for s, d in rep.items()}}, open(f"{base}/_pull_report.json", "w"), indent=0)
print("DONE", cnt, round(time.time() - t0), "s", flush=True)
