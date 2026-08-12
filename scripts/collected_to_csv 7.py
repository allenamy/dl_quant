#!/usr/bin/env python3
"""Convert collected Binance depth JSONL.gz files to pipeline CSV format.

The pipeline expects a CSV with columns:
    timestamp, asks[0].price, asks[0].amount, ..., asks[N-1].price, asks[N-1].amount,
               bids[0].price, bids[0].amount, ..., bids[N-1].price, bids[N-1].amount

where ``timestamp`` is int64 microseconds since epoch.

Usage
-----
    # Convert a single file
    python scripts/collected_to_csv.py data/collected/2026-04-13_BTCUSDT_depth20.jsonl.gz

    # Convert all files in a directory
    python scripts/collected_to_csv.py data/collected/ --output-dir data/csv

    # With explicit level count
    python scripts/collected_to_csv.py data/collected/ --n-levels 20
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("converter")


# ---------------------------------------------------------------------------
# Column definitions
# ---------------------------------------------------------------------------
def build_csv_columns(n_levels: int) -> List[str]:
    """Build the ordered list of CSV column names matching the pipeline format.

    Order: timestamp, asks[0].price, asks[0].amount, ..., bids[0].price, ...
    """
    cols = ["timestamp"]
    for i in range(n_levels):
        cols.append(f"asks[{i}].price")
        cols.append(f"asks[{i}].amount")
    for i in range(n_levels):
        cols.append(f"bids[{i}].price")
        cols.append(f"bids[{i}].amount")
    return cols


# ---------------------------------------------------------------------------
# JSONL line parser
# ---------------------------------------------------------------------------
def parse_depth_line(
    line: str,
    n_levels: int,
) -> Optional[Dict[str, object]]:
    """Parse a single JSONL line into a flat dict matching CSV columns.

    Parameters
    ----------
    line : str
        Raw JSON string (one message from the collector).
    n_levels : int
        Expected number of orderbook levels.

    Returns
    -------
    dict or None
        Flat dict with keys ``timestamp``, ``asks[i].price``, etc.
        Returns None if the line cannot be parsed.
    """
    try:
        msg = json.loads(line)
    except json.JSONDecodeError:
        return None

    # Timestamp: ``E`` is exchange event time in milliseconds -> microseconds
    E = msg.get("E")
    if E is None:
        return None
    timestamp_us = int(E) * 1000  # ms -> us

    asks = msg.get("a", [])
    bids = msg.get("b", [])

    if len(asks) < n_levels or len(bids) < n_levels:
        return None

    row = {"timestamp": timestamp_us}
    for i in range(n_levels):
        row[f"asks[{i}].price"] = float(asks[i][0])
        row[f"asks[{i}].amount"] = float(asks[i][1])
    for i in range(n_levels):
        row[f"bids[{i}].price"] = float(bids[i][0])
        row[f"bids[{i}].amount"] = float(bids[i][1])

    return row


# ---------------------------------------------------------------------------
# File conversion
# ---------------------------------------------------------------------------
def convert_jsonl_to_csv(
    input_path: Path,
    output_path: Path,
    n_levels: int = 20,
) -> Tuple[int, int]:
    """Convert a single JSONL.gz file to a gzip CSV.

    Parameters
    ----------
    input_path : Path
        Path to the ``.jsonl.gz`` input file.
    output_path : Path
        Path to the ``.csv.gz`` output file.
    n_levels : int
        Number of depth levels in the data.

    Returns
    -------
    (total_lines, converted_lines)
        Counts of total and successfully converted lines.
    """
    columns = build_csv_columns(n_levels)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    converted = 0

    # Read JSONL.gz, write CSV.gz
    with gzip.open(str(input_path), "rt", encoding="utf-8") as fin, \
         gzip.open(str(output_path), "wt", encoding="utf-8", newline="") as fout:

        writer = csv.DictWriter(fout, fieldnames=columns)
        writer.writeheader()

        for line in fin:
            total += 1
            line = line.strip()
            if not line:
                continue

            row = parse_depth_line(line, n_levels)
            if row is not None:
                writer.writerow(row)
                converted += 1

    return total, converted


def find_jsonl_files(input_path: Path) -> List[Path]:
    """Find all .jsonl.gz files in a directory, sorted by name."""
    if input_path.is_file():
        return [input_path]
    return sorted(input_path.glob("*_depth*.jsonl.gz"))


def derive_output_path(input_file: Path, output_dir: Path) -> Path:
    """Derive CSV output path from the JSONL input filename.

    ``2026-04-13_BTCUSDT_depth20.jsonl.gz`` -> ``2026-04-13_BTCUSDT_depth20.csv.gz``
    """
    stem = input_file.name
    # Remove .jsonl.gz suffix
    if stem.endswith(".jsonl.gz"):
        stem = stem[: -len(".jsonl.gz")]
    return output_dir / f"{stem}.csv.gz"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Convert collected JSONL.gz depth files to pipeline CSV.gz",
    )
    parser.add_argument(
        "input",
        help="Path to a .jsonl.gz file or directory containing them",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory for CSV.gz files (default: same as input)",
    )
    parser.add_argument(
        "--n-levels",
        type=int,
        default=20,
        help="Number of depth levels (default: 20)",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    input_path = Path(args.input)
    if not input_path.exists():
        log.error("Input path does not exist: %s", input_path)
        sys.exit(1)

    files = find_jsonl_files(input_path)
    if not files:
        log.error("No .jsonl.gz files found at: %s", input_path)
        sys.exit(1)

    output_dir = Path(args.output_dir) if args.output_dir else input_path.parent
    if input_path.is_dir() and args.output_dir is None:
        output_dir = input_path

    log.info("Found %d file(s) to convert", len(files))

    for f in files:
        out = derive_output_path(f, output_dir)
        log.info("Converting %s -> %s", f.name, out.name)
        total, converted = convert_jsonl_to_csv(f, out, n_levels=args.n_levels)
        log.info(
            "  %d/%d lines converted (%.1f%%)",
            converted,
            total,
            100.0 * converted / total if total > 0 else 0.0,
        )

    log.info("Done.")


if __name__ == "__main__":
    main()
