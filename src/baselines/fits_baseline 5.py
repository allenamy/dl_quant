"""FITS: Frequency Interpolation Time Series model.

Simplified implementation of the FITS architecture from:
    Xu et al., "FITS: Modeling Time Series with 10k Parameters", ICLR 2024 Spotlight.

The key insight is that operating in the frequency domain provides built-in
denoising (via low-pass filtering) and a compact representation of temporal
patterns. This is especially valuable in low-SNR regimes like LOB prediction
where high-frequency components are predominantly noise.

Architecture:
    Input (B, L, F)
    -> Feature compression: Linear(F, d_compress)         # bottleneck
    -> rFFT along time dim -> (B, L//2+1, d_compress)    # frequency domain
    -> Low-pass: keep first cut_freq bins                 # denoise
    -> Flatten + concat real/imag                         # (B, cut_freq*d_compress*2)
    -> Linear -> GELU -> Dropout                          # learn freq patterns
    -> Linear -> quantile predictions                     # output head

Total params ~ F*d_compress + cut_freq*d_compress*2*d_hidden + d_hidden*n_quantiles
             ~ 44*8 + 50*8*2*32 + 32*3 = 352 + 25600 + 96 ~ 26K
"""

from __future__ import annotations

import torch
import torch.nn as nn


class FITSModel(nn.Module):
    """Frequency Interpolation Time Series model.

    Operates in frequency domain: compress -> rFFT -> low-pass -> linear -> head.
    ~26K params with default settings. Built-in denoising via low-pass filter.

    Parameters
    ----------
    n_features : int
        Number of input features per timestep.
    seq_len : int
        Length of the input time series (default 300).
    cut_freq : int
        Number of low-frequency components to keep (default 50).
        The rFFT of length L produces L//2+1 bins; we keep only the
        first cut_freq, discarding high-frequency noise.
    d_compress : int
        Feature compression dimension (default 8). Reduces F features
        to d_compress before frequency transform, keeping param count low.
    d_hidden : int
        Hidden dimension for the frequency-domain MLP (default 32).
    n_quantiles : int
        Number of quantile outputs (default 3 for q10/q50/q90).
    dropout : float
        Dropout rate (default 0.1).
    """

    def __init__(
        self,
        n_features: int,
        seq_len: int = 300,
        cut_freq: int = 50,
        d_compress: int = 8,
        d_hidden: int = 32,
        n_quantiles: int = 3,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()

        self.n_features = n_features
        self.seq_len = seq_len
        self.cut_freq = cut_freq
        self.d_compress = d_compress
        self.d_hidden = d_hidden
        self.n_quantiles = n_quantiles

        # Validate cut_freq against the number of frequency bins
        n_freq_bins = seq_len // 2 + 1
        if cut_freq > n_freq_bins:
            raise ValueError(
                f"cut_freq ({cut_freq}) exceeds number of frequency bins "
                f"({n_freq_bins}) for seq_len={seq_len}"
            )

        # Feature compression: (B, L, F) -> (B, L, d_compress)
        self.feature_compress = nn.Linear(n_features, d_compress)

        # Frequency-domain MLP: operates on flattened low-freq components
        # Input: concatenated real + imag parts -> cut_freq * d_compress * 2
        freq_input_dim = cut_freq * d_compress * 2
        self.freq_mlp = nn.Sequential(
            nn.Linear(freq_input_dim, d_hidden),
            nn.GELU(),
            nn.Dropout(dropout),
        )

        # Quantile output head
        self.quantile_head = nn.Linear(d_hidden, n_quantiles)

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        """Forward pass through FITS model.

        Parameters
        ----------
        x : torch.Tensor
            Shape (B, L, F) -- batch of time series windows.

        Returns
        -------
        dict with keys:
            "quantiles"  : (B, n_quantiles) predicted quantile values
            "point_pred" : (B,) median prediction (quantiles[:, 1])
        """
        B, L, F = x.shape

        # 1. Feature compression: (B, L, F) -> (B, L, d_compress)
        x_compressed = self.feature_compress(x)

        # 2. rFFT along time dimension: (B, L, d_compress) -> (B, L//2+1, d_compress)
        x_freq = torch.fft.rfft(x_compressed, dim=1)  # complex tensor

        # 3. Low-pass filter: keep only first cut_freq bins
        x_freq_low = x_freq[:, :self.cut_freq, :]  # (B, cut_freq, d_compress)

        # 4. Flatten and split into real + imag
        x_real = x_freq_low.real.reshape(B, -1)  # (B, cut_freq * d_compress)
        x_imag = x_freq_low.imag.reshape(B, -1)  # (B, cut_freq * d_compress)
        x_flat = torch.cat([x_real, x_imag], dim=1)  # (B, cut_freq * d_compress * 2)

        # 5. Frequency-domain MLP
        h = self.freq_mlp(x_flat)  # (B, d_hidden)

        # 6. Quantile output
        quantiles = self.quantile_head(h)  # (B, n_quantiles)
        point_pred = quantiles[:, 1]       # (B,) -- median quantile

        return {
            "quantiles": quantiles,
            "point_pred": point_pred,
        }

    def count_parameters(self) -> int:
        """Return total number of trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
