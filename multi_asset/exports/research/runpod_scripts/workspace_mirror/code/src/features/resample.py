"""Resample raw L2 orderbook ticks to 1-second bars (last-tick-per-second)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def resample_lob_to_1s(
    df: pd.DataFrame,
    n_levels: int = 25,
    ts_col: str = "timestamp",
) -> pd.DataFrame:
    """Resample a tick-level LOB DataFrame to 1-second bars.

    Parameters
    ----------
    df : pd.DataFrame
        Raw LOB data.  Must contain *ts_col* (int64, **microseconds**) and
        columns ``asks[i].price``, ``asks[i].amount``, ``bids[i].price``,
        ``bids[i].amount`` for ``i`` in ``range(n_levels)``.
    n_levels : int
        Number of orderbook levels (0..n_levels-1).
    ts_col : str
        Name of the timestamp column (microseconds since epoch).

    Returns
    -------
    pd.DataFrame
        One row per second, forward-filled (causal).  The ``timestamp``
        column is an int64 representing the second boundary in microseconds.

    Notes
    -----
    * Timestamps are **floored** (truncated) to the second, never rounded,
      to avoid look-ahead leakage.
    * For each 1-second bucket the **last** tick is kept (most recent state).
    * A complete 1-second grid is created from first to last second; gaps
      are forward-filled.  Leading rows that have no prior data are dropped.
    """

    # --- identify LOB value columns -------------------------------------------
    lob_cols: list[str] = []
    for i in range(n_levels):
        for side in ("asks", "bids"):
            for field in ("price", "amount"):
                col = f"{side}[{i}].{field}"
                if col in df.columns:
                    lob_cols.append(col)

    if not lob_cols:
        raise ValueError("No LOB columns found in DataFrame")

    # Work on a lightweight copy containing only what we need
    work = df[[ts_col] + lob_cols].copy()

    # --- floor timestamp to second boundary (truncate, NOT round) -------------
    us_per_sec = 1_000_000
    work["_ts_sec"] = (work[ts_col] // us_per_sec) * us_per_sec

    # --- keep last tick per second (most recent snapshot) ---------------------
    work.sort_values(ts_col, inplace=True)
    last_per_sec = work.groupby("_ts_sec", sort=True).last().reset_index()

    # --- build complete 1-second grid -----------------------------------------
    ts_min = last_per_sec["_ts_sec"].iloc[0]
    ts_max = last_per_sec["_ts_sec"].iloc[-1]
    full_grid = pd.DataFrame(
        {"_ts_sec": np.arange(ts_min, ts_max + us_per_sec, us_per_sec)}
    )

    # Merge and forward-fill (causal — no future information leaks back)
    merged = full_grid.merge(last_per_sec.drop(columns=[ts_col]), on="_ts_sec", how="left")
    merged.sort_values("_ts_sec", inplace=True)
    merged[lob_cols] = merged[lob_cols].ffill()

    # Drop leading rows that lack top-of-book data (cannot compute mid price).
    # IMPORTANT: deeper levels (L1..L24) are allowed to be NaN and are handled
    # separately below — historically this was dropna(how="any") over *all*
    # LOB columns, which silently voided entire days whenever any deep level
    # was sparsely populated.
    top_cols = [c for c in ("asks[0].price", "asks[0].amount",
                            "bids[0].price", "bids[0].amount")
                if c in lob_cols]
    rows_before = len(merged)
    merged.dropna(subset=top_cols, how="any", inplace=True)
    rows_after = len(merged)

    # Pad missing deeper-level prices / amounts rather than dropping rows.
    # Deeper NaN prices are filled with the top-of-book price on the same side
    # (a flat "wall" of zero liquidity); deeper NaN amounts are filled with 0.
    if len(merged) > 0:
        best_ask = merged["asks[0].price"] if "asks[0].price" in merged else None
        best_bid = merged["bids[0].price"] if "bids[0].price" in merged else None
        for col in lob_cols:
            if col in top_cols:
                continue
            if col.endswith(".amount"):
                merged[col] = merged[col].fillna(0.0)
            elif col.endswith(".price") and best_ask is not None and best_bid is not None:
                side_default = best_ask if col.startswith("asks[") else best_bid
                merged[col] = merged[col].fillna(side_default)
            else:
                merged[col] = merged[col].fillna(0.0)

    merged.reset_index(drop=True, inplace=True)

    # Warn loudly if we lost >5% of rows (likely sparse top-of-book coverage)
    dropped = rows_before - rows_after
    if rows_before > 0 and dropped / rows_before > 0.05:
        import logging
        logging.getLogger(__name__).warning(
            "resample_lob_to_1s: dropped %d/%d rows (%.1f%%) lacking top-of-book data",
            dropped, rows_before, 100.0 * dropped / rows_before,
        )

    # Rename the second-boundary column back to the original ts name
    merged.rename(columns={"_ts_sec": ts_col}, inplace=True)

    return merged


# ---------------------------------------------------------------------------
# Quick smoke test when run directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    print("Reading BTCUSDT.csv (first 10 000 rows) ...")
    raw = pd.read_csv("BTCUSDT.csv", nrows=10_000)
    print(f"  raw shape: {raw.shape}")

    bars = resample_lob_to_1s(raw)
    print(f"  1-sec bars shape: {bars.shape}")
    print(f"  first ts: {bars['timestamp'].iloc[0]}")
    print(f"  last  ts: {bars['timestamp'].iloc[-1]}")
    diff = bars["timestamp"].diff().dropna().unique()
    print(f"  unique diffs (us): {diff}")
    print("OK")
