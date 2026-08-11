"""Unit tests for calibration_losses.py — directional_huber and beta_calib.

Run on pod (or any env with torch installed):
    python -m pytest tests/losses/test_calibration_losses.py -v
"""
import pytest
import torch

from src.losses.calibration_losses import directional_huber_loss, beta_calib_loss


# ---------------------------------------------------------------------------
# directional_huber_loss
# ---------------------------------------------------------------------------

def test_directional_huber_same_sign_smaller_loss():
    """Same-sign predictions should have smaller loss than wrong-sign at same |err|."""
    target = torch.tensor([1.0, 1.0])
    pred_correct = torch.tensor([0.5, 0.5])  # same sign as target, err=0.5
    pred_wrong = torch.tensor([-0.5, -0.5])  # opposite sign, err=1.5

    loss_correct = directional_huber_loss(
        pred_correct, target, delta=2.0, w_wrong=2.0, w_extreme=3.0,
    )
    loss_wrong = directional_huber_loss(
        pred_wrong, target, delta=2.0, w_wrong=2.0, w_extreme=3.0,
    )
    # Wrong-sign Huber base is 9x higher (err 1.5 vs 0.5 squared, both within delta=2)
    # AND has the (1 + w_wrong)=3x multiplier. So total ratio is 27x.
    assert loss_wrong > 5.0 * loss_correct, (
        f"wrong-sign loss {loss_wrong} should be much larger than "
        f"same-sign {loss_correct}"
    )


def test_directional_huber_extreme_miss_heavier_than_normal_miss():
    """When |target|>1.5 AND signs disagree, the extreme-tier weight kicks in.

    Use non-zero pred so sign() is unambiguous: sign(0) is 0, not -1, which
    would silently disable the directional check.
    """
    # Both: pred is clearly negative, target is positive (signs disagree).
    pred_extreme = torch.tensor([-0.5])
    target_extreme = torch.tensor([2.0])         # |y|=2>1.5 → tier-3 (1+2+3=6)
    pred_normal = torch.tensor([-0.5])
    target_normal = torch.tensor([1.0])           # |y|=1<1.5 → tier-2 (1+2=3)

    loss_extreme = directional_huber_loss(
        pred_extreme, target_extreme,
        delta=2.0, w_wrong=2.0, w_extreme=3.0,
    )
    loss_normal = directional_huber_loss(
        pred_normal, target_normal,
        delta=2.0, w_wrong=2.0, w_extreme=3.0,
    )
    # extreme: |err|=2.5 → linear Huber 2*(2.5-1)=3.0, × 6 = 18.0
    # normal:  |err|=1.5 → quadratic Huber 0.5*2.25=1.125, × 3 = 3.375
    # Ratio ≈ 5.33×.
    assert loss_extreme > loss_normal * 5.0, (
        f"extreme miss should weight much more than normal miss: "
        f"{loss_extreme} vs {loss_normal}"
    )


def test_directional_huber_zero_when_perfect():
    """Perfect prediction → zero loss."""
    target = torch.tensor([1.0, -1.0, 0.5])
    loss = directional_huber_loss(target.clone(), target)
    assert loss.item() == pytest.approx(0.0, abs=1e-8)


def test_directional_huber_gradient_flows():
    """Ensure backward works."""
    pred = torch.tensor([0.5, -0.3, 1.2], requires_grad=True)
    target = torch.tensor([1.0, -0.5, 0.8])
    loss = directional_huber_loss(pred, target)
    loss.backward()
    assert pred.grad is not None
    assert torch.isfinite(pred.grad).all()


# ---------------------------------------------------------------------------
# beta_calib_loss
# ---------------------------------------------------------------------------

def test_beta_calib_zero_when_calibrated():
    """When ŷ = y exactly, β = 1, loss = 0."""
    torch.manual_seed(0)
    y = torch.randn(1000)
    yp = y.clone()
    loss = beta_calib_loss(yp, y)
    assert loss.item() < 1e-6


def test_beta_calib_decreases_when_scale_calibrates():
    """A more-calibrated scale should give a smaller β-calib loss.

    With ŷ = scale · y, β = cov(scale·y, y)/var(scale·y) = scale·var(y)/(scale²·var(y)) = 1/scale.
    So loss = (1 - 1/scale)². Decreases as scale → 1.
    """
    torch.manual_seed(0)
    y = torch.randn(2000)

    loss_off = beta_calib_loss(0.1 * y, y)   # 1/0.1 = 10 → (1-10)² = 81
    loss_better = beta_calib_loss(0.5 * y, y)  # 1/0.5 = 2 → (1-2)² = 1
    loss_perfect = beta_calib_loss(1.0 * y, y)  # 1 → 0

    assert loss_better < loss_off
    assert loss_perfect < loss_better
    # Quantitative sanity (tolerant; depends on small finite-sample noise)
    assert loss_off.item() == pytest.approx(81.0, rel=0.05)
    assert loss_better.item() == pytest.approx(1.0, rel=0.1)


def test_beta_calib_gradient_pushes_scale_toward_calibration():
    """SGD on scale (with ŷ=scale·y) should move scale → 1."""
    torch.manual_seed(0)
    y = torch.randn(5000)
    scale = torch.tensor(0.3, requires_grad=True)
    optim = torch.optim.SGD([scale], lr=0.05)
    initial = scale.item()
    for _ in range(300):
        loss = beta_calib_loss(scale * y, y)
        optim.zero_grad()
        loss.backward()
        optim.step()
    # scale should be much closer to 1 than the start (0.3)
    assert abs(scale.item() - 1.0) < abs(initial - 1.0), (
        f"scale should move toward 1: initial={initial:.4f} final={scale.item():.4f}"
    )
    # Reasonable convergence
    assert abs(scale.item() - 1.0) < 0.2, f"scale={scale.item():.4f} did not converge"


