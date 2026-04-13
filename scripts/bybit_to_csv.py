#!/usr/bin/env python3
"""Convert Bybit historical JSONL orderbook data to pipeline-compatible CSV.

Bybit ``.data`` files (from extracted ZIPs) contain one JSON object per line:

    {"ts": 1700000000123, "s": "BTCUSDT", "b": [["30000.0","1.5"], ...], "a": [["30001.0","0.8"], ...]}

This script converts them to the CSV format expected by
``src.features.resample.resample_lob_to_1s``:

    timestamp,asks[0].price,asks[0].amount,...,bids[0].price,bids[0].amount,...

Column details:
    - ``timestamp``: int64, **microseconds** since epoch (Bybit provides ms)
    - ``asks[i].price``, ``asks[i].amount``: float, for i in 0..24
    - ``bids[i].price``, ``bids[i].amount``: float, for i in 0..24

Usage
-----
    # Convert a single .data file
    python -m scripts.bybit_to_csv \\
        --input data/raw/bybit/2025-06-01_BTCUSDT_ob500.data \\
        --output data/csv/BTCUSDT_2025-06-01.csv.gz

    # Convert all .data files in a directory
    python -m scripts.bybit_to_csv \\
        --input-dir data/raw/bybit/ \\
        --output-dir data/csv/ \\
        --symbol BTCUSDT

    # Pipe from a ZIP without manual extraction
    python -m scripts.bybit_to_csv \\
        --input-zip data/raw/bybit/2025-06-01_BTCUSDT_ob500.data.zip \\
        --output data/csv/BTCUSDT_2025-06-01.csv.gz
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import logging
import sys
import zipfile
from pathlib import Path
from typing import IO, Iterator

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
N_LEVELS = 25
"""Number of orderbook levels to extract (top 25 of 500/1000 available)."""


# ---------------------------------------------------------------------------
# Column helpers
# ---------------------------------------------------------------------------

def build_csv_columns(n_levels: int = N_LEVELS) -> list[str]:
    """Return the ordered list of CSV columns the pipeline expects.

    Order: timestamp, then for each level 0..n_levels-1:
        asks[i].price, asks[i].amount, bids[i].price, bids[i].amount
    """
    cols = ["timestamp"]
    for i in range(n_levels):
        cols.append(f"asks[{i}].price")
        cols.append(f"asks[{i}].amount")
        cols.append(f"bids[{i}].price")
        cols.append(f"bids[{i}].amount")
    return cols


# ---------------------------------------------------------------------------
# JSONL parsing
# ---------------------------------------------------------------------------

def parse_bybit_line(
    line: str,
    n_levels: int = N_LEVELS,
) -> dict[str, float | int] | None:
    """Parse a single Bybit JSONL line into a flat dict.

    Parameters
    ----------
    line : str
        Raw JSON line from the ``.data`` file.
    n_levels : int
        Number of bid/ask levels to extract.

    Returns
    -------
    dict or None
        Flat dict with keys matching ``build_csv_columns()``, or ``None`` if
        the line is malformed.
    """
    line = line.strip()
    if not line:
        return None

    try:
        obj = json.loads(line)
    except json.JSONDecodeError as exc:
        logger.warning("Skipping malformed JSON line: %s", exc)
        return None

    # --- timestamp: ms -> microseconds ---
    ts_ms = obj.get("ts")
    if ts_ms is None:
        logger.warning("Skipping line without 'ts' field")
        return None
    ts_us = int(ts_ms) * 1_000  # ms -> us

    bids_raw: list[list[str]] = obj.get("b", [])
    asks_raw: list[list[str]] = obj.get("a", [])

    row: dict[str, float | int] = {"timestamp": ts_us}

    for i in range(n_levels):
        # Asks — pad with 0 if fewer than n_levels
        if i < len(asks_raw):
            try:
                row[f"asks[{i}].price"] = float(asks_raw[i][0])
                row[f"asks[{i}].amount"] = float(asks_raw[i][1])
            except (IndexError, ValueError) as exc:
                logger.warning(
                    "Bad ask level %d at ts=%d: %s — padding with 0", i, ts_us, exc
                )
                row[f"asks[{i}].price"] = 0.0
                row[f"asks[{i}].amount"] = 0.0
        else:
            row[f"asks[{i}].price"] = 0.0
            row[f"asks[{i}].amount"] = 0.0

        # Bids — pad with 0 if fewer than n_levels
        if i < len(bids_raw):
            try:
                row[f"bids[{i}].price"] = float(bids_raw[i][0])
                row[f"bids[{i}].amount"] = float(bids_raw[i][1])
            except (IndexError, ValueError) as exc:
                logger.warning(
                    "Bad bid level %d at ts=%d: %s — padding with 0", i, ts_us, exc
                )
                row[f"bids[{i}].price"] = 0.0
                row[f"bids[{i}].amount"] = 0.0
        else:
            row[f"bids[{i}].price"] = 0.0
            row[f"bids[{i}].amount"] = 0.0

    return row


def iter_parse_jsonl(
    lines: Iterator[str],
    n_levels: int = N_LEVELS,
) -> Iterator[dict[str, float | int]]:
    """Yield parsed rows from an iterable of JSONL lines.

    Malformed lines are skipped with a warning.
    """
    for line_no, line in enumerate(lines, 1):
        row = parse_bybit_line(line, n_levels=n_levels)
        if row is not None:
            yield row
        else:
            if line.strip():  # only warn for non-empty lines
                logger.debug("Skipped line %d", line_no)


# ---------------------------------------------------------------------------
# File I/O helpers
# ---------------------------------------------------------------------------

def _open_output(path: Path) -> IO[str]:
    """Open an output file, using gzip compression if path ends with .gz."""
    if path.name.endswith(".gz"):
        return io.TextIOWrapper(
            gzip.open(path, "wb", compresslevel=6),
            encoding="utf-8",
            newline="",
        )
    return open(path, "w", newline="", encoding="utf-8")


def _read_lines_from_zip(zip_path: Path) -> Iterator[str]:
    """Yield text lines from the first .data member in a ZIP archive."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        data_members = [n for n in zf.namelist() if n.endswith(".data")]
        if not data_members:
            raise ValueError(f"No .data file found in {zip_path}")
        member = data_members[0]
        logger.info("Reading %s from %s", member, zip_path.name)
        with zf.open(member) as raw:
            for raw_line in io.TextIOWrapper(raw, encoding="utf-8"):
                yield raw_line


