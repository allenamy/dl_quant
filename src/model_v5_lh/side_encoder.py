"""Side-aware bid/ask raw LOB encoder with cross-side attention.

Raw LOB input: (B, L, n_levels, 4) with channels [bid_px_bps, bid_log_amt,
ask_px_bps, ask_log_amt]. Split into bid/ask halves, each encoded INDEPENDENTLY
by Conv2d(3, 1) stack over the levels axis. Per-level structure is preserved
via Linear projection of the flattened (channels × levels) feature map rather
than a global pool.

Cross-side attention operates on the TEMPORAL axis: at each timestep t, bid's
embedding attends to the full ask sequence (t0..tL-1) and vice versa. This
captures cross-flow lead-lag patterns (Kyle 1985) rather than same-timestep
level-by-level alignment.

Output = Linear([h_bid_enhanced; h_ask_enhanced; h_bid_enhanced - h_ask_enhanced]).

Reference: Kyle 1985, Easley 1996 — buyer- vs seller-initiated flow have
distinct predictive content.
"""
import torch
import torch.nn as nn


class _SideConvEncoder(nn.Module):
    """Conv2d over (levels, 2) for one side, preserving per-level structure.

    Two Conv2d layers with kernel (3, 1) over the levels axis learn local
    cross-level patterns (touch vs near-touch vs deep). The second conv
    tapers channels down so the final flatten + Linear stays inside the
    parameter budget. Unlike a global pool, this preserves which level
    contributed to each embedding dim.
    """

    def __init__(self, n_levels: int, d_out: int):
        super().__init__()
        self.n_levels = n_levels
        self.conv = nn.Sequential(
            nn.Conv2d(2, 8, kernel_size=(3, 1), padding=(1, 0)),
            nn.GELU(),
            nn.Conv2d(8, 4, kernel_size=(3, 1), padding=(1, 0)),
            nn.GELU(),
        )
        # Flatten (4 channels × n_levels levels) → d_out
        self.proj = nn.Linear(4 * n_levels, d_out)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, L, levels, two = x.shape
        assert two == 2, f"expected last dim 2, got {two}"
        assert levels == self.n_levels, (
            f"encoder built for n_levels={self.n_levels}, got {levels}"
        )
        # (B, L, levels, 2) → (B*L, 2, levels, 1) via explicit reshape
        x = x.reshape(B * L, levels, 2).permute(0, 2, 1).unsqueeze(-1)
        h = self.conv(x)                             # (B*L, 4, levels, 1)
        h = h.squeeze(-1).reshape(B * L, -1)         # (B*L, 4 * levels)
        h = self.proj(h)                             # (B*L, d_out)
        return h.view(B, L, -1)                      # (B, L, d_out)


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
