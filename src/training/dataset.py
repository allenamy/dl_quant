"""NPZ dataset loader and time-series cross-validation fold builder."""

from __future__ import annotations

import os
from typing import List, Dict, Optional, Tuple, Union

import numpy as np
import torch
from torch.utils.data import Dataset


class LOBDataset(Dataset):
    """PyTorch Dataset that loads pre-built LOB NPZ windows.

    Each NPZ file is expected to contain:
        X          – (Nwin, input_len, n_features)
        y          – (Nwin,)
        y_mask     – (Nwin,)
        timestamps – (Nwin,)
        features   – object array of feature names

    Parameters
    ----------
    data_dir : str
        Directory containing ``<day>.npz`` files.
    days : list[str]
        Day identifiers (file stems without ``.npz``).
    normalize : bool
        If *True*, standardise X using *x_mean* / *x_std*.
    x_mean, x_std : np.ndarray | None
        Pre-computed feature-wise mean/std.  Required when *normalize=True*.
    """

    def __init__(
        self,
        data_dir: str,
        days: List[str],
        normalize: bool = False,
        x_mean: Optional[np.ndarray] = None,
        x_std: Optional[np.ndarray] = None,
    ) -> None:
        super().__init__()
        self.data_dir = data_dir
        self.days = list(days)

        xs, ys, masks = [], [], []
        for day in self.days:
            path = os.path.join(data_dir, f"{day}.npz")
            npz = np.load(path, allow_pickle=True)
            xs.append(npz["X"])
            ys.append(npz["y"])
            masks.append(npz["y_mask"])

        self.X = np.concatenate(xs, axis=0).astype(np.float32)
        self.y = np.concatenate(ys, axis=0).astype(np.float32)
        self.mask = np.concatenate(masks, axis=0).astype(np.float32)

        # --- sanitise --------------------------------------------------------
        self.X = np.nan_to_num(self.X, nan=0.0, posinf=0.0, neginf=0.0)
        self.y = np.nan_to_num(self.y, nan=0.0, posinf=0.0, neginf=0.0)
        self.mask = np.nan_to_num(self.mask, nan=0.0, posinf=0.0, neginf=0.0)
        self.y[self.mask == 0] = 0.0

        # --- optional normalisation ------------------------------------------
        if normalize:
            if x_mean is None or x_std is None:
                raise ValueError("x_mean and x_std must be provided when normalize=True")
            # Guard against near-zero std features (e.g. amihud when depth is large)
            safe_std = np.where(x_std < 1e-4, 1.0, x_std).astype(np.float32)
            self.X = (self.X - x_mean) / safe_std
            self.X = np.clip(self.X, -10.0, 10.0)

    # ------------------------------------------------------------------
    # torch Dataset interface
    # ------------------------------------------------------------------
    def __len__(self) -> int:
        return len(self.X)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        x = torch.from_numpy(np.array(self.X[idx], dtype=np.float32))
        y = torch.tensor(float(self.y[idx]))
        m = torch.tensor(float(self.mask[idx]))
        return (x, y, m)

    # ------------------------------------------------------------------
    # statistics
    # ------------------------------------------------------------------
    def compute_stats(self) -> Tuple[np.ndarray, np.ndarray]:
        """Return (mean, std) across samples & time, per feature.

        Returns arrays of shape ``(n_features,)`` suitable for broadcasting
        against ``X`` which has shape ``(N, T, F)``.
        """
        mean = self.X.mean(axis=(0, 1))
        std = self.X.std(axis=(0, 1))
        return mean, std


def _derive_mask_key(horizon_key: str) -> str:
    """Map a label key like ``"y"`` / ``"y_60"`` / ``"y_180"`` to its mask key.

    The NPZ convention produced by ``build_npz_for_day`` is:
      - ``"y"`` (back-compat alias) -> ``"y_mask"``
      - ``"y_<H>"`` (per-horizon)   -> ``"y_mask_<H>"``

    Anything else we refuse up-front -- a wrong mapping would silently train
    on misaligned targets.
    """
    if horizon_key == "y":
        return "y_mask"
    if horizon_key.startswith("y_"):
        return f"y_mask_{horizon_key[2:]}"
    raise ValueError(
        f"horizon_key must be 'y' or start with 'y_<H>', got {horizon_key!r}"
    )


