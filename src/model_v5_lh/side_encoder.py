"""Side-aware bid/ask raw LOB encoder with cross-side attention.

Raw LOB input: (B, L, n_levels, 4) with channels = [bid_px_bps, bid_log_amt,
ask_px_bps, ask_log_amt]. Split into bid (B, L, n_levels, 2) and ask halves,
encode separately via Conv2d, then cross-side attention + asymmetry feature.

Reference: Kyle 1985, Easley 1996 — buyer- vs seller-initiated flow have
distinct predictive content.
"""
import torch
import torch.nn as nn


class _SideConvEncoder(nn.Module):
    """Conv over (levels, 2) for one side."""

    def __init__(self, n_levels: int, d_out: int):
        super().__init__()
        # Input (B, L, levels, 2) → treat as (B*L, 2, levels, 1) for Conv2d
        self.conv = nn.Sequential(
            nn.Conv2d(2, 8, kernel_size=(3, 1), padding=(1, 0)),
            nn.GELU(),
            nn.Conv2d(8, 16, kernel_size=(3, 1), padding=(1, 0)),
            nn.GELU(),
        )
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.proj = nn.Linear(16, d_out)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, L, levels, two = x.shape
        assert two == 2, f"expected last dim 2, got {two}"
        # reshape to (B*L, 2, levels, 1) for Conv2d input
        x = x.reshape(B * L, levels, 2).permute(0, 2, 1).unsqueeze(-1)
        h = self.conv(x)                          # (B*L, 16, levels, 1)
        h = self.pool(h).squeeze(-1).squeeze(-1)  # (B*L, 16)
        h = self.proj(h)                          # (B*L, d_out)
        return h.view(B, L, -1)                   # (B, L, d_out)


class _CrossSideAttention(nn.Module):
    """Single-layer multi-head attention: Q from one side attends to K,V from the other.

    Compatible with PyTorch < 1.9 (no batch_first kwarg): inputs are transposed
    to (L, B, d_side) for the MHA call and transposed back.
    """

    def __init__(self, d_side: int, nhead: int = 2):
        super().__init__()
        self.attn = nn.MultiheadAttention(d_side, nhead)
        self.ln = nn.LayerNorm(d_side)

    def forward(self, q: torch.Tensor, k: torch.Tensor, v: torch.Tensor) -> torch.Tensor:
        # q, k, v: (B, L, d_side) — transpose to (L, B, d_side) for MHA
        q_t = q.transpose(0, 1)  # (L, B, d_side)
        k_t = k.transpose(0, 1)
        v_t = v.transpose(0, 1)
        attn_out, _ = self.attn(q_t, k_t, v_t, need_weights=False)
        attn_out = attn_out.transpose(0, 1)  # back to (B, L, d_side)
        return self.ln(q + attn_out)


class SideAwareRawEncoder(nn.Module):
    """Full side-aware encoder.

    Output = Linear([bid_enhanced; ask_enhanced; bid_enhanced - ask_enhanced]).
    """

    def __init__(self, n_levels: int = 20, d_side: int = 8, d_out: int = 24):
        super().__init__()
        self.bid_enc = _SideConvEncoder(n_levels, d_side)
        self.ask_enc = _SideConvEncoder(n_levels, d_side)
        self.cross_bid_from_ask = _CrossSideAttention(d_side, nhead=2)
        self.cross_ask_from_bid = _CrossSideAttention(d_side, nhead=2)
        self.out_proj = nn.Linear(3 * d_side, d_out)

    def forward(self, x_raw: torch.Tensor) -> torch.Tensor:
        # x_raw: (B, L, levels, 4) with [bid_px, bid_amt, ask_px, ask_amt]
        bid = x_raw[..., :2]   # (B, L, levels, 2)
        ask = x_raw[..., 2:]
        h_bid = self.bid_enc(bid)                # (B, L, d_side)
        h_ask = self.ask_enc(ask)
        # Cross-side attention
        h_bid_e = self.cross_bid_from_ask(h_bid, h_ask, h_ask)
        h_ask_e = self.cross_ask_from_bid(h_ask, h_bid, h_bid)
        # Asymmetry concat
        asym = h_bid_e - h_ask_e
        fused = torch.cat([h_bid_e, h_ask_e, asym], dim=-1)  # (B, L, 3*d_side)
        return self.out_proj(fused)                          # (B, L, d_out)
