#!/usr/bin/env python3
"""Dump Binance Data Vision FUTURES METRICS for BTCUSDT — FREE OI + long/short ratios.

> Created 2026-06-24 | dual-source-perp orthogonal-data lever (OI / positioning).

Source: https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT/ (free, public).
Granularity: 5m. Columns: create_time, symbol, sum_open_interest, sum_open_interest_value,
count_toptrader_long_short_ratio, sum_toptrader_long_short_ratio, count_long_short_ratio,
sum_taker_long_short_vol_ratio. These are POSITIONING/FLOW signals — orthogonal to the
price-microstructure (book/trade) features and to the price-basis. The hypothesized
choppy-0.06 lever (OI flow + crowding is faster + different-dimension than 8h funding).

Local-dev: run LOCAL, output to data/funding/, sync to server for training.
Usage: python multi_asset/data/dump_binance_metrics.py [start YYYY-MM-DD] [end YYYY-MM-DD]
"""
from __future__ import annotations
import datetime as dt
import io
import os
import sys
import time
import urllib.request
import zipfile

BASE = "https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT"
OUTDIR = "data/funding"


def _fetch(url: str) -> bytes | None:
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "metrics-dump/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None  # day not published
            time.sleep(1.5 * (attempt + 1))
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    return None


def dump_metrics(start: dt.date, end: dt.date) -> str:
    os.makedirs(OUTDIR, exist_ok=True)
    header: str | None = None
    rows: list[str] = []
    missing = 0
    d = start
    while d <= end:
        ds = d.strftime("%Y-%m-%d")
        data = _fetch(f"{BASE}/BTCUSDT-metrics-{ds}.zip")
        if data is not None:
            try:
                z = zipfile.ZipFile(io.BytesIO(data))
                lines = z.read(z.namelist()[0]).decode().splitlines()
                if lines:
                    if header is None:
                        header = lines[0]
                    rows.extend(lines[1:])
            except Exception:
                missing += 1
        else:
            missing += 1
        d += dt.timedelta(days=1)
        time.sleep(0.08)

    out = os.path.join(OUTDIR, "btcusdt_metrics_5m.csv")
    with open(out, "w") as f:
        if header:
            f.write(header + "\n")
        f.write("\n".join(rows) + ("\n" if rows else ""))
    print(f"[metrics] {len(rows)} rows | {start} → {end} | {missing} days missing | -> {out}")
    return out


if __name__ == "__main__":
    s = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else dt.date(2023, 2, 1)
    e = dt.date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else dt.date(2026, 6, 23)
    dump_metrics(s, e)
