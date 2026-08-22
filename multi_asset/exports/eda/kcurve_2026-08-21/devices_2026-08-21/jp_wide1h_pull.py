"""W2b · 宽 829 名 1h kline 下载器(data.binance.vision 月度 zip; 与 w3lane/jp_wide5m_pull.py 同源同法, 改 1h + 全 829 名 + 进程池).
目的: 为两书合成书提供【同一时钟】的逐名 4h 前向收益(live 时钟 T+1h→T+5h = 1h bar close[T+4h]/close[T]).
落盘: /mnt/storage/private/work_hsy/w3lane/wide1h_csv/<sym>/<ym>.zip; 已存在即跳过(可续); 404 记入 missing.txt。只读公共数据, 不碰 share/实盘。
用法: python3 jp_wide1h_pull.py 2022-01 2026-07 [nproc]
"""
import sys, os, time, socket, urllib.request, urllib.error, json
from multiprocessing import Pool
import numpy as np
socket.setdefaulttimeout(30)
B = "/mnt/storage/private/work_hsy/pod_backup_2026-08-21"
base = "/mnt/storage/private/work_hsy/w3lane/wide1h_csv"
y0m, y1m = sys.argv[1], sys.argv[2]; NP = int(sys.argv[3]) if len(sys.argv) > 3 else 12
syms = [str(s) for s in np.load(f"{B}/wide_panel_4h_hist_v2.npz", allow_pickle=True)["symbols"]]
def months(a, b):
    ya, ma = map(int, a.split('-')); yb, mb = map(int, b.split('-')); out = []
    while (ya, ma) <= (yb, mb):
        out.append(f'{ya}-{ma:02d}'); ma += 1
        if ma > 12: ma = 1; ya += 1
    return out
ms = months(y0m, y1m)
os.makedirs(base, exist_ok=True)
def work(s):
    d = f'{base}/{s}'; os.makedirs(d, exist_ok=True); got = 0; miss = []; err = []
    for ym in ms:
        p = f'{d}/{ym}.zip'
        if os.path.exists(p) and os.path.getsize(p) > 100: got += 1; continue
        u = f'https://data.binance.vision/data/futures/um/monthly/klines/{s}/1h/{s}-1h-{ym}.zip'
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
    with Pool(NP) as pool:
        for k, (s, got, miss, err) in enumerate(pool.imap_unordered(work, syms)):
            res[s] = {"got": got, "miss404": miss, "err": err}
            if k % 25 == 0: print(k, "/", len(syms), s, got, len(miss), len(err), round(time.time() - t0), "s", flush=True)
    json.dump(res, open(f"{base}/_pull_report.json", "w"), indent=1)
    ng = sum(v["got"] for v in res.values()); nm = sum(len(v["miss404"]) for v in res.values()); ne = sum(len(v["err"]) for v in res.values())
    print("DONE got", ng, "miss404", nm, "err", ne, round(time.time() - t0), "s", flush=True)
