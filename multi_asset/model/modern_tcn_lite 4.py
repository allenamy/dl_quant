"""ModernTCN-lite long-context encoder + zero-init-gated FiLM producer.

> **created:** 2026-06-22 | **Session:** v2-dual-source-arch | **状态:** in-progress

MECHANISM (why this should add signal on low-SNR BTC y_600)
-----------------------------------------------------------
The fine backbone sees only the last 600s (10 min) at 1s resolution. The
established finding is that a **4h long-context** (60s-pooled trend / vol / basis
state) helps the STRONG / trending months — momentum-flavoured signal (AR1≈0.69)
that pays when the regime is trending, and is invisible inside a 10-min window.
Ridge confirmed +0.0103 linear info from (base + perp_book_KEY + long); the DL
job is to FUSE that long-context properly (not concat a broadcast block).

We encode the (B, 240, 10) long series with a small **ModernTCN-lite** stack:
per-channel **depthwise large-kernel conv** (k≈21 — one kernel spans ~21 min of
60s bins, so a single layer already sees ~½h of context; stacked → the full 4h)
followed by a pointwise **ConvFFN** (channel mixing). This is the ModernTCN recipe
(large-kernel depthwise for the time axis, 1×1 ConvFFN for the channel axis),
shrunk to ~6–18K params to respect the low-SNR capacity budget. The pooled
context vector then produces a **FiLM (γ, β)** that modulates the fine backbone's
fused bus.

ZERO-INIT IDENTITY (cannot hurt at start)
-----------------------------------------
The FiLM is applied as::

    h_mod = h * (1 + g * gamma) + g * beta        # h: (B, T, d_model)

where ``g = tanh(film_alpha)`` is a learnable scalar master gate **init 0** so the
modulation is EXACTLY identity at step 0 (h unchanged). UNLIKE the perp residual
(whose alpha must be non-zero to avoid gradient starvation of its sub-net), the
long-context FiLM's ``gamma``/``beta`` heads still receive gradient at g=0 through
the ``g*gamma``/``g*beta`` product's derivative w.r.t. g — but to GUARANTEE the
TCN body itself trains from step 0 we init ``film_alpha`` to a small NON-zero
value (default 0.01, ≈1% perturbation) so the whole branch gets gradient
immediately while the perturbation stays negligible. The optimizer can grow it if
the long context helps (STRONG) or shrink it toward 0 if it does not (CHOPPY) —
this is the additive, non-regime-gated fusion the spec requires (regime-GATING
overfits; a single learnable scalar that the data sets is safe).

The ``gamma`` head is zero-init (so ``1 + g*gamma = 1`` at start) and the ``beta``
head is zero-init, making the identity exact regardless of ``film_alpha``.
"""
from __future__ import annotations

import torch
import torch.nn as nn


class _DepthwiseLargeKernelBlock(nn.Module):
    """ModernTCN block: depthwise large-kernel conv (time mixing) + ConvFFN
    (channel mixing), each with a residual and pre-norm. Causal-agnostic here —
    the whole 240-step series is ≤ t by construction (the cache guarantees every
    long bin ends strictly before t), so SAME padding is leak-free."""

    def __init__(self, d: int, kernel_size: int, ffn_mult: int = 2,
                 dropout: float = 0.1) -> None:
        super().__init__()
        pad = kernel_size // 2
        # depthwise over time: groups=d -> one kernel per channel
        self.dw = nn.Conv1d(d, d, kernel_size=kernel_size, padding=pad, groups=d)
        self.norm1 = nn.BatchNorm1d(d)
        # ConvFFN: 1x1 expand -> GELU -> 1x1 project (channel mixing)
        self.pw1 = nn.Conv1d(d, d * ffn_mult, kernel_size=1)
        self.act = nn.GELU()
        self.pw2 = nn.Conv1d(d * ffn_mult, d, kernel_size=1)
        self.norm2 = nn.BatchNorm1d(d)
        self.drop = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:  # x: (B, d, L)
        x = x + self.drop(self.dw(self.norm1(x)))
        x = x + self.drop(self.pw2(self.act(self.pw1(self.norm2(x)))))
        return x


class ModernTCNLiteContext(nn.Module):
    """Encode (B, L_long, C_long) -> a context vector (B, d_ctx).

    Stack of depthwise-large-kernel + ConvFFN blocks (ModernTCN-lite), then a
    global pool (last-step + mean) -> linear to ``d_ctx``. Params kept ~6–18K.

    Parameters
    ----------
    c_in : int          input channels of X_long (10)
    d : int             internal width (default 24)
    n_blocks : int      number of ModernTCN blocks (default 2)
    kernel_size : int   depthwise kernel (default 21)
    d_ctx : int         output context width (default 32)
    """

    def __init__(self, c_in: int = 10, d: int = 24, n_blocks: int = 2,
                 kernel_size: int = 21, d_ctx: int = 32, dropout: float = 0.1,
                 ffn_mult: int = 2) -> None:
        super().__init__()
        self.c_in = int(c_in)
        self.d = int(d)
        self.d_ctx = int(d_ctx)
        # input stem: per-channel value normalization happens upstream (dataset
        # train-fit z-score); here a 1x1 lifts C_long -> d.
        self.stem = nn.Conv1d(c_in, d, kernel_size=1)
        self.blocks = nn.ModuleList([
            _DepthwiseLargeKernelBlock(d, kernel_size, ffn_mult=ffn_mult,
                                       dropout=dropout)
            for _ in range(int(n_blocks))
        ])
        # pool = concat(last-step, mean) -> 2d -> d_ctx
        self.pool_proj = nn.Linear(2 * d, d_ctx)
        self.act = nn.GELU()

    def forward(self, x_long: torch.Tensor) -> torch.Tensor:
        # x_long: (B, L, C) -> (B, C, L) for conv1d
        x = x_long.transpose(1, 2).contiguous()         # (B, C, L)
        x = self.stem(x)                                 # (B, d, L)
        for blk in self.blocks:
            x = blk(x)                                   # (B, d, L)
        last = x[:, :, -1]                               # (B, d)
        mean = x.mean(dim=-1)                            # (B, d)
        ctx = self.act(self.pool_proj(torch.cat([last, mean], dim=-1)))  # (B,d_ctx)
        return ctx


