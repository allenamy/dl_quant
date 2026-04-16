"""NPZ dataset loader and time-series cross-validation fold builder.

LOBDatasetV2 uses *lazy per-day loading* with an LRU cache so that very long
folds (hundreds of days) do not require holding every NPZ in RAM.  Only the
most recently accessed days remain resident; stats and normalisation are
computed in a streaming fashion.
"""

from __future__ import annotations

import bisect
import logging
import os
import time
import warnings
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import torch
from torch.utils.data import Dataset, Sampler


def _np_load_with_retry(
    path: str,
    *,
    max_retries: int = 3,
    backoff_sec: float = 2.0,
    **kwargs,
):
    """Load an NPZ file with retry on transient I/O errors.

    iCloud / external volumes occasionally stall with TimeoutError when
    opening many files in a row. A simple retry with exponential backoff
    turns the fatal crash into a recoverable warning.
    """
    last_exc: Optional[BaseException] = None
    for attempt in range(max_retries):
        try:
            return np.load(path, **kwargs)
        except (TimeoutError, OSError) as exc:
            last_exc = exc
            wait = backoff_sec * (2 ** attempt)
            logging.getLogger(__name__).warning(
                "np.load(%s) failed on attempt %d/%d: %s; retrying in %.1fs",
                path, attempt + 1, max_retries, exc, wait,
            )
            time.sleep(wait)
    raise last_exc


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

    **Lazy loading.**  Only NPZ metadata is read at construction.  Arrays are
    loaded on first access and cached in a bounded LRU keyed by day index;
    this keeps RAM bounded even for folds spanning hundreds of days.

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
    ``(n_horizons,)``.

    Parameters
    ----------
    data_dir : str
        Directory containing ``<day>.npz`` files.
    days : list[str]
        Day identifiers (file stems without ``.npz``).
    normalize : bool
        If *True*, standardise X_feat per-item using *x_mean* / *x_std*.
        X_raw is already normalized (bps + log1p), skip.
    x_mean, x_std : np.ndarray | None
        Pre-computed feature-wise mean/std.  Required when *normalize=True*.
    horizon_key : str, default ``"y"``
        Which NPZ target field to load in single-horizon mode.
    mask_key : str | None, default ``None``
        Explicit mask field name.  Auto-derived from ``horizon_key`` via
        :func:`_derive_mask_key` when ``None``.
    horizons : list[str] | None, default ``None``
        When provided, enables multi-horizon mode.
    smooth_target : int, default 0
        Stored on ``self.smooth_target`` for downstream code / logging;
        no smoothing is performed here.
    cache_size : int, default 128
        Maximum number of days held in the LRU cache.  Peak additional RAM
        above the metadata scan is bounded by
        ``cache_size * bytes_per_day``.  This is an IO/memory tradeoff:
        a larger cache avoids re-reading days that cycle back into the
        DataLoader (especially under random shuffling of long folds) at
        the cost of resident memory — at ~50-90 MB per day, a 128-day
        cache peaks around 6-12 GB.  Tune down when running on smaller
        hosts; tune up when the fold fits entirely in RAM.
    y_norm : tuple[float, float, float] | None, default ``None``
        ``(median, sigma, clip)`` triple.  When provided, each y value is
        transformed as ``clip((y - median) / sigma, -clip, +clip)`` inside
        ``_load_day`` so the trainer never sees raw targets.  Broadcasts over
        the multi-horizon dimension.
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
        cache_size: int = 128,
        y_norm: Optional[Tuple[float, float, float]] = None,
    ) -> None:
        super().__init__()
        self.data_dir = data_dir
        self.days = list(days)
        self.smooth_target = int(smooth_target)

        # --- resolve horizon / mask keys -------------------------------------
        if horizons is not None:
            if len(horizons) == 0:
                raise ValueError("horizons must be a non-empty list when provided")
            self._horizons: Optional[List[str]] = list(horizons)
            self._horizon_key: Optional[str] = None
            self._mask_key: Optional[str] = None
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

        # --- scan NPZ metadata (no array loads) ------------------------------
        self._day_paths: List[str] = []
        self._day_counts: List[int] = []
        self._has_raw_per_day: List[bool] = []
        self._has_regime_prior_per_day: List[bool] = []
        feature_names_first: Optional[List[str]] = None

        for day in self.days:
            path = os.path.join(data_dir, f"{day}.npz")
            with _np_load_with_retry(path, allow_pickle=True) as npz:
                # npz["X"] lazily opens the array header -- ``.shape`` reads
                # only shape metadata from the NPZ manifest, NOT the full
                # tensor.  Confirmed via timing: ~ms per day regardless of
                # on-disk size.
                n_win = int(npz["X"].shape[0])

                # Feature-name drift check (same across all days)
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

                # Verify requested horizon keys present up-front so we fail
                # fast during init rather than mid-training.
                for y_key, m_key in zip(self._y_keys, self._mask_keys):
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

                self._has_raw_per_day.append("X_raw" in npz.files)
                self._has_regime_prior_per_day.append("regime_prior" in npz.files)
            self._day_paths.append(path)
            self._day_counts.append(n_win)

        # --- validate X_raw consistency --------------------------------------
        if len(set(self._has_raw_per_day)) > 1:
            first = self._has_raw_per_day[0]
            inconsistent = [
                d for d, h in zip(self.days, self._has_raw_per_day) if h != first
            ]
            raise ValueError(
                f"X_raw presence inconsistent across days (first={first}, "
                f"differing days: {inconsistent[:5]}...). "
                f"Re-build affected NPZs with the same pipeline version."
            )
        self._has_raw: bool = bool(self._has_raw_per_day[0]) if self._has_raw_per_day else False

        # --- validate regime_prior consistency ------------------------------
        if len(set(self._has_regime_prior_per_day)) > 1:
            first = self._has_regime_prior_per_day[0]
            inconsistent = [
                d for d, h in zip(self.days, self._has_regime_prior_per_day) if h != first
            ]
            raise ValueError(
                f"regime_prior presence inconsistent across days "
                f"(first={first}, differing days: {inconsistent[:5]}...). "
                f"Re-build affected NPZs with the same pipeline version."
            )
        self._has_regime_prior: bool = (
            bool(self._has_regime_prior_per_day[0])
            if self._has_regime_prior_per_day else False
        )

        self._feature_names = feature_names_first

        # --- offset array for O(log D) day lookup ----------------------------
        self._offsets = np.cumsum([0] + self._day_counts)
        self._total = int(self._offsets[-1])

        # --- normalisation bookkeeping (applied per-item) --------------------
        self.normalize = bool(normalize)
        self._x_mean: Optional[np.ndarray] = None
        self._x_std: Optional[np.ndarray] = None
        if self.normalize:
            if x_mean is None or x_std is None:
                raise ValueError(
                    "x_mean and x_std must be provided when normalize=True"
                )
            self._x_mean = np.asarray(x_mean, dtype=np.float32)
            # Guard near-zero std features (scale=1.0 => centre-only).
            self._x_std = np.where(
                np.asarray(x_std) < 1e-4, 1.0, x_std
            ).astype(np.float32)

        self._y_norm: Optional[Tuple[float, float, float]] = None
        if y_norm is not None:
            if len(y_norm) != 3:
                raise ValueError(
                    "y_norm must be (median, sigma, clip); got tuple of length "
                    f"{len(y_norm)}"
                )
            median, sigma, clip = float(y_norm[0]), float(y_norm[1]), float(y_norm[2])
            if sigma <= 0:
                raise ValueError(f"y_norm sigma must be > 0, got {sigma}")
            self._y_norm = (median, sigma, clip)

        # --- LRU cache -------------------------------------------------------
        self._cache_size = int(cache_size)
        if self._cache_size < 1:
            raise ValueError(f"cache_size must be >= 1, got {self._cache_size}")
        self._cache: Dict[int, Dict[str, np.ndarray]] = {}
        self._cache_order: List[int] = []

        # Will be filled lazily on first __getitem__ if a caller needs it.
        self.n_features_value: Optional[int] = None
        if feature_names_first is not None:
            self.n_features_value = len(feature_names_first)

    # ------------------------------------------------------------------
    # LRU cache management
    # ------------------------------------------------------------------
    def _load_day(self, day_idx: int) -> Dict[str, np.ndarray]:
        """Load one day from disk (with normalisation baked in) or return
        a cached copy.  Evicts the oldest entry when the cache is full."""
        if day_idx in self._cache:
            # Touch: move to most-recently-used position.
            self._cache_order.remove(day_idx)
            self._cache_order.append(day_idx)
            return self._cache[day_idx]

        path = self._day_paths[day_idx]
        with _np_load_with_retry(path, allow_pickle=True) as npz:
            # Read and sanitise X.
            X = np.asarray(npz["X"], dtype=np.float32)
            X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
            if self.normalize:
                # Safe because cached arrays are private to this dataset;
                # callers get a torch.Tensor copy via torch.from_numpy.
                X = np.clip(
                    (X - self._x_mean) / self._x_std, -10.0, 10.0
                ).astype(np.float32)
            data: Dict[str, np.ndarray] = {"X": X}

            if self._has_raw:
                Xr = np.asarray(npz["X_raw"], dtype=np.float32)
                Xr = np.nan_to_num(Xr, nan=0.0, posinf=0.0, neginf=0.0)
                data["X_raw"] = Xr

            if self._has_regime_prior:
                Rp = np.asarray(npz["regime_prior"], dtype=np.float32)
                Rp = np.nan_to_num(Rp, nan=0.0, posinf=0.0, neginf=0.0)
                data["regime_prior"] = Rp

            # y / mask
            per_key_y = [
                np.asarray(npz[k], dtype=np.float32) for k in self._y_keys
            ]
            per_key_m = [
                np.asarray(npz[k], dtype=np.float32) for k in self._mask_keys
            ]
            if self._horizons is not None:
                y_arr = np.stack(per_key_y, axis=-1)   # (N, n_h)
                m_arr = np.stack(per_key_m, axis=-1)
            else:
                y_arr = per_key_y[0]                   # (N,)
                m_arr = per_key_m[0]

            y_arr = np.nan_to_num(y_arr, nan=0.0, posinf=0.0, neginf=0.0)
            m_arr = np.nan_to_num(m_arr, nan=0.0, posinf=0.0, neginf=0.0)
            y_arr = np.where(m_arr == 0, 0.0, y_arr).astype(np.float32)

            if self._y_norm is not None:
                median, sigma, clip = self._y_norm
                y_arr = np.clip(
                    (y_arr - median) / sigma, -clip, clip
                ).astype(np.float32)
                # Re-zero masked entries so they do not leak normalised offset.
                y_arr = np.where(m_arr == 0, 0.0, y_arr).astype(np.float32)

            data["y"] = y_arr
            data["mask"] = m_arr.astype(np.float32)

        # Evict oldest if the cache would exceed budget.
        if len(self._cache) >= self._cache_size:
            oldest = self._cache_order.pop(0)
            self._cache.pop(oldest, None)
        self._cache[day_idx] = data
        self._cache_order.append(day_idx)
        return data

    def _locate(self, idx: int) -> Tuple[int, int]:
        """Binary-search the cumulative offsets to find (day_idx, local_idx)."""
        if idx < 0 or idx >= self._total:
            raise IndexError(
                f"idx {idx} out of range [0, {self._total})"
            )
        day_idx = int(bisect.bisect_right(self._offsets, idx) - 1)
        # Clamp just in case of zero-length days.
        if day_idx < 0:
            day_idx = 0
        local_idx = int(idx - self._offsets[day_idx])
        return day_idx, local_idx

    def clear_cache(self) -> None:
        """Drop all cached day data.  Useful between folds."""
        self._cache.clear()
        self._cache_order.clear()

    # ------------------------------------------------------------------
    # Timestamp streaming
    # ------------------------------------------------------------------
    def get_all_timestamps(self) -> np.ndarray:
        """Stream timestamps across all days; returns shape ``(total,)`` int64.

        Reads the ``timestamps`` field from each day's NPZ in day order and
        concatenates.  Does NOT go through the LRU cache (timestamps are not
        part of the cached per-day payload), so this is safe to call before
        or after training without touching array data.
        """
        parts: List[np.ndarray] = []
        for path in self._day_paths:
            with _np_load_with_retry(path, allow_pickle=True) as npz:
                parts.append(np.asarray(npz["timestamps"], dtype=np.int64))
        if not parts:
            return np.zeros(0, dtype=np.int64)
        return np.concatenate(parts, axis=0)

    # ------------------------------------------------------------------
    # Public read-only properties
    # ------------------------------------------------------------------
    @property
    def has_raw(self) -> bool:
        """Whether X_raw is available."""
        return self._has_raw

    @property
    def has_regime_prior(self) -> bool:
        """Whether regime_prior is available."""
        return self._has_regime_prior

    @property
    def horizons(self) -> Optional[List[str]]:
        """Horizon label keys in multi-horizon mode, else ``None``."""
        return list(self._horizons) if self._horizons is not None else None

    # ------------------------------------------------------------------
    # torch Dataset interface
    # ------------------------------------------------------------------
    def __len__(self) -> int:
        return self._total

    def __getitem__(
        self,
        idx: int,
    ) -> Union[
        Tuple[torch.Tensor, torch.Tensor, torch.Tensor],                                # 3-tuple
        Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor],                  # 4-tuple
        Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor],    # 5-tuple
    ]:
        if idx < 0:
            idx += self._total
        day_idx, local_idx = self._locate(idx)
        data = self._load_day(day_idx)

        x_feat = torch.from_numpy(
            np.ascontiguousarray(data["X"][local_idx], dtype=np.float32)
        )

        y_item = data["y"][local_idx]
        m_item = data["mask"][local_idx]

        if self._horizons is not None:
            y_t = torch.from_numpy(np.asarray(y_item, dtype=np.float32))
            m_t = torch.from_numpy(np.asarray(m_item, dtype=np.float32))
        else:
            y_t = torch.tensor(float(y_item))
            m_t = torch.tensor(float(m_item))

        if self._has_raw:
            x_raw = torch.from_numpy(
                np.ascontiguousarray(data["X_raw"][local_idx], dtype=np.float32)
            )
            if self._has_regime_prior:
                rp = torch.from_numpy(
                    np.ascontiguousarray(data["regime_prior"][local_idx], dtype=np.float32)
                )
                return (x_feat, x_raw, rp, y_t, m_t)
            return (x_feat, x_raw, y_t, m_t)
        # No raw: if regime_prior is present, still skip it to keep tuple arity
        # stable for back-compat callers. (No V4 flow uses this combo today.)
        return (x_feat, y_t, m_t)

    # ------------------------------------------------------------------
    # Back-compat materialising properties
    #
    # Legacy callers (walk_forward.py, some evaluation scripts) still do
    # ``ds.X``, ``ds.y``, ``ds.mask`` expecting a full numpy array.  These
    # now *materialise on demand* by walking every day through the cache.
    # Warns when the projected size exceeds 5 GiB so the user is alerted
    # before an OOM event.
    # ------------------------------------------------------------------
    @property
    def X(self) -> np.ndarray:
        return self._materialize_all("X")

    @property
    def y(self) -> np.ndarray:
        return self._materialize_all("y")

    @property
    def mask(self) -> np.ndarray:
        return self._materialize_all("mask")

    @property
    def X_raw(self) -> Optional[np.ndarray]:
        if not self._has_raw:
            return None
        return self._materialize_all("X_raw")

    def _materialize_all(self, key: str) -> np.ndarray:
        """Concatenate ``key`` across all days.  Use sparingly; prefer a
        DataLoader for training-scale datasets."""
        estimated = self._estimate_size(key)
        if estimated > 5 * 1024 ** 3:  # 5 GiB
            warnings.warn(
                f"Materialising {key!r} for {len(self._day_paths)} days "
                f"(~{estimated / 1024 ** 3:.1f} GB). Use DataLoader for "
                f"training; these properties are only safe for small eval sets.",
                stacklevel=2,
            )
        parts: List[np.ndarray] = []
        for day_idx in range(len(self._day_paths)):
            parts.append(self._load_day(day_idx)[key])
        return np.concatenate(parts, axis=0)

    def _estimate_size(self, key: str) -> int:
        """Estimate total bytes of ``key`` across all days using the first
        day as a template (all days share the same per-window shape)."""
        if not self._day_paths:
            return 0
        first = self._load_day(0)
        if key not in first:
            return 0
        arr = first[key]
        per_win = arr.nbytes // max(arr.shape[0], 1) if arr.shape[0] else arr.nbytes
        return int(per_win) * self._total

    # ------------------------------------------------------------------
    # Streaming statistics
    # ------------------------------------------------------------------
    def compute_stats(self) -> Tuple[np.ndarray, np.ndarray]:
        """Return (mean, std) per feature by streaming through all days.

        Equivalent to ``X.mean(axis=(0,1))`` / ``X.std(axis=(0,1))`` but
        accumulates in float64 across every window × timestep without
        materialising the full tensor.  Matches the monolithic result
        within float32 tolerance.
        """
        n_total = 0
        sum_: Optional[np.ndarray] = None
        sum_sq: Optional[np.ndarray] = None

        for day_idx in range(len(self._day_paths)):
            data = self._load_day(day_idx)
            X = data["X"]
            if X.size == 0:
                continue
            X64 = X.astype(np.float64, copy=False)
            flat = X64.reshape(-1, X64.shape[-1])
            if sum_ is None:
                F = flat.shape[-1]
                sum_ = np.zeros(F, dtype=np.float64)
                sum_sq = np.zeros(F, dtype=np.float64)
            n_total += flat.shape[0]
            sum_ += flat.sum(axis=0)
            sum_sq += (flat * flat).sum(axis=0)

        if n_total == 0 or sum_ is None:
            raise RuntimeError(
                "compute_stats() saw zero samples — dataset is empty or all "
                "days have zero windows."
            )

        mean = sum_ / n_total
        var = (sum_sq / n_total) - mean * mean
        var = np.maximum(var, 0.0)  # numerical safety for tiny negatives
        std = np.sqrt(var)
        return mean.astype(np.float32), std.astype(np.float32)

    def compute_y_stats(self) -> Tuple[float, float]:
        """Return (median, mad_sigma) over all *valid* y values.

        MAD-based sigma: ``1.4826 * MAD(y)``.  Streams through every day,
        collects valid y entries (mask > 0), then runs np.median / MAD on
        the accumulated 1-D array.  Memory: ~4 bytes × total_valid samples
        (typically < 10 MB even on 500-day folds), so still lightweight.

        In multi-horizon mode the statistics are computed over the
        flattened joint array so callers get a single scalar pair.
        """
        parts: List[np.ndarray] = []
        for day_idx in range(len(self._day_paths)):
            data = self._load_day(day_idx)
            y = np.asarray(data["y"], dtype=np.float32)
            m = np.asarray(data["mask"], dtype=np.float32)
            valid = y[m > 0]
            if valid.size:
                parts.append(valid.ravel())

        if not parts:
            return 0.0, 1.0

        y_valid = np.concatenate(parts, axis=0)
        median = float(np.median(y_valid))
        mad = float(np.median(np.abs(y_valid - median)))
        sigma = max(1.4826 * mad, 1e-9)
        return median, sigma


