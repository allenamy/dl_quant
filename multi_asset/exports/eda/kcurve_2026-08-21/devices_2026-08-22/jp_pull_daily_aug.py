"""WS · 影子窗口(2026-08-15..08-22)逐日 1h + 5m K 线拉取 @jpline(data.binance.vision daily zip; 与 jp_wide1h_pull 同源同法).
目的: 影子 score 行(08-16→08-21)与三收益源对账. 落盘 w3lane/wide_daily_aug/<sym>/<iv>/<date>.zip; 已存在即跳过; 404 记 missing.
用法: python jp_pull_daily_aug.py symsfile.json 2026-08-15 2026-08-22 [nproc]"""
import sys, os, time, json, socket, urllib.request, urllib.error, datetime as dt
from multiprocessing import Pool
socket.setdefaulttimeout(30)
base = "/mnt/storage/private/work_hsy/w3lane/wide_daily_aug"
cfg = json.load(open(sys.argv[1])); syms = cfg["symbols_live"]
d0 = dt.date.fromisoformat(sys.argv[2]); d1 = dt.date.fromisoformat(sys.argv[3]); NP = int(sys.argv[4]) if len(sys.argv) > 4 else 12
days = [(d0 + dt.timedelta(k)).isoformat() for k in range((d1 - d0).days + 1)]
def work(s):
    got = 0; miss = []; err = []
    for iv in ("1h", "5m"):
        d = f"{base}/{s}/{iv}"; os.makedirs(d, exist_ok=True)
        for day in days:
            p = f"{d}/{day}.zip"
            if os.path.exists(p) and os.path.getsize(p) > 100: got += 1; continue
            u = f"https://data.binance.vision/data/futures/um/daily/klines/{s}/{iv}/{s}-{iv}-{day}.zip"
            ok = False
            for att in range(4):
                try:
                    urllib.request.urlretrieve(u, p); got += 1; ok = True; break
                except urllib.error.HTTPError as e:
                    if os.path.exists(p): os.remove(p)
                    if e.code == 404: miss.append(f"{iv}/{day}"); break
                    time.sleep(1 + att)
                except Exception:
                    if os.path.exists(p): os.remove(p)
                    time.sleep(1 + att)
            if not ok and f"{iv}/{day}" not in miss: err.append(f"{iv}/{day}")
            time.sleep(0.02)
    return s, got, miss, err
if __name__ == "__main__":
    t0 = time.time(); res = {}
    with Pool(NP) as pool:
        for k, (s, got, miss, err) in enumerate(pool.imap_unordered(work, syms)):
            res[s] = {"got": got, "miss404": miss, "err": err}
            if k % 50 == 0: print(k, "/", len(syms), s, got, len(miss), len(err), round(time.time() - t0), "s", flush=True)
    json.dump(res, open(f"{base}/_pull_report.json", "w"), indent=1)
    ng = sum(v["got"] for v in res.values()); nm = sum(len(v["miss404"]) for v in res.values()); ne = sum(len(v["err"]) for v in res.values())
    print("DONE got", ng, "miss404", nm, "err", ne, round(time.time() - t0), "s", flush=True)
