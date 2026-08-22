"""F-1 · 829 名 5m K 线月度 zip 下载器(data.binance.vision 公共端点), 只拉 2020-01 → 2022-01(hist 缓存 2020 起的前段;
2022-01 仅用于 2022-01-01 00:00 边界行的 ret5)。落盘: /mnt/storage/private/work_hsy/probe_artifacts/f1/klines5m/<sym>/<ym>.zip ;
404 ⇒ <ym>.zip.404 标记; 可续跑。用法: python jp_pull_klines5m_2020_21.py 2020-01 2022-01 [nproc]
(与 WA jp_pull_funding_829.py 同构, 仅 URL/目录不同)"""
import sys, os, time, socket, urllib.request, urllib.error, json
from multiprocessing import Pool
import numpy as np
socket.setdefaulttimeout(30)
B = "/mnt/storage/private/work_hsy/pod_backup_2026-08-21"
base = "/mnt/storage/private/work_hsy/probe_artifacts/f1/klines5m"
y0m, y1m = sys.argv[1], sys.argv[2]; NP = int(sys.argv[3]) if len(sys.argv) > 3 else 16
syms = [str(s) for s in np.load(f"{B}/wide_panel_4h_hist_v2.npz", allow_pickle=True)["symbols"]]
SYMS_FILE = os.environ.get("SYMS_FILE")   # 可选: 限定名单(WA 1h 2020/2021 有数的 139 名; 其余名 2020-21 不存在, 省 404 往返)
if SYMS_FILE:
    sub = set(open(SYMS_FILE).read().split()); syms = [s for s in syms if s in sub]
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
        if os.path.exists(p) and os.path.getsize(p) > 50: got += 1; continue
        if os.path.exists(p + ".404"): miss.append(ym); continue
        u = f'https://data.binance.vision/data/futures/um/monthly/klines/{s}/5m/{s}-5m-{ym}.zip'
        ok = False
        for att in range(4):
            try:
                urllib.request.urlretrieve(u, p); got += 1; ok = True; break
            except urllib.error.HTTPError as e:
                if os.path.exists(p): os.remove(p)
                if e.code == 404:
                    open(p + ".404", "w").close(); miss.append(ym); break
                time.sleep(1 + att)
            except Exception as e:
                if os.path.exists(p): os.remove(p)
                time.sleep(1 + att)
        if not ok and ym not in miss: err.append(ym)
        time.sleep(0.02)
    return s, got, miss, err
if __name__ == "__main__":
    t0 = time.time(); res = {}
    print("panel syms", len(syms), "months", len(ms), flush=True)
    with Pool(NP) as pool:
        for k, (s, got, miss, err) in enumerate(pool.imap_unordered(work, syms)):
            res[s] = {"got": got, "miss404": len(miss), "err": err}
            if k % 25 == 0: print(k, "/", len(syms), s, got, len(miss), len(err), round(time.time() - t0), "s", flush=True)
    json.dump(res, open(f"{base}/_pull_report.json", "w"), indent=1)
    ng = sum(v["got"] for v in res.values()); nm = sum(v["miss404"] for v in res.values()); ne = sum(len(v["err"]) for v in res.values())
    print("DONE got", ng, "miss404", nm, "err", ne, round(time.time() - t0), "s", flush=True)
