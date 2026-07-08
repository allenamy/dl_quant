#!/usr/bin/env python3
"""Phase-0b/A — WIDE-UNIVERSE dump (1h klines + funding) for the funding_ema breadth bet.

> **created:** 2026-07-08 | **Session:** multi-asset-v2 phase-0b→A (0B) | **状态:** in-progress

Scale the ONE real factor (funding_ema) by breadth: ~60 liquid USDT-perps instead of 14. funding
needs NO 1s bars — just funding rates + 1h klines (for point-in-time dollar-volume liquidity
ranking + 1h forward returns as the target). All from data.binance.vision monthly archives
(FAPI REST + S3 listing both blocked from jpline; the CDN file archive is reachable).

We dump a BROAD candidate list; symbols with no archive 404 out (skipped), and downstream the
rolling dollar-volume rank + listing-aware availability select the point-in-time top ~60 (no
survivorship — a coin is only eligible on dates it has klines).

Output: data/wide/<SYM>_klines_1h.csv (openTime_ms,open,high,low,close,volume,quote_volume)
        data/wide/<SYM>_funding.csv   (fundingTime_ms,funding_interval_h,fundingRate)
Parallel (ThreadPool), nohup-friendly, idempotent (skips >200-byte files).
Usage: python multi_asset/data/dump_wide_universe.py [start YYYY-MM-DD] [end YYYY-MM-DD] [workers]
"""
from __future__ import annotations
import csv, datetime as dt, io, os, sys, time, urllib.error, urllib.request, zipfile
from concurrent.futures import ThreadPoolExecutor

OUTDIR = "data/wide"
KLINE = "https://data.binance.vision/data/futures/um/monthly/klines"
FUND = "https://data.binance.vision/data/futures/um/monthly/fundingRate"
WORKERS = 32

CANDIDATES = [
    # core 14
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT", "LINKUSDT",
    "BCHUSDT", "TRXUSDT", "LTCUSDT", "DOTUSDT", "FILUSDT", "ETCUSDT",
    # L1/L2
    "AVAXUSDT", "POLUSDT", "MATICUSDT", "NEARUSDT", "APTUSDT", "ARBUSDT", "OPUSDT", "SUIUSDT",
    "SEIUSDT", "TIAUSDT", "INJUSDT", "ATOMUSDT", "ICPUSDT", "HBARUSDT", "ALGOUSDT", "VETUSDT",
    "EGLDUSDT", "FLOWUSDT", "KASUSDT", "TONUSDT", "STXUSDT", "MANTAUSDT", "STRKUSDT", "ZKUSDT",
    "KAVAUSDT", "ROSEUSDT", "CELOUSDT", "ONEUSDT", "IOTAUSDT", "NEOUSDT", "QTUMUSDT", "ONTUSDT",
    "EOSUSDT", "XLMUSDT", "XTZUSDT", "ZILUSDT", "WAVESUSDT", "KSMUSDT", "THETAUSDT",
    # DeFi
    "UNIUSDT", "AAVEUSDT", "MKRUSDT", "LDOUSDT", "RUNEUSDT", "CRVUSDT", "SNXUSDT", "COMPUSDT",
    "SUSHIUSDT", "1INCHUSDT", "YFIUSDT", "DYDXUSDT", "GMXUSDT", "ENSUSDT", "PENDLEUSDT", "CAKEUSDT",
    # meme
    "1000PEPEUSDT", "1000SHIBUSDT", "1000FLOKIUSDT", "1000BONKUSDT", "WIFUSDT", "BOMEUSDT",
    "MEMEUSDT", "1000LUNCUSDT", "1000RATSUSDT", "1000SATSUSDT", "ORDIUSDT",
    # AI / DePIN
    "FETUSDT", "RENDERUSDT", "RNDRUSDT", "TAOUSDT", "WLDUSDT", "ARUSDT", "AGIXUSDT", "OCEANUSDT",
    "IOUSDT", "AKTUSDT", "GRTUSDT",
    # gaming / NFT / social
    "SANDUSDT", "MANAUSDT", "AXSUSDT", "GALAUSDT", "APEUSDT", "IMXUSDT", "GMTUSDT", "ENJUSDT",
    "CHZUSDT", "MASKUSDT", "CHRUSDT", "JUPUSDT", "PYTHUSDT", "JTOUSDT",
    # new 2024
    "ONDOUSDT", "ENAUSDT", "WUSDT", "ETHFIUSDT", "REZUSDT", "NOTUSDT", "ZROUSDT", "LISTAUSDT",
    "OMNIUSDT", "SAGAUSDT", "TNSRUSDT", "AEVOUSDT", "ALTUSDT", "PIXELUSDT", "PORTALUSDT",
    "DYMUSDT", "STGUSDT", "ARKMUSDT", "SUPERUSDT",
    # majors / classics
    "ZECUSDT", "DASHUSDT", "XMRUSDT", "BATUSDT", "IOSTUSDT", "RVNUSDT", "ZRXUSDT", "OMGUSDT",
    "ANKRUSDT", "SKLUSDT", "BALUSDT", "BANDUSDT", "KNCUSDT", "STORJUSDT", "FLMUSDT", "CTSIUSDT",
]


