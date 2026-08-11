#!/usr/bin/env python3
"""Collect Binance Futures L2 orderbook depth via WebSocket.

Saves daily-rotated gzip JSONL files for long-term data accumulation.

Requirements
------------
    pip install websockets>=10.0

Usage
-----
    python scripts/collect_binance_depth.py
    python scripts/collect_binance_depth.py --symbol ETHUSDT --levels 10
    python scripts/collect_binance_depth.py --output-dir /mnt/data/collected

The collector is designed for weeks of unattended operation with:
- Auto-reconnect with exponential backoff (1s -> 60s)
- Daily file rotation at UTC midnight
- Gap detection via ``pu`` / ``u`` sequence
- Graceful shutdown on SIGINT / SIGTERM
- 60-second statistics logging
"""

from __future__ import annotations

import argparse
import asyncio
import gzip
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import websockets
    import websockets.exceptions
    _HAS_WEBSOCKETS = True
except ImportError:
    _HAS_WEBSOCKETS = False

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("collector")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
WS_BASE = "wss://fstream.binance.com/stream"
STATS_INTERVAL_SEC = 60
RECONNECT_BASE_SEC = 1.0
RECONNECT_MAX_SEC = 60.0


# ---------------------------------------------------------------------------
# Gap tracker
# ---------------------------------------------------------------------------
class GapTracker:
    """Track orderbook update sequence to detect gaps.

    Binance partial depth streams include ``pu`` (previous final update id)
    which must equal the ``u`` of the preceding message for a continuous
    sequence.  A mismatch indicates a gap (missed messages).
    """

    def __init__(self):
        self.prev_u = None  # type: Optional[int]
        self.total_messages = 0
        self.total_gaps = 0

    def check(self, msg: dict) -> bool:
        """Return True if a gap was detected, False otherwise."""
        pu = msg.get("pu")
        u = msg.get("u")
        gap = False

        if self.prev_u is not None and pu is not None:
            if pu != self.prev_u:
                gap = True
                self.total_gaps += 1

        self.prev_u = u
        self.total_messages += 1
        return gap

    def reset(self):
        """Reset sequence state (e.g. after reconnect)."""
        self.prev_u = None


