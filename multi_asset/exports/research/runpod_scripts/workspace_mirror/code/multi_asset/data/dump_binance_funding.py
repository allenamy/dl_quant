#!/usr/bin/env python3
"""Dump Binance USDT-M perp BTCUSDT funding-rate FULL history (free public API).

> Created 2026-06-24 | dual-source-perp orthogonal-data lever (funding rate).

Endpoint: GET /fapi/v1/fundingRate  (free, public, NO 30-day limit).
- Sampling = the funding settlement interval, NOT 1s. BTCUSDT = 8h (00/08/16 UTC).
- Returns {symbol, fundingTime(ms), fundingRate, markPrice}. Full history from the
  BTCUSDT perp launch (2019-09-08) to now (~6-7k rows, tiny).

Open Interest NOTE: the Binance API /futures/data/openInterestHist only serves the
LAST 30 DAYS — useless for the historical 2025-04 / 2026-05 folds. OI long-history
must come from Tardis `derivative_ticker` (the project already uses Tardis for the
book data: /mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/). This script does
funding only; OI is a separate Tardis pull.

Local-dev workflow: run LOCAL, output to data/funding/, sync to server for training.
Usage: python multi_asset/data/dump_binance_funding.py
"""
from __future__ import annotations
import csv
import datetime as dt
import json
import os
import time
import urllib.request

BASE = "https://fapi.binance.com"
SYMBOL = "BTCUSDT"
OUTDIR = "data/funding"
LAUNCH_MS = 1567900800000  # 2019-09-08 00:00 UTC — BTCUSDT perp launch
PAGE = 1000                # max limit per request


def _get(url: str):
    last_err = None
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "funding-dump/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"GET failed after retries: {url} :: {last_err}")


def dump_funding() -> str:
    os.makedirs(OUTDIR, exist_ok=True)
    start = LAUNCH_MS
    seen: set[int] = set()
    rows: list[dict] = []
    while True:
        url = f"{BASE}/fapi/v1/fundingRate?symbol={SYMBOL}&startTime={start}&limit={PAGE}"
        batch = _get(url)
        if not batch:
            break
        fresh = [b for b in batch if int(b["fundingTime"]) not in seen]
        for b in fresh:
            seen.add(int(b["fundingTime"]))
            rows.append(b)
        last = int(batch[-1]["fundingTime"])
        if len(batch) < PAGE:
            break  # final (partial) page consumed
        start = last + 1
        time.sleep(0.25)  # be gentle on the public endpoint

    rows.sort(key=lambda b: int(b["fundingTime"]))
    out = os.path.join(OUTDIR, "btcusdt_funding.csv")
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["fundingTime_ms", "datetime_utc", "fundingRate", "markPrice"])
        for b in rows:
            t = int(b["fundingTime"])
            iso = dt.datetime.utcfromtimestamp(t / 1000).strftime("%Y-%m-%d %H:%M:%S")
            w.writerow([t, iso, b.get("fundingRate", ""), b.get("markPrice", "")])

    # diagnostics
    if rows:
        t0 = int(rows[0]["fundingTime"])
        t1 = int(rows[-1]["fundingTime"])
        intervals = [int(rows[i + 1]["fundingTime"]) - int(rows[i]["fundingTime"])
                     for i in range(min(50, len(rows) - 1))]
        med_h = (sorted(intervals)[len(intervals) // 2] / 3_600_000) if intervals else 0
        print(f"[funding] {len(rows)} rows | "
              f"{dt.datetime.utcfromtimestamp(t0/1000):%Y-%m-%d} → "
              f"{dt.datetime.utcfromtimestamp(t1/1000):%Y-%m-%d} | "
              f"median interval ≈ {med_h:.1f}h | -> {out}")
    return out


def dump_premium_index(interval: str = "5m", start_ms: int = 1675209600000) -> str:
    """Fine-grained funding DRIVER = premium index ((perp mark − spot index)/index,
    TWAP'd → the 8h funding). premiumIndexKlines, full history, free.
    Default start 2023-02-01 (matches npzv4_dual cache). Close = premium index value.
    """
    os.makedirs(OUTDIR, exist_ok=True)
    step = {"1m": 60_000, "5m": 300_000, "15m": 900_000}[interval]
    start = start_ms
    seen: set[int] = set()
    rows: list[tuple] = []
    while True:
        url = (f"{BASE}/fapi/v1/premiumIndexKlines?symbol={SYMBOL}"
               f"&interval={interval}&startTime={start}&limit=1500")
        batch = _get(url)
        if not batch:
            break
        for k in batch:
            t = int(k[0])
            if t in seen:
                continue
            seen.add(t)
            rows.append((t, k[1], k[2], k[3], k[4]))  # open,high,low,close (premium idx)
        last = int(batch[-1][0])
        if len(batch) < 1500:
            break
        start = last + step
        time.sleep(0.18)

    rows.sort(key=lambda r: r[0])
    out = os.path.join(OUTDIR, f"btcusdt_premium_index_{interval}.csv")
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["openTime_ms", "datetime_utc", "pidx_open", "pidx_high",
                    "pidx_low", "pidx_close"])
        for t, o, h, lo, c in rows:
            iso = dt.datetime.utcfromtimestamp(t / 1000).strftime("%Y-%m-%d %H:%M:%S")
            w.writerow([t, iso, o, h, lo, c])
    if rows:
        print(f"[premium_index {interval}] {len(rows)} rows | "
              f"{dt.datetime.utcfromtimestamp(rows[0][0]/1000):%Y-%m-%d} → "
              f"{dt.datetime.utcfromtimestamp(rows[-1][0]/1000):%Y-%m-%d} | -> {out}")
    return out


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "premium":
        dump_premium_index(interval=sys.argv[2] if len(sys.argv) > 2 else "5m")
    else:
        dump_funding()
