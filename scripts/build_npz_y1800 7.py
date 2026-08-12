"""Build y_1800 NPZ matching V4 feature configuration.

Wraps `src.features.multi_day_pipeline.process_multi_day_crypto_folder` with
V4-compatible defaults that the bare-CLI doesn't expose (ridge features +
regime prior + quantization). Runs sequentially day-by-day.

Usage (local smoke for 3 days):
    python scripts/build_npz_y1800.py \
      --book-root crypto_data/book_snapshot_25 \
      --trades-root crypto_data/trades/trades \
      --output-dir data/npz_v4_y1800_smoke \
      --start-date 2024-05-15 --end-date 2024-05-17

Usage (pod full build):
    python scripts/build_npz_y1800.py \
      --book-root crypto_data/book_snapshot_25 \
      --trades-root crypto_data/trades/trades \
      --output-dir data/npz_v4_y1800 \
      --start-date 2023-01-01 --end-date 2025-09-30

Output schema per day NPZ:
    X            : (N_win, 1200, 64)  fp16
    X_raw        : (N_win, 1200, 20, 4) fp16
    regime_prior : (N_win, 6)
    timestamps   : (N_win,) int64 us
    y_1800       : (N_win,) fp32 — log return over 1800s forward
    y_mask_1800  : (N_win,) uint8
    y, y_mask    : aliases of the smallest horizon (= y_1800 here)
    features     : (64,) <U... feature names
    horizons_sec : [1800]
"""
from __future__ import annotations

import argparse
import logging
import pathlib
import sys

# Allow `python scripts/build_npz_y1800.py ...` from repo root.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src.features.multi_day_pipeline import process_multi_day_crypto_folder  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book-root", required=True)
    parser.add_argument("--trades-root", default=None)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--input-len", type=int, default=1200,
                        help="Input window in seconds. Default 1200 (20 min).")
    parser.add_argument("--stride", type=int, default=600,
                        help="Stride between windows. Default 600 (10 min). "
                             "Below horizon for training density; eval subsamples.")
    parser.add_argument("--n-levels", type=int, default=20,
                        help="LOB levels. Default 20 (matches V4).")
    parser.add_argument("--horizon", type=int, default=1800,
                        help="Forward-return horizon in seconds. Default 1800 (30 min).")
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--no-skip-existing", action="store_true",
                        help="Re-build even if NPZ already exists.")
    parser.add_argument("--no-ridge-features", action="store_true",
                        help="Skip ridge-informed features (V4 default: include).")
    parser.add_argument("--no-regime-prior", action="store_true",
                        help="Skip regime-prior block (V4 default: include).")
    parser.add_argument("--no-quantize", action="store_true",
                        help="Store as fp32 instead of fp16. Doubles disk usage.")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    process_multi_day_crypto_folder(
        book_root=args.book_root,
        trades_root=args.trades_root,
        output_dir=args.output_dir,
        horizons_sec=[args.horizon],
        horizon_sec=args.horizon,
        input_len=args.input_len,
        stride=args.stride,
        n_levels=args.n_levels,
        start_date=args.start_date,
        end_date=args.end_date,
        skip_existing=not args.no_skip_existing,
        include_ridge_features=not args.no_ridge_features,
        include_regime_prior=not args.no_regime_prior,
        quantize_features=not args.no_quantize,
    )


if __name__ == "__main__":
    main()
