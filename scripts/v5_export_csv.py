"""V5 production CSV exporter — for colleague backtest after V5 final 3-fold.

Output schema (per row):
  timestamp_us, datetime_utc, fold, mask,
  y_true_logret, y_true_bps,
  y_pred_mu_bps,        # primary signal (μ from heteroscedastic head, or q50 fallback)
  y_pred_sigma_bps,     # per-sample uncertainty (σ; 0 for non-NLL losses)
  y_sigma_train_bps,    # training-period y σ (context)
  y_median_train_bps    # training-period y median (audit; CODEX FIX)

CODEX FIX: de-normalize as z*sigma + median (NOT z*sigma alone).
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd


def export_csv(exp_dir: Path, n_folds: int, ckpt_kind: str, out_path: Path) -> int:
    rows = []
    file_map = {
        "BEST": "test_preds.npz",
        "EMA": "ema_test_preds.npz",
        "SWA": "swa_test_preds.npz",
    }
    fname = file_map[ckpt_kind]
    for fold in range(n_folds):
        npz_path = exp_dir / f"fold_{fold}" / fname
        if not npz_path.exists():
            print(f"[WARN] missing {npz_path}; skip fold {fold}")
            continue
        d = np.load(npz_path)
        ts = d["timestamps"]
        mask = d["mask"]
        y_true_z = d.get("targets")
        sigma_train = float(d["y_sigma"]) if "y_sigma" in d.files else 1.0
        y_median = float(d["y_median"]) if "y_median" in d.files else 0.0

        # V5 may store mu, log_sigma. V4: predictions[:, 1] = q50.
        if "mu" in d.files:
            mu_z = d["mu"].astype(np.float64).ravel()
        else:
            mu_z = d["predictions"][:, 1].astype(np.float64)
        if "log_sigma" in d.files:
            sigma_pred_z = np.exp(d["log_sigma"].astype(np.float64).ravel())
        else:
            sigma_pred_z = np.zeros_like(mu_z)

        # De-normalize: z * sigma + median (CODEX FIX — μ has offset, σ is scale-only)
        for i in range(len(ts)):
            dt_utc = datetime.fromtimestamp(int(ts[i]) / 1e6, tz=timezone.utc)
            y_lr = (float(y_true_z[i]) * sigma_train + y_median) if y_true_z is not None else float("nan")
            mu_lr = float(mu_z[i]) * sigma_train + y_median
            sig_lr = float(sigma_pred_z[i]) * sigma_train  # σ is scale, no median offset
            rows.append({
                "timestamp_us": int(ts[i]),
                "datetime_utc": dt_utc.strftime("%Y-%m-%d %H:%M:%S.%f"),
                "fold": fold,
                "mask": bool(mask[i]),
                "y_true_logret": y_lr,
                "y_true_bps": y_lr * 1e4,
                "y_pred_mu_bps": mu_lr * 1e4,
                "y_pred_sigma_bps": sig_lr * 1e4,
                "y_sigma_train_bps": sigma_train * 1e4,
                "y_median_train_bps": y_median * 1e4,
            })
        print(f"  fold {fold}: {len(ts):,} rows ({int(mask.sum()):,} valid), σ_train={sigma_train*1e4:.4f} bps, median_train={y_median*1e4:.4f} bps")

    df = pd.DataFrame(rows)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False, float_format="%.8g")
    print(f"Wrote {out_path}: {len(df):,} rows ({df['mask'].sum():,} valid)")
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--exp-dir", required=True)
    p.add_argument("--n-folds", type=int, default=3)
    p.add_argument("--ckpt", default="EMA", choices=["BEST", "EMA", "SWA"])
    p.add_argument("--out", required=True)
    args = p.parse_args()
    return export_csv(Path(args.exp_dir), args.n_folds, args.ckpt, Path(args.out))


if __name__ == "__main__":
    raise SystemExit(main())
