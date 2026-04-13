#!/usr/bin/env python3
"""Collect Bybit BTCUSDT L2 orderbook snapshots via REST API polling.

Polls the Bybit V5 REST API every ~1 second for a 25-level depth snapshot
and saves it in the exact CSV format that our pipeline expects. This is the
simplest, most reliable data collection method — no WebSocket, no dependencies
beyond urllib.

Output: daily CSV files at ``{output_dir}/YYYY-MM-DD_BTCUSDT_depth25.csv.gz``
with columns: timestamp, asks[0..24].price, asks[0..24].amount,
              bids[0..24].price, bids[0..24].amount

Rate limit: Bybit V5 orderbook endpoint allows 10 req/s. We use 1 req/s.

Usage
-----
    python scripts/collect_bybit_rest.py --output-dir data/raw/bybit
    python scripts/collect_bybit_rest.py --interval 0.5   # 2 req/s
    python scripts/collect_bybit_rest.py --levels 20       # top 20 levels
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_API_URL = "https://api.bybit.com/v5/market/orderbook"
_DEFAULT_SYMBOL = "BTCUSDT"
_DEFAULT_LEVELS = 25
_DEFAULT_INTERVAL = 1.0  # seconds between polls


# ---------------------------------------------------------------------------
# CSV column helpers
# ---------------------------------------------------------------------------

def build_csv_header(n_levels: int) -> list[str]:
    """Build CSV header matching the pipeline's expected format."""
    cols = ["timestamp"]
    for i in range(n_levels):
        cols.append(f"asks[{i}].price")
        cols.append(f"asks[{i}].amount")
    for i in range(n_levels):
        cols.append(f"bids[{i}].price")
        cols.append(f"bids[{i}].amount")
    return cols


def parse_snapshot(data: dict, n_levels: int) -> dict | None:
    """Parse a Bybit V5 orderbook response into a flat row dict.

    Returns None if the response is invalid or has insufficient levels.
    """
    result = data.get("result", {})
    asks = result.get("a", [])
    bids = result.get("b", [])
    ts_ms = result.get("ts")

    if ts_ms is None or len(asks) < n_levels or len(bids) < n_levels:
        return None

    row = {"timestamp": int(ts_ms) * 1000}  # ms → μs

    for i in range(n_levels):
        row[f"asks[{i}].price"] = float(asks[i][0])
        row[f"asks[{i}].amount"] = float(asks[i][1])

    for i in range(n_levels):
        row[f"bids[{i}].price"] = float(bids[i][0])
        row[f"bids[{i}].amount"] = float(bids[i][1])

    return row


# ---------------------------------------------------------------------------
# Daily file writer
# ---------------------------------------------------------------------------

class DailyCSVWriter:
    """Manages daily-rotated gzip CSV files."""

    def __init__(self, output_dir: str, symbol: str, n_levels: int) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.symbol = symbol
        self.n_levels = n_levels
        self.header = build_csv_header(n_levels)
        self._current_date: str | None = None
        self._file = None
        self._writer = None
        self._row_count = 0

    def _open_day(self, date_str: str) -> None:
        """Open (or append to) the CSV file for the given date.

        Uses plain text CSV (not gzip) for reliable incremental writes.
        Compression can be done offline after collection.
        """
        self._close()
        self._current_date = date_str
        path = self.output_dir / f"{date_str}_{self.symbol}_depth{self.n_levels}.csv"
        is_new = not path.exists() or path.stat().st_size == 0
        self._file = open(path, "a", encoding="utf-8", buffering=1)  # line-buffered
        self._writer = csv.DictWriter(self._file, fieldnames=self.header)
        if is_new:
            self._writer.writeheader()
        self._row_count = 0

    def _close(self) -> None:
        if self._file is not None:
            self._file.flush()
            self._file.close()
            self._file = None
            self._writer = None

    def write_row(self, row: dict) -> None:
        """Write a row, rotating files at UTC day boundaries."""
        ts_us = row["timestamp"]
        date_str = datetime.fromtimestamp(
            ts_us / 1_000_000, tz=timezone.utc
        ).strftime("%Y-%m-%d")

        if date_str != self._current_date:
            self._open_day(date_str)

        self._writer.writerow(row)
        self._row_count += 1

        # File is line-buffered, explicit flush every 60 rows for safety
        if self._row_count % 60 == 0:
            self._file.flush()
            os.fsync(self._file.fileno())

    def close(self) -> None:
        self._close()

    @property
    def current_path(self) -> str:
        if self._current_date is None:
            return "(not started)"
        return str(
            self.output_dir
            / f"{self._current_date}_{self.symbol}_depth{self.n_levels}.csv"
        )


# ---------------------------------------------------------------------------
# Collector loop
# ---------------------------------------------------------------------------

