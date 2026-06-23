"""V2ArchDataset: DualLOBDataset + the 60s-pooled long-context series (X_long).

> **created:** 2026-06-22 | **Session:** v2-dual-source-arch | **状态:** in-progress

Extends :class:`DualLOBDataset` (which already returns the perp deep book as the
trailing tuple element) by ALSO returning ``X_long`` (the (240,10) long-context
series from ``data/npz_v2arch``) as the final element, z-scored per channel with
TRAIN-FIT stats passed in (``xlong_mean`` / ``xlong_std``) — the same
normalization contract the parent uses for the fine ``X`` features, but for the
long branch (which has no RevIN).

Returned tuples
---------------
  dual + regime : (x_feat, x_raw, regime_prior, y, mask, x_perp, x_long)
  dual, no rp   : (x_feat, x_raw,               y, mask, x_perp, x_long)

The trainer (``multi_asset/train/train_v2arch.py``) unpacks the trailing
``x_long`` and threads it into ``model(..., x_long=...)``. With ``xlong_mean`` /
``xlong_std`` None (stats pass) the long series is returned raw (used to compute
the train-fit stats). The model treats ``x_long=None`` as a pure no-op, so a
mis-built cache degrades to the dual-LOB (perp-only) model rather than crashing —
but we fail fast at construction if the key is missing on the first days.
"""
from __future__ import annotations

from typing import List, Optional

import numpy as np
import torch

from src.training.dataset import _np_load_with_retry
from multi_asset.data.dual_lob_dataset import DualLOBDataset, PERP_KEY

LONG_KEY = "X_long"


