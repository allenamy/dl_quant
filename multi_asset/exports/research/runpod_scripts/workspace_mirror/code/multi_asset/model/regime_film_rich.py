"""RichRegimeFeatureExtractor — expanded causal regime descriptors for FiLM.

LEVER 1 of the dual-source perp push: widen the regime FiLM's feature extractor
from the proven 6 descriptors (``src/model/regime_film.py::RegimeFeatureExtractor``)
to ~14, feeding them through the SAME identity-init :class:`FiLM` mechanism that
already gave a both-regime (strong + choppy) win. The 6-feature extractor is
READ-ONLY and unchanged; this is a strict superset.

Mechanism
---------
The 6-feature extractor only sees vol at 3 scales + vol-accel + the mean/lag-60-AC
of feat0 (the OBI proxy). That gives FiLM almost no *signed-direction* or
*regime-transition* information, so its conditioning is mostly a vol gate. The
documented choppy↔strong concept drift (see MEMORY:
``choppy_y600_nonstationarity_mechanism``) is partly a SIGNED-TREND + activity
regime shift the vol-only gate cannot resolve. The added descriptors give the
identity-init FiLM more causal axes to modulate on — at NO risk, because every
added channel is (a) deterministic from x[:, :t] (causal), (b) finite-floored,
and (c) batch-z-scored at the end exactly like the parent, and the FiLM is
identity-init (γ≈1, β≈0) so an unhelpful channel simply stays un-used.

Cache-agnostic design (n_features can be 72 or 88)
--------------------------------------------------
Feature column meanings differ across caches, so — per the project rule — the
ONLY column this module ever indexes by position is column 0 (the OBI proxy,
guaranteed across every cache, same convention as the parent
``obi_feature_idx=0``). Every OTHER added descriptor is either derived from
column 0 or is an ALL-COLUMN aggregate (mean over the F axis), which is valid for
any F. No spread/depth index is ever guessed.

Output channels (n_features_out = 14), all batch-z-scored, all causal (≤ t)
---------------------------------------------------------------------------
 INHERITED 6 (identical math to the parent extractor):
   0. vol_60     — std of feat0 over last 60 steps
   1. vol_300    — std of feat0 over last 300 steps
   2. vol_1200   — std of feat0 over full window
   3. vol_accel  — vol_60 / (vol_1200 + eps)
   4. mean_feat0 — mean of feat0 over full window
   5. ac_60      — lag-60 autocorrelation of feat0
 ADDED 8 (causal, signed where noted; col-0 / all-column only):
   6. trend_fast — feat0[-1] - mean(feat0[-300:])            (signed, fast trend)
   7. trend_slow — mean(feat0[-60:]) - mean(feat0[-600:])    (signed, slow trend)
   8. vov        — std of per-block (block=100) short-window vols of feat0
                   across the window  (vol-of-vol / regime-transition)
   9. microvol   — mean |Δfeat0| over the window (micro-activity / spread proxy)
  10. microvol_s — std  |Δfeat0| over the window (micro-activity dispersion)
  11. ac_30      — lag-30  autocorrelation of feat0 (OBI persistence, short lag)
  12. ac_120     — lag-120 autocorrelation of feat0 (OBI persistence, long lag)
  13. activity_ratio — (mean |Δx| over ALL F cols, last 300 steps)
                       / (mean |Δx| over ALL F cols, full window)   (volume/
                       activity regime, all-column aggregate, ratio)

Every channel uses only ``x[:, :t]`` (the whole window ends at t — no future
leakage is possible). ``nan_to_num`` + ``eps`` floors guarantee finiteness on
short / degenerate windows.
"""
from __future__ import annotations

import torch
import torch.nn as nn

# Reuse the parent FiLM verbatim (identity-init γ≈1, β≈0) — do NOT reimplement.
from src.model.regime_film import FiLM  # noqa: F401  (re-exported for callers)


