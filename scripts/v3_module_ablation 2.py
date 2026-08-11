"""Run one walk-forward fold with each V3 module individually disabled.

Output: JSON list of {label, val_corr, val_r2, val_loss, best_epoch} for the
best epoch of each ablation variant.

Variants:
    full           -- all modules enabled (baseline)
    no_masknet     -- bypass MaskNet
    no_gdcn        -- bypass GDCN
    no_raw_path    -- bypass RawLOBEncoder + fusion (Path A only)
    no_attention   -- bypass patch attention (conv output -> last-step pool)
    no_conv        -- bypass dilated causal convs
    linear_only    -- all of the above off (V3 stripped to quantile head)

CLI:
    python3 scripts/v3_module_ablation.py \
        --config configs/full_run.json \
        --fold-index 0 \
        --out experiments/v3_full/ablation.json

IMPORTANT:
  This runner replicates run_pipeline_v3.py's multi-day normalization:
    1. x_mean / x_std from TRAIN-fold X only (no leakage)
    2. y_median / y_sigma (MAD) from TRAIN-fold y only
  Skipping y-normalization re-introduces the pre-fix bug from commit 74c4cd1.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import torch

# Ensure project root is on sys.path so ``src.*`` imports work when the script
# is invoked as ``python3 scripts/v3_module_ablation.py``.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.model.dual_path_model_v3 import DualPathLOBModelV3  # noqa: E402
from src.training.dataset import LOBDatasetV2, build_time_series_folds  # noqa: E402
from src.training.trainer_v2 import train_one_fold_v2  # noqa: E402


# --------------------------------------------------------------------------- #
# Ablation table -- each entry: (label, extra kwargs for model ctor)           #
# --------------------------------------------------------------------------- #
# V3 ablation reproducibility: pin all V4 flags to False so "full" in this
# script means V3-full (historical semantics), not post-Task-7 V4-default.
# V4 experiments live in configs/v4_full.json + configs/v4_ablations/.
_V3_PINS: Dict[str, Any] = {
    "use_channel_mix_conv": False,
    "use_level_attention_pool": False,
    "use_patch_attention_pool": False,
    "use_ppnet_gate": False,
}

ABLATIONS: List[Tuple[str, Dict[str, Any]]] = [
    ("full", {**_V3_PINS}),
    ("no_masknet", {**_V3_PINS, "use_masknet": False}),
    ("no_gdcn", {**_V3_PINS, "use_gdcn": False}),
    ("no_raw_path", {**_V3_PINS, "use_raw_path": False}),
    ("no_attention", {**_V3_PINS, "use_attention": False}),
    ("no_conv", {**_V3_PINS, "use_conv": False}),
    (
        "linear_only",
        {
            **_V3_PINS,
            "use_masknet": False,
            "use_gdcn": False,
            "use_raw_path": False,
            "use_attention": False,
            "use_conv": False,
        },
    ),
]


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #
def _detect_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


_ALLOWED_MODEL_KEYS = {
    "d_model", "d_raw", "n_mask_blocks", "n_cross_layers",
    "patch_size", "attn_nhead", "attn_d_ff", "d_prior",
    "dropout", "n_horizons", "n_symbols",
    "use_monotonic_quantile",
}


def run_one_ablation(
    *,
    base_model_cfg: Dict[str, Any],
    flags: Dict[str, Any],
    train_ds: LOBDatasetV2,
    val_ds: LOBDatasetV2,
    device: str,
    train_cfg: Dict[str, Any],
    out_dir: Path,
    label: str,
    epochs: int,
    patience: int,
) -> Dict[str, Any]:
    """Train a single V3 variant and return its best validation metrics."""
    n_features = train_ds.X.shape[-1]
    n_levels = (train_ds.X_raw.shape[-2] if train_ds.has_raw else 20)

    model = DualPathLOBModelV3(
        n_features=n_features,
        n_levels=n_levels,
        **base_model_cfg,
        **flags,
    )
    total_params = sum(p.numel() for p in model.parameters())
    print(f"  [{label}] params={total_params:,}")

    best = train_one_fold_v2(
        model=model,
        train_dataset=train_ds,
        val_dataset=val_ds,
        out_dir=str(out_dir / label),
        device=device,
        epochs=epochs,
        batch_size=train_cfg["batch_size"],
        lr=train_cfg["lr"],
        weight_decay=train_cfg["weight_decay"],
        patience=patience,
        grad_clip=train_cfg["grad_clip"],
    )

    return {
        "label": label,
        "flags": flags,
        "params": total_params,
        "best_epoch": best.get("best_epoch"),
        "val_loss": best.get("val_loss"),
        "val_corr": best.get("val_corr"),
        "val_r2": best.get("val_r2"),
    }


# --------------------------------------------------------------------------- #
# Main                                                                        #
# --------------------------------------------------------------------------- #
def main(
    config_path: str,
    fold_index: int,
    out_path: str,
    epochs: int,
    patience: int,
) -> None:
    with open(config_path, "r") as f:
        cfg = json.load(f)
    data_cfg = cfg["data"]
    train_cfg = cfg["training"]
    base_model_cfg = {
        k: v for k, v in cfg.get("model", {}).items() if k in _ALLOWED_MODEL_KEYS
    }

    # ------ build folds -------------------------------------------------------
    npz_dir = data_cfg["npz_dir"]
    days = sorted(p.stem for p in Path(npz_dir).glob("*.npz"))
    folds = build_time_series_folds(
        days,
        train_days=train_cfg["train_days"],
        val_days=train_cfg["val_days"],
        test_days=train_cfg["test_days"],
        stride=train_cfg["fold_stride"],
    )
    if fold_index >= len(folds):
        raise ValueError(
            f"fold_index={fold_index} out of range (n_folds={len(folds)})"
        )
    fold = folds[fold_index]
    print(
        f"[ablation] Fold {fold_index}: "
        f"train={len(fold['train'])}d val={len(fold['val'])}d "
        f"test={len(fold['test'])}d"
    )

    # ------ load train / val (ablation does NOT use test) --------------------
    train_ds = LOBDatasetV2(npz_dir, fold["train"], normalize=False)
    val_ds = LOBDatasetV2(npz_dir, fold["val"], normalize=False)

    # ------ feature normalization (train-set stats only) ---------------------
    x_mean, x_std = train_ds.compute_stats()
    safe_std = np.where(x_std < 1e-4, 1.0, x_std).astype(np.float32)
    for ds in (train_ds, val_ds):
        ds.X = np.clip(
            (ds.X - x_mean) / safe_std, -10.0, 10.0
        ).astype(np.float32)

    # ------ target normalization (train-set MAD only) ------------------------
    # Skipping this is the bug fixed in commit 74c4cd1 -- without it the
    # MonotonicQuantileHead's MIN_DELTA=0.01 no longer matches target scale.
    y_train_valid = train_ds.y[train_ds.mask > 0]
    if len(y_train_valid) > 0:
        y_median = float(np.median(y_train_valid))
        y_mad = float(np.median(np.abs(y_train_valid - y_median)))
        y_sigma = max(1.4826 * y_mad, 1e-9)
    else:
        y_median, y_sigma = 0.0, 1.0
    print(
        f"[ablation] target norm: median={y_median:.6e}, sigma={y_sigma:.6e}"
    )
    for ds in (train_ds, val_ds):
        ds.y = np.clip(
            (ds.y - y_median) / y_sigma, -5.0, 5.0
        ).astype(np.float32)
        ds.y[ds.mask == 0] = 0.0

    # ------ device + output dir ---------------------------------------------
    device = _detect_device()
    print(f"[ablation] device={device}, epochs={epochs}, patience={patience}")

    out_root = Path(cfg["output_dir"]) / "ablation"
    out_root.mkdir(parents=True, exist_ok=True)

    # ------ run every ablation ----------------------------------------------
    results: List[Dict[str, Any]] = []
    for label, flags in ABLATIONS:
        print(f"\n{'=' * 60}\n[ablation] Variant: {label}\n{'=' * 60}")
        r = run_one_ablation(
            base_model_cfg=base_model_cfg,
            flags=flags,
            train_ds=train_ds,
            val_ds=val_ds,
            device=device,
            train_cfg=train_cfg,
            out_dir=out_root,
            label=label,
            epochs=epochs,
            patience=patience,
        )
        results.append(r)
        vc = r["val_corr"] if r["val_corr"] is not None else float("nan")
        print(f"  {label}: val_corr={vc:+.4f}")

    # ------ dump summary -----------------------------------------------------
    out_path_p = Path(out_path)
    out_path_p.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path_p, "w") as f:
        json.dump(
            {
                "fold_index": fold_index,
                "epochs": epochs,
                "patience": patience,
                "train_days": len(fold["train"]),
                "val_days": len(fold["val"]),
                "test_days": len(fold["test"]),
                "y_median": y_median,
                "y_sigma": y_sigma,
                "variants": results,
            },
            f,
            indent=2,
        )
    print(f"\n[ablation] Saved summary to {out_path_p}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--fold-index", type=int, default=0)
    ap.add_argument("--out", required=True)
    ap.add_argument(
        "--epochs",
        type=int,
        default=20,
        help="Max epochs per ablation variant (default 20).",
    )
    ap.add_argument(
        "--patience",
        type=int,
        default=5,
        help="Early-stopping patience per variant (default 5).",
    )
    args = ap.parse_args()
    main(
        args.config,
        args.fold_index,
        args.out,
        args.epochs,
        args.patience,
    )