def _get(url):
    for a in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "wide/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(1.0 * (a + 1))
        except Exception:
            time.sleep(1.0 * (a + 1))
    return None


def _months(start, end):
    m, out = dt.date(start.year, start.month, 1), []
    while m <= end:
        out.append(m); m = dt.date(m.year + (m.month // 12), (m.month % 12) + 1, 1)
    return out


def dump_klines(SYM, months, pool):
    out = os.path.join(OUTDIR, f"{SYM}_klines_1h.csv")
    if os.path.exists(out) and os.path.getsize(out) > 200:
        return "skip"
    urls = [f"{KLINE}/{SYM}/1h/{SYM}-1h-{m.strftime('%Y-%m')}.zip" for m in months]
    blobs = list(pool.map(_get, urls))
    rows, miss = [], 0
    for data in blobs:
        if data is None:
            miss += 1; continue
        try:
            z = zipfile.ZipFile(io.BytesIO(data)); lines = z.read(z.namelist()[0]).decode().splitlines()
            for ln in lines:
                pp = ln.split(",")
                if len(pp) >= 8 and pp[0].strip().lstrip("-").isdigit():
                    # openTime, open, high, low, close, volume, closeTime, quote_asset_volume
                    rows.append((int(pp[0]), pp[1], pp[2], pp[3], pp[4], pp[5], pp[7]))
        except Exception:
            miss += 1
    if not rows:
        return f"NODATA ({miss} m miss)"
    rows.sort()
    with open(out, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["openTime_ms", "open", "high", "low", "close", "volume", "quote_volume"])
        w.writerows(rows)
    return f"{len(rows)} rows ({miss} m miss)"


def dump_funding(SYM, months, pool):
    out = os.path.join(OUTDIR, f"{SYM}_funding.csv")
    if os.path.exists(out) and os.path.getsize(out) > 200:
        return "skip"
    urls = [f"{FUND}/{SYM}/{SYM}-fundingRate-{m.strftime('%Y-%m')}.zip" for m in months]
    blobs = list(pool.map(_get, urls))
    rows, miss = [], 0
    for data in blobs:
        if data is None:
            miss += 1; continue
        try:
            z = zipfile.ZipFile(io.BytesIO(data)); lines = z.read(z.namelist()[0]).decode().splitlines()
            for ln in lines[1:]:
                pp = ln.split(",")
                if len(pp) >= 3 and pp[0].strip().isdigit():
                    rows.append((int(pp[0]), int(pp[1]), pp[2]))
        except Exception:
            miss += 1
    if not rows:
        return f"NODATA ({miss} m miss)"
    rows.sort()
    with open(out, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["fundingTime_ms", "funding_interval_h", "fundingRate"])
        w.writerows(rows)
    return f"{len(rows)} rows"


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    s = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else dt.date(2024, 5, 1)
    e = dt.date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else dt.date(2025, 10, 1)
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else WORKERS
    months = _months(s, e)
    cands = sorted(set(CANDIDATES))
    t0 = time.time(); n_ok = 0
    print(f"[wide] {len(cands)} candidates, {len(months)} months, workers={workers}", flush=True)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, SYM in enumerate(cands):
            rk = dump_klines(SYM, months, pool)
            rf = dump_funding(SYM, months, pool)
            if "rows" in rk or rk == "skip":
                n_ok += 1
            print(f"[{i+1}/{len(cands)}] {SYM:14s} klines={rk:22s} funding={rf}  ({(time.time()-t0)/60:.1f}min)", flush=True)
    print(f"[wide] DONE {n_ok}/{len(cands)} with data in {(time.time()-t0)/60:.1f}min -> {OUTDIR}", flush=True)


if __name__ == "__main__":
    main()
