"""Multi-day feature pipeline for per-day book + trades folders.

Iterates over a per-day folder structure like

    book_root/YYYY-MM-DD/BTCUSDT.csv.gz
    trades_root/YYYY-MM-DD/BTCUSDT.csv.gz

and, for every date, loads the depth snapshot, resamples to 1-second bars,
optionally loads the matching trade file, and calls ``build_npz_for_day``.
Outputs are written as ``output_dir/YYYY-MM-DD.npz`` using
``np.savez_compressed`` (disk-constrained environment — raw ``savez`` can
blow the budget an order of magnitude).

This is the multi-day counterpart to ``pipeline.process_csv_to_npz`` (which
handles a single CSV without trades).  It is intentionally defensive:

* one day's failure (IO error, schema mismatch, empty file) must not abort
  the whole run — the error is logged and iteration continues;
* free disk space is checked before every save and the run is stopped with
  a warning if it drops below a safety floor (default 500 MB);
* ``skip_existing=True`` lets repeated runs cheaply resume without
  recomputing.

Trade CSVs from the ``crypto_data/trades/trades/*`` folders follow the
tardis.dev / Binance-futures schema:
``exchange, symbol, timestamp, local_timestamp, id, side, price, amount``
with ``side`` being lowercase ``"buy"`` / ``"sell"`` and the volume column
named ``amount``.  ``aggregate_trades_to_1s`` expects ``side`` to be
``"Buy"`` / ``"Sell"`` and the volume column to be named ``size``, so we
normalise here before handing the frame down.
"""

from __future__ import annotations

import gc
import logging
import re
import shutil
import time
from pathlib import Path

import numpy as np
import pandas as pd

from src.features.pipeline import _save_result_npz, build_npz_for_day
from src.features.resample import resample_lob_to_1s


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Minimum free bytes we insist on keeping on the output volume.  Below this
# we stop — an in-flight ``savez_compressed`` can consume hundreds of MB
# for a typical day (~1500 windows x 300 x 58 float32 etc.), and running
# the volume completely dry is far worse than truncating a run early.
_MIN_FREE_BYTES = 500 * 1024 * 1024  # 500 MB

# Fallback memory reporter when ``psutil`` isn't available.  Using ``resource``
# avoids a hard dependency just for a log line.
try:  # pragma: no cover - import guard
    import psutil  # type: ignore

    def _rss_mb() -> float:
        return psutil.Process().memory_info().rss / (1024 * 1024)
except Exception:  # pragma: no cover - import guard
    try:
        import resource

        def _rss_mb() -> float:
            # ``ru_maxrss`` is KB on Linux, bytes on macOS.  Normalising here
            # isn't worth it — the value is informational only.
            return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    except Exception:
        def _rss_mb() -> float:
            return float("nan")


def _list_dates(root: Path) -> list[str]:
    """Return sorted ``YYYY-MM-DD`` subfolder names under *root*."""
    if not root.exists() or not root.is_dir():
        return []
    return sorted(
        entry.name
        for entry in root.iterdir()
        if entry.is_dir() and _DATE_RE.match(entry.name)
    )


def _read_gzipped_csv_robust(path: Path) -> pd.DataFrame:
    """Load a possibly-truncated gzip CSV by streaming and ignoring EOF errors.

    Many files in crypto_data/ are truncated at ~14MB (iCloud partial sync).
    Standard pd.read_csv raises EOFError on the incomplete gzip stream,
    discarding all successfully-decompressed rows. This helper streams line
    by line, catches the truncation, and returns whatever was read.
    """
    import gzip as _gzip
    header = None
    rows = []
    try:
        with _gzip.open(path, "rt", errors="replace") as f:
            for line in f:
                if header is None:
                    header = line.rstrip("\n").split(",")
                    continue
                rows.append(line)
    except (EOFError, OSError):
        pass  # truncated; use what we got
    if header is None or not rows:
        raise ValueError(f"{path}: no readable content")
    # Build DataFrame from buffered lines
    from io import StringIO
    buf = StringIO("".join([",".join(header) + "\n"] + rows))
    return pd.read_csv(buf, on_bad_lines="skip")


def _read_book_csv(path: Path) -> pd.DataFrame:
    """Load a depth-snapshot CSV (optionally gzip), robust to truncation."""
    if path.suffix == ".gz" or path.name.endswith(".csv.gz"):
        try:
            return pd.read_csv(path, compression="gzip")
        except EOFError:
            return _read_gzipped_csv_robust(path)
    return pd.read_csv(path)


