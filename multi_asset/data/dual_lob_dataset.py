"""DualLOBDataset: LOBDatasetV2 + the perp deep order book (``X_raw_perp_deep``).

The dual-LOB experiment (Stage D2) feeds ``DualLOBREGArch`` two raw order books:
the SPOT book on the proven Path-B tower (the existing ``X_raw`` key) and the
PERP deep book as a zero-init gated residual (the NEW ``x_raw_perp_deep`` model
input). The merged cache ``data/npz_duallob`` (built by
``multi_asset/data/build_duallob_npz.py``) carries the perp book under the key
``X_raw_perp_deep``, position-joined to the same windows as ``X_raw``.

This subclass adds ``X_raw_perp_deep`` to BOTH dataset code paths that
``LOBDatasetV2`` uses for ``X_raw`` — the lazy per-day LRU cache (``_load_day``)
and the preload fast path (``_do_preload`` / ``__getitem__``) — so the perp book
gets the EXACT same windowing, sanitisation (nan→0) and ordering as the spot
book, and is returned as the trailing element of each ``__getitem__`` tuple:

    dual + regime_prior : (x_feat, x_raw, regime_prior, y, mask, x_raw_perp_deep)
    dual, no regime     : (x_feat, x_raw,               y, mask, x_raw_perp_deep)

The standalone trainer (``multi_asset/train/train_dual_lob.py``) unpacks this
trailing element and threads it into ``model(..., x_raw_perp_deep=...)``. Nothing
about the spot/feature/target contract changes — this is a pure superset of
``LOBDatasetV2``: with the new key absent the class behaves like its parent (it
asserts the key's presence at construction so a misbuilt cache fails fast rather
than silently dropping the perp residual).

Design notes
------------
* ``X_raw_perp_deep`` is NOT normalised by the X feature stats — exactly like
  ``X_raw`` it is already in bps + log1p units. We only ``nan_to_num`` it.
* No multi-horizon / overlay logic is touched; we only piggy-back the extra raw
  tensor onto the parent's already-built per-day ``data`` dict and global
  preload tensors.
* Requires ``X_raw`` to be present (the perp residual is meaningless without the
  spot Path-B book). Enforced at construction.
"""
from __future__ import annotations

import os
from typing import Dict, List

import numpy as np
import torch

from src.training.dataset import LOBDatasetV2, _np_load_with_retry

PERP_KEY = "X_raw_perp_deep"


