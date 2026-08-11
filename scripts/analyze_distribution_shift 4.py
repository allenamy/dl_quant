"""Compute Population Stability Index (PSI) per feature across train/test
for a given fold of the full_run config.

PSI(train || test) = sum_bins (p_test - p_train) * log(p_test / p_train)

Rule-of-thumb interpretation (industry standard, e.g. Morgan Stanley):
    PSI < 0.1          : negligible distribution shift
    0.1 <= PSI < 0.25  : mild shift, model may degrade
    PSI >= 0.25        : significant shift, recalibrate

CLI:
    python3 scripts/analyze_distribution_shift.py --config configs/full_run.json \
        --fold-index 0 --out experiments/v3_full/psi.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

# Ensure project root is on sys.path so `src.*` imports work when the script
# is invoked as ``python3 scripts/analyze_distribution_shift.py``.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.training.dataset import LOBDatasetV2, build_time_series_folds  # noqa: E402


def psi(train: np.ndarray, test: np.ndarray, n_bins: int = 10) -> float:
    """Population Stability Index between train and test samples of one feature.

    Uses train quantiles as bin edges so each train bin has equal mass.
    Edges are extended to (-inf, +inf) so test samples outside the train
    support are placed in the outermost bins. An ``eps`` floor prevents
    ``log(0)`` when a bin is empty in either distribution.
    """
    eps = 1e-6
    # Use train quantiles as bin edges so each bin has equal train mass
    edges = np.quantile(train, np.linspace(0, 1, n_bins + 1))
    edges[0], edges[-1] = -np.inf, np.inf
    p_tr = np.histogram(train, bins=edges)[0] / max(len(train), 1) + eps
    p_te = np.histogram(test, bins=edges)[0] / max(len(test), 1) + eps
    return float(np.sum((p_te - p_tr) * np.log(p_te / p_tr)))


def main(config_path: str, fold_index: int, out_path: str) -> None:
    cfg = json.load(open(config_path))
    data_cfg = cfg["data"]
    train_cfg = cfg["training"]
    days = sorted([p.stem for p in Path(data_cfg["npz_dir"]).glob("*.npz")])
    folds = build_time_series_folds(
        days,
        train_days=train_cfg["train_days"],
        val_days=train_cfg["val_days"],
        test_days=train_cfg["test_days"],
        stride=train_cfg["fold_stride"],
    )
    if not folds:
        raise RuntimeError(
            f"No folds built: {len(days)} days available, need "
            f"{train_cfg['train_days']+train_cfg['val_days']+train_cfg['test_days']}."
        )
    if fold_index >= len(folds):
        raise IndexError(
            f"fold_index={fold_index} out of range (have {len(folds)} folds)."
        )
    fold = folds[fold_index]

    train_ds = LOBDatasetV2(data_cfg["npz_dir"], fold["train"], normalize=False)
    test_ds = LOBDatasetV2(data_cfg["npz_dir"], fold["test"], normalize=False)

    # Use last-timestep features (matches Ridge baseline)
    X_tr = train_ds.X[train_ds.mask > 0, -1, :].astype(np.float64)
    X_te = test_ds.X[test_ds.mask > 0, -1, :].astype(np.float64)

    # Need feature names — read from one NPZ of the train fold
    d0 = np.load(
        Path(data_cfg["npz_dir"]) / f"{fold['train'][0]}.npz", allow_pickle=True
    )
    feats = [str(f) for f in d0["features"]]

    results = []
    for i, name in enumerate(feats):
        p = psi(X_tr[:, i], X_te[:, i])
        results.append({"feature": name, "psi": p})
    results.sort(key=lambda r: -r["psi"])

    # Also: target distribution shift
    y_tr = train_ds.y[train_ds.mask > 0]
    y_te = test_ds.y[test_ds.mask > 0]
    target_psi = psi(y_tr, y_te)

    out = {
        "fold": fold_index,
        "train_days_first": fold["train"][0],
        "train_days_last": fold["train"][-1],
        "test_days_first": fold["test"][0],
        "test_days_last": fold["test"][-1],
        "train_size": int(len(X_tr)),
        "test_size": int(len(X_te)),
        "target_psi": target_psi,
        "target_train_mean": float(y_tr.mean()),
        "target_train_std": float(y_tr.std()),
        "target_test_mean": float(y_te.mean()),
        "target_test_std": float(y_te.std()),
        "top_10_shifted_features": results[:10],
        "all_features": results,
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(out_path, "w"), indent=2)
    print(f"Target PSI: {target_psi:.3f} (>0.25 = severe shift)")
    print(
        f"  target train mean/std: {y_tr.mean():+.2e} / {y_tr.std():.2e}  | "
        f"test mean/std: {y_te.mean():+.2e} / {y_te.std():.2e}"
    )
    print("Top 10 shifted features:")
    for r in results[:10]:
        print(f"  {r['feature']:40s} PSI={r['psi']:.3f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--fold-index", type=int, default=0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    main(args.config, args.fold_index, args.out)