# --------------------------------------------------------------------------
# Day-chunked sampler (cache-friendly access for LOBDatasetV2)
# --------------------------------------------------------------------------


class DayChunkedSampler(Sampler):
    """Chunked sampling: group days into chunks, shuffle globally WITHIN each chunk.

    Balances cache efficiency (all days in a chunk fit in LRU cache) with
    batch-level sample diversity (each batch spans ~chunk_size different
    days, approximating i.i.d. SGD).

    With ``chunk_size=1`` reduces to pure day-chunking (all samples from
    one day in order, before next day). With ``chunk_size=n_days`` reduces
    to global shuffle (and will cache-thrash if chunk_size > cache_size).

    The recommended setting is ``chunk_size <= cache_size``, which keeps
    cache hit rate ~100% while giving each batch ~chunk_size days of
    gradient diversity.

    **No data-leakage concerns.** Shuffling only reorders samples within a
    single (train) set; walk-forward fold construction already guarantees
    train < val < test day ordering. Val/test DataLoader should use
    ``shuffle=False`` (sequential access is cache-friendly on its own).

    Parameters
    ----------
    dataset : LOBDatasetV2
        Must expose ``_offsets`` (cumulative per-day sample counts) and
        ``_day_paths`` (list of path length N_days).
    chunk_size : int, default 32
        Number of days per chunk. All samples from these days are pooled
        and shuffled together, then yielded in shuffled order before the
        next chunk begins. Choose ``<= dataset.cache_size`` for 100% hit
        rate.
    shuffle_days : bool, default True
        Whether to shuffle the order in which chunks (and days within
        chunks) are processed each epoch.
    shuffle_within_day : bool, default True
        DEPRECATED — kept for back-compat. When ``True`` (default), samples
        within each chunk are globally shuffled (spans multiple days).
        When ``False``, chunks are yielded as contiguous day-after-day
        runs without intra-chunk shuffling.
    seed : int, optional
        Base RNG seed. Actual seed per epoch is ``seed + epoch`` (set via
        ``set_epoch()``). Default ``None`` means a fresh RNG each epoch
        (not reproducible).
    drop_last : bool, default False
        Kept for Sampler interface compatibility. The actual DataLoader
        ``drop_last`` parameter handles batch truncation.
    """

    def __init__(
        self,
        dataset,
        chunk_size: int = 32,
        shuffle_days: bool = True,
        shuffle_within_day: bool = True,
        seed: Optional[int] = None,
        drop_last: bool = False,
    ) -> None:
        # Validate dataset has required attrs
        if not hasattr(dataset, "_offsets") or not hasattr(dataset, "_day_paths"):
            raise TypeError(
                "DayChunkedSampler requires a dataset with _offsets and "
                "_day_paths attributes (e.g. LOBDatasetV2)"
            )
        if chunk_size < 1:
            raise ValueError(f"chunk_size must be >= 1, got {chunk_size}")
        self.dataset = dataset
        self.chunk_size = int(chunk_size)
        self.shuffle_days = shuffle_days
        self.shuffle_within_day = shuffle_within_day
        self.seed = seed
        self.drop_last = drop_last
        self._epoch = 0

    def set_epoch(self, epoch: int) -> None:
        """Set the epoch number (for reproducibility across epochs)."""
        self._epoch = int(epoch)

    def __iter__(self):
        import random
        if self.seed is not None:
            rng = random.Random(self.seed + self._epoch)
        else:
            rng = random.Random()

        n_days = len(self.dataset._day_paths)
        day_order = list(range(n_days))
        if self.shuffle_days:
            rng.shuffle(day_order)

        # Split day_order into chunks of chunk_size days
        for chunk_start in range(0, n_days, self.chunk_size):
            chunk_days = day_order[chunk_start : chunk_start + self.chunk_size]

            # Gather all sample indices from this chunk of days
            chunk_indices: List[int] = []
            for d in chunk_days:
                start = int(self.dataset._offsets[d])
                end = int(self.dataset._offsets[d + 1])
                chunk_indices.extend(range(start, end))

            # Global shuffle WITHIN the chunk — gives batch-level day
            # diversity while staying cache-resident. When chunk_size=1
            # this is intra-day shuffle (legacy DayChunkedSampler behaviour).
            if self.shuffle_within_day:
                rng.shuffle(chunk_indices)

            yield from chunk_indices

    def __len__(self) -> int:
        return int(self.dataset._offsets[-1])


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
