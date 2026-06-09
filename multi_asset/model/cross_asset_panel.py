"""Cross-asset attention panel model for crypto y_600 prediction.

The GENUINE multi-asset lever: at each timestamp the 14 asset embeddings are
tokens, and a small Transformer-style MultiheadAttention layer lets each asset
attend to ALL others (a learnable per-asset id embedding makes the tokens
identifiable). This is the structure that the per-asset Ridge / single-asset DL
*cannot* express — the whole point of going multi-asset.

Pipeline per forward:
    X  (B, S, F)   per-window features for S assets at B timestamps
    mask (B, S)    1 where asset is present/valid at that timestamp
    ->  per-asset shared MLP encoder  F -> d
    ->  + learnable asset-id embedding (S, d)
    ->  1-2 cross-asset MultiheadAttention layers (over the S-asset axis),
        masked so padded assets neither attend nor are attended to
    ->  per-asset head  d -> n_out  (n_out=1 normalized q50, or 3 quantiles)
    output (B, S, n_out)  (squeezed to (B, S) when n_out==1)

Small by design (low-SNR rule): d=48, 2 attn layers, nhead=4 -> ~70-120K params.
Shared encoder + shared head weights across assets; only the asset-id embedding
and attention are cross-asset. No time dimension here — the per-window feature
cache already collapses the sequence into 44 causal features, so this trains
directly on the panel (efficient, no heavy sequence pipeline).
"""
from __future__ import annotations

import torch
import torch.nn as nn


class AssetEncoder(nn.Module):
    """Shared per-asset MLP: F -> d, GELU, LayerNorm. Same weights all assets."""

    def __init__(self, n_feat: int, d: int, dropout: float = 0.2):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_feat, d),
            nn.GELU(),
            nn.LayerNorm(d),
            nn.Dropout(dropout),
            nn.Linear(d, d),
            nn.GELU(),
            nn.LayerNorm(d),
        )

    def forward(self, x):  # (B, S, F) -> (B, S, d)
        return self.net(x)


class CrossAssetAttnLayer(nn.Module):
    """One pre-norm MultiheadAttention block over the asset (S) axis + FFN.

    key_padding_mask drops padded assets from the attention (they don't get
    attended to). We zero their residual contribution on the way out too.
    """

    def __init__(self, d: int, nhead: int = 4, dropout: float = 0.2):
        super().__init__()
        self.norm1 = nn.LayerNorm(d)
        self.attn = nn.MultiheadAttention(d, nhead, dropout=dropout, batch_first=True)
        self.norm2 = nn.LayerNorm(d)
        self.ffn = nn.Sequential(
            nn.Linear(d, 2 * d),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(2 * d, d),
        )
        self.drop = nn.Dropout(dropout)

    def forward(self, x, key_padding_mask):
        # x: (B, S, d); key_padding_mask: (B, S) bool, True = PAD (ignored).
        h = self.norm1(x)
        a, _ = self.attn(h, h, h, key_padding_mask=key_padding_mask, need_weights=False)
        x = x + self.drop(a)
        x = x + self.drop(self.ffn(self.norm2(x)))
        return x


class CrossAssetPanelModel(nn.Module):
    """Shared encoder + asset-id embedding + cross-asset attention + shared head."""

    def __init__(
        self,
        n_feat: int,
        n_assets: int,
        d: int = 48,
        nhead: int = 4,
        n_layers: int = 2,
        n_out: int = 1,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.n_assets = n_assets
        self.n_out = n_out
        self.encoder = AssetEncoder(n_feat, d, dropout)
        # learnable per-asset id embedding (makes the S tokens identifiable)
        self.asset_id = nn.Parameter(torch.zeros(n_assets, d))
        nn.init.normal_(self.asset_id, std=0.02)
        self.layers = nn.ModuleList(
            [CrossAssetAttnLayer(d, nhead, dropout) for _ in range(n_layers)]
        )
        self.head_norm = nn.LayerNorm(d)
        self.head = nn.Linear(d, n_out)

    def forward(self, x, mask):
        """x: (B, S, F) float; mask: (B, S) {0,1}. Returns (B, S) or (B, S, n_out).

        Padded assets (mask==0) are zeroed at input, excluded from attention via
        key_padding_mask, and their outputs are not used by the (masked) loss.
        """
        B, S, _ = x.shape
        x = torch.nan_to_num(x, nan=0.0)
        x = x * mask.unsqueeze(-1)              # zero padded assets at input
        h = self.encoder(x)                      # (B, S, d)
        h = h + self.asset_id.unsqueeze(0)       # broadcast asset-id over batch
        key_pad = mask < 0.5                     # (B, S) True = PAD
        # A timestamp with zero valid assets would make MHA produce NaN (all
        # keys masked). Such rows are masked out of the loss anyway; feed an
        # all-False pad row to keep MHA finite, the head output is unused.
        all_pad = key_pad.all(dim=1, keepdim=True)
        key_pad = key_pad & ~all_pad
        for layer in self.layers:
            h = layer(h, key_pad)
        h = self.head_norm(h)
        out = self.head(h)                       # (B, S, n_out)
        if self.n_out == 1:
            out = out.squeeze(-1)                # (B, S)
        return out


def count_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