class RichRegimeFeatureExtractor(nn.Module):
    """Extract 14 deterministic, causal regime descriptors from feature tensor X.

    Drop-in superset of ``src.model.regime_film.RegimeFeatureExtractor``: the
    first 6 channels are computed with identical math; 8 causal channels are
    appended. All channels are batch-z-scored at the end (same as the parent) so
    the downstream FiLM MLP sees a consistent scale.

    Parameters
    ----------
    eps : float
        Numerical floor for divisions / std (matches the parent default).
    obi_feature_idx : int
        Column used as the "OBI proxy" for trend / vol / AC stats. Column 0 is
        the guaranteed-safe choice across every cache (same as the parent).
    """

    def __init__(self, eps: float = 1e-6, obi_feature_idx: int = 0):
        super().__init__()
        self.eps = float(eps)
        self.obi_feature_idx = int(obi_feature_idx)
        self.n_features_out = 14

    @staticmethod
    def _lag_ac(full: torch.Tensor, lag: int, eps: float) -> torch.Tensor:
        """Lag-``lag`` autocorrelation of (B, L) series ``full`` (causal).

        Returns (B,) zeros when the window is too short for the lag.
        """
        B, L = full.shape
        if L <= lag:
            return torch.zeros(B, device=full.device, dtype=full.dtype)
        f1 = full[:, lag:]
        f2 = full[:, :-lag]
        f1c = f1 - f1.mean(dim=1, keepdim=True)
        f2c = f2 - f2.mean(dim=1, keepdim=True)
        num = (f1c * f2c).mean(dim=1)
        den = f1c.std(dim=1) * f2c.std(dim=1) + eps
        return num / den

    @torch.no_grad()
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Parameters
        ----------
        x : (B, L, F) input feature tensor. Only x[:, :t] (the whole window,
            which ends at t) is ever used — strictly causal.

        Returns
        -------
        (B, 14) regime feature tensor, batch-z-scored.
        """
        B, L, F = x.shape
        eps = self.eps
        feat0 = x[:, :, self.obi_feature_idx]                          # (B, L)

        # ---------------- INHERITED 6 (identical to parent) ----------------
        last_60 = feat0[:, -min(60, L):]
        last_300 = feat0[:, -min(300, L):]
        full = feat0
        vol_60 = last_60.std(dim=1) + eps                             # (B,)
        vol_300 = last_300.std(dim=1) + eps
        vol_1200 = full.std(dim=1) + eps
        vol_accel = vol_60 / vol_1200
        mean_feat0 = full.mean(dim=1)
        ac_60 = self._lag_ac(full, 60, eps)

        # ---------------- ADDED 8 (causal) ----------------
        # 6/7. signed multi-scale trend strength.
        last_600 = feat0[:, -min(600, L):]
        trend_fast = feat0[:, -1] - last_300.mean(dim=1)              # signed
        trend_slow = last_60.mean(dim=1) - last_600.mean(dim=1)       # signed

        # 8. vol-of-vol: std across per-block short-window vols (regime transition).
        block = 100
        if L >= 2 * block:
            n_blk = L // block
            usable = n_blk * block
            # take the LAST n_blk*block steps so blocks are contiguous & causal
            blk = full[:, -usable:].reshape(B, n_blk, block)
            blk_vol = blk.std(dim=2)                                  # (B, n_blk)
            vov = blk_vol.std(dim=1)                                  # (B,)
        else:
            vov = torch.zeros(B, device=x.device, dtype=x.dtype)

        # 9/10. micro-activity (|Δfeat0|) — spread/activity proxy w/o a spread col.
        if L > 1:
            dfeat0 = (full[:, 1:] - full[:, :-1]).abs()               # (B, L-1)
            microvol = dfeat0.mean(dim=1)
            microvol_s = dfeat0.std(dim=1)
        else:
            microvol = torch.zeros(B, device=x.device, dtype=x.dtype)
            microvol_s = torch.zeros(B, device=x.device, dtype=x.dtype)

        # 11/12. OBI persistence at extra lags.
        ac_30 = self._lag_ac(full, 30, eps)
        ac_120 = self._lag_ac(full, 120, eps)

        # 13. activity regime: all-column mean |Δx| recent vs full-window ratio.
        if L > 1:
            dx_all = (x[:, 1:, :] - x[:, :-1, :]).abs()               # (B, L-1, F)
            act_full = dx_all.mean(dim=(1, 2))                        # (B,)
            w = min(300, L - 1)
            act_recent = dx_all[:, -w:, :].mean(dim=(1, 2))           # (B,)
            activity_ratio = act_recent / (act_full + eps)
        else:
            activity_ratio = torch.ones(B, device=x.device, dtype=x.dtype)

        feats = torch.stack(
            [vol_60, vol_300, vol_1200, vol_accel, mean_feat0, ac_60,
             trend_fast, trend_slow, vov, microvol, microvol_s,
             ac_30, ac_120, activity_ratio],
            dim=-1,
        )                                                            # (B, 14)

        # Guard against NaN/Inf from degenerate windows before z-scoring.
        feats = torch.nan_to_num(feats, nan=0.0, posinf=0.0, neginf=0.0)

        # Batch-z-score for stable MLP input (identical to the parent).
        m = feats.mean(dim=0, keepdim=True)
        s = feats.std(dim=0, keepdim=True) + eps
        out = (feats - m) / s
        return torch.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0)
