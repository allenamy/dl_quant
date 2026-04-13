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
        instance_mask = sigmoid(Linear(LayerNorm(input)))

    The mask is generated from each instance independently, so it
    captures which dimensions are informative for THIS sample.

    Parameters
    ----------
    d_input : int
        Input (and output) dimension.
    d_hidden : int
        Hidden dimension of the internal FFN.
    dropout : float
        Dropout probability inside the FFN.
    """

    def __init__(self, d_input: int, d_hidden: int, dropout: float = 0.1):
        super().__init__()
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
        For 3D input ``(B, L, d_input)``, the mask is generated from the
        mean across the time dimension (instance-level summary), producing
        a ``(B, 1, d_input)`` mask that broadcasts across all timesteps.
        This is the correct "instance-guided" behavior per the MaskNet
        paper: for THIS market window, these dimensions are informative.
        The mask does not create temporal information flow since all
        timesteps receive the same scaling.
        """
        if x.dim() == 3:
            # Instance-level: use mean across time dimension as summary
            x_summary = x.mean(dim=1, keepdim=True)  # (B, 1, d)
            mask = self.mask_net(x_summary)            # (B, 1, d) — broadcast across L
        else:
            mask = self.mask_net(x)                    # (B, d) — 2D case unchanged
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
    """

    def __init__(
        self,
        d_input: int,
        d_hidden: int,
        n_blocks: int = 2,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.blocks = nn.ModuleList([
            MaskBlock(d_input, d_hidden, dropout=dropout)
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