class LOBDatasetV2(Dataset):
    """Extended dataset supporting dual-path (X_feat + X_raw) inputs.

    NPZ files may contain:
      X             -- (N, L, n_features)  hand-crafted features (always present)
      X_raw         -- (N, L, n_levels, 4) raw LOB tensor (optional)
      y             -- (N,) back-compat target (alias of shortest horizon)
      y_mask        -- (N,) validity mask (alias of shortest horizon)
      y_{H}         -- (N,) target for horizon H seconds (multi-horizon NPZs)
      y_mask_{H}    -- (N,) validity mask for horizon H seconds

    If X_raw is present, ``__getitem__`` returns ``(x_feat, x_raw, y, mask)``.
    If X_raw is absent, ``__getitem__`` returns ``(x_feat, y, mask)``.
    This matches ``trainer_v2``'s auto-detection.

    Multi-horizon mode
    ------------------
    When ``horizons`` is supplied as a list of label keys
    (e.g. ``["y_60", "y_180", "y_300", "y_600"]``) the dataset stacks the
    per-horizon targets / masks along a new trailing axis.  In that mode
    ``__getitem__`` returns ``y`` and ``mask`` tensors of shape
    ``(n_horizons,)``, and batching yields ``(B, n_horizons)``.  Useful for a
    single-forward shared-encoder trainer.  Default ``None`` preserves the
    single-horizon (scalar y, scalar mask) behaviour.

    Parameters
    ----------
    data_dir : str
        Directory containing ``<day>.npz`` files.
    days : list[str]
        Day identifiers (file stems without ``.npz``).
    normalize : bool
        If *True*, standardise X_feat using *x_mean* / *x_std*.
        X_raw is already normalized (bps + log1p), skip.
    x_mean, x_std : np.ndarray | None
        Pre-computed feature-wise mean/std.  Required when *normalize=True*.
    horizon_key : str, default ``"y"``
        Which NPZ target field to load in single-horizon mode
        (e.g. ``"y"``, ``"y_60"``, ``"y_180"``, ``"y_300"``, ``"y_600"``).
    mask_key : str | None, default ``None``
        Explicit mask field name.  When ``None`` (default) it is auto-derived
        from ``horizon_key`` via :func:`_derive_mask_key`.
    horizons : list[str] | None, default ``None``
        When provided, enables multi-horizon mode.  Each element is a label
        key (e.g. ``"y_60"``, ``"y_300"``).  Takes precedence over
        ``horizon_key`` / ``mask_key``.
    smooth_target : int, default 0
        If ``> 0``, requests target smoothing over this many seconds.  The
        cleaner place to smooth is at NPZ-build time in ``pipeline.py``
        (another agent owns that module), so for now this parameter is a
        *pass-through*: the value is stored on ``self.smooth_target`` for
        downstream code / logging but no smoothing is performed here.
        Default ``0`` keeps behaviour unchanged.
    """

    def __init__(
        self,
        data_dir: str,
        days: List[str],
        normalize: bool = False,
        x_mean: Optional[np.ndarray] = None,
        x_std: Optional[np.ndarray] = None,
        horizon_key: str = "y",
        mask_key: Optional[str] = None,
        horizons: Optional[List[str]] = None,
        smooth_target: int = 0,
    ) -> None:
        super().__init__()
        self.data_dir = data_dir
        self.days = list(days)
        # Pass-through; actual smoothing expected at NPZ-build time.
        self.smooth_target = int(smooth_target)

        # Resolve which label (and mask) fields to load.  Multi-horizon takes
        # precedence; otherwise we honour ``horizon_key`` + ``mask_key``.
        if horizons is not None:
            if len(horizons) == 0:
                raise ValueError("horizons must be a non-empty list when provided")
            self._horizons: Optional[List[str]] = list(horizons)
            self._horizon_key = None
            self._mask_key = None
            self._y_keys: List[str] = list(horizons)
            self._mask_keys: List[str] = [_derive_mask_key(k) for k in horizons]
        else:
            if mask_key is None:
                mask_key = _derive_mask_key(horizon_key)
            self._horizons = None
            self._horizon_key = horizon_key
            self._mask_key = mask_key
            self._y_keys = [horizon_key]
            self._mask_keys = [mask_key]

        xs: List[np.ndarray] = []
        # Per-horizon buckets: index into ``self._y_keys`` -> list of day arrays.
        ys_by_key: List[List[np.ndarray]] = [[] for _ in self._y_keys]
        masks_by_key: List[List[np.ndarray]] = [[] for _ in self._mask_keys]
        raws: List[np.ndarray] = []
        has_raw_all: Optional[bool] = None
        feature_names_first: Optional[List[str]] = None
        inconsistent_days: List[str] = []

        for day in self.days:
            path = os.path.join(data_dir, f"{day}.npz")
            npz = np.load(path, allow_pickle=True)
            xs.append(npz["X"])

            # Fetch each requested (y, mask) pair.  Missing horizon keys are
            # a pipeline-version mismatch -- fail loudly with a helpful msg.
            for k_idx, (y_key, m_key) in enumerate(
                zip(self._y_keys, self._mask_keys)
            ):
                if y_key not in npz.files:
                    raise ValueError(
                        f"Label key {y_key!r} not found in {day}.npz. "
                        f"Available keys: {sorted(npz.files)}. "
                        f"Rebuild NPZs via build_npz_for_day with "
                        f"horizons_sec=[...] to populate multi-horizon labels."
                    )
                if m_key not in npz.files:
                    raise ValueError(
                        f"Mask key {m_key!r} not found in {day}.npz. "
                        f"Expected alongside {y_key!r}. "
                        f"Rebuild NPZs via build_npz_for_day."
                    )
                ys_by_key[k_idx].append(npz[y_key])
                masks_by_key[k_idx].append(npz[m_key])

            # Fail fast on feature-name drift across days. Silent schema
            # mismatch would either crash np.concatenate (same n_features,
            # wrong order) or pass and corrupt training (different n_features
            # — impossible here, concatenate would raise).
            if "features" in npz.files:
                names = [str(f) for f in npz["features"]]
                if feature_names_first is None:
                    feature_names_first = names
                elif names != feature_names_first:
                    raise ValueError(
                        f"Feature-name mismatch in {day}.npz: "
                        f"expected {feature_names_first[:5]}... "
                        f"got {names[:5]}... "
                        f"Re-build NPZs with the same pipeline version."
                    )

            day_has_raw = "X_raw" in npz.files
            if has_raw_all is None:
                has_raw_all = day_has_raw
            elif day_has_raw != has_raw_all:
                # Day-to-day X_raw presence differs — silent fallback to
                # Path-A-only would be a dual-path config bug. Fail loudly.
                inconsistent_days.append(day)

            if day_has_raw:
                raws.append(npz["X_raw"])

        if inconsistent_days:
            raise ValueError(
                f"X_raw presence inconsistent across days (first={has_raw_all}, "
                f"differing days: {inconsistent_days[:5]}...). "
                f"Re-build affected NPZs with the same pipeline version."
            )

        self._has_raw = bool(has_raw_all) and len(raws) == len(self.days)
        self._feature_names = feature_names_first

        self.X = np.concatenate(xs, axis=0).astype(np.float32)

        # Build y / mask arrays.  Shapes:
        #   single-horizon: (N,)
        #   multi-horizon:  (N, n_horizons)
        per_key_y = [np.concatenate(b, axis=0).astype(np.float32) for b in ys_by_key]
        per_key_mask = [
            np.concatenate(b, axis=0).astype(np.float32) for b in masks_by_key
        ]
        if self._horizons is not None:
            # Stack along a new trailing dimension so __getitem__ can return
            # a 1-D tensor per sample of length n_horizons.
            self.y = np.stack(per_key_y, axis=-1)           # (N, n_h)
            self.mask = np.stack(per_key_mask, axis=-1)     # (N, n_h)
        else:
            self.y = per_key_y[0]
            self.mask = per_key_mask[0]

        if self._has_raw:
            self.X_raw = np.concatenate(raws, axis=0).astype(np.float32)
        else:
            self.X_raw = None

        # --- sanitise --------------------------------------------------------
        self.X = np.nan_to_num(self.X, nan=0.0, posinf=0.0, neginf=0.0)
        self.y = np.nan_to_num(self.y, nan=0.0, posinf=0.0, neginf=0.0)
        self.mask = np.nan_to_num(self.mask, nan=0.0, posinf=0.0, neginf=0.0)
        # Zero out targets where the mask is 0 (both single- and multi-horizon
        # broadcasting works because shapes line up elementwise).
        self.y = np.where(self.mask == 0, 0.0, self.y).astype(np.float32)

        if self.X_raw is not None:
            self.X_raw = np.nan_to_num(self.X_raw, nan=0.0, posinf=0.0, neginf=0.0)

        # --- optional normalisation (X_feat only, NOT X_raw) -----------------
        if normalize:
            if x_mean is None or x_std is None:
                raise ValueError("x_mean and x_std must be provided when normalize=True")
            # Guard against near-zero std: features with std < 1e-4 are
            # essentially constants and normalizing them blows up the scale.
            # Treat them as "dead" features (scale=1.0, center-only).
            safe_std = np.where(x_std < 1e-4, 1.0, x_std).astype(np.float32)
            self.X = (self.X - x_mean) / safe_std
            self.X = np.clip(self.X, -10.0, 10.0)

    # ------------------------------------------------------------------
    @property
    def has_raw(self) -> bool:
        """Whether X_raw is available (tells trainer which mode to use)."""
        return self._has_raw

    @property
    def horizons(self) -> Optional[List[str]]:
        """The horizon label keys when in multi-horizon mode, else ``None``."""
        return list(self._horizons) if self._horizons is not None else None

    # ------------------------------------------------------------------
    # torch Dataset interface
    # ------------------------------------------------------------------
    def __len__(self) -> int:
        return len(self.X)

    def __getitem__(
        self, idx: int,
    ) -> Union[
        Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor],
        Tuple[torch.Tensor, torch.Tensor, torch.Tensor],
    ]:
        x_feat = torch.from_numpy(np.array(self.X[idx], dtype=np.float32))
        # In single-horizon mode ``self.y[idx]`` is scalar; in multi-horizon
        # mode it's a 1-D array of length n_horizons.  ``torch.from_numpy``
        # preserves the shape either way; ``torch.tensor`` with a scalar keeps
        # the single-horizon legacy return shape.
        y_item = self.y[idx]
        m_item = self.mask[idx]
        if self._horizons is not None:
            y = torch.from_numpy(np.asarray(y_item, dtype=np.float32))
            m = torch.from_numpy(np.asarray(m_item, dtype=np.float32))
        else:
            y = torch.tensor(float(y_item))
            m = torch.tensor(float(m_item))

        if self._has_raw:
            x_raw = torch.from_numpy(np.array(self.X_raw[idx], dtype=np.float32))
            return (x_feat, x_raw, y, m)
        return (x_feat, y, m)

    # ------------------------------------------------------------------
    # statistics (X_feat only)
    # ------------------------------------------------------------------
    def compute_stats(self) -> Tuple[np.ndarray, np.ndarray]:
        """Return (mean, std) across samples & time, per feature for X_feat.

        Returns arrays of shape ``(n_features,)`` suitable for broadcasting
        against ``X`` which has shape ``(N, T, F)``.
        """
        mean = self.X.mean(axis=(0, 1))
        std = self.X.std(axis=(0, 1))
        return mean, std


# --------------------------------------------------------------------------
# Time-series fold builder
# --------------------------------------------------------------------------

def build_time_series_folds(
    days: List[str],
    train_days: int,
    val_days: int,
    test_days: int,
    stride: int,
) -> List[Dict[str, List[str]]]:
    """Create sliding-window cross-validation folds with strict temporal order.

    All training days come before all validation days, which come before all
    test days within each fold.

    Parameters
    ----------
    days : list[str]
        Chronologically sorted list of day identifiers.
    train_days : int
        Number of days in the training window.
    val_days : int
        Number of days in the validation window.
    test_days : int
        Number of days in the test window.
    stride : int
        How many days the window slides forward between folds.

    Returns
    -------
    list[dict]
        Each element is ``{'train': [...], 'val': [...], 'test': [...]}``.
    """
    window = train_days + val_days + test_days
    if window > len(days):
        return []

    folds: List[Dict[str, List[str]]] = []
    start = 0
    while start + window <= len(days):
        tr_end = start + train_days
        va_end = tr_end + val_days
        te_end = va_end + test_days
        folds.append(
            {
                "train": days[start:tr_end],
                "val": days[tr_end:va_end],
                "test": days[va_end:te_end],
            }
        )
        start += stride

    return folds
