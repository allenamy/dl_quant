#!/usr/bin/env python3
"""Phase hardening — FULL-HISTORY 1h klines + funding for the 14 mega-caps (funding_ema replay).

> **created:** 2026-07-08 | **Session:** multi-asset-v2 consolidation/hardening (0B) | **状态:** in-progress

Attacks the #1 honest limit (OOS ~7mo) on the PRIMARY factor: funding_ema is linear + needs only
funding + hourly prices, both full-history on data.binance.vision. Dumps the 14 mega-caps from each
coin's listing (BTC/ETH 2019-2020 ... late alts 2020-2021) through 2026-06 → per-YEAR walk-forward
replay of the crowding-reversion premium across regimes (2020 bull / 2021 mania / 2022 crash /
2023 chop / 2024-25 our window / 2026 partial). Reuses dump_wide_universe's archive fetchers.
Usage: python multi_asset/data/dump_megacap_hist.py [start YYYY-MM-DD] [end YYYY-MM-DD] [workers]
"""
from __future__ import annotations
import datetime as dt, os, sys, time
from concurrent.futures import ThreadPoolExecutor

import multi_asset.data.dump_wide_universe as W

MEGA = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT",
        "LINKUSDT", "BCHUSDT", "TRXUSDT", "LTCUSDT", "DOTUSDT", "FILUSDT", "ETCUSDT"]
W.OUTDIR = "data/megacap_hist"        # override the wide dumper's output dir


def main():
    os.makedirs(W.OUTDIR, exist_ok=True)
    s = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else dt.date(2019, 9, 1)
    e = dt.date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else dt.date(2026, 6, 1)
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 32
    months = W._months(s, e)
    t0 = time.time()
    print(f"[megacap_hist] {len(MEGA)} mega-caps, {len(months)} months {s}..{e} -> {W.OUTDIR}", flush=True)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, SYM in enumerate(MEGA):
            rk = W.dump_klines(SYM, months, pool)
            rf = W.dump_funding(SYM, months, pool)
            print(f"[{i+1}/14] {SYM:10s} klines={rk:24s} funding={rf}  ({(time.time()-t0)/60:.1f}min)", flush=True)
    print(f"[megacap_hist] DONE in {(time.time()-t0)/60:.1f}min -> {W.OUTDIR}", flush=True)


if __name__ == "__main__":
    main()