def _read_lines_from_file(path: Path) -> Iterator[str]:
    """Yield text lines from a plain .data file."""
    with open(path, "r", encoding="utf-8") as f:
        yield from f


# ---------------------------------------------------------------------------
# Core conversion
# ---------------------------------------------------------------------------

def convert_bybit_to_csv(
    lines: Iterator[str],
    output_path: Path,
    *,
    n_levels: int = N_LEVELS,
) -> int:
    """Convert an iterator of JSONL lines to a pipeline-compatible CSV.

    Parameters
    ----------
    lines : Iterator[str]
        Lines from a Bybit ``.data`` file.
    output_path : Path
        Destination CSV (or .csv.gz) path.
    n_levels : int
        Number of orderbook levels to extract.

    Returns
    -------
    int
        Number of rows written.
    """
    columns = build_csv_columns(n_levels)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows_written = 0

    with _open_output(output_path) as out_fh:
        writer = csv.DictWriter(out_fh, fieldnames=columns)
        writer.writeheader()

        for row in iter_parse_jsonl(lines, n_levels=n_levels):
            writer.writerow(row)
            rows_written += 1

            if rows_written % 500_000 == 0:
                logger.info("  %d rows written ...", rows_written)

    return rows_written


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------

def convert_directory(
    input_dir: Path,
    output_dir: Path,
    *,
    symbol: str | None = None,
    n_levels: int = N_LEVELS,
) -> list[Path]:
    """Convert all .data and .data.zip files in *input_dir* to CSV.

    Parameters
    ----------
    input_dir : Path
        Directory containing ``.data`` or ``.data.zip`` files.
    output_dir : Path
        Where to write CSVs.
    symbol : str or None
        If given, only process files whose name contains *symbol*.
    n_levels : int
        Number of orderbook levels.

    Returns
    -------
    list[Path]
        Paths of written CSV files.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Gather input files
    candidates = sorted(input_dir.iterdir())
    inputs: list[tuple[Path, bool]] = []  # (path, is_zip)
    for p in candidates:
        if symbol and symbol not in p.name:
            continue
        if p.name.endswith(".data.zip"):
            inputs.append((p, True))
        elif p.name.endswith(".data"):
            inputs.append((p, False))

    if not inputs:
        logger.warning("No .data or .data.zip files found in %s", input_dir)
        return []

    written: list[Path] = []
    for idx, (path, is_zip) in enumerate(inputs, 1):
        # Derive output name: replace .data or .data.zip with .csv.gz
        stem = path.name
        for suffix in (".data.zip", ".data"):
            if stem.endswith(suffix):
                stem = stem[: -len(suffix)]
                break
        out_path = output_dir / f"{stem}.csv.gz"

        logger.info("[%d/%d] %s -> %s", idx, len(inputs), path.name, out_path.name)

        if is_zip:
            lines = _read_lines_from_zip(path)
        else:
            lines = _read_lines_from_file(path)

        n = convert_bybit_to_csv(lines, out_path, n_levels=n_levels)
        logger.info("  wrote %d rows", n)
        written.append(out_path)

    return written


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Convert Bybit JSONL orderbook data to pipeline-compatible CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Input sources (mutually exclusive)
    inp = parser.add_mutually_exclusive_group(required=True)
    inp.add_argument(
        "--input",
        type=Path,
        help="Path to a single .data file",
    )
    inp.add_argument(
        "--input-zip",
        type=Path,
        help="Path to a .data.zip archive",
    )
    inp.add_argument(
        "--input-dir",
        type=Path,
        help="Directory containing .data or .data.zip files",
    )

    # Output
    parser.add_argument(
        "--output",
        type=Path,
        help="Output CSV path (for single-file mode)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory (for --input-dir mode)",
    )
    parser.add_argument(
        "--symbol",
        help="Filter files by symbol (for --input-dir mode)",
    )
    parser.add_argument(
        "--n-levels",
        type=int,
        default=N_LEVELS,
        help=f"Number of orderbook levels to extract (default: {N_LEVELS})",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    if args.input_dir:
        if not args.output_dir:
            parser.error("--output-dir is required with --input-dir")
        convert_directory(
            args.input_dir,
            args.output_dir,
            symbol=args.symbol,
            n_levels=args.n_levels,
        )
    else:
        # Single-file mode
        if not args.output:
            parser.error("--output is required with --input or --input-zip")

        if args.input_zip:
            lines: Iterator[str] = _read_lines_from_zip(args.input_zip)
        else:
            assert args.input is not None
            lines = _read_lines_from_file(args.input)

        n = convert_bybit_to_csv(lines, args.output, n_levels=args.n_levels)
        print(f"Wrote {n} rows to {args.output}")


if __name__ == "__main__":
    main()
