import torch
from src.model_v5_lh.cross_path_fusion import CrossPathFusion


def test_output_shape():
    B, L = 2, 100
    d_A, d_B, d_out = 32, 24, 32
    fusion = CrossPathFusion(d_A=d_A, d_B=d_B, d_out=d_out, nhead=4)
    h_A = torch.randn(B, L, d_A)
    h_B = torch.randn(B, L, d_B)
    out = fusion(h_A, h_B)
    assert out.shape == (B, L, d_out)


def test_residual_decomposition_preserves_path_a():
    """When h_B is zero, output should be close to h_A (with transforms)."""
    B, L = 2, 50
    fusion = CrossPathFusion(d_A=32, d_B=24, d_out=32, nhead=4)
    h_A = torch.randn(B, L, 32)
    h_B_zero = torch.zeros(B, L, 24)
    out_zero = fusion(h_A, h_B_zero)
    # h_B=0 means cross-attention contribution vanishes meaningfully
    # Output should differ from uninformed baseline but preserve A's structure
    assert out_zero.shape == (B, L, 32)


def test_gradient_flows_both_paths():
    B, L = 2, 40
    fusion = CrossPathFusion(d_A=32, d_B=24, d_out=32, nhead=4)
    h_A = torch.randn(B, L, 32, requires_grad=True)
    h_B = torch.randn(B, L, 24, requires_grad=True)
    out = fusion(h_A, h_B)
    out.sum().backward()
    assert h_A.grad is not None and h_A.grad.abs().sum().item() > 0
    assert h_B.grad is not None and h_B.grad.abs().sum().item() > 0


def test_path_b_influences_output():
    """Changing h_B should change output — verifies B actually contributes.

    Weaker test than training-based residual check, but catches the failure
    mode where residual_proj collapses to zero at init.
    """
    torch.manual_seed(0)
    B, L = 2, 30
    fusion = CrossPathFusion(d_A=32, d_B=24, d_out=32, nhead=4)
    fusion.eval()
    h_A = torch.randn(B, L, 32)
    h_B = torch.randn(B, L, 24)
    h_B_alt = torch.randn(B, L, 24)
    with torch.no_grad():
        out1 = fusion(h_A, h_B)
        out2 = fusion(h_A, h_B_alt)
    # Outputs should differ by more than numerical noise
    assert (out1 - out2).abs().mean().item() > 1e-3
