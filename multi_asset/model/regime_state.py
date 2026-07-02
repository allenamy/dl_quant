"""Fixed regime-conditioning substrate (D1, Stage-0B).

The production regime-FiLM path has two STRUCTURAL bugs that made every prior
"regime not learnable" verdict untrustworthy (Phase-1 FLAGS 1/2, appendix gaps
#1/#2):

  1. The descriptor extractor (``src/model/regime_film.py::RegimeFeatureExtractor``)
     runs on the **post-RevIN** ``x_feat``.  RevIN normalises each window's
     variance to ~1, so ``vol_1200 ≈ const`` and ``mean_feat0 ≈ 0`` — the
     ABSOLUTE volatility level (the thing that distinguishes a strong month from
     a drift month) is destroyed BEFORE the gate ever sees it.
  2. It **batch-z-scores** its 6 descriptors (``regime_film.py:98-101``), so the
     regime is measured RELATIVE TO THE CURRENT BATCH.  A uniformly-shifted
     regime month is invisible at eval, and — a latent correctness bug —
     predictions become batch-composition dependent.

This module re-implements the extractor WITHOUT touching ``src/``:

  * :class:`PreRevINRegimeExtractor` — the SAME 6 descriptors, but computed on
    the **pre-RevIN** tensor (which is ``post-static-450d-z``: cross-fold
    comparable AND regime-level-preserving) and returned RAW (no batch-z).
  * The batch-z is replaced downstream by TRAIN-WINDOW frozen stats
    (:func:`normalize_frozen`), registered as model buffers so they persist in
    the checkpoint and are NEVER recomputed at eval.

The consuming FiLM / normalisation wiring lives in
``multi_asset/model/dual_lob_regarch.py`` behind the ``use_fixed_regime_state``
flag; this file only provides the descriptor maths + a CPU pre-gate helper.
"""
from __future__ import annotations

from typing import Optional

import torch
import torch.nn as nn


class PreRevINRegimeExtractor(nn.Module):
    """Deterministic 6-descriptor regime extractor, RAW (no batch-z).

    Bit-for-bit the same six statistics as
    ``src/model/regime_film.py::RegimeFeatureExtractor`` (so a fold trained with
    the fixed substrate is directly comparable to the bugged baseline), EXCEPT:

      * it does NOT batch-z-score the output (the caller applies frozen
        train-window normalisation instead), and
      * it is meant to be fed the **pre-RevIN** ``x_feat`` (the caller stashes
        that tensor before ``revin.normalize``).

    Output columns (all per-batch-element, from ``x[:, :, obi_feature_idx]``):
      0. realized vol over last 60 steps      (60s scale)
      1. realized vol over last 300 steps     (5min scale)
      2. realized vol over the full window    (window scale)
      3. vol acceleration  vol_60 / vol_full
      4. mean of feature[0] over the window
      5. lag-60 autocorrelation of feature[0]

    All ops are non-learnable statistics under ``no_grad`` (the FiLM MLP is the
    only trainable part downstream).
    """

    def __init__(self, eps: float = 1e-6, obi_feature_idx: int = 0):
        super().__init__()
        self.eps = float(eps)
        self.obi_feature_idx = int(obi_feature_idx)
        self.n_features_out = 6

    @torch.no_grad()
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """``x`` (B, L, F) pre-RevIN -> (B, 6) RAW descriptors."""
        B, L, _ = x.shape
        feat0 = x[:, :, self.obi_feature_idx]                    # (B, L)
        last_60 = feat0[:, -min(60, L):]
        last_300 = feat0[:, -min(300, L):]
        full = feat0
        vol_60 = last_60.std(dim=1) + self.eps                   # (B,)
        vol_300 = last_300.std(dim=1) + self.eps
        vol_full = full.std(dim=1) + self.eps
        vol_accel = vol_60 / vol_full
        mean_feat0 = full.mean(dim=1)
        if L > 60:
            f1 = full[:, 60:]
            f2 = full[:, :-60]
            f1c = f1 - f1.mean(dim=1, keepdim=True)
            f2c = f2 - f2.mean(dim=1, keepdim=True)
            num = (f1c * f2c).mean(dim=1)
            den = f1c.std(dim=1) * f2c.std(dim=1) + self.eps
            ac1 = num / den
        else:
            ac1 = torch.zeros(B, device=x.device, dtype=x.dtype)
        # RAW — no batch-z (the FLAG-2 fix moves normalisation to frozen stats).
        return torch.stack(
            [vol_60, vol_300, vol_full, vol_accel, mean_feat0, ac1], dim=-1)


def normalize_frozen(feats: torch.Tensor, mean: torch.Tensor, std: torch.Tensor,
                     clip: float = 5.0) -> torch.Tensor:
    """``(f - mean) / std`` clipped to ``±clip`` using FROZEN buffers.

    ``mean`` / ``std`` are train-window statistics registered as model buffers
    (persisted in the checkpoint) — the FLAG-2 fix: regime is measured against a
    fixed reference, not the current batch, so a uniformly-shifted regime month
    is visible at eval and predictions are batch-composition invariant.
    """
    return torch.clamp((feats - mean) / std, -float(clip), float(clip))


@torch.no_grad()
def compute_window_stats(values: torch.Tensor, eps: float = 1e-6):
    """Column-wise mean/std over a (N, K) tensor. Returns (mean(K,), std(K,))."""
    mean = values.mean(dim=0)
    std = values.std(dim=0).clamp_min(eps)
    return mean, std


# --------------------------------------------------------------------------- #
# CPU PRE-GATE — do the fixed descriptors separate regimes across months?      #
# --------------------------------------------------------------------------- #
def descriptor_month_separation(desc_a: torch.Tensor, desc_b: torch.Tensor):
    """Per-descriptor inter-month separation test (D1 CPU pre-gate).

    A descriptor "separates" months ``a`` and ``b`` when the gap between their
    means exceeds the pooled within-month dispersion::

        |mean_a - mean_b| > 1 * sqrt((std_a^2 + std_b^2) / 2)

    Parameters
    ----------
    desc_a, desc_b : (N_a, K) / (N_b, K) raw descriptors for two months.

    Returns
    -------
    dict with per-descriptor mean_a/mean_b/std_a/std_b/spread/within_sigma/pass
    and the count of separating descriptors.  The pre-gate PASSES when
    ``n_pass >= 3`` of the 6.
    """
    ma, sa = compute_window_stats(desc_a)
    mb, sb = compute_window_stats(desc_b)
    spread = (ma - mb).abs()
    within = torch.sqrt((sa ** 2 + sb ** 2) / 2.0).clamp_min(1e-12)
    passed = spread > within
    return {
        "mean_a": ma, "mean_b": mb, "std_a": sa, "std_b": sb,
        "spread": spread, "within_sigma": within,
        "pass_per_desc": passed, "n_pass": int(passed.sum().item()),
    }
