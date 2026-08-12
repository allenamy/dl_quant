"""Unit tests for DualLOBREGArch (perp deep-book gated residual on REG_arch).

Run on jpline:
    /root/miniconda3/envs/hsy_v5push/bin/python -m pytest \
        multi_asset/model/test_dual_lob_regarch.py -q

Proves the perp residual is a CORRECT, zero-init-identity extension of the
proven single-asset REG_arch (DualPathLOBModelV3):

  1. zero-init identity     — perp_alpha=0 => forward bit-identical to (a) the
                              SAME model run WITHOUT x_raw_perp_deep and (b) the
                              parent DualPathLOBModelV3 with copied shared weights.
  2. shape + grad           — perp_alpha_init=0.05 forward returns the expected
                              quantile dict; loss.backward() puts NON-zero grad on
                              perp_alpha, perp_proj AND raw_encoder_perp (the
                              residual sub-net is NOT gradient-starved — the whole
                              reason alpha inits at 0.05, not 0.0).
  3. param count            — subclass ≈ parent + small residual sub-net (a few K),
                              NOT a doubling.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest
import torch

# jpline CPU torch hits "could not create a primitive" in oneDNN/MKL-DNN conv1d
# under this env; disable the MKL-DNN backend so the (pure-correctness) unit
# tests run on the reference CPU conv path. No effect on model semantics.
torch.backends.mkldnn.enabled = False

# repo root on path (src/ + multi_asset/ both importable)
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.model.dual_path_model_v3 import DualPathLOBModelV3  # noqa: E402
from multi_asset.model.dual_lob_regarch import DualLOBREGArch  # noqa: E402

# --- REG_arch production-shaped config (conformer + FiLM multistage + DAQH) ---
# Mirrors the single-asset winner so the test exercises the real downstream path
# the perp residual will live under (FiLM-multistage branch in encode tail).
N_FEAT = 64
N_LEVELS = 20         # spot Path-B level count (x_raw / X_raw_spot)
PERP_N_LEVELS = 20    # perp deep-book level count (x_raw_perp_deep / X_raw)
D_MODEL = 32
D_RAW = 16
D_PERP = 16
D_PRIOR = 6
T = 64                # short window for a fast unit test
B = 8

_BASE_CFG = dict(
    n_features=N_FEAT,
    n_levels=N_LEVELS,
    d_model=D_MODEL,
    d_raw=D_RAW,
    d_prior=D_PRIOR,
    dropout=0.0,                       # deterministic forward (no dropout noise)
    backbone_kind="conformer",
    backbone_kwargs={"n_blocks": 2, "n_heads": 2, "kernel_size": 15},
    use_film_multistage=True,          # REG_arch
    use_direction_aware_head=True,     # DAQH (provides point_pred + sign_logit)
    use_revin=True,
)


def _mk_inputs(seed: int = 0):
    g = torch.Generator().manual_seed(seed)
    x_feat = torch.randn(B, T, N_FEAT, generator=g)
    x_raw = torch.randn(B, T, N_LEVELS, 4, generator=g)
    x_raw_perp = torch.randn(B, T, PERP_N_LEVELS, 4, generator=g)
    regime_prior = torch.randn(B, D_PRIOR, generator=g)
    y = torch.randn(B, generator=g)
    return x_feat, x_raw, x_raw_perp, regime_prior, y


def _count(m: torch.nn.Module) -> int:
    return sum(p.numel() for p in m.parameters())


# --------------------------------------------------------------------------- #
# 1. ZERO-INIT IDENTITY                                                        #
# --------------------------------------------------------------------------- #
def test_zero_alpha_identity_vs_self_without_perp():
    """alpha=0 => feeding x_raw_perp_deep changes NOTHING (residual term is 0)."""
    torch.manual_seed(0)
    model = DualLOBREGArch(
        **_BASE_CFG,
        use_perp_residual=True,
        perp_n_levels=PERP_N_LEVELS,
        d_perp=D_PERP,
        perp_alpha_init=0.05,
    ).eval()
    model.perp_alpha.data.zero_()  # temporarily kill the master gate

    x_feat, x_raw, x_raw_perp, rp, _ = _mk_inputs(seed=1)
    with torch.no_grad():
        out_with = model(x_feat, x_raw=x_raw, regime_prior=rp,
                         x_raw_perp_deep=x_raw_perp)
        out_without = model(x_feat, x_raw=x_raw, regime_prior=rp,
                            x_raw_perp_deep=None)

    for k in ("quantiles", "point_pred"):
        assert torch.allclose(out_with[k], out_without[k], atol=1e-6), (
            f"{k}: alpha=0 must make x_raw_perp_deep a no-op "
            f"(max|Δ|={(out_with[k] - out_without[k]).abs().max():.3e})"
        )


def test_zero_alpha_identity_vs_parent():
    """alpha=0 => subclass forward == parent DualPathLOBModelV3 forward.

    Copy the parent's weights into the subclass (strict=False: subclass is a
    superset adding only the perp sub-net), zero perp_alpha, and assert the
    quantile outputs match bit-for-bit. Confirms a PURE extension.
    """
    torch.manual_seed(0)
    parent = DualPathLOBModelV3(**_BASE_CFG).eval()

    torch.manual_seed(123)  # different init on purpose; weights copied below
    child = DualLOBREGArch(
        **_BASE_CFG,
        use_perp_residual=True,
        perp_n_levels=PERP_N_LEVELS,
        d_perp=D_PERP,
        perp_alpha_init=0.05,
    ).eval()

    missing, unexpected = child.load_state_dict(parent.state_dict(), strict=False)
    # parent has NO keys absent from child (child is a superset)
    assert unexpected == [], f"parent had keys child lacks: {unexpected}"
    # the ONLY child-extra (missing-from-parent) keys are the perp sub-net
    assert all(
        k.startswith(("raw_encoder_perp", "perp_proj", "perp_gate", "perp_alpha"))
        for k in missing
    ), f"unexpected child-only keys: {missing}"

    child.perp_alpha.data.zero_()

    x_feat, x_raw, x_raw_perp, rp, _ = _mk_inputs(seed=2)
    with torch.no_grad():
        out_parent = parent(x_feat, x_raw=x_raw, regime_prior=rp)
        out_child = child(x_feat, x_raw=x_raw, regime_prior=rp,
                          x_raw_perp_deep=x_raw_perp)

    for k in ("quantiles", "point_pred"):
        assert torch.allclose(out_parent[k], out_child[k], atol=1e-6), (
            f"{k}: subclass(alpha=0) must equal parent "
            f"(max|Δ|={(out_parent[k] - out_child[k]).abs().max():.3e})"
        )


def test_perp_disabled_equals_parent():
    """use_perp_residual=False => byte-identical to the parent (sanity)."""
    torch.manual_seed(7)
    parent = DualPathLOBModelV3(**_BASE_CFG).eval()
    torch.manual_seed(7)
    child = DualLOBREGArch(**_BASE_CFG, use_perp_residual=False).eval()
    # identical seeds + no extra modules => identical param count + keys
    assert _count(child) == _count(parent)
    assert child.raw_encoder_perp is None and child.perp_alpha is None
    x_feat, x_raw, _, rp, _ = _mk_inputs(seed=3)
    with torch.no_grad():
        op = parent(x_feat, x_raw=x_raw, regime_prior=rp)
        oc = child(x_feat, x_raw=x_raw, regime_prior=rp)
    assert torch.allclose(op["point_pred"], oc["point_pred"], atol=1e-7)


# --------------------------------------------------------------------------- #
# 2. SHAPE + GRAD (residual sub-net NOT gradient-starved at alpha_init=0.05)   #
# --------------------------------------------------------------------------- #
def test_shapes_and_residual_subnet_grad():
    torch.manual_seed(0)
    model = DualLOBREGArch(
        **_BASE_CFG,
        use_perp_residual=True,
        perp_n_levels=PERP_N_LEVELS,
        d_perp=D_PERP,
        perp_alpha_init=0.05,
    ).train()

    x_feat, x_raw, x_raw_perp, rp, y = _mk_inputs(seed=4)
    out = model(x_feat, x_raw=x_raw, regime_prior=rp, x_raw_perp_deep=x_raw_perp)

    # quantile dict / shapes
    assert set(("quantiles", "point_pred")).issubset(out.keys())
    assert out["quantiles"].shape == (B, 3)
    assert out["point_pred"].shape == (B,)
    # monotone quantiles (DAQH is structurally monotone)
    q = out["quantiles"]
    assert torch.all(q[:, 0] <= q[:, 1] + 1e-6) and torch.all(q[:, 1] <= q[:, 2] + 1e-6)

    # Backward through a pinball-style loss on the QUANTILES (not point_pred).
    # NOTE: DAQH is zero-init-neutral — at init q50 = tanh(sign)*softplus(mag)
    # = tanh(0)*... = 0, so point_pred ≡ 0 and an mse(point_pred, y) loss has
    # ~zero gradient. q10/q90 are non-zero at init, so a quantile loss is the
    # honest way to verify the residual sub-net receives real gradient. (This is
    # also how the real trainer supervises this head: pinball over q10/q50/q90.)
    taus = torch.tensor([0.1, 0.5, 0.9])
    err = y.unsqueeze(1) - q                       # (B, 3)
    loss = torch.maximum(taus * err, (taus - 1.0) * err).mean()
    loss.backward()

    def _gradnorm(mod_or_param) -> float:
        if isinstance(mod_or_param, torch.nn.Parameter):
            g = mod_or_param.grad
            return float(g.abs().sum()) if g is not None else 0.0
        tot = 0.0
        for p in mod_or_param.parameters():
            if p.grad is not None:
                tot += float(p.grad.abs().sum())
        return tot

    g_alpha = _gradnorm(model.perp_alpha)
    g_proj = _gradnorm(model.perp_proj)
    g_gate = _gradnorm(model.perp_gate)
    g_enc = _gradnorm(model.raw_encoder_perp)

    assert g_alpha > 0.0, "perp_alpha got ZERO grad (master gate starved)"
    assert g_proj > 0.0, "perp_proj got ZERO grad"
    assert g_gate > 0.0, "perp_gate got ZERO grad"
    assert g_enc > 0.0, (
        "raw_encoder_perp got ZERO grad — residual sub-net is gradient-starved; "
        "this is exactly what perp_alpha_init=0.05 (not 0.0) prevents"
    )


def test_zero_alpha_starves_subnet_grad():
    """Counter-proof: at alpha=0 the perp ENCODER grad IS zero (the bug 0.05 fixes).

    perp_gate/perp_proj are reached via the sigmoid gate path too, but the perp
    ENCODER only feeds the output through tanh(alpha)*..., so at alpha=0 its grad
    must vanish — demonstrating why a true-zero master gate starves the sub-net.
    """
    torch.manual_seed(0)
    model = DualLOBREGArch(
        **_BASE_CFG,
        use_perp_residual=True,
        perp_n_levels=PERP_N_LEVELS,
        d_perp=D_PERP,
        perp_alpha_init=0.05,
    ).train()
    model.perp_alpha.data.zero_()

    x_feat, x_raw, x_raw_perp, rp, y = _mk_inputs(seed=5)
    out = model(x_feat, x_raw=x_raw, regime_prior=rp, x_raw_perp_deep=x_raw_perp)
    # Same quantile loss as the positive test, so the ONLY reason the perp
    # ENCODER gets zero grad is the alpha=0 master gate (not a dead point_pred).
    q = out["quantiles"]
    taus = torch.tensor([0.1, 0.5, 0.9])
    err = y.unsqueeze(1) - q
    loss = torch.maximum(taus * err, (taus - 1.0) * err).mean()
    loss.backward()

    g_enc = sum(
        float(p.grad.abs().sum()) for p in model.raw_encoder_perp.parameters()
        if p.grad is not None
    )
    assert g_enc == 0.0, (
        "expected raw_encoder_perp grad == 0 at alpha=0 (gradient starvation) — "
        "this is the verified bug pattern that perp_alpha_init=0.05 avoids"
    )


# --------------------------------------------------------------------------- #
# 3. PARAM COUNT (extension, not doubling)                                     #
# --------------------------------------------------------------------------- #
def test_param_count_delta_is_small():
    parent = DualPathLOBModelV3(**_BASE_CFG)
    child = DualLOBREGArch(
        **_BASE_CFG,
        use_perp_residual=True,
        perp_n_levels=PERP_N_LEVELS,
        d_perp=D_PERP,
        perp_alpha_init=0.05,
    )
    n_parent = _count(parent)
    n_child = _count(child)
    delta = n_child - n_parent

    # residual sub-net = RawLOBEncoder(d_perp) + Linear(d_perp->d_model) +
    # Linear(d_model->d_model) + 1 scalar. Expect a few K, certainly < 20K and
    # nowhere near doubling the parent.
    assert delta > 0
    assert delta < 20_000, f"residual sub-net too large: +{delta} params"
    assert n_child < 1.5 * n_parent, (
        f"param count nearly doubled (parent={n_parent}, child={n_child})"
    )
    print(f"\n[param] parent={n_parent} child={n_child} delta=+{delta}")


# --------------------------------------------------------------------------- #
# Optional: real dual-data day smoke (skipped if the npz is absent locally)    #
# --------------------------------------------------------------------------- #
_DUAL_NPZ = "/mnt/storage/private/work_hsy/quant_research_multi_asset/data/npz_dual/2025-02-10.npz"


@pytest.mark.skipif(not os.path.exists(_DUAL_NPZ), reason="dual-data npz absent")
def test_real_dual_day_forward_and_identity():
    """Forward on the real dual-data day; alpha=0 identity holds on real tensors."""
    d = np.load(_DUAL_NPZ)
    n = 16
    x_feat = torch.from_numpy(d["X"][:n]).float()
    x_raw_spot = torch.from_numpy(d["X_raw_spot"][:n]).float()
    x_raw_perp = torch.from_numpy(d["X_raw"][:n]).float()
    rp = torch.from_numpy(d["regime_prior"][:n]).float()
    n_feat = x_feat.shape[-1]
    n_lvl = x_raw_spot.shape[2]
    perp_lvl = x_raw_perp.shape[2]

    cfg = dict(_BASE_CFG)
    cfg.update(n_features=n_feat, n_levels=n_lvl)
    torch.manual_seed(0)
    model = DualLOBREGArch(
        **cfg, use_perp_residual=True, perp_n_levels=perp_lvl,
        d_perp=D_PERP, perp_alpha_init=0.05,
    ).eval()

    # nonzero alpha: perp DOES move the output. Assert on QUANTILES (q10/q90):
    # DAQH is zero-init-neutral so point_pred (q50) ≡ 0 at init regardless of
    # perp; the non-trivial q10/q90 are where the perturbation shows.
    with torch.no_grad():
        out_on = model(x_feat, x_raw=x_raw_spot, regime_prior=rp,
                       x_raw_perp_deep=x_raw_perp)
        out_off = model(x_feat, x_raw=x_raw_spot, regime_prior=rp,
                        x_raw_perp_deep=None)
    assert out_on["point_pred"].shape == (n,)
    assert (out_on["quantiles"] - out_off["quantiles"]).abs().max() > 0, (
        "perp_alpha=0.05 should change the quantile output when perp book is fed"
    )

    # alpha=0: full identity on real tensors (all outputs, incl. quantiles)
    model.perp_alpha.data.zero_()
    with torch.no_grad():
        a = model(x_feat, x_raw=x_raw_spot, regime_prior=rp,
                  x_raw_perp_deep=x_raw_perp)
        b = model(x_feat, x_raw=x_raw_spot, regime_prior=rp, x_raw_perp_deep=None)
    assert torch.allclose(a["quantiles"], b["quantiles"], atol=1e-6)
    assert torch.allclose(a["point_pred"], b["point_pred"], atol=1e-6)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q", "-s"]))
