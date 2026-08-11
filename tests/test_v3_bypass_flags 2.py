"""Unit tests for the V3 ablation bypass flags (Phase A2).

Verifies every bypass combination produces a valid quantile output with the
expected shape (B, n_quantiles) and finite values.  The all-off combo is the
strictest check -- it exercises the "V3 stripped to just the quantile head"
path where masknet/gdcn/raw/conv/attention are all skipped.

Run directly:
    python3 tests/test_v3_bypass_flags.py
"""

from __future__ import annotations

import os
import sys

import torch

# Make ``src.*`` importable when running from the repo root without pytest.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.model.dual_path_model_v3 import DualPathLOBModelV3  # noqa: E402


def test_all_bypasses_produce_output() -> None:
    """Every bypass combo must produce finite quantiles with shape (B, 3)."""
    cfg = dict(
        n_features=58,
        n_levels=20,
        d_model=32,
        d_raw=16,
        n_mask_blocks=1,
        n_cross_layers=1,
        patch_size=10,
        attn_nhead=2,
        attn_d_ff=64,
        d_prior=0,
        dropout=0.0,
        n_horizons=1,
        n_symbols=1,
        use_monotonic_quantile=True,
    )
    B, L = 2, 300
    x_feat = torch.randn(B, L, cfg["n_features"])
    x_raw = torch.randn(B, L, cfg["n_levels"], 4)

    combos = [
        dict(),  # all enabled (default)
        dict(use_masknet=False),
        dict(use_gdcn=False),
        dict(use_raw_path=False),
        dict(use_attention=False),
        dict(use_conv=False),
        dict(
            use_masknet=False,
            use_gdcn=False,
            use_raw_path=False,
            use_attention=False,
            use_conv=False,
        ),  # pure linear head -- V3 stripped to just the quantile head
    ]

    for combo in combos:
        m = DualPathLOBModelV3(**cfg, **combo)
        m.eval()
        # If Path B is disabled, the ablation runner passes x_raw=None.  We
        # test both modes: bypass flag false AND x_raw=None.
        with torch.no_grad():
            xr = x_raw if combo.get("use_raw_path", True) else None
            out = m(x_feat, x_raw=xr)
        q = out["quantiles"]
        pp = out["point_pred"]
        assert q.shape == (B, 3), f"{combo}: shape {q.shape}"
        assert pp.shape == (B,), f"{combo}: point_pred shape {pp.shape}"
        assert torch.isfinite(q).all(), f"{combo}: non-finite quantiles"
        assert torch.isfinite(pp).all(), f"{combo}: non-finite point_pred"

    # Extra check: the "no raw path" combo must also accept x_raw=None when
    # the caller passes it explicitly (this is how the ablation runner does
    # it for the no_raw_path variant).
    m = DualPathLOBModelV3(**cfg, use_raw_path=False)
    m.eval()
    with torch.no_grad():
        out = m(x_feat, x_raw=None)
    assert out["quantiles"].shape == (B, 3)
    assert torch.isfinite(out["quantiles"]).all()

    print("PASS: test_all_bypasses_produce_output")


if __name__ == "__main__":
    test_all_bypasses_produce_output()
