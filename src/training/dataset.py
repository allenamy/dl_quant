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


class LOBDatasetV2(Dataset):
    """Extended dataset supporting dual-path (X_feat + X_raw) inputs.

    NPZ files may contain:
      X       -- (N, L, n_features)  hand-crafted features (always present)
      X_raw   -- (N, L, n_levels, 4) raw LOB tensor (optional)
      y       -- (N,) targets
      y_mask  -- (N,) validity mask

    If X_raw is present, ``__getitem__`` returns ``(x_feat, x_raw, y, mask)``.
    If X_raw is absent, ``__getitem__`` returns ``(x_feat, y, mask)``.
    This matches ``trainer_v2``'s auto-detection.

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
        raws: List[np.ndarray] = []
        has_raw_all: Optional[bool] = None

        for day in self.days:
            path = os.path.join(data_dir, f"{day}.npz")
            npz = np.load(path, allow_pickle=True)
            xs.append(npz["X"])
            ys.append(npz["y"])
            masks.append(npz["y_mask"])

            day_has_raw = "X_raw" in npz.files
            if has_raw_all is None:
                has_raw_all = day_has_raw
            # If any day has raw, all must be consistent; fallback to False
            if day_has_raw != has_raw_all:
                has_raw_all = False

            if day_has_raw:
                raws.append(npz["X_raw"])

        self._has_raw = bool(has_raw_all) and len(raws) == len(self.days)

        self.X = np.concatenate(xs, axis=0).astype(np.float32)
        self.y = np.concatenate(ys, axis=0).astype(np.float32)
        self.mask = np.concatenate(masks, axis=0).astype(np.float32)

        if self._has_raw:
            self.X_raw = np.concatenate(raws, axis=0).astype(np.float32)
        else:
            self.X_raw = None

        # --- sanitise --------------------------------------------------------
        self.X = np.nan_to_num(self.X, nan=0.0, posinf=0.0, neginf=0.0)
        self.y = np.nan_to_num(self.y, nan=0.0, posinf=0.0, neginf=0.0)
        self.mask = np.nan_to_num(self.mask, nan=0.0, posinf=0.0, neginf=0.0)
        self.y[self.mask == 0] = 0.0

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
        y = torch.tensor(float(self.y[idx]))
        m = torch.tensor(float(self.mask[idx]))

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