class DualLOBDataset(LOBDatasetV2):
    """``LOBDatasetV2`` that also returns the perp deep book (``X_raw_perp_deep``).

    All constructor kwargs are forwarded to ``LOBDatasetV2`` unchanged. After the
    parent scans NPZ metadata we verify every day carries the perp key (fail
    fast) and, when ``preload=True``, materialise the perp tensor into a global
    array alongside ``_pre_X_raw``.
    """

    def __init__(self, *args, **kwargs) -> None:
        # Parent __init__ scans metadata and (if preload=True) calls _do_preload,
        # which we override below to also gather the perp tensor. We set a flag
        # BEFORE super().__init__ so _do_preload (invoked inside it) sees it.
        self._pre_X_raw_perp: np.ndarray | None = None
        super().__init__(*args, **kwargs)

        if not self._has_raw:
            raise ValueError(
                "DualLOBDataset requires X_raw (the spot Path-B book) to be "
                "present; the perp gated residual has no base stream without it."
            )

        # Fail fast if any day lacks the perp deep-book key — a silently-missing
        # key would turn the dual-LOB run back into the spot-only baseline.
        missing: List[str] = []
        for day, path in zip(self.days, self._day_paths):
            with _np_load_with_retry(path, allow_pickle=True) as npz:
                if PERP_KEY not in npz.files:
                    missing.append(day)
            if len(missing) >= 5:
                break
        if missing:
            raise ValueError(
                f"{PERP_KEY!r} not found in {len(missing)}+ day NPZ(s) "
                f"(e.g. {missing[:5]}). Build the dual-LOB cache via "
                f"multi_asset/data/build_duallob_npz.py before training."
            )

    # ------------------------------------------------------------------ #
    # Lazy per-day path: extend the parent's cached dict with the perp book #
    # ------------------------------------------------------------------ #
    def _load_day(self, day_idx: int) -> Dict[str, np.ndarray]:
        """Parent ``_load_day`` (X / X_raw / regime / y / mask + overlays) plus
        the perp deep book under ``X_raw_perp_deep``.

        The parent caches its ``data`` dict in the LRU; we attach the perp array
        to that same dict (idempotent — re-reads of a cached day already carry
        it) so the preload path and the lazy path share one code route.
        """
        data = super()._load_day(day_idx)
        if PERP_KEY not in data:
            path = self._day_paths[day_idx]
            with _np_load_with_retry(path, allow_pickle=True) as npz:
                xp = np.asarray(npz[PERP_KEY], dtype=np.float32)
            # Same sanitisation as the parent applies to X_raw (already in
            # bps + log1p units → no feature-stat normalisation).
            xp = np.nan_to_num(xp, nan=0.0, posinf=0.0, neginf=0.0)
            data[PERP_KEY] = xp
        return data

    # ------------------------------------------------------------------ #
    # Preload fast path: build the global perp tensor next to _pre_X_raw    #
    # ------------------------------------------------------------------ #
    def _do_preload(self) -> None:
        """Materialise every day (incl. the perp book) into global tensors.

        Mirrors the parent's concatenation but additionally stacks
        ``X_raw_perp_deep`` into ``self._pre_X_raw_perp``. We walk the days with
        our overridden ``_load_day`` (so each ``data`` dict carries the perp
        key), collect every array, then clear the LRU like the parent does.

        MEMORY FIX (Stage G OOM, rc=137 at 400d): the parent ``_load_day`` upcasts
        the SPOT ``X_raw`` to float32 (src/training/dataset.py ~L560) and our
        ``_load_day`` upcasts the PERP ``X_raw_perp_deep`` to float32 — so two
        (N,600,20,4) f32 raw books (192 KB/row EACH) dominate the preload. With
        N=477/day, a 400+60+31-day fold preloads all three datasets at once for a
        MEASURED 128.7 GB (X 63.6 + spot-raw 36.6 + perp-raw 36.6 + ...), which
        exceeds the ~102 GB free on the box → OOM kill. FIX: store BOTH raw books
        as float16 in the resident preload arrays (they are float16 on disk
        already — bps + log1p units — so this is lossless w.r.t. the cache, and
        ``__getitem__`` already upcasts each fetched row to float32 via
        ``np.ascontiguousarray(..., dtype=np.float32)`` so the model still sees
        f32). This drops the 400d preload to a MEASURED 83.8 GB (fits). The
        feature tensor ``X`` and ``y``/``mask``/``regime_prior`` stay float32
        exactly as the parent stores them — only the two raw books are halved.
        """
        x_parts: List[np.ndarray] = []
        xraw_parts: List[np.ndarray] = []
        xperp_parts: List[np.ndarray] = []
        rp_parts: List[np.ndarray] = []
        y_parts: List[np.ndarray] = []
        mask_parts: List[np.ndarray] = []
        for day_idx in range(len(self._day_paths)):
            data = self._load_day(day_idx)
            x_parts.append(data["X"])
            if self._has_raw:
                # Downcast each day's raw books to f16 BEFORE collecting so the
                # transient per-day f32 arrays are freed and the concatenated
                # resident tensors are f16 (halved RAM). nan_to_num already ran
                # in _load_day; f16 round-trip of bps/log1p values is lossless to
                # the on-disk f16 caliber.
                xraw_parts.append(data["X_raw"].astype(np.float16))
                xperp_parts.append(data[PERP_KEY].astype(np.float16))
            if self._has_regime_prior:
                rp_parts.append(data["regime_prior"])
            y_parts.append(data["y"])
            mask_parts.append(data["mask"])
        self._pre_X = np.concatenate(x_parts, axis=0)
        if self._has_raw:
            # f16 resident storage; __getitem__ upcasts each row to f32 on fetch.
            self._pre_X_raw = np.concatenate(xraw_parts, axis=0)
            self._pre_X_raw_perp = np.concatenate(xperp_parts, axis=0)
        if self._has_regime_prior:
            self._pre_regime_prior = np.concatenate(rp_parts, axis=0)
        self._pre_y = np.concatenate(y_parts, axis=0)
        self._pre_mask = np.concatenate(mask_parts, axis=0)
        self.clear_cache()

    # ------------------------------------------------------------------ #
    # __getitem__: append the perp book as the trailing tuple element       #
    # ------------------------------------------------------------------ #
    def __getitem__(self, idx: int):  # type: ignore[override]
        if idx < 0:
            idx += self._total

        if self._preloaded:
            # Reproduce the parent's preload item assembly, then append perp.
            x_feat = torch.from_numpy(
                np.ascontiguousarray(self._pre_X[idx], dtype=np.float32)
            )
            y_item = self._pre_y[idx]
            m_item = self._pre_mask[idx]
            if self._horizons is not None:
                y_t = torch.from_numpy(np.asarray(y_item, dtype=np.float32))
                m_t = torch.from_numpy(np.asarray(m_item, dtype=np.float32))
                if len(self._horizons) == 1:
                    y_t = y_t.squeeze(-1)
                    m_t = m_t.squeeze(-1)
            else:
                y_t = torch.tensor(float(y_item))
                m_t = torch.tensor(float(m_item))
            x_raw = torch.from_numpy(
                np.ascontiguousarray(self._pre_X_raw[idx], dtype=np.float32)
            )
            x_perp = torch.from_numpy(
                np.ascontiguousarray(self._pre_X_raw_perp[idx], dtype=np.float32)
            )
            if self._has_regime_prior:
                rp = torch.from_numpy(
                    np.ascontiguousarray(self._pre_regime_prior[idx], dtype=np.float32)
                )
                return (x_feat, x_raw, rp, y_t, m_t, x_perp)
            return (x_feat, x_raw, y_t, m_t, x_perp)

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
            if len(self._horizons) == 1:
                y_t = y_t.squeeze(-1)
                m_t = m_t.squeeze(-1)
        else:
            y_t = torch.tensor(float(y_item))
            m_t = torch.tensor(float(m_item))

        x_raw = torch.from_numpy(
            np.ascontiguousarray(data["X_raw"][local_idx], dtype=np.float32)
        )
        x_perp = torch.from_numpy(
            np.ascontiguousarray(data[PERP_KEY][local_idx], dtype=np.float32)
        )
        if self._has_regime_prior:
            rp = torch.from_numpy(
                np.ascontiguousarray(data["regime_prior"][local_idx], dtype=np.float32)
            )
            return (x_feat, x_raw, rp, y_t, m_t, x_perp)
        return (x_feat, x_raw, y_t, m_t, x_perp)