# ---------------------------------------------------------------------------
# Daily-rotated gzip writer
# ---------------------------------------------------------------------------
class DailyGzWriter:
    """Write JSONL lines to daily-rotated gzip files.

    File naming: ``<output_dir>/YYYY-MM-DD_<symbol>_depth<levels>.jsonl.gz``
    """

    def __init__(self, output_dir: str, symbol: str, levels: int):
        self.output_dir = Path(output_dir)
        self.symbol = symbol.upper()
        self.levels = levels
        self._current_date = None  # type: Optional[str]
        self._fh = None  # type: Optional[gzip.GzipFile]
        self._bytes_written = 0
        self._current_path = None  # type: Optional[Path]

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _date_str(self) -> str:
        """Current UTC date string."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _rotate_if_needed(self):
        """Open a new file if the UTC date has changed."""
        today = self._date_str()
        if today != self._current_date:
            self.close()
            self._current_date = today
            fname = f"{today}_{self.symbol}_depth{self.levels}.jsonl.gz"
            self._current_path = self.output_dir / fname
            # Append mode: if the collector restarts on the same day, we
            # continue writing to the same file instead of overwriting.
            self._fh = gzip.open(str(self._current_path), "ab")
            log.info("Opened file: %s", self._current_path)

    def write_line(self, line: bytes):
        """Write a single JSONL line (bytes, newline-terminated)."""
        self._rotate_if_needed()
        self._fh.write(line)
        self._bytes_written += len(line)

    def close(self):
        if self._fh is not None:
            self._fh.close()
            self._fh = None

    @property
    def bytes_written(self) -> int:
        return self._bytes_written

    @property
    def current_path(self) -> Optional[Path]:
        return self._current_path


# ---------------------------------------------------------------------------
# Statistics reporter
# ---------------------------------------------------------------------------
class StatsReporter:
    """Log collection statistics every ``interval`` seconds."""

    def __init__(self, interval: int = STATS_INTERVAL_SEC):
        self.interval = interval
        self.msg_count = 0
        self.gap_count = 0
        self._last_report = time.monotonic()
        self._last_msg_count = 0

    def tick(self, gap: bool):
        self.msg_count += 1
        if gap:
            self.gap_count += 1

    def maybe_report(self, writer: DailyGzWriter):
        now = time.monotonic()
        elapsed = now - self._last_report
        if elapsed < self.interval:
            return
        msgs_in_period = self.msg_count - self._last_msg_count
        rate = msgs_in_period / elapsed if elapsed > 0 else 0.0

        file_size_mb = 0.0
        if writer.current_path and writer.current_path.exists():
            file_size_mb = writer.current_path.stat().st_size / (1024 * 1024)

        log.info(
            "Stats: %.1f msg/s | total=%d | gaps=%d | file=%.2f MB (%s)",
            rate,
            self.msg_count,
            self.gap_count,
            file_size_mb,
            writer.current_path.name if writer.current_path else "N/A",
        )
        self._last_report = now
        self._last_msg_count = self.msg_count


# ---------------------------------------------------------------------------
# Main collector loop
# ---------------------------------------------------------------------------
class BinanceDepthCollector:
    """Async WebSocket collector for Binance Futures partial depth."""

    def __init__(self, symbol: str, levels: int, output_dir: str):
        if not _HAS_WEBSOCKETS:
            raise ImportError(
                "'websockets' package is required. Install with: "
                "pip install websockets>=10.0"
            )
        self.symbol = symbol.lower()
        self.levels = levels
        self.stream = f"{self.symbol}@depth{levels}@100ms"
        self.url = f"{WS_BASE}?streams={self.stream}"

        self.writer = DailyGzWriter(output_dir, symbol, levels)
        self.gap_tracker = GapTracker()
        self.stats = StatsReporter()

        self._running = True
        self._reconnect_delay = RECONNECT_BASE_SEC

    def stop(self):
        """Signal the collector to shut down gracefully."""
        self._running = False

    async def run(self):
        """Main loop: connect, consume, reconnect on failure."""
        log.info(
            "Starting collector: symbol=%s levels=%d stream=%s",
            self.symbol.upper(),
            self.levels,
            self.stream,
        )
        log.info("Output dir: %s", self.writer.output_dir)
        log.info("WebSocket URL: %s", self.url)

        while self._running:
            try:
                await self._connect_and_consume()
            except (
                websockets.exceptions.ConnectionClosed,
                websockets.exceptions.InvalidStatusCode,
                ConnectionRefusedError,
                OSError,
            ) as exc:
                if not self._running:
                    break
                log.warning(
                    "Connection lost (%s). Reconnecting in %.0fs ...",
                    exc,
                    self._reconnect_delay,
                )
                await asyncio.sleep(self._reconnect_delay)
                # Exponential backoff
                self._reconnect_delay = min(
                    self._reconnect_delay * 2, RECONNECT_MAX_SEC
                )
                # Reset gap tracker on reconnect — first message has no
                # valid predecessor.
                self.gap_tracker.reset()
            except asyncio.CancelledError:
                break
            except Exception:
                log.exception("Unexpected error in collector loop")
                if not self._running:
                    break
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * 2, RECONNECT_MAX_SEC
                )
                self.gap_tracker.reset()

        self.writer.close()
        log.info(
            "Collector stopped. Total messages: %d, gaps: %d",
            self.stats.msg_count,
            self.stats.gap_count,
        )

    async def _connect_and_consume(self):
        """Connect to WebSocket and consume messages until disconnect."""
        async with websockets.connect(
            self.url,
            ping_interval=20,
            ping_timeout=20,
            close_timeout=10,
            max_size=2 ** 20,  # 1 MiB — depth20 messages are ~2 KB
        ) as ws:
            log.info("Connected to Binance Futures WebSocket")
            self._reconnect_delay = RECONNECT_BASE_SEC  # reset backoff

            while self._running:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=30.0)
                except asyncio.TimeoutError:
                    # No message in 30s — send a ping to check liveness.
                    # websockets library handles ping/pong automatically, but
                    # a 30s silence is unusual for 100ms streams.
                    log.warning("No message for 30s — connection may be stale")
                    continue

                local_ts = int(time.time() * 1_000_000)  # local microseconds

                # Parse and extract the data payload from the combined stream
                # wrapper: {"stream":"...", "data":{...}}
                try:
                    envelope = json.loads(raw)
                    msg = envelope.get("data", envelope)
                except json.JSONDecodeError:
                    log.warning("Non-JSON message received, skipping")
                    continue

                # Gap detection
                gap = self.gap_tracker.check(msg)
                if gap:
                    log.warning(
                        "Gap detected: pu=%s != prev_u=%s",
                        msg.get("pu"),
                        self.gap_tracker.prev_u,
                    )

                # Build JSONL line: prepend local_ts into the message dict
                msg["local_ts"] = local_ts
                line = json.dumps(msg, separators=(",", ":")).encode("utf-8") + b"\n"
                self.writer.write_line(line)

                # Stats
                self.stats.tick(gap)
                self.stats.maybe_report(self.writer)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Collect Binance Futures L2 depth via WebSocket",
    )
    parser.add_argument(
        "--symbol",
        default="BTCUSDT",
        help="Trading pair symbol (default: BTCUSDT)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/collected",
        help="Output directory for JSONL.gz files (default: data/collected)",
    )
    parser.add_argument(
        "--levels",
        type=int,
        default=20,
        choices=[5, 10, 20],
        help="Number of depth levels: 5, 10, or 20 (default: 20)",
    )
    return parser.parse_args(argv)


def main(argv=None):
    if not _HAS_WEBSOCKETS:
        print(
            "ERROR: 'websockets' package is not installed.\n"
            "       Install it with:  pip install websockets>=10.0\n"
            "       Then re-run this script.",
            file=sys.stderr,
        )
        sys.exit(1)

    args = parse_args(argv)

    collector = BinanceDepthCollector(
        symbol=args.symbol,
        levels=args.levels,
        output_dir=args.output_dir,
    )

    loop = asyncio.get_event_loop()

    # Graceful shutdown on SIGINT / SIGTERM
    def _shutdown(signum, frame):
        sig_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
        log.info("Received %s — shutting down ...", sig_name)
        collector.stop()
        # Cancel all running tasks to unblock the event loop
        for task in asyncio.all_tasks(loop):
            task.cancel()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        loop.run_until_complete(collector.run())
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        loop.close()


if __name__ == "__main__":
    main()
