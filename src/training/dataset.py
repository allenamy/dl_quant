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
from concurrent.futures import ThreadPoolExecutor
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
        preload: bool = False,
        smooth_target_dir: Optional[str] = None,
        tradeflow_dir: Optional[str] = None,
        # v5push (2026-05-11): two additional overlay dirs for E2E feature test
        # - novel_book_dir: 16 cols from compute_novel_features() (entropy, energy, dva, qd, etc.)
        # - novel_trade_dir: 10 cols (sv_ewm_HL, apb_W, run_signed_qty/len, cum_abs_qty)
        # Same broadcast pattern as tradeflow.
        novel_book_dir: Optional[str] = None,
        novel_trade_dir: Optional[str] = None,
        # v5push (2026-05-12): rolling causal y-normalize. JSON {day_str: sigma_in_raw_units}.
        # If set, dataset divides y_arr by σ_day before returning. Trainer's per-fold
        # normalize then sees vol-normalized target → model learns regime-invariant function.
        # Eval must denorm: y_pred_bps = y_pred_z × y_sigma_fold × σ_day × 1e4.
        y_rolling_sigma_path: Optional[str] = None,
        # v5push Phase 3 Track A (2026-05-13): TIME-VARYING feature overlay.
        # Loads (N, T, K) tv_feats per day and concatenates to X along channel dim
        # (NOT broadcast — preserves time evolution for Conformer to learn).
        # Output X shape becomes (N, T, n_features + K).
        tv_overlay_dir: Optional[str] = None,
        # v5push Track v7 (2026-05-15): Intraday Regime Overlay.
        # Same (N, T, K) format as tv_overlay_dir but a separate dir for the
        # per-timestep regime-context features (orthogonal to TV alpha signals).
        # Default None → loader skipped → baseline behavior preserved.
        intraday_regime_dir: Optional[str] = None,
        # v5push Track v8 (2026-05-15): Microprice Trajectory Overlay.
        # 4 per-timestep features (EMA / slope / persistence / amplitude of
        # microprice deviation from mid). Same (N, T, K) format. Default off.
        microprice_trajectory_dir: Optional[str] = None,
        use_smoothed_target: bool = True,
        use_time2vec: bool = False,
        # Phase B.2: append past_30d_y_mean as 7th regime_prior column.
        # Causal: uses days [D-30, D-1] strictly past, day D excluded.
        # Path is JSON {day_str: y_600_mean_in_log_return}.
        recent_y_mean_path: Optional[str] = None,
        recent_y_lookback_days: int = 30,
        # Phase B.6: multi-timescale + vol-adjusted regime features
        # Adds N features to regime_prior; each spec is (lookback_days, kind)
        # kind: "mean" = past_Nd y mean (raw); "sharpe" = mean / std (vol-adjusted)
        # Detailed stats path is JSON {day_str: {"mean": x, "std": y}}.
        recent_y_stats_path: Optional[str] = None,
        recent_y_features: Optional[list] = None,  # [(7, "mean"), (30, "mean"), (30, "sharpe"), (90, "sharpe")]
    ) -> None:
        super().__init__()
        self.data_dir = data_dir
        self.days = list(days)
        self.smooth_target = int(smooth_target)
        self.smooth_target_dir = smooth_target_dir
        self.tradeflow_dir = tradeflow_dir
        self.novel_book_dir = novel_book_dir
        self.novel_trade_dir = novel_trade_dir
        self.tv_overlay_dir = tv_overlay_dir
        # v5push Track v7 (2026-05-15)
        self.intraday_regime_dir = intraday_regime_dir
        # v5push Track v8 (2026-05-15)
        self.microprice_trajectory_dir = microprice_trajectory_dir
        # v5push: rolling y-normalize JSON {day: sigma_raw}
        self.y_rolling_sigma_path = y_rolling_sigma_path
        self._y_rolling_sigma: Optional[Dict[str, Optional[float]]] = None
        if self.y_rolling_sigma_path is not None:
            import json as _json
            with open(self.y_rolling_sigma_path, "r") as f:
                self._y_rolling_sigma = _json.load(f)
        # Time-of-day + day-of-week sin/cos features (4 channels) appended to X
        # via the extra_channels broadcast path. Mechanism: BTC perpetuals show
        # session-driven activity (US/Asia/EU) and weekend illiquidity that the
        # backbone otherwise has no way to identify from price alone.
        self.use_time2vec = bool(use_time2vec)
        # When False AND smooth_target_dir is set, inject long_context_feats
        # into X but KEEP raw y_600 as target (training + eval). Used to
        # isolate feature contribution from target smoothing confound.
        self.use_smoothed_target = bool(use_smoothed_target)

        # Phase B.2: past_30d_y_mean regime feature.
        # Loaded once at __init__; per-sample injection at _load_day.
        # Strictly causal — uses days [D - lookback, D - 1].
        self.recent_y_mean_path = recent_y_mean_path
        self.recent_y_lookback_days = int(recent_y_lookback_days)
        self._daily_y_mean: Optional[Dict[str, float]] = None
        if self.recent_y_mean_path is not None:
            import json as _json
            with open(self.recent_y_mean_path, "r") as f:
                self._daily_y_mean = _json.load(f)
            # Build sorted list of (day_str, y_mean) for efficient past lookup
            self._daily_y_mean_sorted = sorted(
                self._daily_y_mean.items(), key=lambda kv: kv[0]
            )
            # day_str → index into sorted list
            self._daily_y_mean_idx = {
                d: i for i, (d, _) in enumerate(self._daily_y_mean_sorted)
            }

        # Phase B.6 + v5push Track REG_arch_v6b (2026-05-14):
        # multi-timescale + vol-adjusted regime features.
        # recent_y_stats_path: JSON {day_str: {"mean": float, "std": float, "n": int}}
        # recent_y_features: list of (lookback_days, kind) tuples; kind ∈
        #   {"mean", "std", "sharpe", "vol_mean", "vol_std"}
        # Each tuple becomes one extra regime_prior column.
        # See _compute_past_y_stat for semantics.
        self.recent_y_stats_path = recent_y_stats_path
        self.recent_y_features = list(recent_y_features) if recent_y_features else []
        self._daily_y_stats: Optional[Dict[str, Dict]] = None
        if self.recent_y_stats_path is not None and len(self.recent_y_features) > 0:
            import json as _json
            with open(self.recent_y_stats_path, "r") as f:
                self._daily_y_stats = _json.load(f)

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

        if self._has_regime_prior and not self._has_raw:
            raise ValueError(
                "regime_prior requires X_raw to be present (V4 invariant). "
                "Re-build NPZs with raw_lob=True, or strip regime_prior from the NPZ."
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

        # --- Optional preload of all days into a single in-memory tensor.
        # When the training fold fits in container RAM (here: ~50 GB for
        # 700 days), preloading eliminates per-batch dataset I/O and lets
        # the GPU saturate. Sets self._preloaded; __getitem__ then slices
        # the global tensors directly with O(1) cost. Loaded arrays are
        # already normalised and sanitised so __getitem__ is a pure view.
        self._preloaded: bool = False
        self._pre_X: Optional[np.ndarray] = None
        self._pre_X_raw: Optional[np.ndarray] = None
        self._pre_regime_prior: Optional[np.ndarray] = None
        self._pre_y: Optional[np.ndarray] = None
        self._pre_mask: Optional[np.ndarray] = None
        if preload and self._total > 0:
            self._do_preload()
            self._preloaded = True

    def _do_preload(self) -> None:
        """Walk every day, load + normalise via _load_day, and concatenate
        into single global tensors. After this call __getitem__ does pure
        index lookups on self._pre_*."""
        x_parts: List[np.ndarray] = []
        xraw_parts: List[np.ndarray] = []
        rp_parts: List[np.ndarray] = []
        y_parts: List[np.ndarray] = []
        mask_parts: List[np.ndarray] = []
        for day_idx in range(len(self._day_paths)):
            data = self._load_day(day_idx)
            x_parts.append(data["X"])
            if self._has_raw:
                xraw_parts.append(data["X_raw"])
            if self._has_regime_prior:
                rp_parts.append(data["regime_prior"])
            y_parts.append(data["y"])
            mask_parts.append(data["mask"])
        self._pre_X = np.concatenate(x_parts, axis=0)
        if self._has_raw:
            self._pre_X_raw = np.concatenate(xraw_parts, axis=0)
        if self._has_regime_prior:
            self._pre_regime_prior = np.concatenate(rp_parts, axis=0)
        self._pre_y = np.concatenate(y_parts, axis=0)
        self._pre_mask = np.concatenate(mask_parts, axis=0)
        # Free the per-day LRU cache — preloaded tensors hold everything.
        self.clear_cache()

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

                # Phase B.2: append past_N_d y_600 mean as extra regime column.
                # Causal: uses days [D - lookback, D - 1] only; day D excluded.
                if self._daily_y_mean is not None:
                    day_str = self.days[day_idx]
                    past_mean = self._compute_past_y_mean(day_str)
                    extra_col = np.full(
                        (Rp.shape[0], 1), past_mean, dtype=np.float32
                    )
                    Rp = np.concatenate([Rp, extra_col], axis=1)

                # Phase B.6: multi-timescale + vol-adjusted regime features.
                # Each feature in recent_y_features list = one extra column.
                if self._daily_y_stats is not None and len(self.recent_y_features) > 0:
                    day_str = self.days[day_idx]
                    extra_cols = []
                    for lookback_days, kind in self.recent_y_features:
                        v = self._compute_past_y_stat(day_str, int(lookback_days), str(kind))
                        extra_cols.append(np.full((Rp.shape[0], 1), v, dtype=np.float32))
                    if extra_cols:
                        Rp = np.concatenate([Rp] + extra_cols, axis=1)

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

            # v5push: rolling causal y-normalize. Divide y by σ_day BEFORE
            # per-fold normalize so trainer sees vol-regime-invariant target.
            # Eval must denorm by σ_day for raw bps; stored in test_preds.npz
            # via the timestamps column lookup at eval time.
            if self._y_rolling_sigma is not None:
                day_str = self.days[day_idx]
                sigma_d = self._y_rolling_sigma.get(day_str)
                if sigma_d is not None and sigma_d > 1e-9:
                    y_arr = (y_arr / sigma_d).astype(np.float32)
                    y_arr = np.where(m_arr == 0, 0.0, y_arr).astype(np.float32)

            if self._y_norm is not None:
                median, sigma, clip = self._y_norm
                y_arr = np.clip(
                    (y_arr - median) / sigma, -clip, clip
                ).astype(np.float32)
                # Re-zero masked entries so they do not leak normalised offset.
                y_arr = np.where(m_arr == 0, 0.0, y_arr).astype(np.float32)

            # --- Optional overlays: long-context (+6) and tradeflow (+5) -----
            # Per-sample scalar features broadcast to all timesteps via
            # X-concat. Target smoothing (y_600_smooth) is applied only when
            # use_smoothed_target=True to keep train/val/test on a single
            # target distribution when the caller requests raw.
            # Long-context (and optional target smoothing) applies whenever
            # y_600 is one of the targets. In multi-horizon mode, target
            # smoothing touches only the y_600 slice.
            _has_y600 = (
                self._horizons is None
                or "y_600" in self._horizons
            )
            _has_y1800 = (
                self._horizons is not None and "y_1800" in self._horizons
            )
            # Index of y_600 within self._horizons (for multi-horizon smooth
            # replacement). -1 when single-horizon (we'll treat the single
            # slot as y_600).
            _y600_idx = -1
            if self._horizons is not None:
                for _k, _name in enumerate(self._horizons):
                    if _name == "y_600":
                        _y600_idx = _k
                        break
            extra_channels: List[np.ndarray] = []

            # v5push Phase 3 Track A: TIME-VARYING feature overlay.
            # Concat (N, T, K) tv_feats directly to X along channel axis BEFORE
            # extra_channels broadcast — preserves time evolution for Conformer
            # to learn dynamics. Different from constant broadcast pattern.
            # Defensive: use getattr so pickled instances from older dataset.py
            # versions (without this attribute) don't break workers.
            if getattr(self, "tv_overlay_dir", None) is not None and _has_y600:
                day_name = self.days[day_idx]
                tv_path = os.path.join(self.tv_overlay_dir, f"{day_name}.npz")
                if os.path.exists(tv_path):
                    try:
                        with _np_load_with_retry(tv_path, allow_pickle=True) as tv:
                            tv_arr = np.asarray(tv["tv_feats"], dtype=np.float32)  # (N, T, K)
                        if tv_arr.shape[0] == X.shape[0] and tv_arr.shape[1] == X.shape[1]:
                            # Per-channel median-abs scaling over all (N, T) values.
                            K = tv_arr.shape[-1]
                            flat = tv_arr.reshape(-1, K)
                            scale = np.maximum(np.median(np.abs(flat), axis=0), 1e-3)
                            tv_scaled = np.clip(tv_arr / scale, -10.0, 10.0).astype(np.float32)
                            X = np.concatenate([X, tv_scaled], axis=-1).astype(np.float32)
                    except Exception:
                        pass

            # v5push Track v7 (2026-05-15): Intraday Regime Overlay.
            # Same loader pattern as tv_overlay_dir, but a separate dir for the
            # per-timestep regime-context features (vol_1h_pct_30d, KER_1h,
            # ret_autocorr_lag10_1h, dd_24h). Concatenated to X channel axis
            # AFTER TV overlay so order is: 64 base + 14 TV + K intraday_regime.
            # Default-off: gated behind `intraday_regime_dir is not None` —
            # baseline configs without this field are bit-identical.
            if getattr(self, "intraday_regime_dir", None) is not None and _has_y600:
                day_name = self.days[day_idx]
                ir_path = os.path.join(self.intraday_regime_dir, f"{day_name}.npz")
                ir_added = False
                if os.path.exists(ir_path):
                    try:
                        with _np_load_with_retry(ir_path, allow_pickle=True) as ir:
                            ir_arr = np.asarray(ir["tv_feats"], dtype=np.float32)  # (N, T, K)
                        if ir_arr.shape[0] == X.shape[0] and ir_arr.shape[1] == X.shape[1]:
                            K = ir_arr.shape[-1]
                            flat = ir_arr.reshape(-1, K)
                            scale = np.maximum(np.median(np.abs(flat), axis=0), 1e-3)
                            ir_scaled = np.clip(ir_arr / scale, -10.0, 10.0).astype(np.float32)
                            X = np.concatenate([X, ir_scaled], axis=-1).astype(np.float32)
                            ir_added = True
                    except Exception:
                        pass
                # If overlay file missing/malformed, pad zeros so X shape stays
                # consistent across batches (collate requires same channel count).
                if not ir_added:
                    K_default = 4  # 4 intraday regime features (FEAT_NAMES len)
                    zeros = np.zeros((X.shape[0], X.shape[1], K_default), dtype=np.float32)
                    X = np.concatenate([X, zeros], axis=-1).astype(np.float32)

            # v5push Track v8 (2026-05-15): Microprice Trajectory Overlay.
            # 4 per-timestep features encoding micro-price-deviation trajectory
            # (EMA / slope / persistence / amplitude over 60s rolling). Same
            # concat-to-X pattern as intraday_regime_dir.
            if getattr(self, "microprice_trajectory_dir", None) is not None and _has_y600:
                day_name = self.days[day_idx]
                mt_path = os.path.join(self.microprice_trajectory_dir, f"{day_name}.npz")
                mt_added = False
                if os.path.exists(mt_path):
                    try:
                        with _np_load_with_retry(mt_path, allow_pickle=True) as mt:
                            mt_arr = np.asarray(mt["tv_feats"], dtype=np.float32)
                        if mt_arr.shape[0] == X.shape[0] and mt_arr.shape[1] == X.shape[1]:
                            K = mt_arr.shape[-1]
                            flat = mt_arr.reshape(-1, K)
                            scale = np.maximum(np.median(np.abs(flat), axis=0), 1e-3)
                            mt_scaled = np.clip(mt_arr / scale, -10.0, 10.0).astype(np.float32)
                            X = np.concatenate([X, mt_scaled], axis=-1).astype(np.float32)
                            mt_added = True
                    except Exception:
                        pass
                if not mt_added:
                    K_default = 4
                    zeros = np.zeros((X.shape[0], X.shape[1], K_default), dtype=np.float32)
                    X = np.concatenate([X, zeros], axis=-1).astype(np.float32)

            # Long-context overlay read: independent of horizon (y_600 path
            # uses build_smoothed_target_overlay; y_1800 path uses
            # build_long_context_overlay_y1800 which has no y_600_smooth key).
            # Target smoothing still requires y_600 + use_smoothed_target=True.
            if self.smooth_target_dir is not None and (_has_y600 or _has_y1800):
                day_name = self.days[day_idx]
                overlay_path = os.path.join(self.smooth_target_dir, f"{day_name}.npz")
                lcf_scaled_filled = np.zeros((X.shape[0], 6), dtype=np.float32)
                if os.path.exists(overlay_path):
                    try:
                        with _np_load_with_retry(overlay_path, allow_pickle=True) as ov:
                            ov_keys = set(ov.files)
                            y_smooth = (
                                np.asarray(ov["y_600_smooth"], dtype=np.float32)
                                if "y_600_smooth" in ov_keys else None
                            )
                            m_smooth = (
                                np.asarray(ov["mask_smooth"], dtype=np.float32)
                                if "mask_smooth" in ov_keys else None
                            )
                            lcf = (
                                np.asarray(ov["long_context_feats"], dtype=np.float32)
                                if "long_context_feats" in ov_keys else None
                            )
                        if (
                            self.use_smoothed_target
                            and y_smooth is not None
                            and m_smooth is not None
                            and _has_y600
                        ):
                            if self._y_norm is not None:
                                median, sigma, clip = self._y_norm
                                y_smooth = np.clip((y_smooth - median) / sigma, -clip, clip).astype(np.float32)
                            if self._horizons is None:
                                # Single-horizon (default horizon_key=y or y_600)
                                m_use = (m_smooth > 0) & (m_arr > 0)
                                y_arr = np.where(m_use, y_smooth, y_arr).astype(np.float32)
                            elif _y600_idx >= 0:
                                # Multi-horizon: replace only the y_600 slice
                                col_m = m_arr[:, _y600_idx]
                                m_use_col = (m_smooth > 0) & (col_m > 0)
                                y_arr[:, _y600_idx] = np.where(
                                    m_use_col, y_smooth, y_arr[:, _y600_idx]
                                )
                        if lcf is not None and lcf.shape[-1] == 6 and lcf.shape[0] == X.shape[0]:
                            scale = np.maximum(np.median(np.abs(lcf), axis=0), 1e-3)
                            lcf_scaled_filled = np.clip(lcf / scale, -10.0, 10.0).astype(np.float32)
                    except Exception:
                        pass
                extra_channels.append(lcf_scaled_filled)

            if self.tradeflow_dir is not None and _has_y600:
                day_name = self.days[day_idx]
                tf_path = os.path.join(self.tradeflow_dir, f"{day_name}.npz")
                tf_scaled_filled = np.zeros((X.shape[0], 5), dtype=np.float32)
                if os.path.exists(tf_path):
                    try:
                        with _np_load_with_retry(tf_path, allow_pickle=True) as tv:
                            tf = np.asarray(tv["trade_feats"], dtype=np.float32)
                        if tf.shape[-1] == 5 and tf.shape[0] == X.shape[0]:
                            scale = np.maximum(np.median(np.abs(tf), axis=0), 1e-3)
                            tf_scaled_filled = np.clip(tf / scale, -10.0, 10.0).astype(np.float32)
                    except Exception:
                        pass
                extra_channels.append(tf_scaled_filled)

            # v5push: novel book-derived overlay (16 cols) — entropy, energy, dva, qd, etc.
            if self.novel_book_dir is not None and _has_y600:
                day_name = self.days[day_idx]
                nb_path = os.path.join(self.novel_book_dir, f"{day_name}.npz")
                nb_scaled = np.zeros((X.shape[0], 16), dtype=np.float32)
                if os.path.exists(nb_path):
                    try:
                        with _np_load_with_retry(nb_path, allow_pickle=True) as nv:
                            nb = np.asarray(nv["novel_feats"], dtype=np.float32)
                        if nb.shape[-1] == 16 and nb.shape[0] == X.shape[0]:
                            scale = np.maximum(np.median(np.abs(nb), axis=0), 1e-3)
                            nb_scaled = np.clip(nb / scale, -10.0, 10.0).astype(np.float32)
                    except Exception:
                        pass
                extra_channels.append(nb_scaled)

            # v5push: novel trade-derived overlay (10 cols) — sv_ewm, apb, meta_order, abs_qty
            if self.novel_trade_dir is not None and _has_y600:
                day_name = self.days[day_idx]
                nt_path = os.path.join(self.novel_trade_dir, f"{day_name}.npz")
                nt_scaled = np.zeros((X.shape[0], 10), dtype=np.float32)
                if os.path.exists(nt_path):
                    try:
                        with _np_load_with_retry(nt_path, allow_pickle=True) as nv:
                            nt = np.asarray(nv["novel_trade_feats"], dtype=np.float32)
                        if nt.shape[-1] == 10 and nt.shape[0] == X.shape[0]:
                            scale = np.maximum(np.median(np.abs(nt), axis=0), 1e-3)
                            nt_scaled = np.clip(nt / scale, -10.0, 10.0).astype(np.float32)
                    except Exception:
                        pass
                extra_channels.append(nt_scaled)

            if self.use_time2vec:
                # Per-window timestamp lives in npz["timestamps"] as int64
                # microseconds-since-epoch. Convert to (sec_of_day, dow) and
                # encode as 4 sin/cos channels — same scale (~unit range) as
                # the other normalized X features.
                ts_us = np.asarray(npz["timestamps"], dtype=np.int64)
                ts_s = ts_us.astype(np.float64) / 1e6
                sec_of_day = np.mod(ts_s, 86400.0)
                # Day-of-week index 0..6, with 2023-01-01 (Sunday) at 0; the
                # absolute mapping does not matter — sin/cos give a smooth
                # cyclic encoding that the backbone aligns to whichever days
                # carry signal (US/Asia activity, weekend illiquidity).
                dow = np.mod(np.floor(ts_s / 86400.0) + 4.0, 7.0)
                tau_h = sec_of_day / 86400.0
                tau_w = dow / 7.0
                t2v = np.stack(
                    [
                        np.sin(2.0 * np.pi * tau_h),
                        np.cos(2.0 * np.pi * tau_h),
                        np.sin(2.0 * np.pi * tau_w),
                        np.cos(2.0 * np.pi * tau_w),
                    ],
                    axis=1,
                ).astype(np.float32)
                if t2v.shape[0] != X.shape[0]:
                    t2v = np.zeros((X.shape[0], 4), dtype=np.float32)
                extra_channels.append(t2v)

            if extra_channels:
                extra = np.concatenate(extra_channels, axis=1)  # (N, K)
                extra_broadcast = np.broadcast_to(
                    extra[:, None, :], (X.shape[0], X.shape[1], extra.shape[1])
                )
                X_aug = np.concatenate([X, extra_broadcast], axis=-1).astype(np.float32)
                data["X"] = np.ascontiguousarray(X_aug)
            elif X.shape[-1] != data["X"].shape[-1]:
                # Per-timestep overlays (TV / intraday_regime) modified local X
                # without going through extra_channels broadcast path. Sync.
                # Explicit copy to ensure contiguous writable numpy array (avoids
                # multiprocessing "storage not resizable" errors when X originates
                # from npz lazy-load memmap views).
                data["X"] = np.array(X, dtype=np.float32, copy=True)

            # Final assignment (runs whether or not overlay was applied)
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
    # Phase B.2: Past-N-day y_600 mean lookup (causal)
    # ------------------------------------------------------------------
    def _compute_past_y_mean(self, day_str: str) -> float:
        """Mean of daily y_600 means over [day - lookback, day - 1].

        Strictly causal: day_str itself is EXCLUDED. Only fully-realized
        prior days are used. If fewer than half the lookback days are
        available (e.g., near data start), return 0.0 (neutral baseline).
        """
        if self._daily_y_mean is None:
            return 0.0
        from datetime import datetime, timedelta
        try:
            day_dt = datetime.strptime(day_str, "%Y-%m-%d")
        except ValueError:
            return 0.0
        means = []
        for i in range(1, self.recent_y_lookback_days + 1):
            d = day_dt - timedelta(days=i)
            d_str = d.strftime("%Y-%m-%d")
            v = self._daily_y_mean.get(d_str)
            if v is not None:
                means.append(v)
        # Require at least half the window populated; else neutral
        if len(means) < self.recent_y_lookback_days // 2:
            return 0.0
        return float(np.mean(means))

    def _compute_past_y_stat(self, day_str: str, lookback_days: int, kind: str) -> float:
        """Aggregate past-N-day daily y_600 statistics. Strictly causal (day_str excluded).

        v5push Track REG_arch_v6b (2026-05-14): supports kinds:
          - "mean"     = mean over past N days of daily_mean
          - "std"      = std over past N days of daily_mean (regime instability)
          - "sharpe"   = mean / (std + eps) (existing Phase B.6 kind)
          - "vol_mean" = mean over past N days of daily_std (vol regime level)
          - "vol_std"  = std over past N days of daily_std (vol-of-vol regime)

        Requires self._daily_y_stats with each value being {"mean": float, "std": float, "n": int}.

        Returns neutral 0.0 if <half the lookback window is populated (early days).
        """
        if self._daily_y_stats is None:
            return 0.0
        from datetime import datetime, timedelta
        try:
            day_dt = datetime.strptime(day_str, "%Y-%m-%d")
        except ValueError:
            return 0.0
        means: list = []
        stds: list = []
        for i in range(1, int(lookback_days) + 1):
            d = day_dt - timedelta(days=i)
            d_str = d.strftime("%Y-%m-%d")
            stat = self._daily_y_stats.get(d_str)
            if stat is None:
                continue
            m = stat.get("mean")
            s = stat.get("std")
            if m is not None:
                means.append(float(m))
            if s is not None and s > 0:
                stds.append(float(s))
        if len(means) < int(lookback_days) // 2:
            return 0.0
        eps = 1e-9
        kind = str(kind).lower()
        if kind == "mean":
            return float(np.mean(means))
        if kind == "std":
            return float(np.std(means)) if len(means) >= 2 else 0.0
        if kind == "sharpe":
            mu = float(np.mean(means))
            sd = float(np.std(means)) if len(means) >= 2 else 0.0
            return mu / (sd + eps)
        if kind == "vol_mean":
            return float(np.mean(stds)) if stds else 0.0
        if kind == "vol_std":
            return float(np.std(stds)) if len(stds) >= 2 else 0.0
        # Unknown kind → neutral
        return 0.0

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

        # Fast path: when fully preloaded, slice the global tensors. No
        # disk IO, no LRU lookup, near-zero overhead per item.
        if self._preloaded:
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
            if self._has_raw:
                x_raw = torch.from_numpy(
                    np.ascontiguousarray(self._pre_X_raw[idx], dtype=np.float32)
                )
                if self._has_regime_prior:
                    rp = torch.from_numpy(
                        np.ascontiguousarray(self._pre_regime_prior[idx], dtype=np.float32)
                    )
                    return (x_feat, x_raw, rp, y_t, m_t)
                return (x_feat, x_raw, y_t, m_t)
            return (x_feat, y_t, m_t)

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
            # When horizons is a single-element list, squeeze to scalar so
            # batched (B, 1) tensors reduce to (B,). The single-horizon
            # trainer path expects (B,) targets; (B, 1) silently broadcasts
            # loss/corr incorrectly.
            if len(self._horizons) == 1:
                y_t = y_t.squeeze(-1)
                m_t = m_t.squeeze(-1)
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
    # Streaming statistics (parallel I/O — FUSE-bound on remote storage)
    # ------------------------------------------------------------------
    def _per_day_X_stats(self, day_idx: int) -> Tuple[int, np.ndarray, np.ndarray]:
        """Stream X for one day; return (n, sum, sum_sq) over the flat F axis.

        Loads ONLY the X array (not X_raw / labels / regime_prior) so the
        compute_stats pass does ~20% of the I/O of a full _load_day.
        """
        path = self._day_paths[day_idx]
        with _np_load_with_retry(path, allow_pickle=True) as npz:
            X = np.asarray(npz["X"], dtype=np.float32)
        if X.size == 0:
            return 0, np.zeros(0, dtype=np.float64), np.zeros(0, dtype=np.float64)
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        flat = X.astype(np.float64, copy=False).reshape(-1, X.shape[-1])
        return flat.shape[0], flat.sum(axis=0), (flat * flat).sum(axis=0)

    def compute_stats(self, max_workers: int = 8) -> Tuple[np.ndarray, np.ndarray]:
        """Return (mean, std) per feature by streaming through all days.

        Parallel I/O across ``max_workers`` threads — the bottleneck is
        FUSE/remote NPZ reads, not Python-level compute. 8 workers sustain
        close to the storage throughput ceiling on typical pod setups.
        """
        n_total = 0
        sum_: Optional[np.ndarray] = None
        sum_sq: Optional[np.ndarray] = None

        n_days = len(self._day_paths)
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            for n, s, sq in ex.map(self._per_day_X_stats, range(n_days)):
                if n == 0:
                    continue
                if sum_ is None:
                    F = s.shape[0]
                    sum_ = np.zeros(F, dtype=np.float64)
                    sum_sq = np.zeros(F, dtype=np.float64)
                n_total += n
                sum_ += s
                sum_sq += sq

        if n_total == 0 or sum_ is None:
            raise RuntimeError(
                "compute_stats() saw zero samples — dataset is empty or all "
                "days have zero windows."
            )

        mean = sum_ / n_total
        var = np.maximum((sum_sq / n_total) - mean * mean, 0.0)
        std = np.sqrt(var)
        return mean.astype(np.float32), std.astype(np.float32)

    def _per_day_y_valid(self, day_idx: int) -> Optional[np.ndarray]:
        """Stream y + mask for one day; return the flat array of valid entries."""
        path = self._day_paths[day_idx]
        with _np_load_with_retry(path, allow_pickle=True) as npz:
            per_key_y = [np.asarray(npz[k], dtype=np.float32) for k in self._y_keys]
            per_key_m = [np.asarray(npz[k], dtype=np.float32) for k in self._mask_keys]
        if self._horizons is not None:
            y = np.stack(per_key_y, axis=-1)
            m = np.stack(per_key_m, axis=-1)
        else:
            y = per_key_y[0]
            m = per_key_m[0]
        y = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)
        m = np.nan_to_num(m, nan=0.0, posinf=0.0, neginf=0.0)
        # v5push: rolling causal y-normalize. Apply σ_day divide so compute_y_stats
        # sees vol-normalized y → fold sigma is unit-scale (~1.0), not raw 9.5e-4.
        if self._y_rolling_sigma is not None:
            day_str = self.days[day_idx]
            sigma_d = self._y_rolling_sigma.get(day_str)
            if sigma_d is not None and sigma_d > 1e-9:
                y = (y / sigma_d).astype(np.float32)
        valid = y[m > 0]
        return valid.ravel() if valid.size else None

    def compute_y_stats(self, max_workers: int = 8) -> Tuple[float, float]:
        """Return (median, mad_sigma) over all *valid* y values.

        MAD-based sigma: ``1.4826 * MAD(y)``. I/O parallel across days;
        valid-y arrays are tiny (< 10 MB total), median/MAD runs serially
        on the concatenated result.
        """
        parts: List[np.ndarray] = []
        n_days = len(self._day_paths)
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            for valid in ex.map(self._per_day_y_valid, range(n_days)):
                if valid is not None:
                    parts.append(valid)

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
        index_stride: int = 1,
    ) -> None:
        # Validate dataset has required attrs
        if not hasattr(dataset, "_offsets") or not hasattr(dataset, "_day_paths"):
            raise TypeError(
                "DayChunkedSampler requires a dataset with _offsets and "
                "_day_paths attributes (e.g. LOBDatasetV2)"
            )
        if chunk_size < 1:
            raise ValueError(f"chunk_size must be >= 1, got {chunk_size}")
        if index_stride < 1:
            raise ValueError(f"index_stride must be >= 1, got {index_stride}")
        self.dataset = dataset
        self.chunk_size = int(chunk_size)
        self.shuffle_days = shuffle_days
        self.shuffle_within_day = shuffle_within_day
        self.seed = seed
        self.drop_last = drop_last
        self.index_stride = int(index_stride)
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

            # Gather all sample indices from this chunk of days.
            # index_stride > 1 subsamples every Nth sample WITHIN each day
            # (randomly-offset per-epoch). Used to break label overlap for
            # horizons where stride < horizon — e.g. y_600 with stride=180
            # has 70% overlap, index_stride=4 skips to ~720 s spacing =
            # non-overlapping training samples.
            chunk_indices: List[int] = []
            for d in chunk_days:
                start = int(self.dataset._offsets[d])
                end = int(self.dataset._offsets[d + 1])
                if self.index_stride > 1:
                    # Random offset in [0, index_stride) per day per epoch
                    offset = rng.randrange(self.index_stride)
                    chunk_indices.extend(range(start + offset, end, self.index_stride))
                else:
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
    embargo_days: int = 0,
) -> List[Dict[str, List[str]]]:
    """Create sliding-window cross-validation folds with strict temporal order.

    All training days come before all validation days, which come before all
    test days within each fold. Optional ``embargo_days`` inserts a buffer
    BEFORE val (between train end and val start) — used to break the
    train→val regime adjacency that drives val-overfit selection in
    non-stationary settings (anti-pattern #15 mitigation).

    Parameters
    ----------
    days : list[str]
        Chronologically sorted list of day identifiers.
    train_days : int
    val_days : int
    test_days : int
    stride : int
        How many days the window slides forward between folds.
    embargo_days : int, default 0
        Days dropped between train end and val start. Days inside the
        embargo are NOT used by any split (no train, no val, no test).

    Returns
    -------
    list[dict] of {train, val, test} day lists.
    """
    window = train_days + embargo_days + val_days + test_days
    if window > len(days):
        return []

    folds: List[Dict[str, List[str]]] = []
    start = 0
    while start + window <= len(days):
        tr_end = start + train_days
        va_start = tr_end + embargo_days
        va_end = va_start + val_days
        te_end = va_end + test_days
        folds.append(
            {
                "train": days[start:tr_end],
                "val": days[va_start:va_end],
                "test": days[va_end:te_end],
            }
        )
        start += stride

    return folds
