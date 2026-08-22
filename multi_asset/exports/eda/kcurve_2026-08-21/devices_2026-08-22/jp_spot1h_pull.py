"""F7 · 宽宇宙(U400 并集 727 名)对应现货 1h kline 下载器(data.binance.vision 月度 zip; 与 devices_2026-08-21/jp_wide1h_pull.py 同法, 改 spot + 映射表 + 进程池).
目的: 现货角度候选(现货成交占比 / 现货主动买入失衡 / 占比变化)需要现货 1h quoteVolume / takerBuyQuote.
落盘: /mnt/storage/private/work_hsy/w3lane/spot1h_csv/<spot_sym>/<ym>.zip; 已存在即跳过(可续); 404 记入报告。只读公共数据, 不碰 share/实盘。
用法: python3 jp_spot1h_pull.py 2021-11 2026-07 [nproc]
"""
import sys, os, time, socket, urllib.request, urllib.error, json
from multiprocessing import Pool
socket.setdefaulttimeout(30)
base = "/mnt/storage/private/work_hsy/w3lane/spot1h_csv"
MAP = json.load(open("/mnt/storage/private/work_hsy/probe_artifacts/f7/f7_spot_map.json"))["map"]
y0m, y1m = sys.argv[1], sys.argv[2]; NP = int(sys.argv[3]) if len(sys.argv) > 3 else 20
def months(a, b):
    ya, ma = map(int, a.split('-')); yb, mb = map(int, b.split('-')); out = []
    while (ya, ma) <= (yb, mb):
        out.append(f'{ya}-{ma:02d}'); ma += 1
        if ma > 12: ma = 1; ya += 1
    return out
ms = months(y0m, y1m)
syms = sorted(set(v for v in MAP.values() if v))
os.makedirs(base, exist_ok=True)
def work(s):
    d = f'{base}/{s}'; os.makedirs(d, exist_ok=True); got = 0; miss = []; err = []
    for ym in ms:
        p = f'{d}/{ym}.zip'
        if os.path.exists(p) and os.path.getsize(p) > 100: got += 1; continue
        u = f'https://data.binance.vision/data/spot/monthly/klines/{s}/1h/{s}-1h-{ym}.zip'
        ok = False
        for att in range(4):
            try:
                urllib.request.urlretrieve(u, p); got += 1; ok = True; break
            except urllib.error.HTTPError as e:
                if os.path.exists(p): os.remove(p)
                if e.code == 404: miss.append(ym); break
                time.sleep(1 + att)
            except Exception as e:
                if os.path.exists(p): os.remove(p)
                time.sleep(1 + att)
        if not ok and ym not in miss: err.append(ym)
        time.sleep(0.02)
    return s, got, miss, err
if __name__ == "__main__":
    t0 = time.time(); res = {}
    print("spot symbols", len(syms), "months", len(ms), "nproc", NP, flush=True)
    with Pool(NP) as pool:
        for k, (s, got, miss, err) in enumerate(pool.imap_unordered(work, syms)):
            res[s] = {"got": got, "miss404": miss, "err": err}
            if k % 25 == 0: print(k, "/", len(syms), s, got, len(miss), len(err), round(time.time() - t0), "s", flush=True)
    json.dump(res, open(f"{base}/_pull_report.json", "w"), indent=1)
    ng = sum(v["got"] for v in res.values()); nm = sum(len(v["miss404"]) for v in res.values()); ne = sum(len(v["err"]) for v in res.values())
    print("DONE got", ng, "miss404", nm, "err", ne, round(time.time() - t0), "s", flush=True)
