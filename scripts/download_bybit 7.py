#!/usr/bin/env python3
"""Download Bybit historical L2 orderbook data (ob500/ob1000).

Bybit publishes daily ZIP archives of tick-level orderbook snapshots at:
    https://quote-saver.bycsi.com/{YYYY-MM-DD}_{SYMBOL}_{data_type}.data.zip

Each ZIP contains a single ``.data`` file in JSONL format (one JSON object
per line).

Usage examples
--------------
    # Download BTCUSDT ob500 data for a date range
    python -m scripts.download_bybit \\
        --symbol BTCUSDT \\
        --start-date 2025-06-01 \\
        --end-date 2025-06-30 \\
        --output-dir data/raw/bybit

    # Download ob1000 (available after Sep 2025)
    python -m scripts.download_bybit \\
        --symbol BTCUSDT \\
        --start-date 2025-10-01 \\
        --end-date 2025-10-31 \\
        --data-type ob1000 \\
        --output-dir data/raw/bybit

Notes
-----
* The exact URL format was inferred from Bybit documentation and community
  reports.  **Verify the URL pattern against a known working date before
  launching bulk downloads.**  Bybit may change the CDN host or path layout
  without notice.
* The script retries transient HTTP errors (5xx, timeouts) up to
  ``--max-retries`` times with exponential back-off.
* Files that already exist on disk are skipped (use ``--force`` to re-download).
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASE_URL = "https://quote-saver.bycsi.com"
_USER_AGENT = "dl_quant/0.1 (bybit-history-downloader)"
_CHUNK_SIZE = 1 << 16  # 64 KiB


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_url(dt: date, symbol: str, data_type: str) -> str:
    """Construct the download URL for a single day.

    WARNING: this URL pattern is based on community-observed conventions.
    Always verify with a manual download before trusting it.
    """
    date_str = dt.strftime("%Y-%m-%d")
    return f"{_BASE_URL}/{date_str}_{symbol}_{data_type}.data.zip"


def _download_with_retry(
    url: str,
    dest: Path,
    *,
    max_retries: int = 3,
    timeout_sec: int = 60,
) -> bool:
    """Download *url* to *dest*, returning True on success.

    Retries on 5xx errors and connection timeouts with exponential back-off.
    Returns False (with a printed warning) on 404 or other client errors.
    """
    req = Request(url, headers={"User-Agent": _USER_AGENT})

    for attempt in range(1, max_retries + 1):
        try:
            with urlopen(req, timeout=timeout_sec) as resp:
                content_length = resp.headers.get("Content-Length")
                total = int(content_length) if content_length else None

                downloaded = 0
                with open(dest, "wb") as f:
                    while True:
                        chunk = resp.read(_CHUNK_SIZE)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        # Progress indicator
                        if total:
                            pct = downloaded * 100 / total
                            mb = downloaded / (1 << 20)
                            print(
                                f"\r  {mb:6.1f} MiB ({pct:5.1f}%)",
                                end="",
                                flush=True,
                            )
                print()  # newline after progress
            return True

        except HTTPError as exc:
            if 400 <= exc.code < 500:
                # Client error (404, 403, etc.) — do not retry
                print(f"  HTTP {exc.code}: {exc.reason} — skipping")
                if dest.exists():
                    dest.unlink()
                return False
            # Server error — retry
            wait = 2 ** attempt
            print(
                f"  HTTP {exc.code} (attempt {attempt}/{max_retries}), "
                f"retrying in {wait}s ..."
            )
            time.sleep(wait)

        except (URLError, OSError) as exc:
            wait = 2 ** attempt
            print(
                f"  Connection error: {exc} (attempt {attempt}/{max_retries}), "
                f"retrying in {wait}s ..."
            )
            time.sleep(wait)

    print(f"  FAILED after {max_retries} attempts")
    if dest.exists():
        dest.unlink()
    return False


def _iter_dates(start: date, end: date):
    """Yield dates from *start* to *end* inclusive."""
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def download_bybit_history(
    symbol: str,
    start_date: date,
    end_date: date,
    output_dir: Path,
    *,
    data_type: str = "ob500",
    max_retries: int = 3,
    timeout_sec: int = 120,
    force: bool = False,
) -> list[Path]:
    """Download Bybit orderbook ZIPs for *symbol* over a date range.

    Parameters
    ----------
    symbol : str
        Trading pair symbol, e.g. ``"BTCUSDT"``.
    start_date, end_date : date
        Inclusive date range.
    output_dir : Path
        Directory where ZIP files will be saved.
    data_type : str
        ``"ob500"`` (500 levels, before Oct 2025) or ``"ob1000"`` (1000 levels).
    max_retries : int
        Maximum download attempts per file.
    timeout_sec : int
        HTTP read timeout in seconds.
    force : bool
        If True, re-download files that already exist on disk.

    Returns
    -------
    list[Path]
        Paths of successfully downloaded ZIP files.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    dates = list(_iter_dates(start_date, end_date))
    total_days = len(dates)
    downloaded: list[Path] = []
    skipped = 0
    failed = 0

    print(
        f"Downloading {symbol} {data_type} data: "
        f"{start_date} → {end_date} ({total_days} day(s))"
    )
    print(f"Output directory: {output_dir}")
    print()

    for idx, dt in enumerate(dates, 1):
        url = _build_url(dt, symbol, data_type)
        filename = f"{dt.strftime('%Y-%m-%d')}_{symbol}_{data_type}.data.zip"
        dest = output_dir / filename

        print(f"[{idx}/{total_days}] {filename}")

        if dest.exists() and not force:
            print("  already exists — skipping (use --force to re-download)")
            downloaded.append(dest)
            skipped += 1
            continue

        ok = _download_with_retry(
            url,
            dest,
            max_retries=max_retries,
            timeout_sec=timeout_sec,
        )
        if ok:
            downloaded.append(dest)
        else:
            failed += 1

    print()
    print(
        f"Done: {len(downloaded)} downloaded, "
        f"{skipped} skipped (existed), {failed} failed"
    )
    return downloaded


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_date(s: str) -> date:
    """Parse YYYY-MM-DD string to a date object."""
    return datetime.strptime(s, "%Y-%m-%d").date()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Download Bybit historical L2 orderbook data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "NOTE: the download URL pattern is inferred from community reports.\n"
            "Verify with a manual browser download before bulk usage."
        ),
    )
    parser.add_argument(
        "--symbol",
        required=True,
        help="Trading pair symbol, e.g. BTCUSDT",
    )
    parser.add_argument(
        "--start-date",
        required=True,
        type=_parse_date,
        help="Start date (inclusive), YYYY-MM-DD",
    )
    parser.add_argument(
        "--end-date",
        required=True,
        type=_parse_date,
        help="End date (inclusive), YYYY-MM-DD",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory to save downloaded ZIP files",
    )
    parser.add_argument(
        "--data-type",
        default="ob500",
        choices=["ob500", "ob1000"],
        help="Orderbook depth type (default: ob500)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Max download retries per file (default: 3)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="HTTP timeout in seconds (default: 120)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download files that already exist",
    )
    args = parser.parse_args(argv)

    download_bybit_history(
        symbol=args.symbol,
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=args.output_dir,
        data_type=args.data_type,
        max_retries=args.max_retries,
        timeout_sec=args.timeout,
        force=args.force,
    )


if __name__ == "__main__":
    main()
