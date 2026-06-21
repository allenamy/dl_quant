"""SlicedLOBDataset — in-memory channel/column SLICE of an NPZ cache.

WHY (disk-safe single-axis bisection)
-------------------------------------
The Phase-2 dual-source collapse bisection needs each addition ALONE:
  (b) +basis SEQ : X kept (69), regime_prior sliced to 6   (drop basis LEVELs)
  (c) +basis LVL : X sliced to 64 (drop divergence SEQ), regime_prior kept (10)
Materialising those as separate NPZ dirs would cost ~60 GB EACH and the box's
data disk is 100% full (23 GB free). So instead we read ``data/npz_dualsrc``
(the already-built dual cache) and SLICE X-channels / regime_prior-columns
IN MEMORY at load time — zero extra disk, and guaranteed apples-to-apples
(same rows / timestamps / target / X_raw as the dualsrc cache, which itself
copied spot X[:64] / regime_prior[:6] / X_raw / y / ts verbatim from the
leak-free ``npz_spot2perp_clean`` baseline).

CORRECTNESS (why slicing AFTER the parent's normalize is exact)
---------------------------------------------------------------
The parent ``LOBDatasetV2`` standardises X PER CHANNEL: ``(X - mean)/std`` with
a per-feature ``x_mean``/``x_std`` vector. compute_stats runs on the FULL-width
(69) X via a SEPARATE stats dataset (``normalize=False``) — we do NOT override it,
so it returns FULL-width stats and the normalized datasets normalise the FULL X
with the matching full-width vector (no shape mismatch). Because standardisation
is independent per channel, slicing the KEPT channels AFTER normalisation yields
byte-identical values to normalising only those channels. ``regime_prior`` is
NOT standardised by the dataset (it reaches FiLM/PPNet raw), so slicing its
columns is a trivial, exact subset. X_raw / y / mask / timestamps are untouched.

The trainer reads ``n_features`` from ``_load_day(0)["X"].shape[-1]`` (→ sliced
width, so the model is built at the sliced width) and preload concatenates
``_load_day`` outputs (→ sliced), so a single ``_load_day`` override covers the
lazy, preload, stats-of-normalized, and model-construction paths.

USAGE
-----
Set the config ``data.npz_dir`` to ``data/npz_dualsrc`` and add a ``data.slice``
block read by ``train_dual_lob`` (which constructs this class when present):
    "slice": {"x_channels": 69, "prior_cols": 6}   # arm (b) seqonly
    "slice": {"x_channels": 64, "prior_cols": 10}  # arm (c) lvlonly
``x_channels``/``prior_cols`` = how many LEADING channels/cols to KEEP. ``None``
(or absent) keeps all (no-op). The class is otherwise a drop-in LOBDatasetV2.
"""
from __future__ import annotations

import os.path as p
import sys
from typing import Dict, Optional

import numpy as np

_REPO = p.dirname(p.dirname(p.dirname(p.abspath(__file__))))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from src.training.dataset import LOBDatasetV2  # noqa: E402


class SlicedLOBDataset(LOBDatasetV2):
    """LOBDatasetV2 that keeps only the leading ``x_channels`` of X and the
    leading ``prior_cols`` of regime_prior (in-memory; disk-free)."""

    def __init__(self, *args, x_channels: Optional[int] = None,
                 prior_cols: Optional[int] = None, **kwargs):
        self._slice_xc = int(x_channels) if x_channels is not None else None
        self._slice_pc = int(prior_cols) if prior_cols is not None else None
        super().__init__(*args, **kwargs)

    # ---- per-day load: slice the channels/cols AFTER the parent processes ----
    def _load_day(self, day_idx: int) -> Dict[str, np.ndarray]:
        data = super()._load_day(day_idx)
        if self._slice_xc is not None and "X" in data \
                and data["X"].shape[-1] > self._slice_xc:
            # NOTE: cached dicts are private to this dataset (parent guarantees
            # callers get a torch copy), but to be safe against the LRU cache
            # returning the same object twice we slice with a view-copy only
            # when needed. The parent already returns a fresh array per miss;
            # on a cache hit the array is already sliced (idempotent: shape
            # check above short-circuits once width == target).
            data["X"] = np.ascontiguousarray(data["X"][..., : self._slice_xc])
        if self._slice_pc is not None and "regime_prior" in data \
                and data["regime_prior"].shape[-1] > self._slice_pc:
            data["regime_prior"] = np.ascontiguousarray(
                data["regime_prior"][..., : self._slice_pc])
        return data
