"""H1-aligned TRAINING-DISTRIBUTION arm helpers (Phase-2 D6 choppy-specialist + D2 tail-weight).

Two evidence-backed drift levers, implemented as pure helpers so the trainer (0A's
train_dual_lob.py) wires them in a few lines. Neither touches the loss math (anti-patterns
#20/#21 safe: pinball anchor + dul_config unchanged).

ARM A — CHOPPY-SPECIALIST day-filter (replicates the only weak-regime WIN 0.0167->0.0311 OOS).
  Keep only LOW-TREND (choppy) TRAIN days. Trendiness = Kaufman efficiency ratio on the day's
  NON-OVERLAPPING y_600 increments: ER = |sum(r)| / sum(|r|)  (0 = pure chop, 1 = pure trend).
  Threshold is computed on TRAIN days ONLY (causal by construction) and the TEST month is never
  filtered (full-month deploy eval). This is a DAY-LEVEL filter: pass the kept-day subset to the
  train Dataset; val/test stay full (D6: checkpoint selection on ALL-day val — no matched-val
  inflation).

ARM B — TAIL-WEIGHTED training (H1: 100% of drift signal lives in top-quintile |y|; stop spending
  capacity ranking the noisy 80%). Per-sample weight w = 1 + k * 1{|y_norm| >= train top-quintile},
  k pre-registered = 2.0. Implemented as WeightedRandomSampler weights over the train set (a
  dataset-side reweight; the dul_config losses are UNCHANGED). Threshold from TRAIN |y_norm| only.

Both levers are strictly train-side; the deployed model is a single unconditional predictor.
"""
from __future__ import annotations
import numpy as np

DAY_US = 86_400_000_000
HZ_US = 600_000_000            # y_600 horizon -> 600s non-overlap spacing


def _nonoverlap_idx(ts_us: np.ndarray, gap_us: int = HZ_US) -> np.ndarray:
    """Greedy >=gap non-overlap subsample (same rule as the per-day-CLEAN caliber)."""
    o = np.argsort(ts_us); keep = []; last = -(1 << 62)
    for i in o:
        if ts_us[i] - last >= gap_us:
            keep.append(i); last = ts_us[i]
    return np.array(keep, dtype=int)


def _daily_er(y: np.ndarray, ts_us: np.ndarray) -> float:
    """Kaufman efficiency ratio on non-overlapping daily y increments. NaN-safe; -1 if empty."""
    k = _nonoverlap_idx(ts_us)
    if len(k) < 3:
        return -1.0
    r = y[k].astype(np.float64)
    denom = np.sum(np.abs(r))
    return float(abs(np.sum(r)) / denom) if denom > 1e-12 else -1.0


def compute_daily_er(npz_dir: str, days: list[str],
                     y_key: str = "y_600", mask_key: str = "y_mask_600",
                     ts_key: str = "timestamps") -> dict[str, float]:
    """Per-day efficiency ratio from the cache y-series (valid rows only). days = cache stems."""
    import os
    er: dict[str, float] = {}
    for d in days:
        fp = os.path.join(npz_dir, f"{d}.npz")
        if not os.path.exists(fp):
            er[d] = -1.0; continue
        z = np.load(fp, allow_pickle=True)
        y = np.asarray(z[y_key]).reshape(-1).astype(np.float64)
        ts = np.asarray(z[ts_key]).reshape(-1).astype(np.int64)
        if mask_key in z.files:
            m = np.asarray(z[mask_key]).reshape(len(y)).astype(bool)
        else:
            m = np.ones(len(y), bool)
        v = m & np.isfinite(y)
        er[d] = _daily_er(y[v], ts[v]) if v.sum() >= 3 else -1.0
    return er


def choppy_filter_days(npz_dir: str, train_days: list[str], quantile: float = 0.5,
                       **npz_keys) -> tuple[list[str], dict]:
    """Keep the LOW-TREND (choppy) train days: ER <= train-quantile threshold.
    quantile 0.5 = keep the choppier half; 0.34 = keep the choppiest third (D6 low-tercile).
    Returns (kept_days, stats). Days with too few rows (er<0) are dropped from BOTH the
    threshold estimate and the kept set."""
    er = compute_daily_er(npz_dir, train_days, **npz_keys)
    valid = [d for d in train_days if er[d] >= 0.0]
    vals = np.array([er[d] for d in valid])
    thr = float(np.quantile(vals, quantile)) if len(vals) else 0.0
    kept = [d for d in valid if er[d] <= thr]
    stats = {"n_in": len(train_days), "n_valid": len(valid), "n_kept": len(kept),
             "quantile": quantile, "threshold": thr,
             "er_min": float(vals.min()) if len(vals) else float("nan"),
             "er_median": float(np.median(vals)) if len(vals) else float("nan"),
             "er_max": float(vals.max()) if len(vals) else float("nan")}
    return kept, stats


def tail_sample_weights(y_norm: np.ndarray, mask: np.ndarray | None = None,
                        k: float = 2.0, quantile: float = 0.8) -> tuple[np.ndarray, float]:
    """Per-sample WeightedRandomSampler weights: w = 1 + k*1{|y_norm| >= train top-quintile}.
    Threshold from VALID train samples only; masked/padded samples get weight 0 (never drawn).
    y_norm: (N,) or (N,H) normalized targets (use the trained horizon column). k pre-reg 2.0."""
    y = np.asarray(y_norm, dtype=np.float64)
    ay = np.abs(y[:, -1] if y.ndim > 1 else y)          # primary horizon = last column
    n = len(ay)
    if mask is None:
        valid = np.isfinite(ay)
    else:
        mm = np.asarray(mask)
        mm = mm[:, -1] if mm.ndim > 1 else mm
        valid = (mm > 0) & np.isfinite(ay)
    thr = float(np.quantile(ay[valid], quantile)) if valid.any() else float("inf")
    w = np.zeros(n, dtype=np.float64)
    w[valid] = 1.0 + k * (ay[valid] >= thr).astype(np.float64)
    return w, thr
