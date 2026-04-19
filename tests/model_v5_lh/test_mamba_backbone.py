import torch
from src.model_v5_lh.mamba_backbone import MambaBackbone


def test_shape_preservation():
    """Output should have same (B, L, d_model) shape."""
    B, L, d = 2, 100, 32
    backbone = MambaBackbone(d_model=d, n_layers=2, d_state=16, use_fallback=True)
    x = torch.randn(B, L, d)
    out = backbone(x)
    assert out.shape == (B, L, d)


def test_causal_no_future_leak():
    """Changing future should not change past outputs (causal test)."""
    B, L, d = 1, 50, 16
    backbone = MambaBackbone(d_model=d, n_layers=1, d_state=8, use_fallback=True)
    backbone.eval()
    x1 = torch.randn(B, L, d)
    x2 = x1.clone()
    x2[:, L // 2:, :] = torch.randn(B, L - L // 2, d)  # change future
    with torch.no_grad():
        y1 = backbone(x1)
        y2 = backbone(x2)
    # Past output (first half) must be identical
    assert torch.allclose(y1[:, :L // 2, :], y2[:, :L // 2, :], atol=1e-5)


def test_gradient_flow():
    B, L, d = 2, 30, 16
    backbone = MambaBackbone(d_model=d, n_layers=1, d_state=8, use_fallback=True)
    x = torch.randn(B, L, d, requires_grad=True)
    y = backbone(x).sum()
    y.backward()
    assert x.grad is not None