class V2ArchDataset(DualLOBDataset):
    """``DualLOBDataset`` that also returns the long-context series ``X_long``."""

    def __init__(self, *args, xlong_mean: Optional[np.ndarray] = None,
                 xlong_std: Optional[np.ndarray] = None,
                 x_channels: Optional[int] = None, **kwargs) -> None:
        self._pre_X_long: np.ndarray | None = None
        # Optional in-memory X-channel slice (keep leading ``x_channels`` cols of
        # X), the matched-BASE arm's spot-64 reference (drop the 8 cross cols).
        # Exact like SlicedLOBDataset: per-channel normalize is independent, so
        # slicing AFTER normalize is byte-identical to normalizing only those
        # channels. Applied in _load_day (covers lazy + preload + stats + model
        # n_features), BEFORE the parent stacks raw books / long.
        self._x_channels = (None if x_channels is None else int(x_channels))
        # store norm BEFORE super().__init__ (it may call _do_preload)
        self._xlong_mean = (None if xlong_mean is None
                            else np.asarray(xlong_mean, dtype=np.float32))
        if xlong_std is None:
            self._xlong_std = None
        else:
            s = np.asarray(xlong_std, dtype=np.float32)
            self._xlong_std = np.where(s < 1e-6, 1.0, s).astype(np.float32)
        super().__init__(*args, **kwargs)

        # fail fast if X_long missing on the first days
        missing: List[str] = []
        for day, path in zip(self.days, self._day_paths):
            with _np_load_with_retry(path, allow_pickle=True) as npz:
                if LONG_KEY not in npz.files:
                    missing.append(day)
            if len(missing) >= 5:
                break
        if missing:
            raise ValueError(
                f"{LONG_KEY!r} not found in {len(missing)}+ day NPZ(s) "
                f"(e.g. {missing[:5]}). Build the v2arch cache via "
                f"multi_asset/data/build_v2arch_npz.py before training."
            )

    def _norm_long(self, xl: np.ndarray) -> np.ndarray:
        if self._xlong_mean is not None and self._xlong_std is not None:
            xl = (xl - self._xlong_mean) / self._xlong_std
        return np.nan_to_num(xl, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)

    # -- lazy per-day: attach X_long to the parent's cached dict ----------- #
    def _load_day(self, day_idx: int):
        data = super()._load_day(day_idx)
        # apply the optional X-channel slice in place (idempotent — re-reads of a
        # cached day already see the sliced width since the slice is recorded on
        # the cached dict's array).
        if self._x_channels is not None and data["X"].shape[-1] > self._x_channels:
            data["X"] = np.ascontiguousarray(data["X"][..., : self._x_channels])
        if LONG_KEY not in data:
            path = self._day_paths[day_idx]
            with _np_load_with_retry(path, allow_pickle=True) as npz:
                xl = np.asarray(npz[LONG_KEY], dtype=np.float32)
            data[LONG_KEY] = self._norm_long(xl)
        return data

    # -- preload: SINGLE-PASS build of ALL global tensors (memory-safe) ----- #
    def _do_preload(self) -> None:
        """One pass over the days building every resident tensor, reading each
        NPZ exactly ONCE.

        MEMORY FIX (the silent-kill bug): the prior version called
        ``super()._do_preload()`` (which loads every day via ``_load_day``) and
        THEN re-looped loading every day a SECOND time for X_long — doubling the
        NPZ decompression I/O and transient arrays, which on a 200+-day fold blew
        past RAM (~125 GB for one 200-day dataset) and the process was SIGKILLed
        with no Python traceback. Here we replicate the parent's f16-raw-book
        scheme (``X_raw``/``X_raw_perp_deep`` stored float16; ``__getitem__``
        upcasts on fetch) and add X_long in the SAME loop, so each day's NPZ is
        opened once and the per-day transient arrays are freed immediately. The
        f16 raw books halve their footprint (they are f16 on disk — lossless)."""
        x_parts: List[np.ndarray] = []
        xraw_parts: List[np.ndarray] = []
        xperp_parts: List[np.ndarray] = []
        rp_parts: List[np.ndarray] = []
        y_parts: List[np.ndarray] = []
        mask_parts: List[np.ndarray] = []
        long_parts: List[np.ndarray] = []
        for day_idx in range(len(self._day_paths)):
            data = self._load_day(day_idx)          # X (sliced) + raw + perp + long + rp/y/mask
            x_parts.append(np.ascontiguousarray(data["X"], dtype=np.float32))
            if self._has_raw:
                xraw_parts.append(data["X_raw"].astype(np.float16))
                xperp_parts.append(data[PERP_KEY].astype(np.float16))
            if self._has_regime_prior:
                rp_parts.append(data["regime_prior"])
            y_parts.append(data["y"])
            mask_parts.append(data["mask"])
            long_parts.append(data[LONG_KEY])       # already normed f32 (240,10)
            # free this day from the LRU immediately so transients don't pile up
            self.clear_cache()
        self._pre_X = np.concatenate(x_parts, axis=0); del x_parts
        if self._has_raw:
            self._pre_X_raw = np.concatenate(xraw_parts, axis=0); del xraw_parts
            self._pre_X_raw_perp = np.concatenate(xperp_parts, axis=0); del xperp_parts
        if self._has_regime_prior:
            self._pre_regime_prior = np.concatenate(rp_parts, axis=0); del rp_parts
        self._pre_y = np.concatenate(y_parts, axis=0); del y_parts
        self._pre_mask = np.concatenate(mask_parts, axis=0); del mask_parts
        self._pre_X_long = np.concatenate(long_parts, axis=0); del long_parts
        self.clear_cache()

    # -- compute train-fit per-channel stats for X_long (stats pass) ------- #
    def compute_long_stats(self):
        """Per-channel mean/std of X_long over all rows of these days (masked).

        Used on the stats (train) dataset to fit the z-score applied to X_long in
        the train/val/test datasets — the long-branch analogue of compute_stats."""
        s1 = None; s2 = None; n = 0
        for day_idx in range(len(self._day_paths)):
            path = self._day_paths[day_idx]
            with _np_load_with_retry(path, allow_pickle=True) as npz:
                xl = np.asarray(npz[LONG_KEY], dtype=np.float64)  # (N,240,C)
            flat = xl.reshape(-1, xl.shape[-1])
            flat = np.nan_to_num(flat, nan=0.0, posinf=0.0, neginf=0.0)
            if s1 is None:
                s1 = flat.sum(0); s2 = (flat * flat).sum(0)
            else:
                s1 += flat.sum(0); s2 += (flat * flat).sum(0)
            n += flat.shape[0]
        mean = s1 / max(n, 1)
        var = s2 / max(n, 1) - mean * mean
        std = np.sqrt(np.clip(var, 0.0, None))
        return mean.astype(np.float32), std.astype(np.float32)

    # -- __getitem__: append x_long as the final tuple element ------------- #
    def __getitem__(self, idx: int):  # type: ignore[override]
        base = super().__getitem__(idx)   # (..., x_perp) from DualLOBDataset
        if idx < 0:
            idx += self._total
        if self._preloaded:
            xl = self._pre_X_long[idx]
        else:
            day_idx, local_idx = self._locate(idx)
            data = self._load_day(day_idx)
            xl = data[LONG_KEY][local_idx]
        x_long = torch.from_numpy(np.ascontiguousarray(xl, dtype=np.float32))
        return (*base, x_long)
