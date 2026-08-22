"""F2 · 宽 829 名 premiumIndexKlines 1h 月度 zip 下载器 + 小时网格构建(data.binance.vision 公共端点, 只读行情; Session 6737834a-F2).
落盘: /mnt/storage/private/work_hsy/probe_artifacts/f2/premium_csv/<sym>/<ym>.zip ; 404 ⇒ <ym>.zip.404 标记; 可续跑.
  pull  : python f2_pull_premium_829.py pull  2021-01 2026-07 [nproc] [rev]   — 每名只拉 [首个有收盘月, 末个有收盘月] ∩ [y0m, y1m](来自 wa/syms829_span.json)
  daily : python f2_pull_premium_829.py daily 2026-08-01 2026-08-21 [nproc] — 8 月逐日 zip(只拉末收盘 ≥ 2026-08-01 的名)
  build : python f2_pull_premium_829.py build                          — 汇成 premium_1h_829.npz(ts_hour = bar open time ms, 与 basis_premium_1h.npz 同约定; PREM float32 (nH, 829))
语义: premiumIndexKlines close = 该小时 bar 收盘时的溢价指数 (mark − index)/index; bar open=t 的 close 在 t+1h 已知 ⇒ 锚 N 用 open=N−1h 的行(FF/RC 同约定 "PREM 行 N−1h").
"""
import sys, os, time, socket, urllib.request, urllib.error, json, zipfile, datetime as dt
from multiprocessing import Pool
import numpy as np
socket.setdefaulttimeout(30)
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; WA = f"{PD}/wa"; F2 = f"{PD}/f2"; base = f"{F2}/premium_csv"
os.makedirs(base, exist_ok=True)
SPAN = json.load(open(f"{WA}/syms829_span.json"))
SYMS = SPAN["symbols"]; FIRST = SPAN["first"]; LAST = SPAN["last"]
def ym_of(ts): d = dt.datetime.fromtimestamp(int(ts), dt.timezone.utc); return (d.year, d.month)
def months(a, b):
    (ya, ma), (yb, mb) = a, b; out = []
    while (ya, ma) <= (yb, mb):
        out.append(f'{ya}-{ma:02d}'); ma += 1
        if ma > 12: ma = 1; ya += 1
    return out
def fetch(u, p):
    """返回 'ok' | '404' | 'err'"""
    if os.path.exists(p) and os.path.getsize(p) > 50: return "ok"
    if os.path.exists(p + ".404"): return "404"
    for att in range(4):
        try:
            urllib.request.urlretrieve(u, p); return "ok"
        except urllib.error.HTTPError as e:
            if os.path.exists(p): os.remove(p)
            if e.code == 404:
                open(p + ".404", "w").close(); return "404"
            time.sleep(1 + att)
        except Exception:
            if os.path.exists(p): os.remove(p)
            time.sleep(1 + att)
    return "err"
def work_month(args):
    s, ms = args; d = f'{base}/{s}'; os.makedirs(d, exist_ok=True); got = 0; miss = []; err = []
    for ym in ms:
        r = fetch(f'https://data.binance.vision/data/futures/um/monthly/premiumIndexKlines/{s}/1h/{s}-1h-{ym}.zip', f'{d}/{ym}.zip')
        if r == "ok": got += 1
        elif r == "404": miss.append(ym)
        else: err.append(ym)
        time.sleep(0.02)
    return s, got, miss, err
def work_daily(args):
    s, days = args; d = f'{base}/{s}'; os.makedirs(d, exist_ok=True); got = 0; miss = []; err = []
    for dd in days:
        r = fetch(f'https://data.binance.vision/data/futures/um/daily/premiumIndexKlines/{s}/1h/{s}-1h-{dd}.zip', f'{d}/D{dd}.zip')
        if r == "ok": got += 1
        elif r == "404": miss.append(dd)
        else: err.append(dd)
        time.sleep(0.02)
    return s, got, miss, err
def read_zip(p):
    try:
        with zipfile.ZipFile(p) as z: raw = z.read(z.namelist()[0])
    except Exception:
        return None
    ot = []; cl = []
    for ln in raw.decode("utf-8", "ignore").split("\n"):
        if not ln or ln[0] == "o": continue
        q = ln.split(",")
        try: ot.append(int(q[0])); cl.append(float(q[4]))
        except Exception: continue
    if not ot: return None
    return np.array(ot, np.int64), np.array(cl, np.float64)
def _build_sym(j):
    s = SYMS[j]; d = f'{base}/{s}'
    if not os.path.isdir(d): return j, None, 0
    rows = []; nz = 0
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".zip"): continue
        r = read_zip(f'{d}/{fn}')
        if r is None: continue
        nz += 1; rows.append(r)
    if not rows: return j, None, 0
    ot = np.concatenate([r[0] for r in rows]); cl = np.concatenate([r[1] for r in rows])
    return j, (ot, cl), nz