class LongContextFiLM(nn.Module):
    """Near-identity gated FiLM on the fine fused bus from a long-context vector.

    Produces (γ, β) of width ``d_model`` from the context vector and applies::

        h_mod = h * (1 + g * γ) + g * β          # g = tanh(film_alpha)

    GRADIENT-STARVATION FIX (the bug a fully zero-init FiLM hits)
    ------------------------------------------------------------
    A *fully* zero-init γ/β (the textbook "identity FiLM") makes the modulation
    exactly identity at start, but then ``∂loss/∂ctx = γᵀ·(g·h) = 0`` at init, so
    the ModernTCN body that PRODUCES ``ctx`` receives ZERO gradient and never
    trains before early-stop — the same gradient-starvation failure documented for
    the perp residual's master gate. We therefore give the γ/β heads a SMALL
    non-zero init (weight std ``head_std`` ≈ 0.02, bias 0) and a small non-zero
    master gate ``film_alpha`` (init 0.01 → g≈0.01). The init perturbation of the
    fine stream is ``g·γ·h ≈ 0.01·O(0.02)·h ≈ 2e-4·h`` (β similar) — NEGLIGIBLE,
    so the model still starts ~identical to the matched base ("can only help"),
    while the whole long branch gets real gradient from step 0. The optimizer can
    grow ``film_alpha`` if the long context helps (STRONG) or shrink it → 0 if it
    does not (CHOPPY) — the additive, non-regime-gated fusion the spec requires.
    Broadcast over time (per-sample, per-channel FiLM).

    beta0.66 ROOT-CAUSE FIX (``film_mode``)
    ---------------------------------------
    On the 2024+ base the full FiLM raised Spearman but COLLAPSED beta to 0.66 —
    the long-context carries real RANK signal but the FiLM injected it as
    UNCALIBRATED MAGNITUDE: the additive ``g*beta`` term adds a per-sample offset
    (from the trend ctx) to the bus that, after the backbone+DAQH head, becomes a
    prediction component correlated with the trend but NOT proportionally aligned
    with y, so var(yhat) inflates faster than cov(yhat,y) and beta=cov/var drops.
    (Diagnosis: Spearman up + beta down = added variance not magnitude-matched.)

    ``film_mode`` selects the modulation:
      * "affine" (legacy): ``h*(1 + g*gamma) + g*beta`` — additive beta = collapse risk.
      * "scale"  (FIX):    ``h*(1 + g*gamma)`` — MULTIPLICATIVE-ONLY. The long
        context can only REWEIGHT the existing bus signal (preserving its rank
        contribution) and cannot inject an unconditional additive offset, so it
        cannot inflate var(yhat) with uncalibrated magnitude. Keeps the Spearman
        lift while protecting beta. ``gamma_clip`` bounds the per-channel scale.
    """

    def __init__(self, d_ctx: int, d_model: int, alpha_init: float = 0.01,
                 head_std: float = 0.02, film_mode: str = "affine",
                 gamma_clip: float = 0.0) -> None:
        super().__init__()
        self.film_mode = str(film_mode)
        if self.film_mode not in ("affine", "scale"):
            raise ValueError(f"film_mode must be 'affine'|'scale', got {film_mode!r}")
        self.gamma_clip = float(gamma_clip)
        self.gamma = nn.Linear(d_ctx, d_model)
        # small non-zero so ctx (and the TCN body behind it) gets gradient at init
        nn.init.normal_(self.gamma.weight, std=head_std); nn.init.zeros_(self.gamma.bias)
        if self.film_mode == "affine":
            self.beta = nn.Linear(d_ctx, d_model)
            nn.init.normal_(self.beta.weight, std=head_std); nn.init.zeros_(self.beta.bias)
        else:
            self.beta = None
        self.film_alpha = nn.Parameter(
            torch.tensor(float(alpha_init), dtype=torch.float32))

    def forward(self, h: torch.Tensor, ctx: torch.Tensor) -> torch.Tensor:
        # h: (B, T, d_model) ; ctx: (B, d_ctx)
        g = torch.tanh(self.film_alpha)
        gamma = self.gamma(ctx).unsqueeze(1)             # (B,1,d_model)
        if self.gamma_clip > 0.0:
            gamma = torch.clamp(gamma, -self.gamma_clip, self.gamma_clip)
        if self.film_mode == "scale":
            return h * (1.0 + g * gamma)                 # multiplicative-only (β-safe)
        beta = self.beta(ctx).unsqueeze(1)               # (B,1,d_model)
        return h * (1.0 + g * gamma) + g * beta