def test_beta_calib_gradient_flows():
    """Ensure backward works on direct prediction tensor."""
    torch.manual_seed(0)
    pred = torch.randn(500, requires_grad=True)
    target = torch.randn(500)
    loss = beta_calib_loss(pred, target)
    loss.backward()
    assert pred.grad is not None
    assert torch.isfinite(pred.grad).all()


# ---------------------------------------------------------------------------
# Integration: MultiHorizonDulFocalUnit with calibration losses
# ---------------------------------------------------------------------------

def test_multi_horizon_dul_with_calibration_losses_runs():
    """MultiHorizonDulFocalUnit accepts new λ_dir_huber and λ_beta_calib params
    and produces finite loss when invoked."""
    from src.losses.multi_horizon_dul import MultiHorizonDulFocalUnit

    torch.manual_seed(0)
    B, n_h, Q = 512, 1, 3
    outputs = {
        "quantiles_by_horizon": torch.randn(B, n_h, Q, requires_grad=True),
        "point_pred_by_horizon": torch.randn(B, n_h),
    }
    y = torch.randn(B, n_h)
    mask = torch.ones(B, n_h)

    loss_fn = MultiHorizonDulFocalUnit(
        n_horizons=n_h,
        y_sigmas=[1.0],
        use_unit=False,
        focal_extra_weight=0.0,
        lambda_quantile=1.0,
        lambda_rank=0.3,
        lambda_dir_huber=0.2,
        lambda_beta_calib=0.05,
    )
    loss = loss_fn(outputs, y, mask)
    assert torch.isfinite(loss), f"loss must be finite, got {loss}"
    loss.backward()
    assert outputs["quantiles_by_horizon"].grad is not None


def test_multi_horizon_dul_calibration_term_actually_increases_loss():
    """When β-calib is enabled, total loss should INCREASE vs the baseline
    composition (since β-calib ≥ 0 and adds to total). Symmetric for dir_huber."""
    from src.losses.multi_horizon_dul import MultiHorizonDulFocalUnit

    torch.manual_seed(0)
    B, n_h, Q = 512, 1, 3
    q = torch.randn(B, n_h, Q)
    outputs = {"quantiles_by_horizon": q, "point_pred_by_horizon": q[:, :, 1]}
    y = torch.randn(B, n_h)
    mask = torch.ones(B, n_h)

    loss_baseline = MultiHorizonDulFocalUnit(
        n_horizons=n_h, y_sigmas=[1.0], use_unit=False,
        focal_extra_weight=0.0, lambda_quantile=1.0, lambda_rank=0.3,
        lambda_dir_huber=0.0, lambda_beta_calib=0.0,
    )(outputs, y, mask)

    loss_with_calib = MultiHorizonDulFocalUnit(
        n_horizons=n_h, y_sigmas=[1.0], use_unit=False,
        focal_extra_weight=0.0, lambda_quantile=1.0, lambda_rank=0.3,
        lambda_dir_huber=0.2, lambda_beta_calib=0.05,
    )(outputs, y, mask)

    assert loss_with_calib > loss_baseline, (
        f"adding non-zero λ_dir_huber + λ_beta_calib should increase total loss; "
        f"baseline={loss_baseline.item():.4f} with_calib={loss_with_calib.item():.4f}"
    )


# ---------------------------------------------------------------------------
# Integration: single-horizon compute_dul_loss with calibration losses
# ---------------------------------------------------------------------------

def test_compute_dul_loss_with_calibration_runs():
    """Single-horizon compute_dul_loss accepts new λs and produces finite loss."""
    from src.training.dul_loss import compute_dul_loss

    torch.manual_seed(0)
    quantiles = torch.randn(512, 3, requires_grad=True)
    target = torch.randn(512)
    total, parts = compute_dul_loss(
        quantiles, target,
        lambda_quantile=1.0,
        lambda_utility_rank=0.3,
        lambda_calib=0.0,
        lambda_dir_huber=0.2,
        lambda_beta_calib=0.05,
        utility_alpha=1.0,
        return_parts=True,
    )
    assert torch.isfinite(total), f"loss must be finite, got {total}"
    assert "dir_huber" in parts and parts["dir_huber"] > 0
    assert "beta_calib" in parts and parts["beta_calib"] > 0
    total.backward()
    assert quantiles.grad is not None


def test_compute_dul_loss_calib_disabled_when_lambda_zero():
    """λ=0 → component absent from gradient + reported as 0 in parts."""
    from src.training.dul_loss import compute_dul_loss

    torch.manual_seed(0)
    quantiles = torch.randn(512, 3, requires_grad=True)
    target = torch.randn(512)
    _, parts = compute_dul_loss(
        quantiles, target,
        lambda_quantile=1.0,
        lambda_utility_rank=0.0,
        lambda_calib=0.0,
        lambda_dir_huber=0.0,
        lambda_beta_calib=0.0,
        return_parts=True,
    )
    assert parts["dir_huber"] == 0.0
    assert parts["beta_calib"] == 0.0
