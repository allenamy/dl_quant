"""V5 loss smoke test — local, no pod / no NPZ dependency.

Verifies:
1. vol_adaptive: σ_local computation correct, no look-ahead, NaN handling
2. DualHead: forward shapes, gradient flow, init sanity
3. Each loss component: shape, mask handling, no NaN, gradient flow
4. cs_ic auto-noop for S=1 vs active for S=3
5. End-to-end: 5-layer toy training on synthetic y = sign(x_a) * |x_b| + noise,
   verify dual head recovers ground truth (final P > 0.5 on held-out)

Run: python scripts/v5_loss_smoke_test.py
"""
from __future__ import annotations

import sys
import numpy as np
import torch
import torch.nn as nn

# Path bootstrap
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src.training.v5_losses import (  # noqa
    compute_sigma_local_mad,
    compute_sigma_local_ewma,
    DualHead,
    loss_dir_margin,
    loss_mag_huber,
    loss_joint_mse,
    loss_cs_ic,
    V5LossAssembly,
)
from src.training.v5_losses.vol_adaptive import normalize_y_with_sigma_local
from src.training.v5_losses.loss_assembly import V5LossConfig
from src.training.v5_losses.components import loss_beta_consistency


GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"


def ok(msg):
    print(f"{GREEN}✓{RESET} {msg}")


def fail(msg):
    print(f"{RED}✗{RESET} {msg}")
    sys.exit(1)


# ------------------------------------------------------------------------------
# 1. vol_adaptive
# ------------------------------------------------------------------------------
def test_vol_adaptive():
    print("\n=== 1. vol_adaptive ===")
    np.random.seed(42)
    n = 2000
    rets = np.random.randn(n) * 1e-3  # 10 bps stdev

    sigma_mad = compute_sigma_local_mad(rets, window=720, min_periods=60)
    assert np.isnan(sigma_mad[:60]).all(), "first min_periods must be NaN"
    assert np.isfinite(sigma_mad[720:]).all(), "post-warmup must be finite"
    assert (sigma_mad[720:] > 0).all(), "sigma must be positive"
    mean_sigma = np.nanmean(sigma_mad)
    assert 5e-4 < mean_sigma < 2e-3, f"sigma scale unreasonable: {mean_sigma:.4e}"
    ok(f"compute_sigma_local_mad: mean={mean_sigma:.4e}, post-warmup all finite")

    sigma_ewma = compute_sigma_local_ewma(rets, alpha=0.06, warmup_periods=200)
    assert np.isnan(sigma_ewma[:200]).all()
    assert np.isfinite(sigma_ewma[200:]).all()
    ok(f"compute_sigma_local_ewma: mean={np.nanmean(sigma_ewma):.4e}, post-warmup all finite")

    # Look-ahead check: sigma[t] should not depend on rets[t:]
    rets_b = rets.copy()
    rets_b[1500:] = 999.0
    sigma_b = compute_sigma_local_mad(rets_b, window=720, min_periods=60)
    diff = np.abs(sigma_mad[:1500] - sigma_b[:1500])
    diff_clean = diff[np.isfinite(diff)]
    assert diff_clean.max() < 1e-12, f"future leak detected: max diff={diff_clean.max():.4e}"
    ok("no future leak: changing rets[1500:] does not affect sigma[:1500]")

    # Normalization round-trip
    y = rets.copy()
    y[100] = np.nan  # inject some NaN
    y_normed = normalize_y_with_sigma_local(y, sigma_mad)
    valid = np.isfinite(y_normed)
    n_valid = valid.sum()
    assert n_valid > 0
    # Recovery: y_recovered = y_normed * sigma_local
    y_recov = y_normed * sigma_mad
    diff = np.abs(y_recov[valid] - y[valid])
    assert diff.max() < 1e-12, f"round-trip error: {diff.max():.4e}"
    ok(f"normalize round-trip exact: {n_valid} valid samples")


