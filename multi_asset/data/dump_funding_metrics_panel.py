#!/usr/bin/env python3
"""Phase-0b/A — dump 14-asset FUNDING + METRICS (OI/positioning) for the multi-asset-v2 panel.

> **created:** 2026-07-08 | **Session:** multi-asset-v2 phase-0b→A (0B) | **状态:** in-progress
> **2026-07-08 PARALLELIZED:** the archive fetch is NETWORK-bound (data.binance.vision daily 5m
>   ZIPs, ~8.6s/day single-threaded → ~70min/asset). Replaced the serial day-loop with a
>   ThreadPoolExecutor over (asset, day) tasks (WORKERS=32) → near-linear wall-clock cut. Assembly
>   is deterministic (chronological) and identical byte-for-byte to the serial version.

Extends the BTC-only dumps to all 14 panel perps. FULL history is public (no 30-day limit):
- FUNDING: data.binance.vision monthly fundingRate ZIPs (calc_time, funding_interval_h, rate).
- METRICS: data.binance.vision/data/futures/um/daily/metrics/<SYM>/ daily 5m ZIPs
  (sum_open_interest[_value], count/sum_toptrader_long_short_ratio = account/position ratio,
   count_long_short_ratio = global account ratio, sum_taker_long_short_vol_ratio).
All leak-safe downstream (funding stamped at settlement; metrics 5m; ffill ≤t at align time).

Output: data/funding/<sym>_funding.csv + <sym>_metrics_5m.csv for sym in the 14 panel coins.
nohup-friendly (survives an agent rate-limit). Idempotent (skips existing non-empty files).
Usage: python multi_asset/data/dump_funding_metrics_panel.py [start YYYY-MM-DD] [end YYYY-MM-DD] [workers]
"""
from __future__ import annotations
import csv, datetime as dt, io, os, sys, time, urllib.error, urllib.request, zipfile
from concurrent.futures import ThreadPoolExecutor

OUTDIR = "data/funding"
VISION = "https://data.binance.vision/data/futures/um/daily/metrics"
FUND_VISION = "https://data.binance.vision/data/futures/um/monthly/fundingRate"
# panel internal name -> Binance USDT-perp symbol
PANEL = {"bnfbtc": "BTCUSDT", "bnfeth": "ETHUSDT", "bnfsol": "SOLUSDT", "bnfbnb": "BNBUSDT",
         "bnfxrp": "XRPUSDT", "bnfdog": "DOGEUSDT", "bnfada": "ADAUSDT", "bnflink": "LINKUSDT",
         "bnfbch": "BCHUSDT", "bnftrx": "TRXUSDT", "bnfltc": "LTCUSDT", "bnfdot": "DOTUSDT",
         "bnffil": "FILUSDT", "bnfetc": "ETCUSDT"}
WORKERS = 32


def _get_zip(url):
    for a in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "metrics-dump/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(1.2 * (a + 1))
        except Exception:
            time.sleep(1.2 * (a + 1))
    return None


def _fetch_all(urls, pool):
    """Fetch a list of urls concurrently; return list of bytes|None in the SAME order."""
    return list(pool.map(_get_zip, urls))


def dump_funding(sym_int, SYM, start, end, pool):
    """Funding from the VISION MONTHLY bulk archive (calc_time, funding_interval_hours,
    last_funding_rate). Server-reachable (unlike the FAPI REST endpoint)."""
    out = os.path.join(OUTDIR, f"{sym_int}_funding.csv")
    if os.path.exists(out) and os.path.getsize(out) > 200:
        return "skip"
    months = []
    m = dt.date(start.year, start.month, 1)
    while m <= end:
        months.append(m)
        m = dt.date(m.year + (m.month // 12), (m.month % 12) + 1, 1)
    urls = [f"{FUND_VISION}/{SYM}/{SYM}-fundingRate-{mm.strftime('%Y-%m')}.zip" for mm in months]
    blobs = _fetch_all(urls, pool)
    rows, miss = [], 0
    for data in blobs:  # months are already chronological
        if data is not None:
            try:
                z = zipfile.ZipFile(io.BytesIO(data)); lines = z.read(z.namelist()[0]).decode().splitlines()
                for ln in lines[1:]:
                    p = ln.split(",")
                    if len(p) >= 3 and p[0].strip().isdigit():
                        rows.append((int(p[0]), int(p[1]), p[2]))   # calc_time, interval_h, rate
            except Exception:
                miss += 1
        else:
            miss += 1
    rows.sort()
    with open(out, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["fundingTime_ms", "funding_interval_h", "fundingRate"])
        for t, ih, r in rows:
            w.writerow([t, ih, r])
    return f"{len(rows)} rows ({miss} m miss)"


def dump_metrics(sym_int, SYM, start, end, pool):
    out = os.path.join(OUTDIR, f"{sym_int}_metrics_5m.csv")
    if os.path.exists(out) and os.path.getsize(out) > 200:
        return "skip"
    days = []
    d = start
    while d <= end:
        days.append(d); d += dt.timedelta(days=1)
    urls = [f"{VISION}/{SYM}/{SYM}-metrics-{dd.strftime('%Y-%m-%d')}.zip" for dd in days]
    blobs = _fetch_all(urls, pool)
    header, rows, missing = None, [], 0
    for data in blobs:  # days are already chronological -> byte-identical to serial assembly
        if data is not None:
            try:
                z = zipfile.ZipFile(io.BytesIO(data)); lines = z.read(z.namelist()[0]).decode().splitlines()
                if lines:
                    if header is None: header = lines[0]
                    rows.extend(lines[1:])
            except Exception:
                missing += 1
        else:
            missing += 1
    with open(out, "w") as f:
        if header: f.write(header + "\n")
        f.write("\n".join(rows) + ("\n" if rows else ""))
    return f"{len(rows)} rows ({missing} d miss)"


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    s = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else dt.date(2024, 5, 1)
    e = dt.date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else dt.date(2025, 10, 1)
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else WORKERS
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, (sym_int, SYM) in enumerate(PANEL.items()):
            rf = dump_funding(sym_int, SYM, s, e, pool)
            rm = dump_metrics(sym_int, SYM, s, e, pool)
            print(f"[{i+1}/14] {sym_int:8s} {SYM:10s} funding={rf:16s} metrics={rm}  ({(time.time()-t0)/60:.1f}min)", flush=True)
    print(f"[dump] DONE 14 assets in {(time.time()-t0)/60:.1f}min -> {OUTDIR}", flush=True)


if __name__ == "__main__":
    main()