def collect(
    symbol: str = _DEFAULT_SYMBOL,
    n_levels: int = _DEFAULT_LEVELS,
    interval: float = _DEFAULT_INTERVAL,
    output_dir: str = "data/raw/bybit",
    collect_trades: bool = True,
) -> None:
    """Main collection loop. Runs until interrupted.

    Collects both depth snapshots and recent trades (if enabled).
    Trade data is saved in a separate daily CSV with columns:
        timestamp, price, size, side (Buy/Sell)
    """

    url = f"{_API_URL}?category=linear&symbol={symbol}&limit={n_levels}"
    trade_url = f"https://api.bybit.com/v5/market/recent-trade?category=linear&symbol={symbol}&limit=50"
    writer = DailyCSVWriter(output_dir, symbol, n_levels)

    # Trade writer (separate file)
    trade_file = None
    trade_writer = None
    trade_date = None
    last_trade_id = None

    # Graceful shutdown
    running = True

    def _handle_signal(signum, frame):
        nonlocal running
        print(f"\n[collector] Received signal {signum}, shutting down...")
        running = False

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    total_ok = 0
    total_err = 0
    t_start = time.time()

    print(f"[collector] Starting: {symbol} {n_levels}-level @ {interval}s interval")
    print(f"[collector] Output: {output_dir}")
    print(f"[collector] Press Ctrl+C to stop\n")

    while running:
        t0 = time.time()

        try:
            # --- Depth snapshot ---
            with urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read())

            if data.get("retCode") != 0:
                total_err += 1
                print(f"[collector] API error: {data.get('retMsg')}")
            else:
                row = parse_snapshot(data, n_levels)
                if row is not None:
                    writer.write_row(row)
                    total_ok += 1
                else:
                    total_err += 1

            # --- Trade data (same request cycle) ---
            if collect_trades:
                try:
                    with urlopen(trade_url, timeout=10) as resp2:
                        tdata = json.loads(resp2.read())
                    if tdata.get("retCode") == 0:
                        trades = tdata["result"]["list"]
                        now_date = datetime.fromtimestamp(
                            time.time(), tz=timezone.utc
                        ).strftime("%Y-%m-%d")
                        # Rotate trade file on day change
                        if now_date != trade_date:
                            if trade_file is not None:
                                trade_file.flush()
                                trade_file.close()
                            trade_path = Path(output_dir) / f"{now_date}_{symbol}_trades.csv"
                            is_new = not trade_path.exists() or trade_path.stat().st_size == 0
                            trade_file = open(trade_path, "a", buffering=1)
                            trade_writer = csv.writer(trade_file)
                            if is_new:
                                trade_writer.writerow(["timestamp", "price", "size", "side", "exec_id"])
                            trade_date = now_date

                        for t in trades:
                            eid = t.get("execId", "")
                            if last_trade_id is not None and eid <= last_trade_id:
                                continue  # skip already-seen trades
                            ts_us = int(t["time"]) * 1000
                            trade_writer.writerow([ts_us, t["price"], t["size"], t["side"], eid])
                        if trades:
                            last_trade_id = trades[0].get("execId", "")
                except Exception:
                    pass  # trade collection is best-effort

        except (HTTPError, URLError, OSError, json.JSONDecodeError) as exc:
            total_err += 1
            print(f"[collector] Error: {exc}")

        # Stats every 60 snapshots
        if total_ok > 0 and total_ok % 60 == 0:
            elapsed = time.time() - t_start
            rate = total_ok / elapsed
            trade_info = ""
            if collect_trades and trade_file is not None:
                trade_info = f" | trades: {Path(trade_file.name).name}"
            print(
                f"[collector] {total_ok:,} snapshots | "
                f"{total_err} errors | "
                f"{rate:.2f}/s | "
                f"file: {writer.current_path}"
                f"{trade_info}"
            )

        # Sleep to maintain interval
        dt = time.time() - t0
        sleep_time = max(0.0, interval - dt)
        if sleep_time > 0 and running:
            time.sleep(sleep_time)

    writer.close()
    if trade_file is not None:
        trade_file.flush()
        trade_file.close()
    elapsed = time.time() - t_start
    print(f"\n[collector] Done. {total_ok:,} snapshots in {elapsed:.0f}s, {total_err} errors")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect Bybit BTCUSDT orderbook via REST polling"
    )
    parser.add_argument("--symbol", default=_DEFAULT_SYMBOL)
    parser.add_argument("--levels", type=int, default=_DEFAULT_LEVELS)
    parser.add_argument("--interval", type=float, default=_DEFAULT_INTERVAL,
                        help="Seconds between polls (default: 1.0)")
    parser.add_argument("--output-dir", default="data/raw/bybit")
    args = parser.parse_args()

    collect(
        symbol=args.symbol,
        n_levels=args.levels,
        interval=args.interval,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