# ------------------------------------------------------------------------------
# 2. DualHead
# ------------------------------------------------------------------------------
def test_dual_head():
    print("\n=== 2. DualHead ===")
    torch.manual_seed(42)
    head = DualHead(d_emb=32, n_horizons=1, hidden=16, dropout=0.1)
    emb = torch.randn(8, 32, requires_grad=True)
    out = head(emb)

    expected_keys = {"dir_logit", "mag", "soft_sign", "y_pred"}
    assert set(out.keys()) == expected_keys
    for k in expected_keys:
        assert out[k].shape == (8, 1), f"{k} shape: {out[k].shape}"
    assert (out["mag"] >= 0).all(), "mag must be non-negative"
    assert ((out["soft_sign"] > -1) & (out["soft_sign"] < 1)).all(), "soft_sign in (-1, 1)"
    ok(f"forward shapes correct: {dict((k, v.shape) for k, v in out.items())}")

    # Initial mag should be near 1.0 (we set mag bias = 0.5413 → softplus ≈ 1.0)
    init_mag_mean = out["mag"].mean().item()
    assert 0.5 < init_mag_mean < 1.5, f"initial mag mean unreasonable: {init_mag_mean:.3f}"
    ok(f"initial mag near 1.0: mean={init_mag_mean:.3f}")

    # Backward through full loss
    y = torch.randn(8, 1)
    mask = torch.ones(8, 1, dtype=torch.bool)
    loss = loss_joint_mse(out["y_pred"], y, mask)
    loss.backward()
    assert emb.grad is not None
    assert torch.isfinite(emb.grad).all()
    assert emb.grad.abs().sum() > 0, "no gradient flow"
    ok(f"backward through head + joint_mse: grad norm={emb.grad.norm().item():.4f}")


# ------------------------------------------------------------------------------
# 3. Loss components
# ------------------------------------------------------------------------------
def test_loss_components():
    print("\n=== 3. Loss components ===")
    torch.manual_seed(42)
    n = 16
    dir_logit = torch.randn(n, 1, requires_grad=True)
    mag = torch.nn.functional.softplus(torch.randn(n, 1, requires_grad=True))
    y = torch.randn(n, 1)
    mask = torch.ones(n, 1, dtype=torch.bool)

    # dir_margin
    l1 = loss_dir_margin(dir_logit, y, mask)
    assert torch.isfinite(l1)
    assert l1.requires_grad
    l1.backward(retain_graph=True)
    ok(f"dir_margin: loss={l1.item():.4f}, grad OK")

    # mag_huber
    dir_logit.grad = None
    l2 = loss_mag_huber(mag, y, mask, delta=2.0)
    assert torch.isfinite(l2) and l2 >= 0
    l2.backward(retain_graph=True)
    ok(f"mag_huber: loss={l2.item():.4f}, grad OK")

    # joint_mse
    dir_logit.grad = None
    soft_sign = torch.tanh(dir_logit)
    y_pred = soft_sign * mag
    l3 = loss_joint_mse(y_pred, y, mask)
    assert torch.isfinite(l3) and l3 >= 0
    l3.backward()
    ok(f"joint_mse: loss={l3.item():.4f}, grad OK")

    # mask test: all-False mask → 0 loss with grad
    mask_empty = torch.zeros(n, 1, dtype=torch.bool)
    dir_logit2 = torch.randn(n, 1, requires_grad=True)
    l4 = loss_dir_margin(dir_logit2, y, mask_empty)
    assert l4.item() == 0.0
    l4.backward()
    ok(f"all-mask=False handled: loss=0 with valid grad")

    # NaN handling
    y_nan = y.clone()
    y_nan[3] = float("nan")
    l5 = loss_dir_margin(dir_logit, y_nan, mask)
    assert torch.isfinite(l5)
    ok(f"NaN in y handled: loss={l5.item():.4f}")


