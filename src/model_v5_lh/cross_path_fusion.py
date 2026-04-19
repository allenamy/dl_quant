"""Bidirectional cross-attention fusion with residual decomposition.

  h_A_enh = CrossAttn(Q=h_A, K=h_B_proj, V=h_B_proj)   # A attends to B
  h_B_enh = CrossAttn(Q=h_B_proj, K=h_A, V=h_A)         # B attends to A
  residual = h_B_enh - Proj(h_A_enh)
  h_fused  = Linear(h_A_enh) + Linear(residual)

The subtraction forces the B-path to contribute what A cannot represent
(residual / complementary signal), not redundant information.

PyTorch < 1.9 compatibility: nn.MultiheadAttention does not accept
batch_first=True. Inputs are transposed (B, L, d) → (L, B, d) for the
MHA call and transposed back after.
"""
import torch
import torch.nn as nn


class _CrossAttention(nn.Module):
    """Single cross-attention layer (PyTorch < 1.9 compatible).

    Q from one path attends to K, V from the other.
    Includes a residual connection and LayerNorm.
    """

    def __init__(self, d_model: int, nhead: int):
        super().__init__()
        self.attn = nn.MultiheadAttention(d_model, nhead)
        self.ln = nn.LayerNorm(d_model)

    def forward(
        self, q: torch.Tensor, k: torch.Tensor, v: torch.Tensor
    ) -> torch.Tensor:
        # q, k, v: (B, L, d_model) — transpose to (L, B, d_model) for MHA
        q_t = q.transpose(0, 1)   # (L, B, d_model)
        k_t = k.transpose(0, 1)
        v_t = v.transpose(0, 1)
        attn_out, _ = self.attn(q_t, k_t, v_t, need_weights=False)
        attn_out = attn_out.transpose(0, 1)  # back to (B, L, d_model)
        return self.ln(q + attn_out)


class CrossPathFusion(nn.Module):
    """Bidirectional cross-path fusion with residual decomposition.

    Both attention paths operate at d_A. h_B is projected to d_A first,
    making attention symmetric in dimensionality.

    Args:
        d_A:   dimension of Path A embeddings
        d_B:   dimension of Path B embeddings
        d_out: output dimension
        nhead: number of attention heads (must divide d_A evenly)
    """

    def __init__(self, d_A: int, d_B: int, d_out: int, nhead: int = 4):
        super().__init__()
        # Project B into A's dim so attention is shape-compatible
        self.b_to_a = nn.Linear(d_B, d_A)
        # Bidirectional cross-attention (both operate at d_A)
        self.attn_A_from_B = _CrossAttention(d_A, nhead)
        self.attn_B_from_A = _CrossAttention(d_A, nhead)
        # Project h_A_enh to shared space for residual subtraction
        self.a_to_common = nn.Linear(d_A, d_A)
        # Two output projections — h_A_enh carries the primary signal;
        # residual carries what B adds beyond what A can explain
        self.out_proj = nn.Linear(d_A, d_out)
        self.residual_proj = nn.Linear(d_A, d_out)

    def forward(self, h_A: torch.Tensor, h_B: torch.Tensor) -> torch.Tensor:
        """
        Args:
            h_A: (B, L, d_A)
            h_B: (B, L, d_B)
        Returns:
            fused: (B, L, d_out)
        """
        # Project B to common dim
        h_B_proj = self.b_to_a(h_B)                          # (B, L, d_A)

        # A attends to B: enrich A with B's information
        h_A_enh = self.attn_A_from_B(h_A, h_B_proj, h_B_proj)  # (B, L, d_A)

        # B attends to A: enrich B with A's information
        h_B_enh = self.attn_B_from_A(h_B_proj, h_A, h_A)       # (B, L, d_A)

        # Residual decomposition: what in B is NOT explained by A
        residual = h_B_enh - self.a_to_common(h_A_enh)          # (B, L, d_A)

        # Combine: primary path A signal + complementary B residual
        return self.out_proj(h_A_enh) + self.residual_proj(residual)  # (B, L, d_out)
