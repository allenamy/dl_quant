"""Backbone interface contract tests.

Every backbone in src/model/backbones/ must:
  1. Accept input shape (B, L, D) and return (B, D).
  2. Be deterministic in eval mode.
  3. Produce finite outputs given finite inputs.
  4. Have backward-pass propagating gradients to the input.

Mamba test is gated by mamba-ssm availability + CUDA.
"""
import pytest
import torch

from src.model.backbones.conv_backbone import ConvLastTSBackbone
from src.model.backbones.ema_pool_backbone import EMAPoolBackbone
from src.model.backbones.gru_backbone import GRUBackbone
from src.model.backbones.itransformer_backbone import ITransformerBackbone
from src.model.backbones.moe_backbone import MoEBackbone


B, L, D = 4, 1200, 32


def _check_backbone_contract(bb: torch.nn.Module):
    bb.eval()
    h = torch.randn(B, L, D)
    out = bb(h)
    assert out.shape == (B, D), f"expected ({B},{D}), got {out.shape}"
    assert torch.isfinite(out).all()
    # Determinism in eval mode (dropout off)
    out2 = bb(h)
    assert torch.allclose(out, out2)
    # Backward
    bb.train()
    h2 = torch.randn(B, L, D, requires_grad=True)
    bb(h2).sum().backward()
    assert h2.grad is not None
    assert torch.isfinite(h2.grad).all()


def test_conv_lasts_backbone_contract():
    _check_backbone_contract(ConvLastTSBackbone(d_model=D, dropout=0.0))


def test_ema_pool_backbone_contract():
    _check_backbone_contract(EMAPoolBackbone(d_model=D, decay=0.95, dropout=0.0))


def test_gru_backbone_contract():
    _check_backbone_contract(GRUBackbone(d_model=D, hidden=D, n_layers=1, dropout=0.0))


def test_ema_pool_decay_at_extremes():
    """decay near 1 → all weight on early steps; decay near 0 → all on last step."""
    torch.manual_seed(0)
    h = torch.randn(2, 100, D)

    # decay = 0.999 → essentially uniform weight
    bb_high = EMAPoolBackbone(d_model=D, decay=0.999, dropout=0.0)
    bb_high.eval()
    out_high = bb_high(h)

    # decay = 0.01 → essentially last-timestep
    bb_low = EMAPoolBackbone(d_model=D, decay=0.01, dropout=0.0)
    bb_low.eval()
    out_low = bb_low(h)

    # Sanity: outputs differ
    assert not torch.allclose(out_high, out_low)


def test_ema_pool_backbone_invalid_decay_raises():
    with pytest.raises(ValueError):
        EMAPoolBackbone(d_model=D, decay=0.0)
    with pytest.raises(ValueError):
        EMAPoolBackbone(d_model=D, decay=1.0)


def test_conv_backbone_param_count():
    """ConvLastTSBackbone has only conv params (no extra)."""
    bb = ConvLastTSBackbone(d_model=32, dropout=0.0)
    n = sum(p.numel() for p in bb.parameters())
    # 3 dilated conv layers + LayerNorm per block. Sanity: ~10k params.
    assert 5_000 < n < 20_000, f"expected ~10K params, got {n}"


def test_gru_backbone_extra_param_count():
    """GRU adds ~6K params over conv stack at hidden=32."""
    conv_only = ConvLastTSBackbone(d_model=32, dropout=0.0)
    gru_bb = GRUBackbone(d_model=32, hidden=32, n_layers=1, dropout=0.0)
    delta = sum(p.numel() for p in gru_bb.parameters()) - sum(p.numel() for p in conv_only.parameters())
    # GRU(32→32, 1 layer) has 4*hidden*(input+hidden+1) ~ 4*32*65 = 8320 params
    assert 4_000 < delta < 12_000, f"GRU extra params should be ~6-8K, got {delta}"


def test_itransformer_backbone_contract():
    _check_backbone_contract(
        ITransformerBackbone(d_model=D, L=L, d_emb=64, n_heads=4, n_layers=1, dropout=0.0)
    )


def test_itransformer_d_emb_divisibility_check():
    with pytest.raises(ValueError):
        ITransformerBackbone(d_model=D, L=L, d_emb=63, n_heads=4)


def test_itransformer_rejects_wrong_L():
    bb = ITransformerBackbone(d_model=D, L=600, d_emb=32, n_heads=4)
    bb.eval()
    h_wrong = torch.randn(2, 1200, D)
    with pytest.raises(ValueError):
        bb(h_wrong)


def test_moe_backbone_contract_no_regime():
    """MoE w/o regime input — uses h.mean(dim=1) for routing."""
    bb = MoEBackbone(d_model=D, n_experts=4, top_k=2, dropout=0.0,
                     load_balance_aux_weight=0.0)
    _check_backbone_contract(bb)


def test_moe_backbone_with_regime_signature():
    """MoE w/ regime_dim must be called with regime tensor."""
    bb = MoEBackbone(d_model=D, n_experts=3, top_k=2, regime_dim=6, dropout=0.0,
                     load_balance_aux_weight=0.0)
    h = torch.randn(B, L, D)
    regime = torch.randn(B, 6)
    bb.eval()
    out = bb(h, regime=regime)
    assert out.shape == (B, D)
    # Without regime, must raise
    with pytest.raises(ValueError):
        bb(h)


def test_moe_top_k_validation():
    with pytest.raises(ValueError):
        MoEBackbone(d_model=D, n_experts=4, top_k=5)
    with pytest.raises(ValueError):
        MoEBackbone(d_model=D, n_experts=4, top_k=0)


def test_moe_aux_loss_emitted_in_train_mode():
    """Aux loss is finite in train mode, zero in eval mode."""
    bb = MoEBackbone(d_model=D, n_experts=4, top_k=2, dropout=0.0,
                     load_balance_aux_weight=0.01)
    h = torch.randn(B, L, D)
    bb.train()
    bb(h)
    assert torch.isfinite(bb.last_aux_loss)
    assert bb.last_aux_loss.item() > 0  # nonzero in train

    bb.eval()
    bb(h)
    assert bb.last_aux_loss.item() == 0.0


def test_mamba_backbone_skipped_without_cuda_or_mamba():
    """Mamba contract test is conditional on mamba-ssm + CUDA."""
    pytest.importorskip("mamba_ssm")
    if not torch.cuda.is_available():
        pytest.skip("Mamba2 requires CUDA")
    from src.model.backbones.mamba_backbone_v2 import MambaBackboneV2
    bb = MambaBackboneV2(d_model=D, d_state=16, expand=1, dropout=0.0).cuda()
    h = torch.randn(B, L, D).cuda()
    out = bb(h)
    assert out.shape == (B, D)
    assert torch.isfinite(out).all()
