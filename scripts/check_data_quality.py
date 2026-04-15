"""Data quality checker for collected LOB depth and trade CSV files.

Validates gap detection, NaN presence, spread positivity, price monotonicity,
and sampling interval consistency.

CLI usage:
    python scripts/check_data_quality.py --data-dir data/raw/bybit
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
from typing import Dict

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# 1. Depth quality check
# ---------------------------------------------------------------------------

def check_depth_quality(csv_path: str) -> dict:
    """Check a single day's depth CSV for issues.

    Returns dict with:
      total_rows, duration_sec, avg_interval, max_gap_sec,
      gap_count_gt5s, gap_count_gt60s, nan_count,
      price_monotonic_pct, spread_always_positive,
      mid_price_range, status ('OK' / 'WARNING' / 'ERROR')
    """
    df = pd.read_csv(csv_path)
    result: Dict[str, object] = {"file": os.path.basename(csv_path)}

    total_rows = len(df)
    result["total_rows"] = total_rows

    if total_rows == 0:
        result["status"] = "ERROR"
        result["reason"] = "empty file"
        return result

    # --- Timestamps ----------------------------------------------------------
    ts = df["timestamp"].values.astype(np.float64)
    # Detect unit: if max > 1e15, assume microseconds
    if ts.max() > 1e15:
        ts_sec = ts / 1e6
    elif ts.max() > 1e12:
        ts_sec = ts / 1e3
    else:
        ts_sec = ts

    duration_sec = float(ts_sec[-1] - ts_sec[0])
    result["duration_sec"] = round(duration_sec, 2)

    diffs = np.diff(ts_sec)
    avg_interval = float(np.mean(diffs)) if len(diffs) > 0 else 0.0
    max_gap_sec = float(np.max(diffs)) if len(diffs) > 0 else 0.0
    gap_count_gt5s = int(np.sum(diffs > 5.0))
    gap_count_gt60s = int(np.sum(diffs > 60.0))

    result["avg_interval"] = round(avg_interval, 4)
    result["max_gap_sec"] = round(max_gap_sec, 2)
    result["gap_count_gt5s"] = gap_count_gt5s
    result["gap_count_gt60s"] = gap_count_gt60s

    # --- NaN count -----------------------------------------------------------
    nan_count = int(df.isna().sum().sum())
    result["nan_count"] = nan_count

    # --- Spread (best ask - best bid) ----------------------------------------
    best_ask_col = "asks[0].price"
    best_bid_col = "bids[0].price"
    if best_ask_col in df.columns and best_bid_col in df.columns:
        spreads = df[best_ask_col].values - df[best_bid_col].values
        spread_always_positive = bool(np.all(spreads > 0))
        result["spread_always_positive"] = spread_always_positive
    else:
        spread_always_positive = True  # can't check, assume ok
        result["spread_always_positive"] = "N/A"

    # --- Mid price range & monotonicity --------------------------------------
    if best_ask_col in df.columns and best_bid_col in df.columns:
        mid = (df[best_ask_col].values + df[best_bid_col].values) / 2.0
        result["mid_price_range"] = (round(float(np.nanmin(mid)), 2),
                                     round(float(np.nanmax(mid)), 2))
        # "Monotonic pct" = fraction of consecutive moves that are non-decreasing
        if len(mid) > 1:
            mid_diffs = np.diff(mid)
            nondec = np.sum(mid_diffs >= 0)
            price_monotonic_pct = round(float(nondec / len(mid_diffs) * 100), 2)
        else:
            price_monotonic_pct = 100.0
        result["price_monotonic_pct"] = price_monotonic_pct
    else:
        result["mid_price_range"] = "N/A"
        result["price_monotonic_pct"] = "N/A"

    # --- Status determination ------------------------------------------------
    status = "OK"
    reasons = []

    if nan_count > 0:
        status = "ERROR"
        reasons.append(f"nan_count={nan_count}")

    if max_gap_sec > 60.0:
        status = "ERROR"
        reasons.append(f"max_gap={max_gap_sec:.1f}s")
    elif max_gap_sec > 5.0:
        if status != "ERROR":
            status = "WARNING"
        reasons.append(f"max_gap={max_gap_sec:.1f}s")

    if abs(avg_interval - 1.0) > 0.1:
        if status != "ERROR":
            status = "WARNING"
        reasons.append(f"avg_interval={avg_interval:.3f}s")

    if isinstance(spread_always_positive, bool) and not spread_always_positive:
        status = "ERROR"
        reasons.append("negative spread detected")

    result["status"] = status
    if reasons:
        result["reason"] = "; ".join(reasons)

    return result


# ---------------------------------------------------------------------------
# 2. Trades quality check
# ---------------------------------------------------------------------------

def check_trades_quality(csv_path: str) -> dict:
    """Check a single day's trades CSV for issues.

    Returns dict with:
      total_rows, duration_sec, avg_interval, max_gap_sec,
      gap_count_gt5s, gap_count_gt60s, nan_count,
      buy_count, sell_count, status ('OK' / 'WARNING' / 'ERROR')
    """
    df = pd.read_csv(csv_path)
    result: Dict[str, object] = {"file": os.path.basename(csv_path)}

    total_rows = len(df)
    result["total_rows"] = total_rows

    if total_rows == 0:
        result["status"] = "ERROR"
        result["reason"] = "empty file"
        return result

    # --- Timestamps ----------------------------------------------------------
    ts = df["timestamp"].values.astype(np.float64)
    if ts.max() > 1e15:
        ts_sec = ts / 1e6
    elif ts.max() > 1e12:
        ts_sec = ts / 1e3
    else:
        ts_sec = ts

    # Sort for interval calculation (trades may not be sorted)
    ts_sorted = np.sort(ts_sec)
    duration_sec = float(ts_sorted[-1] - ts_sorted[0])
    result["duration_sec"] = round(duration_sec, 2)

    diffs = np.diff(ts_sorted)
    # Filter out zero diffs (multiple trades at same timestamp)
    nonzero_diffs = diffs[diffs > 0]
    avg_interval = float(np.mean(nonzero_diffs)) if len(nonzero_diffs) > 0 else 0.0
    max_gap_sec = float(np.max(diffs)) if len(diffs) > 0 else 0.0
    gap_count_gt5s = int(np.sum(diffs > 5.0))
    gap_count_gt60s = int(np.sum(diffs > 60.0))

    result["avg_interval"] = round(avg_interval, 4)
    result["max_gap_sec"] = round(max_gap_sec, 2)
    result["gap_count_gt5s"] = gap_count_gt5s
    result["gap_count_gt60s"] = gap_count_gt60s

    # --- NaN count -----------------------------------------------------------
    nan_count = int(df.isna().sum().sum())
    result["nan_count"] = nan_count

    # --- Side counts ---------------------------------------------------------
    if "side" in df.columns:
        result["buy_count"] = int((df["side"] == "Buy").sum())
        result["sell_count"] = int((df["side"] == "Sell").sum())
    else:
        result["buy_count"] = "N/A"
        result["sell_count"] = "N/A"

    # --- Duplicate exec_id detection -----------------------------------------
    # REST collectors commonly double-poll and can produce duplicate trades.
    # Without dedup, volumes / trade_imbalance are inflated and the model
    # learns a fake signal.  Flag as ERROR at >1% duplicates (the pipeline
    # defensively dedupes but we still want data quality visibility).
    if "exec_id" in df.columns and total_rows > 0:
        n_unique = int(df["exec_id"].nunique(dropna=False))
        dup_count = total_rows - n_unique
        dup_pct = (dup_count / total_rows) * 100.0
        result["duplicate_exec_id_count"] = dup_count
        result["duplicate_exec_id_pct"] = round(dup_pct, 2)
    else:
        dup_count = 0
        dup_pct = 0.0
        result["duplicate_exec_id_count"] = "N/A"
        result["duplicate_exec_id_pct"] = "N/A"

    # --- Status determination ------------------------------------------------
    status = "OK"
    reasons = []

    if nan_count > 0:
        status = "ERROR"
        reasons.append(f"nan_count={nan_count}")

    if max_gap_sec > 60.0:
        status = "ERROR"
        reasons.append(f"max_gap={max_gap_sec:.1f}s")
    elif max_gap_sec > 5.0:
        if status != "ERROR":
            status = "WARNING"
        reasons.append(f"max_gap={max_gap_sec:.1f}s")

    if isinstance(dup_pct, float) and dup_pct > 1.0:
        status = "ERROR"
        reasons.append(f"duplicates={dup_pct:.2f}% ({dup_count})")

    result["status"] = status
    if reasons:
        result["reason"] = "; ".join(reasons)

    return result


# ---------------------------------------------------------------------------
# 3. Scan all daily files
# ---------------------------------------------------------------------------

def check_all_days(data_dir: str) -> None:
    """Scan all daily files, print quality report, flag issues."""
    depth_files = sorted(glob.glob(os.path.join(data_dir, "*_depth*.csv")))
    trade_files = sorted(glob.glob(os.path.join(data_dir, "*_trades*.csv")))

    print("=" * 80)
    print(f"Data Quality Report  --  {data_dir}")
    print("=" * 80)

    # --- Depth files ---------------------------------------------------------
    print(f"\n--- Depth files ({len(depth_files)}) ---")
    for fp in depth_files:
        report = check_depth_quality(fp)
        _print_report(report)

    # --- Trade files ---------------------------------------------------------
    print(f"\n--- Trade files ({len(trade_files)}) ---")
    for fp in trade_files:
        report = check_trades_quality(fp)
        _print_report(report)

    if not depth_files and not trade_files:
        print("[WARNING] No CSV files found in directory.")

    print("\n" + "=" * 80)


def _print_report(report: dict) -> None:
    """Pretty-print a single file quality report."""
    status = report.get("status", "UNKNOWN")
    tag = {"OK": "[  OK  ]", "WARNING": "[ WARN ]", "ERROR": "[ERROR!]"}.get(status, "[  ?   ]")
    file_name = report.get("file", "?")
    rows = report.get("total_rows", "?")
    dur = report.get("duration_sec", "?")
    avg = report.get("avg_interval", "?")
    maxgap = report.get("max_gap_sec", "?")
    reason = report.get("reason", "")
    detail = f"  ({reason})" if reason else ""
    print(f"  {tag} {file_name}  rows={rows}  dur={dur}s  avg_interval={avg}s  max_gap={maxgap}s{detail}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Check LOB data quality")
    parser.add_argument("--data-dir", required=True, help="Directory with daily CSV files")
    args = parser.parse_args()

    if not os.path.isdir(args.data_dir):
        print(f"Error: directory not found: {args.data_dir}", file=sys.stderr)
        sys.exit(1)

    check_all_days(args.data_dir)


if __name__ == "__main__":
    main()