# ------------------------------------------------------------------------------
# 4. cs_ic auto-noop for S=1
# ------------------------------------------------------------------------------
def test_cs_ic():
    print("\n=== 4. cs_ic auto-noop ===")
    torch.manual_seed(42)

    # S=1 → must return 0 with grad path
    pred = torch.randn(4, 5, 1, 1, requires_grad=True)
    target = torch.randn(4, 5, 1, 1)
    mask = torch.ones_like(pred, dtype=torch.bool)
    l = loss_cs_ic(pred, target, mask)
    assert l.item() == 0.0, f"S=1 must noop, got {l.item():.4f}"
    assert l.requires_grad
    l.backward()
    ok(f"S=1 noop: loss=0, backward OK")

    # S=3 → real loss
    pred_ms = torch.randn(4, 5, 3, 1, requires_grad=True)
    target_ms = torch.randn(4, 5, 3, 1)
    mask_ms = torch.ones_like(pred_ms, dtype=torch.bool)
    l_ms = loss_cs_ic(pred_ms, target_ms, mask_ms)
    assert torch.isfinite(l_ms)
    l_ms.backward()
    ok(f"S=3 active: loss={l_ms.item():.4f}, grad OK")

    # S=3 with perfect correlation → loss should be ~0
    pred_perfect = target_ms.clone() * 2.0  # perfectly correlated, scaled
    l_perfect = loss_cs_ic(pred_perfect, target_ms, mask_ms)
    assert l_perfect.item() < 0.1, f"perfect corr should give loss<<1, got {l_perfect.item():.4f}"
    ok(f"S=3 perfect corr: loss={l_perfect.item():.4f} (expect << 1)")

    # S=3 with anti-correlation → loss should be ~2 (1 - (-1) = 2)
    pred_anti = -target_ms.clone()
    l_anti = loss_cs_ic(pred_anti, target_ms, mask_ms)
    assert l_anti.item() > 1.5, f"anti-corr should give loss > 1.5, got {l_anti.item():.4f}"
    ok(f"S=3 anti-corr: loss={l_anti.item():.4f} (expect ~2)")


# ------------------------------------------------------------------------------
# 5. End-to-end toy training
# ------------------------------------------------------------------------------
class ToyEncoder(nn.Module):
    def __init__(self, d_in=4, d_emb=32):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d_in, d_emb),
            nn.LeakyReLU(0.1),
            nn.Linear(d_emb, d_emb),
        )

    def forward(self, x):
        return self.net(x)


def test_end_to_end_toy():
    """Train a tiny model on synthetic y = sign(x[0]) * |x[1]|^0.5 * 0.5 + noise.

    Goal: verify dual-head architecture can learn a magnitude × sign relationship
    when ground truth has this structure. Success criterion: held-out Pearson > 0.4.
    """
    print("\n=== 5. End-to-end toy training (synthetic ground truth) ===")
    torch.manual_seed(42)
    np.random.seed(42)

    # Generate
    n_train = 5000
    n_test = 1000
    d_in = 4
    x_train = torch.randn(n_train, d_in)
    x_test = torch.randn(n_test, d_in)

    def true_y(x):
        # y = sign(x[:,0]) * sqrt(|x[:,1]|) * 0.5 + noise
        return torch.sign(x[:, 0:1]) * torch.sqrt(torch.abs(x[:, 1:2])) * 0.5 + torch.randn(x.shape[0], 1) * 0.3

    y_train = true_y(x_train)
    y_test = true_y(x_test)
    mask_train = torch.ones_like(y_train, dtype=torch.bool)
    mask_test = torch.ones_like(y_test, dtype=torch.bool)

    encoder = ToyEncoder(d_in=d_in, d_emb=32)
    head = DualHead(d_emb=32, n_horizons=1, hidden=16, dropout=0.0)
    params = list(encoder.parameters()) + list(head.parameters())
    opt = torch.optim.Adam(params, lr=3e-3)

    cfg = V5LossConfig(w_dir_margin=0.3, w_mag_huber=0.3, w_joint_mse=0.5)
    assembler = V5LossAssembly(cfg)

    losses = []
    for epoch in range(200):
        encoder.train()
        head.train()
        emb = encoder(x_train)
        out = head(emb)
        ld = assembler(out, y_train, mask_train)
        opt.zero_grad()
        ld["total"].backward()
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step()
        losses.append(ld["total"].item())

    # Eval on held-out
    encoder.eval()
    head.eval()
    with torch.no_grad():
        emb_t = encoder(x_test)
        out_t = head(emb_t)
        y_pred = out_t["y_pred"].squeeze().numpy()
        y_true = y_test.squeeze().numpy()
    P = np.corrcoef(y_pred, y_true)[0, 1]
    sign_acc = float((np.sign(y_pred) == np.sign(y_true)).mean())
    mag_corr = np.corrcoef(np.abs(y_pred), np.abs(y_true))[0, 1]
    print(f"  final train loss: {losses[-1]:.4f} (start: {losses[0]:.4f})")
    print(f"  held-out Pearson: {P:+.4f}")
    print(f"  sign accuracy:    {sign_acc:.3f}")
    print(f"  |y| correlation:  {mag_corr:+.4f}")

    if P > 0.4:
        ok(f"toy training converged: P={P:+.4f} (gate: >0.4)")
    else:
        fail(f"toy training failed to converge: P={P:+.4f} (expect >0.4)")
    if sign_acc > 0.7:
        ok(f"sign acc good: {sign_acc:.3f}")
    else:
        fail(f"sign acc too low: {sign_acc:.3f} (expect >0.7)")


