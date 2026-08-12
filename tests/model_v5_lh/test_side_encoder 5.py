import torch
from src.model_v5_lh.side_encoder import SideAwareRawEncoder


def test_output_shape():
    B, L, levels = 2, 100, 20
    enc = SideAwareRawEncoder(n_levels=levels, d_out=24)
    x_raw = torch.randn(B, L, levels, 4)  # 4 = [bid_px, bid_amt, ask_px, ask_amt]
    out = enc(x_raw)
    assert out.shape == (B, L, 24), f"got {out.shape}"


def test_bid_ask_not_mixed_at_first_layer():
    """Sanity: swapping bid and ask channels should change output
    (otherwise model is treating sides symmetrically already)."""
    B, L, levels = 2, 50, 20
    enc = SideAwareRawEncoder(n_levels=levels, d_out=24)
    x_raw = torch.randn(B, L, levels, 4)
    out1 = enc(x_raw)
    # Swap bid and ask channels
    x_swapped = torch.stack([x_raw[..., 2], x_raw[..., 3], x_raw[..., 0], x_raw[..., 1]], dim=-1)
    out2 = enc(x_swapped)
    assert not torch.allclose(out1, out2, atol=1e-4)


def test_gradient_flows():
    B, L, levels = 2, 50, 20
    enc = SideAwareRawEncoder(n_levels=levels, d_out=24)
    x_raw = torch.randn(B, L, levels, 4, requires_grad=True)
    out = enc(x_raw)
    out.sum().backward()
    assert x_raw.grad is not None
