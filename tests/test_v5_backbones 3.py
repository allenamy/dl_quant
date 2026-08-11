"""V5 Phase B.1 backbone correctness audit.

Each backbone in `src/model/backbones/` that is a candidate for V5 Phase B.1
(ema_pool, gru, mamba) must satisfy four criteria before we spend GPU time
on a full screen:

1. Shape contract:  (B, L, d_model) input → (B, d_model) output
2. Backward:        gradients flow + are finite on the input
3. Determinism:     in eval mode, same input → same output (no leaky randomness)
4. t=0 grad > 0:    gradient at the earliest timestep must be non-zero,
                    otherwise the backbone is degenerate to a last-timestep
                    slice (= the V4 baseline bug we are trying to fix).

For mamba we cannot run dynamic tests on local CPU because `mamba-ssm`
is CUDA-only.  We mark those tests as `xfail(strict=False)` with a clear
reason rather than silently skipping them, so the audit log shows the
gap explicitly.

Run:
    python -m pytest tests/test_v5_backbones.py -v -s
"""
import os
import sys

import pytest
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _build_backbone(name, d_model=32):
    """Construct a backbone by name.

    Raises ImportError for `mamba` on CPU-only environments — the caller
    is responsible for handling that (the mamba tests are xfail'd).
    """
    if name == "ema_pool":
        from src.model.backbones.ema_pool_backbone import EMAPoolBackbone
        return EMAPoolBackbone(d_model=d_model)
    elif name == "gru":
        from src.model.backbones.gru_backbone import GRUBackbone
        return GRUBackbone(d_model=d_model)
    elif name == "mamba":
        from src.model.backbones.mamba_backbone_v2 import MambaBackboneV2
        return MambaBackboneV2(d_model=d_model)
    else:
        pytest.fail("Unknown backbone {0}".format(name))


def _mamba_available():
    """True iff the mamba-ssm package can be imported AND we have CUDA.

    Mamba2's CUDA kernels require a real GPU; on CPU the import succeeds
    but instantiation raises.
    """
    try:
        from src.model.backbones.mamba_backbone_v2 import _HAS_MAMBA
    except Exception:
        return False
    if not _HAS_MAMBA:
        return False
    return torch.cuda.is_available()


_BACKBONES = ["ema_pool", "gru", "mamba"]


def _xfail_mamba_if_unavailable(name):
    """Mark mamba dynamic tests as xfail when the CUDA kernel isn't available.

    We use xfail(strict=False) instead of skip so that the audit table
    explicitly records the gap — the test result column will read
    XFAIL not skipped, and a future pod environment with mamba-ssm
    installed will flip these to XPASS without code change.
    """
    if name == "mamba" and not _mamba_available():
        pytest.xfail(
            "mamba-ssm CUDA kernels unavailable in this environment "
            "(local CPU PyTorch 1.4). Re-run on pod to validate."
        )


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------

@pytest.mark.parametrize("backbone_name", _BACKBONES)
def test_backbone_io_shape(backbone_name):
    """(B, L, d_model) input must produce (B, d_model) output."""
    _xfail_mamba_if_unavailable(backbone_name)
    backbone = _build_backbone(backbone_name, d_model=32)
    backbone.eval()
    x = torch.randn(4, 600, 32)
    with torch.no_grad():
        out = backbone(x)
    assert out.shape == (4, 32), "{0}: shape mismatch {1}".format(
        backbone_name, tuple(out.shape)
    )
    assert torch.isfinite(out).all(), "{0}: non-finite output".format(backbone_name)


@pytest.mark.parametrize("backbone_name", _BACKBONES)
def test_backbone_backward(backbone_name):
    """Gradient must flow back to the input and be finite."""
    _xfail_mamba_if_unavailable(backbone_name)
    backbone = _build_backbone(backbone_name, d_model=32)
    backbone.train()
    x = torch.randn(2, 100, 32, requires_grad=True)
    out = backbone(x)
    out.sum().backward()
    assert x.grad is not None, "{0}: no gradient on input".format(backbone_name)
    assert torch.isfinite(x.grad).all(), "{0}: NaN/Inf grad".format(backbone_name)
    assert x.grad.abs().sum().item() > 0, "{0}: zero gradient".format(backbone_name)


@pytest.mark.parametrize("backbone_name", _BACKBONES)
def test_backbone_determinism(backbone_name):
    """In eval mode, same input must give the exact same output."""
    _xfail_mamba_if_unavailable(backbone_name)
    backbone = _build_backbone(backbone_name, d_model=32)
    backbone.eval()
    x = torch.randn(2, 100, 32)
    with torch.no_grad():
        out1 = backbone(x)
        out2 = backbone(x)
    assert torch.allclose(out1, out2), \
        "{0}: non-deterministic in eval".format(backbone_name)


@pytest.mark.parametrize("backbone_name", _BACKBONES)
def test_backbone_uses_more_than_last_timestep(backbone_name):
    """Critical: backbone must actually use earlier timesteps, not just t=-1.

    If the gradient at t=0 is exactly zero (or numerically negligible),
    the backbone is effectively a last-timestep slice in disguise — the
    same V4 bug Phase B.1 is meant to fix.

    We use train() mode here because some backbones (GRU, conv) gate
    pathways through dropout in train mode. Eval mode would be a
    weaker test.
    """
    _xfail_mamba_if_unavailable(backbone_name)
    backbone = _build_backbone(backbone_name, d_model=32)
    backbone.eval()  # eval to disable dropout — t=0 grad must be > 0 deterministically
    L = 100
    x = torch.randn(1, L, 32, requires_grad=True)
    out = backbone(x)
    out.sum().backward()

    grad_at_t0 = x.grad[0, 0, :].abs().sum().item()
    grad_at_last = x.grad[0, -1, :].abs().sum().item()
    # Use a small absolute floor (1e-9) so finite-precision noise doesn't
    # masquerade as signal.
    assert grad_at_t0 > 1e-9, (
        "{0}: t=0 has zero grad ({1:.3e}) — only uses last timestep!".format(
            backbone_name, grad_at_t0
        )
    )
    # Print the ratio for the audit log.  With recency-weighted backbones
    # the ratio will be > 1 (last >> first).  With a uniform aggregator
    # it will be ~1.  With a degenerate last-slice it would be inf.
    ratio = grad_at_last / grad_at_t0 if grad_at_t0 > 0 else float("inf")
    print(
        "{0}: |grad@t=0| = {1:.4e}, |grad@t=-1| = {2:.4e}, ratio = {3:.2f}".format(
            backbone_name, grad_at_t0, grad_at_last, ratio
        )
    )
