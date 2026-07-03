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
        # D1 state_prior OVERLAY (Stage-0B): dir of per-day npz carrying the 18-d
        # causal state vector (funding/pidx/OI/L-S/rvol) keyed by timestamps. When
        # set, _load_day concatenates it onto regime_prior -> d_prior=24. Popped
        # BEFORE super().__init__ (LOBDatasetV2 does not accept it) and set BEFORE
        # so _do_preload (invoked inside super().__init__) sees it.
        self.state_prior_dir: str | None = kwargs.pop("state_prior_dir", None)
        # ALIGN arm (V2, Stage-1+ 2026-07-03): dir of per-day npz with the causal
        # trailing-1h-mean m(t) + demeaned target y_align = y_600 - m. When set,
        # _load_day REPLACES the (normalised) y target with the (normalised)
        # DEMEANED target, so the model trains on the tradeable 10-min residual
        # instead of the slow >1h band where the artifacts/β-swings live. The
        # per-fold y_median/y_sigma stay computed on RAW y_600 (stats_ds has no
        # align_target_dir), so eval denorm is unchanged; eval reconstructs raw y
        # (+m) and the deploy 1h-demean caliber from the sidecar.
        self.align_target_dir: str | None = kwargs.pop("align_target_dir", None)
        # mh180 y_180 SIDECAR (Stage-3): dir of per-day npz carrying the leak-free
        # 180s perp target keyed by timestamps. The parent LOBDatasetV2 reads y_{H}
        # DIRECTLY from the main npz (src/ is read-only), and npz_v2arch has only
        # y_600 — so we let the PARENT read the npz-present horizons (drop y_180),
        # then promote self._horizons back to the full list and inject y_180 from
        # the sidecar in _load_day. Requires preload=False (preload runs inside
        # super().__init__ BEFORE we can restore _horizons), so we force it off.
        self.y180_sidecar_dir: str | None = kwargs.pop("y180_sidecar_dir", None)
        self._y180_full_horizons: Optional[List[str]] = None
        if self.y180_sidecar_dir is not None:
            hz = kwargs.get("horizons")
            if not hz or "y_180" not in hz:
                raise ValueError(
                    "y180_sidecar_dir requires horizons to include 'y_180' "
                    f"(got {hz!r}); set data.horizons_sec=[180,600]."
                )
            self._y180_full_horizons = list(hz)
            kwargs["horizons"] = [h for h in hz if h != "y_180"]   # parent reads npz only
            if kwargs.get("preload"):
                print("[DualLOBDataset] y180 sidecar: forcing preload=False "
                      "(multi-horizon injection is lazy-path only).")
            kwargs["preload"] = False

        # ALIGN-as-AUX (interference-free variant): raw y_600 stays the PRIMARY
        # (VAL-selected) target; the demeaned y_align = y_600 - m rides as a
        # low-weight AUX horizon-0 so the backbone allocates capacity to the
        # short-term signal WITHOUT stripping the level from the primary objective
        # (fixes the pure-ALIGN interference). Same plumbing as y180: promote
        # _horizons post-init + inject in _load_day (lazy-only -> preload off).
        self.align_aux_dir: str | None = kwargs.pop("align_aux_dir", None)
        self._align_aux_full_horizons: Optional[List[str]] = None
        if self.align_aux_dir is not None:
            if self.y180_sidecar_dir is not None:
                raise ValueError("align_aux_dir and y180_sidecar_dir are mutually exclusive.")
            if self.align_target_dir is not None:
                raise ValueError("align_aux_dir (aux head) and align_target_dir "
                                 "(target substitution) are mutually exclusive.")
            hz = kwargs.get("horizons")
            if not hz or "y_600" not in hz:
                raise ValueError(f"align_aux_dir requires horizons include 'y_600' (got {hz!r}).")
            # aux target y_align FIRST (idx 0); primary y_600 LAST (primary_idx = n-1)
            self._align_aux_full_horizons = ["y_align"] + list(hz)
            kwargs["horizons"] = list(hz)           # parent reads npz-present y_600 only
            if kwargs.get("preload"):
                print("[DualLOBDataset] align_aux: forcing preload=False "
                      "(multi-horizon injection is lazy-path only).")
            kwargs["preload"] = False
        super().__init__(*args, **kwargs)

        if self._align_aux_full_horizons is not None:
            self._horizons = list(self._align_aux_full_horizons)
            missing_aux = [d for d in self.days
                           if not os.path.exists(os.path.join(self.align_aux_dir, f"{d}.npz"))]
            if missing_aux:
                raise ValueError(
                    f"align_aux y_align sidecar npz missing for {len(missing_aux)}+ day(s) "
                    f"(e.g. {missing_aux[:5]}) under {self.align_aux_dir!r}.")

        if self._y180_full_horizons is not None:
            # promote to the full multi-horizon view for __getitem__ / the model;
            # the parent still reads only self._y_keys (y_600) from the npz.
            self._horizons = list(self._y180_full_horizons)
            missing_y180 = [d for d in self.days
                            if not os.path.exists(os.path.join(self.y180_sidecar_dir, f"{d}.npz"))]
            if missing_y180:
                raise ValueError(
                    f"y_180 sidecar npz missing for {len(missing_y180)}+ day(s) "
                    f"(e.g. {missing_y180[:5]}) under {self.y180_sidecar_dir!r}. "
                    f"Build via multi_asset/data/build_y180_sidecar.py first."
                )

        # Fail fast if the state overlay is requested but missing/misaligned for
        # any day — a silently-missing overlay would corrupt d_prior alignment.
        if self.state_prior_dir:
            if not self._has_regime_prior:
                raise ValueError(
                    "state_prior_dir set but the cache has no regime_prior; the "
                    "18-d state overlay is appended onto regime_prior."
                )
            missing_state: List[str] = []
            for day in self.days:
                if not os.path.exists(os.path.join(self.state_prior_dir, f"{day}.npz")):
                    missing_state.append(day)
                if len(missing_state) >= 5:
                    break
            if missing_state:
                raise ValueError(
                    f"state_prior overlay npz missing for {len(missing_state)}+ "
                    f"day(s) (e.g. {missing_state[:5]}) under {self.state_prior_dir!r}. "
                    f"Build it via multi_asset/data/build_state_prior.py first."
                )

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

        # D1 state_prior overlay: append the 18-d causal state onto regime_prior.
        # Values are RAW (funding/OI/etc); the MODEL frozen-normalises them
        # (FLAG-11 fix). Order is guaranteed row-aligned by the builder (it walks
        # the source npz timestamps in order); we ASSERT timestamp equality to
        # catch a stale/misbuilt overlay. Idempotent: only appends if the width
        # is still the base prior width (re-reads of a cached day skip it).
        if (self.state_prior_dir and "regime_prior" in data
                and int(data["regime_prior"].shape[1]) <= 6):
            # base prior width for npz_v2arch is 6; the <=6 guard also makes this
            # a no-op on LRU cache hits (the cached dict already carries 24-d).
            day = self.days[day_idx]
            sp_path = os.path.join(self.state_prior_dir, f"{day}.npz")
            with _np_load_with_retry(sp_path, allow_pickle=True) as sp:
                state = np.asarray(sp["state"], dtype=np.float32)   # (N, 18)
                ov_ts = np.asarray(sp["timestamps"], dtype=np.int64)
            if state.shape[0] != data["regime_prior"].shape[0]:
                raise ValueError(
                    f"state overlay row count {state.shape[0]} != regime_prior "
                    f"{data['regime_prior'].shape[0]} for {day}"
                )
            with _np_load_with_retry(self._day_paths[day_idx], allow_pickle=True) as npz:
                main_ts = np.asarray(npz["timestamps"], dtype=np.int64)
            if not np.array_equal(ov_ts, main_ts):
                raise ValueError(
                    f"state overlay timestamps misaligned with cache for {day} "
                    f"(builder must preserve row order)."
                )
            state = np.nan_to_num(state, nan=0.0, posinf=0.0, neginf=0.0)
            data["regime_prior"] = np.concatenate(
                [data["regime_prior"], state], axis=1).astype(np.float32)

        # ALIGN arm: replace the (normalised) y_600 target with the (normalised)
        # DEMEANED target y_align = y_600 - m (m = causal trailing-1h-mean of
        # realized past y_600, from the sidecar), using the SAME fold y_norm
        # (median/sigma/clip) the parent applied to y_600 — so eval denorm is
        # unchanged and the model just learns the tradeable 10-min residual.
        # Single-horizon only. Idempotent via a per-day flag (LRU-cache safe).
        if self.align_target_dir is not None and not bool(data.get("_align_done", False)):
            if self._y_norm is None:
                raise ValueError("align_target_dir requires normalize=True (y_norm set).")
            day = self.days[day_idx]
            ap = os.path.join(self.align_target_dir, f"{day}.npz")
            with _np_load_with_retry(ap, allow_pickle=True) as az:
                y_align = np.asarray(az["y_align"], dtype=np.float64)     # (N,) = y_600 - m
                a_ts = np.asarray(az["timestamps"], dtype=np.int64)
            with _np_load_with_retry(self._day_paths[day_idx], allow_pickle=True) as npz:
                main_ts = np.asarray(npz["timestamps"], dtype=np.int64)
            if not np.array_equal(a_ts, main_ts):
                raise ValueError(f"align sidecar timestamps misaligned with cache for {day}")
            median, sigma, clip = self._y_norm
            yan = np.clip((y_align - median) / sigma, -clip, clip)
            yan = yan.reshape(np.asarray(data["y"]).shape).astype(np.float32)
            data["y"] = np.where(np.asarray(data["mask"]) == 0, 0.0, yan).astype(np.float32)
            data["_align_done"] = True

        # mh180 y_180 sidecar: promote the parent's single-horizon y_600
        # (data["y"]/["mask"] shape (N, len(_y_keys))) to the full multi-horizon
        # view in self._horizons order, injecting y_180 from the sidecar
        # (normalised by the SAME fold y_norm the parent applied to y_600).
        # Idempotent: skips if the y column count already matches _horizons
        # (LRU cache hit).
        if (self.y180_sidecar_dir is not None and self._y180_full_horizons is not None
                and np.atleast_2d(data["y"]).shape[1] < len(self._horizons)):
            day = self.days[day_idx]
            y_parent = np.atleast_2d(data["y"]).astype(np.float32)      # (N, k) over _y_keys
            m_parent = np.atleast_2d(data["mask"]).astype(np.float32)
            yp_path = os.path.join(self.y180_sidecar_dir, f"{day}.npz")
            with _np_load_with_retry(yp_path, allow_pickle=True) as yp:
                y180 = np.asarray(yp["y_180"], dtype=np.float32)
                m180 = np.asarray(yp["y_mask_180"], dtype=np.float32)
                ov_ts = np.asarray(yp["timestamps"], dtype=np.int64)
            if y180.shape[0] != y_parent.shape[0]:
                raise ValueError(f"y_180 sidecar row count {y180.shape[0]} != "
                                 f"{y_parent.shape[0]} for {day}")
            with _np_load_with_retry(self._day_paths[day_idx], allow_pickle=True) as npz:
                main_ts = np.asarray(npz["timestamps"], dtype=np.int64)
            if not np.array_equal(ov_ts, main_ts):
                raise ValueError(f"y_180 sidecar timestamps misaligned for {day}.")
            # normalise y_180 through the SAME pipeline the parent applied to y_600
            y180 = np.nan_to_num(y180, nan=0.0, posinf=0.0, neginf=0.0)
            y180 = np.where(m180 == 0, 0.0, y180).astype(np.float32)
            if self._y_rolling_sigma is not None:
                sd = self._y_rolling_sigma.get(day)
                if sd:
                    y180 = (y180 / sd).astype(np.float32)
                    y180 = np.where(m180 == 0, 0.0, y180).astype(np.float32)
            if self._y_norm is not None:
                med, sig, clip = self._y_norm
                y180 = np.clip((y180 - med) / sig, -clip, clip).astype(np.float32)
                y180 = np.where(m180 == 0, 0.0, y180).astype(np.float32)
            cols_y: List[np.ndarray] = []
            cols_m: List[np.ndarray] = []
            for h in self._horizons:
                if h == "y_180":
                    cols_y.append(y180[:, None]); cols_m.append(m180[:, None])
                else:
                    j = self._y_keys.index(h)
                    cols_y.append(y_parent[:, j:j + 1]); cols_m.append(m_parent[:, j:j + 1])
            data["y"] = np.concatenate(cols_y, axis=1).astype(np.float32)
            data["mask"] = np.concatenate(cols_m, axis=1).astype(np.float32)

        # ALIGN-as-AUX: promote parent's y_600 to [y_align (aux,0), y_600 (primary,1)],
        # injecting demeaned y_align from the align sidecar, normalised by the SAME
        # fold y_norm the parent applied to y_600 (identical to the pure-ALIGN arm).
        # Aux mask = primary y_600 mask (same convention as align_target).
        if (self.align_aux_dir is not None and self._align_aux_full_horizons is not None
                and np.atleast_2d(data["y"]).shape[1] < len(self._horizons)):
            if self._y_norm is None:
                raise ValueError("align_aux_dir requires normalize=True (y_norm set).")
            day = self.days[day_idx]
            y_parent = np.atleast_2d(data["y"]).astype(np.float32)      # (N, k) over _y_keys (y_600)
            m_parent = np.atleast_2d(data["mask"]).astype(np.float32)
            ap = os.path.join(self.align_aux_dir, f"{day}.npz")
            with _np_load_with_retry(ap, allow_pickle=True) as az:
                y_align = np.asarray(az["y_align"], dtype=np.float64)    # (N,) = y_600 - m (raw units)
                a_ts = np.asarray(az["timestamps"], dtype=np.int64)
            if y_align.shape[0] != y_parent.shape[0]:
                raise ValueError(f"align_aux y_align row count {y_align.shape[0]} != "
                                 f"{y_parent.shape[0]} for {day}")
            with _np_load_with_retry(self._day_paths[day_idx], allow_pickle=True) as npz:
                main_ts = np.asarray(npz["timestamps"], dtype=np.int64)
            if not np.array_equal(a_ts, main_ts):
                raise ValueError(f"align_aux sidecar timestamps misaligned for {day}.")
            median, sigma, clip = self._y_norm
            yan = np.clip((y_align - median) / sigma, -clip, clip).reshape(-1).astype(np.float32)
            j600 = self._y_keys.index("y_600")
            m600 = m_parent[:, j600]
            yan = np.where(m600 == 0, 0.0, yan).astype(np.float32)
            cols_y2: List[np.ndarray] = []
            cols_m2: List[np.ndarray] = []
            for h in self._horizons:
                if h == "y_align":
                    cols_y2.append(yan[:, None]); cols_m2.append(m600[:, None])
                else:
                    j = self._y_keys.index(h)
                    cols_y2.append(y_parent[:, j:j + 1]); cols_m2.append(m_parent[:, j:j + 1])
            data["y"] = np.concatenate(cols_y2, axis=1).astype(np.float32)
            data["mask"] = np.concatenate(cols_m2, axis=1).astype(np.float32)
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
        f32). This drops the 400d preload to a MEASURED 83.8 GB (fits).

        TRAIN700 FIX (2026-06-24): with the raw books already f16, the resident
        preload is dominated by the float32 feature tensor ``X`` (MEASURED
        100.7 MB/day = 51% of the 196.9 MB/day resident). At train700 the
        all-splits preload is 155.7 GB > the ~125 GB cgroup cap -> OOM (the
        whole-session train300/lazy bottleneck). FIX: also store ``_pre_X`` as
        float16 in resident RAM (gated by ``PRELOAD_X_FLOAT16``, default True).
        X is in clipped z-scored / bps / log1p units with |X|<=1000, so f16 is
        a ~1.7e-4 median relative perturbation (well below the R^2<1% signal
        floor; verified prediction-Pearson-equivalent before enabling). The
        existing ``__getitem__`` ALREADY upcasts each fetched X row to f32 via
        ``np.ascontiguousarray(self._pre_X[idx], dtype=np.float32)`` (line ~177),
        so the model still trains in f32 -- a resident-storage-only change. New
        resident/day = 146.5 MB -> train700 all-splits = 115.9 GB (fits). Set
        env ``DUAL_PRELOAD_X_F32=1`` to disable (revert to f32 X) for the
        equivalence A/B test or if a precision regression is ever observed.
        OLD NOTE (raw books): The
        feature tensor ``X`` and ``y``/``mask``/``regime_prior`` stay float32
        exactly as the parent stores them — only the two raw books are halved.
        """
        # train700 RAM fix: store resident X as float16 unless explicitly
        # disabled. __getitem__ upcasts each fetched X row to f32, so the model
        # is unaffected; this only halves the resident feature tensor.
        x_f16 = os.environ.get("DUAL_PRELOAD_X_F32", "0") != "1"
        x_store_dtype = np.float16 if x_f16 else np.float32
        x_parts: List[np.ndarray] = []
        xraw_parts: List[np.ndarray] = []
        xperp_parts: List[np.ndarray] = []
        rp_parts: List[np.ndarray] = []
        y_parts: List[np.ndarray] = []
        mask_parts: List[np.ndarray] = []
        for day_idx in range(len(self._day_paths)):
            data = self._load_day(day_idx)
            # Downcast each day's X to the resident dtype BEFORE collecting so
            # the transient per-day f32 array is freed and the concatenated
            # resident tensor is f16 (halved RAM).
            x_parts.append(data["X"].astype(x_store_dtype, copy=False))
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