def _read_and_normalise_trades(path: Path) -> pd.DataFrame:
    """Load a trades CSV and coerce it into the shape expected by
    ``aggregate_trades_to_1s``.

    The crypto_data files ship with columns
    ``exchange, symbol, timestamp, local_timestamp, id, side, price, amount``.
    The aggregator wants ``timestamp, price, size, side`` with ``side`` being
    ``"Buy"`` or ``"Sell"`` and (optionally) ``exec_id`` for de-duplication.
    We rename/capitalise in place — cheap, string-only work.
    """
    if path.suffix == ".gz" or path.name.endswith(".csv.gz"):
        try:
            df = pd.read_csv(path, compression="gzip")
        except EOFError:
            df = _read_gzipped_csv_robust(path)
    else:
        df = pd.read_csv(path)

    # Map the public-feed naming to the internal one.  ``inplace=True`` to
    # avoid doubling the frame's memory footprint for big trade files.
    rename_map: dict[str, str] = {}
    if "amount" in df.columns and "size" not in df.columns:
        rename_map["amount"] = "size"
    if "id" in df.columns and "exec_id" not in df.columns:
        rename_map["id"] = "exec_id"
    if rename_map:
        df.rename(columns=rename_map, inplace=True)

    if "side" in df.columns:
        # ``aggregate_trades_to_1s`` does exact-string matching on "Buy".
        # Using ``.str.title()`` is safe even if the column already holds
        # ``"Buy"`` / ``"Sell"``; no-ops if upper-cased.
        df["side"] = df["side"].astype(str).str.title()

    return df


