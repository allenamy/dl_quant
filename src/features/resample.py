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

    # Drop leading rows that couldn't be filled (no prior data)
    merged.dropna(subset=lob_cols, how="any", inplace=True)
    merged.reset_index(drop=True, inplace=True)

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
