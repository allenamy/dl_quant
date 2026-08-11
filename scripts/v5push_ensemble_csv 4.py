"""Generate production CSV from Track A + V5 prod ensemble.

Format mirrors exports/v5_singh_alpha0_huber/y600_predictions_live.csv.
Ensemble: value-blend in q50_bps_live space; w_TrackA=0.4 default.
"""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import numpy as np
import pathlib

EMA_ALPHA = 0.01
WARMUP = 50


def causal_ema_demean(q50_bps: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return demeaned q50 and the EMA state series (lag-1)."""
    n = len(q50_bps)
    ema = np.zeros(n)
    cur = 0.0
    for i in range(n):
        if i > 0:
            cur = EMA_ALPHA * q50_bps[i - 1] + (1 - EMA_ALPHA) * cur
        ema[i] = cur
    demeaned = q50_bps - ema
    # Zero out warmup
    demeaned[:WARMUP] = 0.0
    return demeaned, ema


def load_fold(npz_path: pathlib.Path):
    z = np.load(npz_path, allow_pickle=True)
    pred = z["predictions"]
    y = z["targets"].reshape(-1)
    m = z["mask"].reshape(-1).astype(bool)
    ts = z["timestamps"]
    sy = float(z["y_sigma"])
    ymed = float(z["y_median"])
    q10 = pred[:, 0] * sy + ymed
    q50 = pred[:, 1] * sy + ymed
    q90 = pred[:, 2] * sy + ymed
    order = np.argsort(ts)
    return {
        "ts": ts[order],
        "q10": q10[order], "q50": q50[order], "q90": q90[order],
        "y": (y * sy + ymed)[order],
        "y_z": y[order],
        "q50_z": pred[order, 1],
        "mask": m[order],
        "y_sigma": sy,
        "y_median": ymed,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--track-a-dir", default="/tmp/track_a_preds",
                    help="Folder with fold_0/1/2.npz (Track A preds)")
    ap.add_argument("--v5-prod-dir", default="experiments/v5_final/singleh_alpha0_huber",
                    help="V5 prod 3-fold dir")
    ap.add_argument("--w-track-a", type=float, default=0.4,
                    help="Weight of Track A in ensemble (V5 prod gets 1-w)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    track_a_dir = pathlib.Path(args.track_a_dir)
    v5_dir = pathlib.Path(args.v5_prod_dir)
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    print(f"Loading Track A from {track_a_dir}")
    print(f"Loading V5 prod from {v5_dir}")
    print(f"Ensemble weight: w_TrackA={args.w_track_a}, w_V5prod={1 - args.w_track_a}")
    print(f"Output: {out}")

    rows = []
    for f in range(3):
        # Track A may be named fold_X.npz (from scp) or in subdir
        ta_paths = [track_a_dir / f"fold_{f}.npz", track_a_dir / f"fold_{f}" / "test_preds.npz"]
        ta_p = next((p for p in ta_paths if p.exists()), None)
        if ta_p is None:
            raise FileNotFoundError(f"Track A fold {f}: tried {ta_paths}")
        v5_p = v5_dir / f"fold_{f}" / "test_preds.npz"
        if not v5_p.exists():
            raise FileNotFoundError(v5_p)
        a = load_fold(ta_p)
        b = load_fold(v5_p)

        # Align on ts. They should have identical timestamps since both use same fold split.
        assert np.array_equal(a["ts"], b["ts"]), f"fold {f} ts mismatch"
        assert np.array_equal(a["mask"], b["mask"]), f"fold {f} mask mismatch"

        n = len(a["ts"])
        # Per-fold live calibration on each side
        q50_a_bps = a["q50"] * 1e4
        q50_b_bps = b["q50"] * 1e4
        q50_a_live, ema_a = causal_ema_demean(q50_a_bps)
        q50_b_live, ema_b = causal_ema_demean(q50_b_bps)
        w = args.w_track_a
        q50_ens_live = w * q50_a_live + (1 - w) * q50_b_live
        ema_ens = w * ema_a + (1 - w) * ema_b

        y_bps = a["y"] * 1e4
        y_sigma_bps = a["y_sigma"] * 1e4

        for i in range(n):
            ts_us = int(a["ts"][i])
            dt_str = dt.datetime.fromtimestamp(ts_us / 1e6, tz=dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            warmup = i < WARMUP
            # Ensemble q50 raw (un-live) — value blend in logret space
            q50_ens_logret = w * a["q50"][i] + (1 - w) * b["q50"][i]
            q10_ens_logret = w * a["q10"][i] + (1 - w) * b["q10"][i]
            q90_ens_logret = w * a["q90"][i] + (1 - w) * b["q90"][i]
            rows.append({
                "timestamp_us": ts_us,
                "datetime_utc": dt_str,
                "fold": f,
                "horizon_sec": 600,
                "mask": int(a["mask"][i]),
                "y_true_logret": float(a["y_z"][i] * a["y_sigma"] + a["y_median"]),
                "y_true_bps": float(y_bps[i]),
                "y_pred_q10_logret": float(q10_ens_logret),
                "y_pred_q50_logret": float(q50_ens_logret),
                "y_pred_q90_logret": float(q90_ens_logret),
                "y_pred_q50_bps": float(q50_ens_logret * 1e4),
                "y_pred_q50_bps_live": float(q50_ens_live[i]) if not warmup else 0.0,
                "y_pred_q50_bps_live_ema_state": float(ema_ens[i]),
                "y_sigma_train_bps": y_sigma_bps,
                "warmup": warmup,
            })
        print(f"  fold {f}: n={n} (mask=1: {a['mask'].sum()})")

    # Write CSV
    fieldnames = list(rows[0].keys())
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows):,} rows to {out}")


if __name__ == "__main__":
    main()
