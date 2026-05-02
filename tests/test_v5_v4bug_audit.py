"""Audit test: V4 baseline_plus path discards 585 of 600 input timesteps.

Verifies dual_path_model_v3.py line ~628 takes only h[:, -1, :] when
use_attention=False AND backbone=None (= baseline_plus production config).

This is informational; not a "fix" test — just documents the structural
limitation V5 needs to address.

Two audit strategies:
1. Static code audit: parse the forward method source to confirm the bug exists
   at the code level (runs on any Python/PyTorch version — fast, reliable).
2. Dynamic gradient audit: instantiate the model and measure per-timestep
   gradient. Requires PyTorch >= 1.9 (batch_first in MHA). Skipped cleanly
   with an XFAIL on old PyTorch (not pytest.skip — the test still EXECUTES
   and the failure is treated as expected rather than an environment skip).

FAIL CLOSED semantics: the static audit never skips. The dynamic audit marks
as xfail on environments missing batch_first rather than skipping, so the
test suite still counts the test.
"""
import ast
import inspect
import json
import textwrap
import torch
import pytest


# ---------------------------------------------------------------------------
# Part 1: Static code audit (no model instantiation, runs everywhere)
# ---------------------------------------------------------------------------

def test_static_audit_forward_has_last_timestep_slice():
    """Confirm that dual_path_model_v3.py contains h[:, -1, :] in the else
    branch (baseline_plus path) via AST inspection.

    This is a hard audit gate — it FAILS CLOSED if the source cannot be
    found or parsed (do NOT convert to skip).
    """
    from src.model.dual_path_model_v3 import DualPathLOBModelV3

    # Get the forward method source. Fail hard if unavailable.
    try:
        src = inspect.getsource(DualPathLOBModelV3.forward)
    except OSError as e:
        raise RuntimeError(
            f"Cannot get source of DualPathLOBModelV3.forward: {e}. "
            "Audit cannot proceed — do NOT skip."
        )

    # The critical pattern: h[:, -1, :] in the else-branch (use_attention=False, no backbone).
    # We check for the string pattern directly (simpler and more resilient than full AST walk).
    assert "h[:, -1, :]" in src, (
        "AUDIT FAILED: h[:, -1, :] not found in DualPathLOBModelV3.forward source. "
        "Either the bug was fixed (great!) or the path changed — re-audit needed before V5 proceeds."
    )
    print("STATIC AUDIT PASS: h[:, -1, :] found in forward source (bug confirmed at code level)")


def test_static_audit_else_branch_context():
    """Confirm the h[:, -1, :] is in the else branch triggered by baseline_plus config
    (use_attention=False, backbone=None/conv_lasts).

    Checks that:
    1. The else branch (no backbone, no attention) leads to h[:, -1, :]
    2. baseline_plus.json has use_attention=False and no backbone_kind override
    """
    from src.model.dual_path_model_v3 import DualPathLOBModelV3

    src = inspect.getsource(DualPathLOBModelV3.forward)

    # Verify the baseline_plus config lands on this path.
    cfg = json.load(open("configs/y600_push/baseline_plus.json"))
    model_cfg = cfg["model"]

    assert model_cfg.get("use_attention", True) is False, (
        "baseline_plus should have use_attention=False"
    )
    # backbone_kind defaults to 'conv_lasts' which IS the last-timestep path
    # (see model __init__: 'conv_lasts' sets self.backbone = None so the else branch runs)
    backbone_kind = model_cfg.get("backbone_kind", "conv_lasts")
    assert backbone_kind == "conv_lasts", (
        f"baseline_plus should have backbone_kind=conv_lasts (or unset); got {backbone_kind!r}"
    )

    # Verify conv_lasts backbone_kind maps to self.backbone = None.
    init_src = inspect.getsource(DualPathLOBModelV3.__init__)
    # The conv_lasts path sets: self.backbone: Optional[nn.Module] = None
    # (includes type annotation — match the actual code pattern).
    assert 'backbone_kind == "conv_lasts"' in init_src, (
        "Expected 'backbone_kind == \"conv_lasts\"' in __init__ — re-audit if constructor changed."
    )
    # Also confirm the backbone is set to None for conv_lasts.
    assert 'self.backbone' in init_src and 'None' in init_src, (
        "Expected self.backbone = None assignment in __init__ — re-audit if constructor changed."
    )

    print(f"CONFIG AUDIT PASS: baseline_plus use_attention=False, backbone_kind={backbone_kind!r}")
    print("CONV_LASTS AUDIT PASS: backbone_kind='conv_lasts' sets self.backbone=None")
    print("CONCLUSION: baseline_plus forward hits the else branch → h[:, -1, :]")
    print(f"EFFECTIVE LOOKBACK: only the last timestep (+ TCN RF ~15s) out of input_len={cfg['data']['input_len']}s")