# ------------------------------------------------------------------------------
# 6. Multi-asset (S=3) end-to-end with cs_ic active
# ------------------------------------------------------------------------------
def test_multi_asset_e2e():
    """Verify cs_ic loss path works in a multi-asset setting (S=3)."""
    print("\n=== 6. Multi-asset toy (S=3) with cs_ic active ===")
    torch.manual_seed(42)
    B, S, H = 64, 3, 1
    d_emb = 16

    encoder = nn.Linear(8, d_emb)
    head = DualHead(d_emb=d_emb, n_horizons=H, n_symbols=S)

    x = torch.randn(B, S, 8)
    symbol_ids = torch.arange(S).unsqueeze(0).expand(B, -1)
    y_target = torch.randn(B, S, H) * 0.5

    emb = encoder(x)
    out = head(emb, symbol_id=symbol_ids)
    mask = torch.ones(B, S, H, dtype=torch.bool)

    cfg = V5LossConfig(w_dir_margin=0.3, w_mag_huber=0.3, w_joint_mse=0.5, w_cs_ic=0.2)
    assembler = V5LossAssembly(cfg)
    ld = assembler(out, y_target, mask)
    assert "cs_ic" in ld, "cs_ic should be active when S=3"
    assert torch.isfinite(ld["total"])
    ld["total"].backward()
    ok(f"multi-asset e2e: total={ld['total'].item():.4f}, cs_ic={ld['cs_ic'].item():.4f}")


# ------------------------------------------------------------------------------
# 7. beta_consistency aux
# ------------------------------------------------------------------------------
def test_beta_consistency():
    print("\n=== 7. beta_consistency aux ===")
    torch.manual_seed(42)
    # Construct y_pred and y with known beta
    y_true = torch.randn(500, 1)
    # If y_pred = 0.5 * y_true, beta = cov(y, ŷ) / var(ŷ) = 0.5*var(y) / 0.25*var(y) = 2.0
    y_pred = 0.5 * y_true.clone().requires_grad_(True)
    mask = torch.ones_like(y_true, dtype=torch.bool)
    l = loss_beta_consistency(y_pred, y_true, mask, target_beta=2.0)
    assert l.item() < 0.01, f"beta=2 vs target=2 should give loss~0, got {l.item():.4f}"
    ok(f"beta_consistency: target=2 actual=2 → loss={l.item():.4e} (~0)")

    l_off = loss_beta_consistency(y_pred, y_true, mask, target_beta=1.0)
    assert l_off.item() > 0.5, f"beta=2 vs target=1 should give loss~1, got {l_off.item():.4f}"
    ok(f"beta_consistency: target=1 actual=2 → loss={l_off.item():.4f} (~1)")


def main():
    print("=" * 72)
    print("V5 Loss Smoke Test")
    print("=" * 72)
    test_vol_adaptive()
    test_dual_head()
    test_loss_components()
    test_cs_ic()
    test_end_to_end_toy()
    test_multi_asset_e2e()
    test_beta_consistency()
    print("\n" + "=" * 72)
    print(f"{GREEN}ALL TESTS PASSED{RESET}")
    print("=" * 72)


if __name__ == "__main__":
    main()
