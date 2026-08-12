"""MaskNet: Instance-Guided Mask for per-sample noise suppression.

Reference: Wang et al., "MaskNet: Introducing Feature-Level Mask to
CTR Prediction", DLP-KDD 2021 (Twitter/X production).
arXiv: 2102.07619

Architecture (serial mode):
    input -> MaskBlock_1 -> MaskBlock_2 -> ... -> output

Each MaskBlock generates a per-instance sigmoid mask that gates which
input dimensions are informative for THIS sample, suppressing noisy
dimensions element-wise.  This is critical for low-SNR financial data
where different samples have different informative features.

Causality (important for LOB / time-series use)
-----------------------------------------------
When operating on 3D input ``(B, L, d_input)``, the original MaskNet
formulation would pool across the FULL sequence to build a single
"instance-level" summary that gates every timestep identically.  In
forecasting settings where the model extracts its prediction from a
non-terminal timestep (e.g. ``pred_step=150`` on an L=300 window),
this leaks **future** information into the mask at past positions.

This implementation defaults to a **causal cumulative mean**: the mask
at time *t* is produced from ``x[:, :t+1, :].mean(dim=1)``, so position
*t* sees only its own past.  When the caller always reads the last
timestep (``pred_step=-1``) the causal cumulative mean at *t=L-1* is
identical to a mean over the full window -- so this change is a pure
strengthening that preserves backwards compatibility for the dominant
use case and FIXES the leakage for non-terminal prediction.

Set ``causal=False`` to recover the exact legacy behavior (full-window
mean) if you need it for reproducing old experiments.
"""

from __future__ import annotations

import torch
import torch.nn as nn


class MaskBlock(nn.Module):
    """Instance-Guided Mask Block.

    For each input instance, generates a dynamic mask that element-wise
    gates both the input and the hidden layer.  This suppresses noisy
    dimensions on a per-sample basis.

    Architecture::

        input -> LayerNorm -> [instance_mask * input] -> FFN -> output
        instance_mask = sigmoid(Linear(LayerNorm(summary(input))))

    where ``summary`` is a causal cumulative mean over time for 3D inputs
    (see module docstring).  For 2D inputs ``summary`` is the identity.

    Parameters
    ----------
    d_input : int
        Input (and output) dimension.
    d_hidden : int
        Hidden dimension of the internal FFN.
    dropout : float
        Dropout probability inside the FFN.
    causal : bool
        For 3D inputs, if True (default) the mask at time *t* uses only
        timesteps ``0..t``; if False, uses the full-window mean (legacy
        behavior, leaks future into past when ``pred_step != -1``).
    """

    def __init__(
        self,
        d_input: int,
        d_hidden: int,
        dropout: float = 0.1,
        causal: bool = True,
    ):
        super().__init__()
        self.causal = causal
        # Mask generator: from input -> per-dimension mask
        self.mask_net = nn.Sequential(
            nn.LayerNorm(d_input),
            nn.Linear(d_input, d_input),
            nn.Sigmoid(),
        )
        # FFN with residual
        self.norm = nn.LayerNorm(d_input)
        self.ffn = nn.Sequential(
            nn.Linear(d_input, d_hidden),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_hidden, d_input),
            nn.Dropout(dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass.

        Parameters
        ----------
        x : torch.Tensor
            Shape ``(B, d_input)`` or ``(B, L, d_input)``.

        Returns
        -------
        torch.Tensor
            Same shape as input, with residual connection.

        Notes
        -----
        For 3D input ``(B, L, d_input)`` with ``causal=True`` (default),
        the mask at time *t* is produced from the cumulative mean over
        ``x[:, :t+1, :]``, so each timestep receives a (different) mask
        derived only from its own past.  At ``t = L-1`` this matches the
        full-window mean, so reading the last timestep (``pred_step=-1``)
        is equivalent to the legacy behavior.
        """
        if x.dim() == 3:
            if self.causal:
                # Causal cumulative mean: at time t, summary uses x[0..t]
                # x: (B, L, d)
                cumsum = x.cumsum(dim=1)                                  # (B, L, d)
                counts = torch.arange(
                    1, x.size(1) + 1, device=x.device, dtype=x.dtype,
                ).view(1, -1, 1)                                          # (1, L, 1)
                x_summary = cumsum / counts                               # (B, L, d)
                mask = self.mask_net(x_summary)                           # (B, L, d)
            else:
                # Legacy: full-window mean -> single mask broadcast over L
                x_summary = x.mean(dim=1, keepdim=True)                   # (B, 1, d)
                mask = self.mask_net(x_summary)                           # (B, 1, d)
        else:
            mask = self.mask_net(x)                                       # (B, d)
        h = self.norm(x * mask)       # masked + normalized
        return x + self.ffn(h)        # residual connection


class MaskNet(nn.Module):
    """Stack of MaskBlocks for progressive noise suppression (serial mode).

    Each MaskBlock refines the representation from the previous one,
    progressively filtering out noise while preserving signal.

    Parameters
    ----------
    d_input : int
        Input (and output) dimension.
    d_hidden : int
        Hidden dimension of the FFN inside each MaskBlock.
    n_blocks : int
        Number of serial MaskBlocks.
    dropout : float
        Dropout probability.
    causal : bool
        Forwarded to each MaskBlock (default True).
    """

    def __init__(
        self,
        d_input: int,
        d_hidden: int,
        n_blocks: int = 2,
        dropout: float = 0.1,
        causal: bool = True,
    ):
        super().__init__()
        self.blocks = nn.ModuleList([
            MaskBlock(d_input, d_hidden, dropout=dropout, causal=causal)
            for _ in range(n_blocks)
        ])

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass through serial MaskBlocks.

        Parameters
        ----------
        x : torch.Tensor
            Shape ``(B, d_input)`` or ``(B, L, d_input)``.

        Returns
        -------
        torch.Tensor
            Same shape as input.
        """
        for block in self.blocks:
            x = block(x)
        return x