def _free_bytes(path: Path) -> int:
    """Return free bytes on the volume holding *path*, or the nearest
    ancestor that exists (``shutil.disk_usage`` requires an existing path).
    """
    target = path
    while not target.exists():
        parent = target.parent
        if parent == target:
            break
        target = parent
    return shutil.disk_usage(target).free


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def process_multi_day_crypto_folder(
    book_root: str | Path,
    trades_root: str | Path | None,
    output_dir: str | Path,
    *,
    horizons_sec: list[int] | None = None,
    horizon_sec: int = 180,
    input_len: int = 300,
    stride: int = 180,
    n_levels: int = 25,
    start_date: str | None = None,
    end_date: str | None = None,
    skip_existing: bool = True,
    verbose: bool = True,
    include_ridge_features: bool = False,
    include_regime_prior: bool = False,
    quantize_features: bool = False,
) -> list[Path]:
    """Iterate per-day folders, build sliding-window NPZ files.

    Parameters
    ----------
    book_root : str or Path
        Root containing ``YYYY-MM-DD/BTCUSDT.csv.gz`` depth snapshots
        (e.g. ``crypto_data/book_snapshot_25``).
    trades_root : str or Path or None
        Root containing trades for the matching dates, or ``None`` to
        skip trade features entirely.  Missing per-day trade files are
        handled gracefully — depth-only features (49) will be emitted.
    output_dir : str or Path
        Output directory for NPZ files (one per day).  Created if absent.
    horizons_sec : list[int] | None
        Multi-horizon label list.  When supplied the pipeline emits
        ``y_{H}`` / ``y_mask_{H}`` for each horizon and requires
        ``min_rows >= input_len + max(horizons_sec)`` for a day to be
        emitted.  ``None`` (default) keeps single-horizon behaviour.
    horizon_sec, input_len, stride, n_levels
        Forwarded to ``build_npz_for_day``.  ``stride >= horizon_sec`` is
        recommended (CLAUDE.md) to avoid label overlap.  When
        ``horizons_sec`` is supplied the recommendation becomes
        ``stride >= max(horizons_sec)``.
    start_date, end_date
        Inclusive ``YYYY-MM-DD`` bounds.  ``None`` = unbounded on that side.
    skip_existing
        If True, skip days whose output NPZ already exists.
    verbose
        If True, log per-day progress at INFO level.
    include_ridge_features : bool
        If True, 6 ridge-informed derived features are appended to the
        feature matrix (58 base + 6 = 64 cols). Default False (V3 behaviour).
    include_regime_prior : bool
        If True, 6 regime-prior features are computed and stored as a
        separate (N_win, 6) ``regime_prior`` array in the NPZ, keyed per
        window at pred_idx. Default False.
    quantize_features : bool
        If True, X and X_raw are stored as float16 in the NPZ (halves
        disk footprint at negligible precision loss after per-sample
        normalize + clip). Default False (V3 compatibility).

    Returns
    -------
    list[Path]
        Paths of every NPZ file that was written (or already existed and
        was skipped — the full set the caller can iterate over).
    """
    book_root = Path(book_root)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    trades_root_p: Path | None = Path(trades_root) if trades_root is not None else None

    # Effective horizon set for all downstream size / skip logic.  We use the
    # max for the ``min_rows`` gate (otherwise days that would produce a
    # mostly-masked long horizon get silently dropped from the output).
    if horizons_sec is not None:
        if len(horizons_sec) == 0:
            raise ValueError("horizons_sec must be a non-empty list")
        horizons_list = [int(h) for h in horizons_sec]
        if any(h <= 0 for h in horizons_list):
            raise ValueError(
                f"horizons_sec must contain positive integers, got {horizons_list}"
            )
        max_horizon = max(horizons_list)
    else:
        horizons_list = None
        max_horizon = int(horizon_sec)

    # Warn the caller early about CLAUDE.md's stride >= horizon requirement.
    # build_npz_for_day already warns, but here we surface it once per run
    # rather than once per day.  When multi-horizon is requested we check
    # against the longest horizon because that one governs label overlap.
    if stride < max_horizon:
        if horizons_list is not None:
            logger.warning(
                "stride (%d) < max(horizons_sec)=%d: labels will overlap by %ds "
                "at the longest horizon",
                stride,
                max_horizon,
                max_horizon - stride,
            )
        else:
            logger.warning(
                "stride (%d) < horizon_sec (%d): labels will overlap by %ds",
                stride,
                horizon_sec,
                horizon_sec - stride,
            )

    dates = _list_dates(book_root)
    if start_date is not None:
        dates = [d for d in dates if d >= start_date]
    if end_date is not None:
        dates = [d for d in dates if d <= end_date]

    if verbose:
        logger.info(
            "Discovered %d candidate dates in %s (range %s .. %s)",
            len(dates),
            book_root,
            dates[0] if dates else "-",
            dates[-1] if dates else "-",
        )

    saved_paths: list[Path] = []

    for date_str in dates:
        out_path = output_dir / f"{date_str}.npz"

        if skip_existing and out_path.exists():
            if verbose:
                logger.info("[%s] skip (exists)", date_str)
            saved_paths.append(out_path)
            continue

        book_path = book_root / date_str / "BTCUSDT.csv.gz"
        if not book_path.exists():
            # ``.csv`` fallback for uncompressed variants.
            alt = book_root / date_str / "BTCUSDT.csv"
            if alt.exists():
                book_path = alt
            else:
                logger.warning("[%s] book file missing: %s", date_str, book_path)
                continue

        trades_path: Path | None = None
        if trades_root_p is not None:
            cand = trades_root_p / date_str / "BTCUSDT.csv.gz"
            if cand.exists():
                trades_path = cand
            else:
                alt = trades_root_p / date_str / "BTCUSDT.csv"
                if alt.exists():
                    trades_path = alt

        # --- disk guard before we allocate large arrays -------------------
        free = _free_bytes(output_dir)
        if free < _MIN_FREE_BYTES:
            logger.error(
                "[%s] aborting run: only %.1f MB free on output volume (need >%.0f MB)",
                date_str,
                free / (1024 * 1024),
                _MIN_FREE_BYTES / (1024 * 1024),
            )
            break

        t0 = time.time()
        try:
            raw_book = _read_book_csv(book_path)
            df_1s = resample_lob_to_1s(raw_book, n_levels=n_levels)

            # Date-folder sanity: some upstream CSVs leak a few rows of the
            # previous or next UTC day. Filter rows whose timestamp is
            # outside the [folder_date_00:00:00, folder_date_24:00:00) range.
            try:
                folder_start_us = int(
                    pd.Timestamp(date_str, tz="UTC").timestamp() * 1_000_000
                )
                folder_end_us = folder_start_us + 86_400 * 1_000_000
                ts_col = "timestamp"
                before_n = len(df_1s)
                df_1s = df_1s[
                    (df_1s[ts_col] >= folder_start_us)
                    & (df_1s[ts_col] < folder_end_us)
                ].reset_index(drop=True)
                stripped = before_n - len(df_1s)
                if stripped > 0:
                    logger.warning(
                        "[%s] stripped %d rows outside folder date range",
                        date_str, stripped,
                    )
            except (ValueError, KeyError):
                # If parsing fails, leave rows untouched; downstream will
                # still work correctly on the uniform 1s grid.
                pass

            # Require enough rows for at least one valid-mask window:
            #   window spans [start, start+input_len-1]
            #   label uses mid at pred_idx + H for the largest horizon H
            # Using max_horizon (not horizon_sec alone) ensures we don't emit
            # a day whose longest-horizon labels would be entirely masked.
            min_rows = input_len + max_horizon
            if len(df_1s) < min_rows:
                logger.warning(
                    "[%s] only %d 1s rows (< input_len+max_horizon=%d); skipping",
                    date_str,
                    len(df_1s),
                    min_rows,
                )
                continue

            trades_df: pd.DataFrame | None = None
            if trades_path is not None:
                trades_df = _read_and_normalise_trades(trades_path)
            elif trades_root_p is not None and verbose:
                logger.info("[%s] no trades file; depth-only features", date_str)

            result = build_npz_for_day(
                df_1s,
                trades_df=trades_df,
                horizons_sec=horizons_list,
                horizon_sec=horizon_sec,
                input_len=input_len,
                stride=stride,
                n_levels=n_levels,
                include_ridge_features=include_ridge_features,
                include_regime_prior=include_regime_prior,
                quantize_features=quantize_features,
            )

            # One more disk check immediately before the write, because
            # ``build_npz_for_day`` allocates hundreds of MB transiently
            # and the earlier check may now be stale.
            free = _free_bytes(output_dir)
            if free < _MIN_FREE_BYTES:
                logger.error(
                    "[%s] aborting before save: %.1f MB free",
                    date_str,
                    free / (1024 * 1024),
                )
                break

            # Use the shared saver so every ``y_{H}`` / ``y_mask_{H}`` field
            # and the ``horizons_sec`` metadata get persisted automatically.
            _save_result_npz(out_path, result)
            saved_paths.append(out_path)

            if verbose:
                size_mb = out_path.stat().st_size / (1024 * 1024)
                dt = time.time() - t0
                logger.info(
                    "[%s] OK n_win=%d feat=%d size=%.1fMB time=%.1fs rss=%.0fMB",
                    date_str,
                    result["X"].shape[0],
                    result["X"].shape[2],
                    size_mb,
                    dt,
                    _rss_mb(),
                )

            # Free the big arrays before the next iteration; day frames can
            # be 100s of MB and we don't want them lingering.
            del raw_book, df_1s, result
            if trades_df is not None:
                del trades_df
            gc.collect()

        except Exception as exc:  # noqa: BLE001 - deliberately broad, we
            # must keep marching.  ``logger.exception`` records the trace.
            logger.exception("[%s] failed: %s", date_str, exc)
            continue

    if verbose:
        logger.info(
            "Finished: %d NPZ files in %s",
            len(saved_paths),
            output_dir,
        )

    return saved_paths


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Multi-day LOB + trades -> per-day NPZ pipeline",
    )
    parser.add_argument("--book-root", required=True)
    parser.add_argument("--trades-root", default=None)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--horizon", type=int, default=180)
    parser.add_argument(
        "--horizons",
        type=str,
        default=None,
        help="Comma-separated list of horizons in seconds (e.g. '60,180,300,600'). "
             "Overrides --horizon when supplied.",
    )
    parser.add_argument("--input-len", type=int, default=300)
    parser.add_argument("--stride", type=int, default=180)
    parser.add_argument("--n-levels", type=int, default=25)
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--no-skip-existing", action="store_true")
    args = parser.parse_args()

    horizons_sec: list[int] | None = None
    if args.horizons is not None:
        horizons_sec = [int(h) for h in args.horizons.split(",") if h.strip()]

    process_multi_day_crypto_folder(
        book_root=args.book_root,
        trades_root=args.trades_root,
        output_dir=args.output_dir,
        horizons_sec=horizons_sec,
        horizon_sec=args.horizon,
        input_len=args.input_len,
        stride=args.stride,
        n_levels=args.n_levels,
        start_date=args.start_date,
        end_date=args.end_date,
        skip_existing=not args.no_skip_existing,
    )