if __name__ == "__main__":
    mode = sys.argv[1]; t0 = time.time()
    if mode == "pull":
        y0m = tuple(map(int, sys.argv[2].split("-"))); y1m = tuple(map(int, sys.argv[3].split("-"))); NP = int(sys.argv[4]) if len(sys.argv) > 4 else 16
        tasks = []
        for s, f, l in zip(SYMS, FIRST, LAST):
            if f < 0: continue
            a = max(ym_of(f), y0m); b = min(ym_of(l), y1m)
            if a > b: continue
            tasks.append((s, months(a, b)))
        if len(sys.argv) > 5 and sys.argv[5] == "rev": tasks = tasks[::-1]      # 第二实例反向扫, 与正向实例在中间相遇(已存在文件即跳过)
        print("symbols", len(SYMS), "tasks", len(tasks), "symbol-months", sum(len(m) for _, m in tasks), flush=True)
        res = {}
        with Pool(NP) as pool:
            for k, (s, got, miss, err) in enumerate(pool.imap_unordered(work_month, tasks)):
                res[s] = {"got": got, "miss404": miss, "err": err}
                if k % 25 == 0: print(k, "/", len(tasks), s, got, len(miss), len(err), round(time.time() - t0), "s", flush=True)
        json.dump(res, open(f"{base}/_pull_report_monthly.json", "w"), indent=1)
        ng = sum(v["got"] for v in res.values()); nm = sum(len(v["miss404"]) for v in res.values()); ne = sum(len(v["err"]) for v in res.values())
        print("DONE monthly got", ng, "miss404", nm, "err", ne, round(time.time() - t0), "s", flush=True)
    elif mode == "daily":
        d0 = dt.date.fromisoformat(sys.argv[2]); d1 = dt.date.fromisoformat(sys.argv[3]); NP = int(sys.argv[4]) if len(sys.argv) > 4 else 16
        days = []; d = d0
        while d <= d1: days.append(d.isoformat()); d += dt.timedelta(days=1)
        cut = int(dt.datetime(d0.year, d0.month, d0.day, tzinfo=dt.timezone.utc).timestamp())
        tasks = [(s, days) for s, l in zip(SYMS, LAST) if l >= cut]
        print("daily tasks", len(tasks), "x", len(days), flush=True)
        res = {}
        with Pool(NP) as pool:
            for k, (s, got, miss, err) in enumerate(pool.imap_unordered(work_daily, tasks)):
                res[s] = {"got": got, "miss404": miss, "err": err}
                if k % 50 == 0: print(k, "/", len(tasks), s, got, len(miss), len(err), round(time.time() - t0), "s", flush=True)
        json.dump(res, open(f"{base}/_pull_report_daily.json", "w"), indent=1)
        print("DONE daily got", sum(v["got"] for v in res.values()), "miss404", sum(len(v["miss404"]) for v in res.values()), "err", sum(len(v["err"]) for v in res.values()), round(time.time() - t0), "s", flush=True)
    elif mode == "build":
        # grid: 与 wa/close1h_829.npz 的 ts(秒, bar 边界)同跨度; 这里按 open time ms 存, 与 basis_premium_1h.npz 同约定
        C = np.load(f"{WA}/close1h_829.npz", allow_pickle=True); cts = C["ts"].astype(np.int64); assert [str(x) for x in C["symbols"]] == SYMS
        ts_hour = cts * 1000                      # open time ms; 行 i 的 bar = [cts[i], cts[i]+1h)
        pos = {int(t): i for i, t in enumerate(ts_hour)}
        PREM = np.full((len(ts_hour), len(SYMS)), np.nan, np.float32); NZ = np.zeros(len(SYMS), int); dup = 0; oob = 0
        with Pool(16) as pool:
            for j, r, nz in pool.imap_unordered(_build_sym, range(len(SYMS))):
                NZ[j] = nz
                if r is None: continue
                ot, cl = r
                # 去重(月度与逐日可能重叠): 取最后出现
                ix = np.array([pos.get(int(t), -1) for t in ot]); ok = ix >= 0; oob += int((~ok).sum())
                u, first_idx, cnt = np.unique(ix[ok], return_index=True, return_counts=True); dup += int((cnt > 1).sum())
                PREM[ix[ok], j] = cl[ok]
        fin = np.isfinite(PREM)
        rep = {"created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "session": "6737834a-F2", "source": "data.binance.vision futures/um monthly+daily premiumIndexKlines 1h close",
               "n_hours": int(len(ts_hour)), "n_symbols": len(SYMS), "span_open_ms": [int(ts_hour[0]), int(ts_hour[-1])], "symbols_with_data": int((NZ > 0).sum()), "zips_total": int(NZ.sum()),
               "finite_frac": float(fin.mean()), "dup_cells": dup, "out_of_grid_rows": oob,
               "symbols_without_data": [SYMS[j] for j in range(len(SYMS)) if NZ[j] == 0]}
        np.savez_compressed(f"{F2}/premium_1h_829.npz", ts_hour=ts_hour, symbols=np.array(SYMS), PREM=PREM, source=np.array(rep["source"]), session=np.array("6737834a-F2"))
        json.dump(rep, open(f"{F2}/premium_1h_829_report.json", "w"), indent=1)
        print("BUILD DONE", rep, round(time.time() - t0), "s", flush=True)