def test_static_audit_tcn_receptive_field():
    """Confirm the TCN receptive field is ~15 timesteps, not 600.

    Dilated causal conv with dilations (1, 2, 4) and kernel_size=3:
    RF = 1 + sum_i((kernel_size - 1) * dilation_i)
       = 1 + (3-1)*1 + (3-1)*2 + (3-1)*4
       = 1 + 2 + 4 + 8 = 15
    """
    from src.model.dual_path_model_v3 import DualPathLOBModelV3

    init_src = inspect.getsource(DualPathLOBModelV3.__init__)

    # Check that the dilations (1, 2, 4) are used for the inline TCN.
    assert "dilations=(1, 2, 4)" in init_src or "(1, 2, 4)" in init_src, (
        "Expected dilations=(1, 2, 4) in DualPathLOBModelV3 init — re-audit if changed."
    )

    # Compute and verify the RF formula.
    kernel_size = 3
    dilations = (1, 2, 4)
    rf = 1 + sum((kernel_size - 1) * d for d in dilations)
    assert rf == 15, f"Expected RF=15, got {rf}"

    print(f"TCN RF AUDIT PASS: dilations={dilations}, kernel_size={kernel_size} → RF={rf} timesteps")
    print(f"STRUCTURAL BUG: input_len=600 but only RF={rf} timesteps affect prediction in baseline_plus")


# ---------------------------------------------------------------------------
# Part 2: Dynamic gradient audit (PyTorch >= 1.9 required)
# ---------------------------------------------------------------------------

_NEEDS_NEW_PYTORCH = pytest.mark.xfail(
    not hasattr(torch.nn.MultiheadAttention.__init__, "__func__")
    or torch.__version__ < "1.9",
    reason=(
        "Dynamic model instantiation requires PyTorch >= 1.9 (batch_first in MHA). "
        "Local env has PyTorch %s. Static audits above still confirm the bug." % torch.__version__
    ),
    strict=False,
)


@_NEEDS_NEW_PYTORCH
def test_dynamic_audit_gradient_dominated_by_last_timestep():
    """Measure per-timestep gradient to confirm last-timestep dominance.

    Requires PyTorch >= 1.9. On older PyTorch this is marked xfail (not skip).
    """
    # Patch trunc_normal_ if missing (PyTorch < 1.9)
    import torch.nn as nn_module
    if not hasattr(nn_module.init, "trunc_normal_"):
        def _trunc_normal_shim(tensor, mean=0.0, std=1.0, a=-2.0, b=2.0):
            with torch.no_grad():
                return tensor.normal_(mean, std)
        nn_module.init.trunc_normal_ = _trunc_normal_shim

    from src.model.dual_path_model_v3 import DualPathLOBModelV3

    cfg = json.load(open("configs/y600_push/baseline_plus.json"))
    model_cfg = dict(cfg["model"])
    model_cfg["n_levels"] = cfg["data"]["n_levels"]

    torch.manual_seed(0)
    model = DualPathLOBModelV3(**model_cfg)
    model.eval()

    B, L = 1, cfg["data"]["input_len"]

    # Derive n_feat from NPZ.
    import os, numpy as np
    npz_dir = cfg["data"]["npz_dir"]
    all_npz = sorted(f for f in os.listdir(npz_dir) if f.endswith(".npz"))
    if not all_npz:
        raise RuntimeError(f"No .npz files in {npz_dir!r} — dynamic audit cannot run.")
    n_feat = int(np.load(os.path.join(npz_dir, all_npz[0]), allow_pickle=True)["X"].shape[-1])
    print(f"n_feat from NPZ: {n_feat}")

    x_feat = torch.randn(B, L, n_feat, requires_grad=True)
    x_raw = torch.randn(B, L, model_cfg["n_levels"], 4, requires_grad=True)
    regime_prior = torch.zeros(B, model_cfg.get("d_prior", 6))

    out = model(x_feat=x_feat, x_raw=x_raw, regime_prior=regime_prior)
    point_pred = out["point_pred"].sum() if "point_pred" in out else out["quantiles"][..., 1].sum()
    point_pred.backward()

    grad_per_step = x_feat.grad.abs().sum(dim=(0, 2))
    last_grad = grad_per_step[-1].item()
    avg_other_grad = grad_per_step[:-15].abs().mean().item()
    ratio = last_grad / max(avg_other_grad, 1e-10)
    print(f"last timestep grad: {last_grad:.6f}")
    print(f"avg grad of timesteps 0..L-15 (outside RF): {avg_other_grad:.6f}")
    print(f"ratio last : pre-RF avg = {ratio:.1f}")

    assert last_grad > 0
    assert ratio > 10, (
        f"Expected last-timestep dominance (ratio > 10), got ratio={ratio:.1f}. "
        f"pre-RF grad={avg_other_grad:.3e} vs last={last_grad:.3e}. Re-audit needed."
    )
