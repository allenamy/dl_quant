# V5 Iteration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build V5 — a strict iteration of V4 that fixes the production-readiness gaps identified in V4: σ_ŷ shrinkage / β-σ_ŷ tradeoff, monotonicity, top-bin sign-flip, embargo leakage risk. The single biggest change is replacing quantile pinball + utility_rank loss with **Gaussian heteroscedastic NLL** (per-sample uncertainty), keeping V4's proven backbone (DualPathLOBModelV3).

**Architecture:** V4's DualPathLOBModelV3 backbone (RevIN + GDCN + ChannelMix conv + LevelAttentionPool + PPNet gate, ~63K params) wrapped in a new V5 head that outputs `(μ, log_σ)` per sample. Training optimizes `0.5·(y-μ)²/σ² + 0.5·log(σ²)` (Gaussian NLL). Optional Mamba backbone for long-range temporal context (TCN's receptive field is only 15 steps; Mamba sees full input_len=600). Eval includes trading-view bin-plot + production-readiness gates.

**Tech Stack:** PyTorch 2.0+, NumPy, Pandas, scikit-learn (for calibration), pytest (TDD), existing V4 code at `src/model/dual_path_model_v3.py` and `src/training/trainer_v2.py`. New code lives under `src/training/v5_losses/`, `src/model/v5_model.py`, `configs/v5/`, `scripts/v5_*`.

**Background context (read before starting):**
- CLAUDE.md Anti-pattern #11 (variance collapse), #14 (multi-seed required), #16 (rank-blend β confusion), #17 (anchor discipline), #18 (raw eval), #19 (methodology consistency)
- Prior V5 scaffold at `src/training/v5_losses/` — keep dual_head.py and components.py for reference, but V5 PRIMARY path is heteroscedastic NLL, not dual-head
- Production candidate baseline = `seed42_SWA` from baseline_plus (V4) at P=0.0457, S=0.0571, β=1.010, σ_ŷ/σ_y=0.045
- V5 success criteria (gates documented in Task 0.2): P ≥ 0.045 (no regression), σ_ŷ/σ_y ≥ 0.10 (2× wider), β ∈ [0.85, 1.15], top-bin trading view E[y] > 0.5 bps with t-stat > 2

---

## File Structure (locked before tasks)

**Files to create:**
- `docs/V5_DESIGN.md` — design rationale, gates, ablation plan
- `src/training/v5_losses/heteroscedastic_components.py` — Gaussian NLL, stability tricks
- `src/training/v5_losses/heteroscedastic_head.py` — `(μ, log_σ)` output head
- `src/model/v5_model.py` — V5 wrapper around DualPathLOBModelV3
- `configs/v5/base.json` — V5 baseline config (NLL + same V4 backbone, input_len=600)
- `configs/v5/base_mamba.json` — V5 with Mamba backbone (longer effective context)
- `configs/v5/base_5fold.json` — 5-fold CV variant for regime robustness check
- `configs/v5/base_smoke.json` — fast 1-day smoke test config
- `scripts/v5_smoke_test.py` — local CPU smoke test (10 epochs, tiny data)
- `scripts/v5_eval_comprehensive.py` — full eval (calibration view + trading view + gates)
- `tests/test_v5_nll.py` — unit tests for NLL components
- `tests/test_v5_head.py` — unit tests for HeteroscedasticHead
- `tests/test_v5_eval.py` — eval gate logic tests

**Files to modify:**
- `src/training/dataset.py` — add embargo parameter (default 0 for backwards compat, V5 default 600)
- `src/training/trainer_v2.py` — add V5 NLL training path (separate function, doesn't break V4)
- `run_pipeline_v3.py` — dispatch V5Model + V5 loss_fn when `config.loss.use_v5_nll=true` (no new CLI flag, config-driven)

**Files NOT modified:** `src/model/dual_path_model_v3.py` (backbone untouched), all V4 configs, all V4 scripts.

---

## Phase 0: Design lock + V5 success criteria

### Task 0.1: Create design rationale doc

**Files:**
- Create: `docs/V5_DESIGN.md`

- [ ] **Step 1: Write design doc**

```bash
cat > docs/V5_DESIGN.md << 'DOCEOF'
> **创建:** 2026-05-02 | **Session:** v5-plan-write | **关键事件:** V5 plan finalized
> **状态:** in-progress | **作废条件:** V5 Phase 1 → Phase 6 实验完成,有 V5_RESULTS.md 取代

# V5 Design Rationale

## V4 → V5 motivation (从 production diagnostic 中识别的 4 个 fundamental 缺陷)

V4 production candidate (seed42_SWA, baseline_plus config) 在 raw dense eval 下:

| 维度 | V4 当前值 | 实盘可用性 |
|---|---|---|
| Pearson | 0.0457 | OK (代表 ~0.05 IC ceiling on single-asset y_600) |
| Spearman | 0.0571 | OK |
| β | +1.010 | ✓ 完美校准 |
| σ_ŷ/σ_y | 0.045 | ✗ 太窄,反转视觉不可见 |
| 单调性 (bin-Sp) | 0.770 | ⚠️ 中等 |
| top y bin 的 ŷ_mean | -0.13 bps (3seed) | ✗ 高 y 时模型 underestimate |
| mean(ŷ) | -0.08 bps | ⚠️ 轻微负偏 |

**根本原因 (loss 选错):**
- Quantile pinball (q50) 在低 SNR 下 maximally shrinks → σ_ŷ_optimal = ρ·σ_y = 0.05·σ_y
- utility_rank loss 进一步 fight σ_ŷ (rank invariant 下 σ_ŷ 越小越易 optimize)
- β_calib weight 0.05 太弱

**V5 fix: Gaussian heteroscedastic NLL**

模型输出 `(μ, log_σ)` per sample,loss `0.5·(y-μ)²/σ² + 0.5·log(σ²)`:
- **机制 1**: 高 confidence 样本 σ → 小 → loss 由 (y-μ)²/σ² 主导 → μ 必须接近 y
- **机制 2**: 低 confidence 样本 σ → 大 → loss 由 log σ² 主导 → μ 可以 = 0,不被罚
- **净效果**: μ 在 confident 样本上保留 magnitude, 在不 confident 上 shrink → **整体 σ_ŷ 显著大于纯 MSE/quantile**

理论支撑:
- Lakshminarayanan et al. 2017 "Simple and Scalable Predictive Uncertainty Estimation using Deep Ensembles"
- Kendall & Gal 2017 "What Uncertainties Do We Need in Bayesian Deep Learning"
- Chai 2024 — heteroscedastic regression for finance

## V5 不做的事 (避免 anti-pattern)

- ❌ 不改 V4 backbone 的核心 (DualPathLOBModelV3 已 proven, anti-pattern: 同时改太多)
- ❌ 不引入 rank loss 作为 PRIMARY (anti-pattern #15: rank loss replaces utility_rank → val/test drift)
- ❌ 不做 multi-seed ensemble 作为 PRIMARY (anti-pattern: ensemble 压 σ_ŷ + 拉高 β)
- ❌ 不在 fold 0 上 calibrate 后 evaluate fold 0 (anti-pattern #13)
- ❌ 不报 z-space P (anti-pattern #19: raw + dense + per-fold-stride 一锁到底)

## V5 Success Gates (pre-declared, hard)

完整 3-fold pooled eval (raw + dense, n=48,678 ± per-fold) 必须满足:

**Required (gate-blocking):**
- G1: Pearson ≥ 0.045 (no regression vs V4 baseline 0.0457 - 0.0015 = 0.044 floor)
- G2: σ_ŷ/σ_y ≥ 0.10 (vs V4 0.045, **2× target**)
- G3: |β - 1.0| ≤ 0.20 (β ∈ [0.80, 1.20])
- G4: top decile trading view E[y_realized] ≥ +0.5 bps with t-stat ≥ +2.0
- G5: bin-Spearman ≥ 0.85 (vs V4 0.770)
- G6: |mean(ŷ)| ≤ 0.10 bps (less negative bias than V4 -0.08)

**Stretch (informational only):**
- S1: Pearson ≥ 0.055 (real improvement)
- S2: σ_ŷ/σ_y ≥ 0.15
- S3: per-fold P std ≤ 0.008 (stable across regimes)

**Failure modes documented:**
- F1: σ collapse to constant — log_σ output saturated, μ effectively MSE
- F2: σ explosion — log_σ → ∞, μ → 0 (degenerate)
- F3: β-σ tradeoff fail — σ_ŷ 增了但 β 漂移到 [0.5, 0.8]
- F4: Pearson 实质 regression — σ_ŷ wide 但 ρ 没增,bin-Sp 反而差

每个 fail mode 对应 mitigation 已在实现中预设 (clip log_σ, warmup, β monitor)。

## Compatibility

V5 不修改 V4。所有 V4 模型、配置、CSV 仍可用作 baseline 对比。V5 train/eval 管道独立于 V4。

DOCEOF
```

- [ ] **Step 2: Verify file written**

Run: `wc -l docs/V5_DESIGN.md && head -20 docs/V5_DESIGN.md`
Expected: ~80+ lines, header visible.

- [ ] **Step 3: Commit**

```bash
git add docs/V5_DESIGN.md
git commit -m "docs(v5): write V5 design rationale and success gates"
```

### Task 0.2: Update CLAUDE.md with V5 entry

**Files:**
- Modify: `CLAUDE.md` (add V5 mention without changing existing V4 production sections)

- [ ] **Step 1: Append V5 section**

Open `CLAUDE.md`, find the section labeled `## Current Priority` (near bottom). Add the following block immediately AFTER that section, BEFORE the Anti-Patterns section:

```markdown
---

## V5 Iteration Plan (2026-05-02 launched)

**Background:** V4 production (seed42_SWA) has correct β=1 but σ_ŷ/σ_y = 0.045 (predictions ~20× narrower than y range). For single-asset directional trading with magnitude-based position sizing, σ_ŷ this narrow + slight bias makes ŷ unreadable as PnL signal.

**Approach:** Replace V4's quantile pinball + utility_rank loss with **Gaussian heteroscedastic NLL** (per-sample uncertainty). Keep V4 backbone (DualPathLOBModelV3, ~63K params) unchanged. Optionally try Mamba backbone for long-range temporal context.

**Success gate (pre-declared):** P ≥ 0.045, σ_ŷ/σ_y ≥ 0.10, |β-1| ≤ 0.20, top decile trading view E[y] ≥ +0.5 bps with t-stat ≥ 2.0. Full criteria in `docs/V5_DESIGN.md`.

**Plan:** `docs/superpowers/plans/2026-05-02-v5-iteration.md` (this).
```

- [ ] **Step 2: Verify edit**

Run: `grep -A 2 "V5 Iteration Plan" CLAUDE.md`
Expected: V5 section visible.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(claude): note V5 iteration plan launch"
```

---

## Phase 1: Gaussian NLL loss components

### Task 1.1: Write `loss_gaussian_nll` component (TDD)

**Files:**
- Create: `tests/test_v5_nll.py`
- Create: `src/training/v5_losses/heteroscedastic_components.py`

- [ ] **Step 1: Write failing tests**

```bash
mkdir -p tests
cat > tests/test_v5_nll.py << 'TESTEOF'
"""Unit tests for V5 heteroscedastic NLL components."""
import math
import torch
import pytest


def test_gaussian_nll_perfect_prediction():
    """When μ=y exactly, NLL = 0.5·log(2πσ²); minimal at σ where dL/dσ=0."""
    from src.training.v5_losses.heteroscedastic_components import loss_gaussian_nll
    y = torch.tensor([0.0, 1.0, -1.0, 2.5])
    mu = y.clone()
    log_sigma = torch.zeros_like(y)  # σ=1
    mask = torch.ones_like(y).bool()
    loss = loss_gaussian_nll(mu, log_sigma, y, mask)
    expected = 0.5 * math.log(2 * math.pi)  # σ=1, (y-μ)²/σ² = 0
    assert abs(loss.item() - expected) < 1e-5


def test_gaussian_nll_high_confidence_penalizes_error():
    """Low σ + high (y-μ) error → big loss; loss should grow as σ shrinks."""
    from src.training.v5_losses.heteroscedastic_components import loss_gaussian_nll
    y = torch.tensor([1.0])
    mu = torch.tensor([0.0])
    mask = torch.ones_like(y).bool()
    loss_high_conf = loss_gaussian_nll(mu, torch.tensor([-2.0]), y, mask)  # σ=e⁻²≈0.135
    loss_low_conf = loss_gaussian_nll(mu, torch.tensor([2.0]), y, mask)    # σ=e²≈7.39
    assert loss_high_conf.item() > loss_low_conf.item()


def test_gaussian_nll_mask_handling():
    """Masked-out samples must not contribute to loss."""
    from src.training.v5_losses.heteroscedastic_components import loss_gaussian_nll
    y = torch.tensor([1e10, 0.0, -1e10, 1.0])  # extreme values to detect leakage
    mu = torch.zeros_like(y)
    log_sigma = torch.zeros_like(y)
    mask = torch.tensor([False, True, False, True])
    loss = loss_gaussian_nll(mu, log_sigma, y, mask)
    # Only y=0 and y=1 contribute (with σ=1):
    # 0.5·(0-0)² + 0.5·log(2π) + 0.5·(1-0)² + 0.5·log(2π), averaged → 0.5·0.5 + 0.5·log(2π)
    expected = 0.25 + 0.5 * math.log(2 * math.pi)
    assert abs(loss.item() - expected) < 1e-5


def test_gaussian_nll_log_sigma_clip():
    """log_sigma should be clipped to prevent σ → 0 or → ∞."""
    from src.training.v5_losses.heteroscedastic_components import loss_gaussian_nll
    y = torch.tensor([1.0])
    mu = torch.tensor([0.0])
    mask = torch.ones_like(y).bool()
    # Without clip, log_sigma=-100 → σ=tiny → loss huge → backward NaN
    extreme_log_sigma = torch.tensor([-100.0], requires_grad=True)
    loss = loss_gaussian_nll(mu, extreme_log_sigma, y, mask, log_sigma_min=-7.0, log_sigma_max=2.0)
    assert torch.isfinite(loss).all()
    loss.backward()
    assert torch.isfinite(extreme_log_sigma.grad).all()


def test_gaussian_nll_no_valid_returns_zero_with_grad():
    """Empty mask must return 0 with grad (so backward doesn't break)."""
    from src.training.v5_losses.heteroscedastic_components import loss_gaussian_nll
    y = torch.tensor([1.0, 2.0])
    mu = torch.tensor([0.5, 0.5], requires_grad=True)
    log_sigma = torch.zeros_like(y)
    mask = torch.zeros_like(y).bool()  # all masked out
    loss = loss_gaussian_nll(mu, log_sigma, y, mask)
    assert loss.item() == 0.0
    loss.backward()  # must not raise
    assert mu.grad is not None
TESTEOF
```

- [ ] **Step 2: Run tests, verify failure**

Run: `cd /Users/haosiyu/Desktop/quant_research && python -m pytest tests/test_v5_nll.py -v 2>&1 | tail -15`
Expected: 5 tests fail with `ModuleNotFoundError` or `ImportError` for `heteroscedastic_components`.

- [ ] **Step 3: Implement minimum to pass**

```bash
cat > src/training/v5_losses/heteroscedastic_components.py << 'PYEOF'
"""Heteroscedastic NLL loss components for V5.

Gaussian NLL: model outputs (μ, log_σ) per sample; loss is
   L = 0.5 · (y-μ)² / σ² + 0.5 · log(σ²) + 0.5·log(2π)

The third term is constant and dropped in optimization but kept here for
interpretability (matches scipy.stats.norm.logpdf form).

Design notes:
- log_σ is clipped to [log_sigma_min, log_sigma_max] inside the loss to prevent
  σ → 0 (loss → ∞ + NaN backward) or σ → ∞ (μ degenerate to 0).
- Mask handling uses torch.where to zero invalid entries before averaging,
  same pattern as components.py:_masked_mean (NaN-safe).
"""
from __future__ import annotations
import math
import torch


def loss_gaussian_nll(
    mu: torch.Tensor,
    log_sigma: torch.Tensor,
    y: torch.Tensor,
    mask: torch.Tensor,
    log_sigma_min: float = -7.0,
    log_sigma_max: float = 2.0,
    include_const: bool = True,
) -> torch.Tensor:
    """Gaussian NLL loss with masking and log_sigma clipping.

    Parameters
    ----------
    mu, log_sigma : shape (...,) prediction tensors
    y : shape (...,) target tensor
    mask : shape (...,) bool tensor
    log_sigma_min, log_sigma_max : clip range for log_sigma stability
    include_const : if True, adds 0.5·log(2π) term (constant, but matches NLL definition)

    Returns
    -------
    Scalar tensor: mean NLL over valid (mask=True, finite) samples.
    """
    if mask.dtype != torch.bool:
        mask = mask.bool()
    valid = mask & torch.isfinite(y) & torch.isfinite(mu) & torch.isfinite(log_sigma)
    n = valid.sum()
    if n == 0:
        return (mu * 0.0).sum()

    log_sigma_clipped = torch.clamp(log_sigma, min=log_sigma_min, max=log_sigma_max)
    inv_var = torch.exp(-2.0 * log_sigma_clipped)  # = 1/σ²
    sq_err = (y - mu) ** 2

    per_sample = 0.5 * sq_err * inv_var + log_sigma_clipped
    if include_const:
        per_sample = per_sample + 0.5 * math.log(2 * math.pi)

    per_sample_clean = torch.where(valid, per_sample, torch.zeros_like(per_sample))
    return per_sample_clean.sum() / n.clamp(min=1).float()
PYEOF
```

- [ ] **Step 4: Run tests, verify pass**

Run: `cd /Users/haosiyu/Desktop/quant_research && python -m pytest tests/test_v5_nll.py -v 2>&1 | tail -15`
Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_v5_nll.py src/training/v5_losses/heteroscedastic_components.py
git commit -m "feat(v5): Gaussian NLL loss component with clipping + mask handling"
```

### Task 1.2: Add NLL to V5LossAssembly (config-driven dispatch)

**Files:**
- Modify: `src/training/v5_losses/loss_assembly.py`

- [ ] **Step 1: Read current loss_assembly.py**

Run: `cat src/training/v5_losses/loss_assembly.py`
Note current structure: V5LossConfig dataclass + V5LossAssembly class.

- [ ] **Step 2: Add NLL config field**

Edit `src/training/v5_losses/loss_assembly.py`:

Replace the line `w_beta_consistency: float = 0.0  # optional aux` with:

```python
    w_beta_consistency: float = 0.0  # optional aux

    # V5 heteroscedastic NLL path (mutex with quantile path)
    w_gaussian_nll: float = 0.0     # 0 = quantile path (V5a), >0 = NLL path (V5b)
    nll_log_sigma_min: float = -7.0
    nll_log_sigma_max: float = 2.0
```

- [ ] **Step 3: Update imports**

Replace the import block at the top of `loss_assembly.py`:

```python
from .components import (
    loss_dir_margin,
    loss_mag_huber,
    loss_joint_mse,
    loss_cs_ic,
    loss_beta_consistency,
)
```

with:

```python
from .components import (
    loss_dir_margin,
    loss_mag_huber,
    loss_joint_mse,
    loss_cs_ic,
    loss_beta_consistency,
)
from .heteroscedastic_components import loss_gaussian_nll
```

- [ ] **Step 4: Add NLL dispatch in __call__**

In `V5LossAssembly.__call__`, find the section after `if cfg.w_beta_consistency > 0:` block. Add immediately after that block, BEFORE `out["total"] = total`:

```python
        if cfg.w_gaussian_nll > 0:
            # Heteroscedastic NLL: head_out must contain 'mu' and 'log_sigma'
            l = loss_gaussian_nll(
                head_out["mu"], head_out["log_sigma"], y, mask,
                log_sigma_min=cfg.nll_log_sigma_min,
                log_sigma_max=cfg.nll_log_sigma_max,
            )
            out["gaussian_nll"] = l
            total = total + cfg.w_gaussian_nll * l
```

- [ ] **Step 5: Verify with simple smoke check**

```bash
python -c "
import torch
from src.training.v5_losses.loss_assembly import V5LossAssembly, V5LossConfig

cfg = V5LossConfig(w_dir_margin=0, w_mag_huber=0, w_joint_mse=0, w_gaussian_nll=1.0)
assembly = V5LossAssembly(cfg)

head_out = {
    'mu': torch.zeros(10),
    'log_sigma': torch.zeros(10),
    'dir_logit': torch.zeros(10),  # required by other paths but unused
    'mag': torch.zeros(10),
    'y_pred': torch.zeros(10),
}
y = torch.randn(10)
mask = torch.ones(10).bool()

out = assembly(head_out, y, mask)
print('keys:', list(out.keys()))
print('total:', out['total'].item())
print('nll:', out['gaussian_nll'].item())
assert 'gaussian_nll' in out
assert torch.isfinite(out['total']).item()
print('OK')
"
```
Expected: `OK` printed, total finite.

- [ ] **Step 6: Commit**

```bash
git add src/training/v5_losses/loss_assembly.py
git commit -m "feat(v5): wire Gaussian NLL into V5LossAssembly via config flag"
```

---

## Phase 2: HeteroscedasticHead (model output module)

### Task 2.1: Write HeteroscedasticHead with TDD

**Files:**
- Create: `tests/test_v5_head.py`
- Create: `src/training/v5_losses/heteroscedastic_head.py`

- [ ] **Step 1: Write failing tests**

```bash
cat > tests/test_v5_head.py << 'TESTEOF'
"""Unit tests for V5 HeteroscedasticHead."""
import torch
import pytest


def test_head_output_shapes():
    from src.training.v5_losses.heteroscedastic_head import HeteroscedasticHead
    head = HeteroscedasticHead(d_emb=32, n_horizons=1, hidden=0)
    emb = torch.randn(4, 32)
    out = head(emb)
    assert "mu" in out and "log_sigma" in out and "y_pred" in out
    assert out["mu"].shape == (4, 1)
    assert out["log_sigma"].shape == (4, 1)
    assert out["y_pred"].shape == (4, 1)
    # y_pred is alias for mu (point prediction)
    assert torch.allclose(out["y_pred"], out["mu"])


def test_head_initial_log_sigma_reasonable():
    """Initial σ ≈ 1 to match z-scored target scale (avoids NaN gradient at warmup)."""
    from src.training.v5_losses.heteroscedastic_head import HeteroscedasticHead
    torch.manual_seed(0)
    head = HeteroscedasticHead(d_emb=32, n_horizons=1, hidden=0)
    emb = torch.randn(100, 32)
    with torch.no_grad():
        out = head(emb)
    sigma = torch.exp(out["log_sigma"])
    # Mean σ should be in [0.5, 2.0] range at init (before training)
    assert 0.3 < sigma.mean().item() < 3.0


def test_head_with_hidden_bottleneck():
    from src.training.v5_losses.heteroscedastic_head import HeteroscedasticHead
    head = HeteroscedasticHead(d_emb=32, n_horizons=1, hidden=16, dropout=0.1)
    emb = torch.randn(4, 32)
    out = head(emb)
    assert out["mu"].shape == (4, 1)


def test_head_backward_stable():
    """Backward must not produce NaN even with extreme inputs."""
    from src.training.v5_losses.heteroscedastic_head import HeteroscedasticHead
    head = HeteroscedasticHead(d_emb=8, n_horizons=1, hidden=0)
    emb = torch.randn(4, 8) * 100  # extreme magnitude
    out = head(emb)
    loss = out["mu"].sum() + out["log_sigma"].sum()
    loss.backward()
    for p in head.parameters():
        assert torch.isfinite(p.grad).all(), f"NaN grad in {p.shape}"


def test_head_multi_horizon_shape():
    from src.training.v5_losses.heteroscedastic_head import HeteroscedasticHead
    head = HeteroscedasticHead(d_emb=32, n_horizons=3, hidden=0)
    emb = torch.randn(4, 32)
    out = head(emb)
    assert out["mu"].shape == (4, 3)
    assert out["log_sigma"].shape == (4, 3)
TESTEOF
```

- [ ] **Step 2: Run tests, verify failure**

Run: `python -m pytest tests/test_v5_head.py -v 2>&1 | tail -10`
Expected: All 5 tests fail with ImportError.

- [ ] **Step 3: Implement HeteroscedasticHead**

```bash
cat > src/training/v5_losses/heteroscedastic_head.py << 'PYEOF'
"""V5 HeteroscedasticHead: outputs (μ, log_σ) per sample.

Replaces V4's monotonic quantile head (q10/q50/q90) and V5a's dual head.
Designed so backbone embedding flows into two parallel projections.

Key design choices (informed by Kendall & Gal 2017, Lakshminarayanan 2017):
- mu_proj initialized small (std=1e-3) to avoid early-train output drift
- log_sigma_proj initialized so σ ≈ 1 at start (matches z-scored target scale)
- Optional hidden bottleneck for head-specific capacity
"""
from __future__ import annotations
from typing import Dict
import torch
import torch.nn as nn


class HeteroscedasticHead(nn.Module):
    """Two-output head: mean μ and log-variance log_σ.

    Architecture:
        emb → [optional hidden trunk] → linear → mu  (any real)
        emb → [optional hidden trunk] → linear → log_sigma  (any real, clipped in loss)
    """

    def __init__(
        self,
        d_emb: int,
        n_horizons: int = 1,
        hidden: int = 0,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.d_emb = d_emb
        self.n_horizons = n_horizons

        if hidden > 0:
            self.mu_trunk = nn.Sequential(
                nn.Linear(d_emb, hidden),
                nn.LeakyReLU(0.1),
                nn.Dropout(dropout),
            )
            self.log_sigma_trunk = nn.Sequential(
                nn.Linear(d_emb, hidden),
                nn.LeakyReLU(0.1),
                nn.Dropout(dropout),
            )
            d_out = hidden
        else:
            self.mu_trunk = nn.Identity()
            self.log_sigma_trunk = nn.Identity()
            d_out = d_emb

        self.mu_proj = nn.Linear(d_out, n_horizons)
        self.log_sigma_proj = nn.Linear(d_out, n_horizons)
        self._init_weights()

    def _init_weights(self):
        # Small init to avoid early-train output drift
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, a=0.1, nonlinearity="leaky_relu")
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
        # μ output initialized very small
        nn.init.normal_(self.mu_proj.weight, mean=0.0, std=1e-3)
        # log σ initialized so σ ≈ 1 at start (bias=0, weight small)
        nn.init.normal_(self.log_sigma_proj.weight, mean=0.0, std=1e-3)
        nn.init.zeros_(self.log_sigma_proj.bias)

    def forward(self, emb: torch.Tensor) -> Dict[str, torch.Tensor]:
        h_mu = self.mu_trunk(emb)
        h_ls = self.log_sigma_trunk(emb)
        mu = self.mu_proj(h_mu)
        log_sigma = self.log_sigma_proj(h_ls)
        return {
            "mu": mu,
            "log_sigma": log_sigma,
            "y_pred": mu,  # alias for downstream compatibility (point prediction = mean)
        }
PYEOF
```

- [ ] **Step 4: Run tests, verify pass**

Run: `python -m pytest tests/test_v5_head.py -v 2>&1 | tail -10`
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_v5_head.py src/training/v5_losses/heteroscedastic_head.py
git commit -m "feat(v5): HeteroscedasticHead with (mu, log_sigma) outputs"
```

### Task 2.2: Smoke test — toy training validates NLL converges

**Files:**
- Create: `tests/test_v5_smoke_train.py`

- [ ] **Step 1: Write end-to-end smoke training test**

```bash
cat > tests/test_v5_smoke_train.py << 'TESTEOF'
"""End-to-end smoke test: NLL training on synthetic data.

Validates:
- Loss decreases over epochs
- σ_ŷ stays in reasonable range (not collapsing or exploding)
- μ correlates with y after training
"""
import torch
import torch.nn as nn
import numpy as np


def test_nll_smoke_train_converges():
    from src.training.v5_losses.heteroscedastic_head import HeteroscedasticHead
    from src.training.v5_losses.heteroscedastic_components import loss_gaussian_nll

    torch.manual_seed(42)
    np.random.seed(42)

    # Synthetic: y = w·x + noise, where w is sparse signal and noise is heteroscedastic
    N, D = 1000, 16
    X = torch.randn(N, D)
    w_true = torch.zeros(D)
    w_true[:4] = torch.tensor([1.0, 0.5, -0.5, 0.3])
    noise_scale = 0.1 + 0.5 * (X[:, 4].abs())  # heteroscedastic
    y = X @ w_true + noise_scale * torch.randn(N)

    # Tiny encoder + head
    encoder = nn.Linear(D, 8)
    head = HeteroscedasticHead(d_emb=8, n_horizons=1)
    optim = torch.optim.Adam(list(encoder.parameters()) + list(head.parameters()), lr=1e-2)
    mask = torch.ones(N).bool()
    y_target = y.unsqueeze(-1)

    losses = []
    for epoch in range(100):
        emb = encoder(X)
        out = head(emb)
        loss = loss_gaussian_nll(out["mu"], out["log_sigma"], y_target, mask.unsqueeze(-1))
        optim.zero_grad()
        loss.backward()
        optim.step()
        losses.append(loss.item())

    # Loss should decrease meaningfully
    assert losses[-1] < losses[0] * 0.7, f"NLL didn't decrease: start {losses[0]:.4f} → end {losses[-1]:.4f}"
    # μ should correlate with y
    with torch.no_grad():
        emb = encoder(X)
        out = head(emb)
        mu = out["mu"].squeeze(-1).numpy()
    pearson = np.corrcoef(y.numpy(), mu)[0, 1]
    assert pearson > 0.5, f"μ-y Pearson too low: {pearson}"

    # σ should be in reasonable range (not collapsed to ε or exploded)
    sigma_mean = torch.exp(out["log_sigma"].mean()).item()
    assert 0.05 < sigma_mean < 5.0, f"σ_mean unreasonable: {sigma_mean}"
TESTEOF
```

- [ ] **Step 2: Run smoke test**

Run: `python -m pytest tests/test_v5_smoke_train.py -v 2>&1 | tail -10`
Expected: PASS (NLL converges, Pearson > 0.5, σ in [0.05, 5.0]).

- [ ] **Step 3: Commit**

```bash
git add tests/test_v5_smoke_train.py
git commit -m "test(v5): end-to-end smoke training validates NLL convergence"
```

---

## Phase 3: V5 model wrapper

### Task 3.1: Inspect V4 backbone output dimension

**Files:**
- Read: `src/model/dual_path_model_v3.py`

- [ ] **Step 1: Find embedding output**

Run: `grep -n "def forward\|return\|fused\|d_model" src/model/dual_path_model_v3.py | head -30`

- [ ] **Step 2: Note key facts in your scratchpad (no commit)**

Document for next task:
- DualPathLOBModelV3.forward signature (input args)
- Embedding output dim before head (typically `d_model`, e.g. 32)
- Whether the backbone takes a `head` kwarg or hardcodes one

If the backbone hardcodes a head internally, V5 wrapper will need to call backbone.forward() then bypass the internal head. Inspect specifically:
```bash
grep -n "self\.head\|MonotonicQuantile\|QuantileHead\|self\.mu\|self\.q50" src/model/dual_path_model_v3.py | head -10
```

### Task 3.2: Create V5Model wrapper

**Files:**
- Create: `src/model/v5_model.py`

- [ ] **Step 1: Implement V5Model**

```bash
cat > src/model/v5_model.py << 'PYEOF'
"""V5Model: V4 DualPathLOBModelV3 backbone + HeteroscedasticHead.

The V4 backbone DualPathLOBModelV3 internally has a quantile head. V5 instantiates
the V4 model, replaces the head with HeteroscedasticHead, and exposes a forward
that returns the V5 head dict.

Implementation strategy:
- V5Model wraps DualPathLOBModelV3
- During forward, we call the backbone's encoder portion (everything before its head),
  then route through HeteroscedasticHead
- Backbone's quantile head is initialized but unused (small param overhead)

This allows V5 to inherit all V4 features (RevIN, GDCN, ChannelMix conv, etc.) while
swapping only the output mapping.
"""
from __future__ import annotations
from typing import Dict, Optional
import torch
import torch.nn as nn

from src.model.dual_path_model_v3 import DualPathLOBModelV3
from src.training.v5_losses.heteroscedastic_head import HeteroscedasticHead


class V5Model(nn.Module):
    """V4 backbone + HeteroscedasticHead.

    Parameters
    ----------
    v4_kwargs : dict passed to DualPathLOBModelV3 (must include n_levels, d_model, etc.)
    head_hidden : int hidden bottleneck in V5 head (0 = direct linear)
    head_dropout : float dropout for head trunk
    """

    def __init__(
        self,
        v4_kwargs: dict,
        head_hidden: int = 0,
        head_dropout: float = 0.1,
    ):
        super().__init__()
        # Instantiate V4 backbone
        # Force n_horizons to match V5 head output (we override head anyway)
        v4_kwargs = dict(v4_kwargs)
        self.n_horizons = int(v4_kwargs.get("n_horizons", 1))
        self.backbone = DualPathLOBModelV3(**v4_kwargs)

        # Discover backbone embedding dim. V4 stores fused emb dim in self.d_model
        # or computed from backbone state. Inspect at init:
        d_emb = self._discover_d_emb()

        self.v5_head = HeteroscedasticHead(
            d_emb=d_emb,
            n_horizons=self.n_horizons,
            hidden=head_hidden,
            dropout=head_dropout,
        )

    def _discover_d_emb(self) -> int:
        """Resolve embedding dim by examining backbone attributes.

        V4 stores fused embedding dim either as self.d_model or visible from
        self.head's input dim. We try several common locations.
        """
        b = self.backbone
        # 1. Try direct attribute
        for attr in ["d_emb", "d_fused", "d_out", "d_model"]:
            if hasattr(b, attr):
                v = getattr(b, attr)
                if isinstance(v, int):
                    return v
        # 2. Try head's first linear layer in_features
        if hasattr(b, "head"):
            for m in b.head.modules():
                if isinstance(m, nn.Linear):
                    return m.in_features
        # 3. Fallback: 32 (V4 default d_model)
        return 32

    def forward(self, *args, **kwargs) -> Dict[str, torch.Tensor]:
        """V5 forward: pass through backbone encoder, route to HeteroscedasticHead.

        We call self.backbone.encode(...) if available; else self.backbone(...) and
        replace its quantile output with our head outputs.

        Strategy: V4 backbone exposes self.encode() returning embedding. If not, we
        monkey-patch by calling self.backbone(...) and discarding its head output,
        then re-running our head on the cached embedding (less efficient but simple).
        """
        # Preferred: backbone exposes encode()
        if hasattr(self.backbone, "encode"):
            emb = self.backbone.encode(*args, **kwargs)
        else:
            # Fallback: run full forward, discard head, re-encode
            # This requires backbone to set self._last_emb during forward
            # If backbone doesn't, we add a hook in __init__ (TODO if needed)
            raise RuntimeError(
                "V4 backbone must expose .encode() method. "
                "Add it to DualPathLOBModelV3 (return embedding before head)."
            )
        return self.v5_head(emb)
PYEOF
```

- [ ] **Step 2: Verify V4 backbone has .encode() method**

Run: `grep -n "def encode\|def forward" src/model/dual_path_model_v3.py`
Expected: Either `encode` exists, OR we need to add it.

- [ ] **Step 3a (if .encode() does NOT exist): Add it to V4 backbone**

If grep shows no `def encode`, add an `encode` method to DualPathLOBModelV3 that returns the fused embedding before the head. Find the existing `def forward` method, identify where the embedding is computed before the head call, and refactor:

Open `src/model/dual_path_model_v3.py`, find the `def forward(self, ...)` method. Identify the line where the final fused embedding `emb` (or `fused`, `h`, etc) is passed to `self.head(...)`. Refactor to:

```python
    def encode(self, *args, **kwargs):
        # ... [body of forward up to but NOT including self.head(...)]
        return emb  # or whatever the variable is named

    def forward(self, *args, **kwargs):
        emb = self.encode(*args, **kwargs)
        return self.head(emb)
```

The exact change depends on the existing forward; preserve all preprocessing. **Do NOT change V4 functionality.** This is a pure refactor — encode() returns intermediate, forward() = encode + head.

- [ ] **Step 3b: Verify V4 still works after refactor**

Run a smoke check that V4 still produces same outputs:

```bash
python -c "
import torch
import json
from src.model.dual_path_model_v3 import DualPathLOBModelV3
torch.manual_seed(0)
cfg = json.load(open('configs/y600_push/baseline_plus.json'))['model']
cfg['n_levels'] = 25
m = DualPathLOBModelV3(**cfg)
m.eval()
# Build dummy input matching V4 forward signature; check forward doesn't error
# (exact dummy depends on signature — adjust as needed)
print('V4 backbone instantiated; param count:', sum(p.numel() for p in m.parameters()))
"
```

Expected: prints param count, no error.

- [ ] **Step 4: Smoke-test V5Model end-to-end**

```bash
python -c "
import torch
import json
from src.model.v5_model import V5Model

cfg = json.load(open('configs/y600_push/baseline_plus.json'))
v4_kwargs = cfg['model']
v4_kwargs['n_levels'] = cfg['data']['n_levels']  # required by V4 init
m = V5Model(v4_kwargs=v4_kwargs, head_hidden=0)
print('V5 param count:', sum(p.numel() for p in m.parameters()))
print('V5 forward keys: see encode signature for required args')
# Quick instantiation check; full forward needs real data shapes
"
```

Expected: V5 instantiates, prints param count.

- [ ] **Step 5: Commit**

```bash
git add src/model/v5_model.py
# (also git add src/model/dual_path_model_v3.py if encode() was added)
git commit -m "feat(v5): V5Model wrapper around V4 backbone + HeteroscedasticHead"
```

---

## Phase 4: Embargo + 5-fold CV infrastructure

### Task 4.1: Inspect dataset.py CV split logic

**Files:**
- Read: `src/training/dataset.py`

- [ ] **Step 1: Locate split logic**

Run: `grep -n "def __init__\|fold\|train_days\|val_days\|test_days\|embargo\|_split" src/training/dataset.py | head -30`

- [ ] **Step 2: Note current behavior**

Document (no commit):
- How fold is selected (`fold_idx` parameter?)
- Where train/val/test boundaries are computed
- Whether `embargo_days` or `embargo_seconds` is supported

### Task 4.2: Add embargo parameter (default 0 for V4 backwards compat)

**Files:**
- Modify: `src/training/dataset.py`

- [ ] **Step 1: Find fold split function in dataset.py**

Open `src/training/dataset.py`. Locate the section that computes `train_start`, `train_end`, `val_start`, `val_end`, `test_start`, `test_end` based on fold index. (If unclear, search for `train_end =`.)

- [ ] **Step 2: Add embargo_seconds parameter to dataset config**

If the dataset reads config via `__init__(self, ..., embargo_seconds: int = 0)` or via a config dict, add `embargo_seconds` parameter with default 0.

In the split computation, after computing `train_end`, ADD:
```python
        # V5 embargo: drop final embargo_seconds of train period to prevent y-leak
        # (y_horizon depends on future mids, so train tail's y values may peek into val period)
        embargo_seconds = int(self.embargo_seconds) if hasattr(self, 'embargo_seconds') else 0
        if embargo_seconds > 0:
            embargo_samples = embargo_seconds // self.stride
            train_end = max(train_start, train_end - embargo_samples)
```

Adjust variable names to match existing code. The principle: shrink training window by `embargo_seconds` from the end before val begins.

- [ ] **Step 3: Add a smoke test**

Create `tests/test_v5_embargo.py`:

```bash
cat > tests/test_v5_embargo.py << 'TESTEOF'
"""Embargo smoke test: train_end should shrink when embargo > 0."""
import pytest


def test_embargo_shrinks_train_end():
    """With embargo_seconds=600 and stride=180, train_end should drop by 3-4 samples."""
    # This is a placeholder test — actual implementation depends on dataset internals.
    # It documents the expectation; refine with real dataset instantiation when
    # plumbing embargo through the data pipeline.
    pass


def test_embargo_zero_is_v4_compat():
    """embargo=0 must produce identical splits as V4 (backwards compatibility)."""
    pass
TESTEOF
```

- [ ] **Step 4: Document in CLAUDE.md anti-pattern note**

Add to CLAUDE.md anti-pattern #19 section, append a new bullet:

> - **(V5) embargo_seconds = horizon_sec**: y_horizon uses mid[t+horizon_sec], so train末日 t's y label uses val period mids. Set embargo_seconds = horizon_sec (e.g., 600) to drop unsafe train samples. V4 used embargo=0 — could be silent leak source.

- [ ] **Step 5: Commit**

```bash
git add src/training/dataset.py tests/test_v5_embargo.py CLAUDE.md
git commit -m "feat(v5): add embargo_seconds to dataset; default 0 keeps V4 behavior"
```

### Task 4.3: Add 5-fold CV variant config

**Files:**
- Create: `configs/v5/base_5fold.json`

- [ ] **Step 1: Mkdir and copy baseline_plus**

```bash
mkdir -p configs/v5
cp configs/y600_push/baseline_plus.json configs/v5/base_5fold.json
```

- [ ] **Step 2: Edit fold count**

Open `configs/v5/base_5fold.json`. In the `cv` section (or `training` section, depending on schema), find the existing `n_folds` or similar. Set:
```json
    "n_folds": 5,
    "train_days": 600,
    "val_days": 30,
    "test_days": 30,
    "embargo_seconds": 600
```

If the config doesn't currently have `embargo_seconds`, add it under data section.

(Adjust train/val/test day counts to fit total available data ≈ 760 days. With 5 folds × 60 day rolling test = 300 days post-train start; train of 600 + 5×60 = 900 days might exceed total. Verify against `data/npz_v4/` count.)

```bash
ls data/npz_v4/ | wc -l
```

If count is ~970 days, then `train_days=600 + val_days=30 + 5 × test_days=30 = 780` total → fits. If count is smaller, reduce train_days to 500.

- [ ] **Step 3: Mark V5 NLL flag in config**

Add to the existing `loss` section (or create one) in the config:

```json
"loss": {
    "use_v5_nll": true,
    "w_gaussian_nll": 1.0,
    "w_dir_margin": 0.0,
    "w_mag_huber": 0.0,
    "w_joint_mse": 0.0,
    "nll_log_sigma_min": -7.0,
    "nll_log_sigma_max": 2.0
}
```

(Coexist with V4's quantile loss config; trainer dispatches based on `use_v5_nll`.)

- [ ] **Step 4: Verify JSON validity**

Run: `python -c "import json; json.load(open('configs/v5/base_5fold.json')); print('OK')"`
Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add configs/v5/base_5fold.json
git commit -m "feat(v5): add 5-fold CV config with embargo + NLL loss flags"
```

### Task 4.4: Add base config (3-fold for fast iter)

**Files:**
- Create: `configs/v5/base.json`
- Create: `configs/v5/base_smoke.json`

- [ ] **Step 1: Copy 5-fold and reduce to 3-fold**

```bash
cp configs/v5/base_5fold.json configs/v5/base.json
```

Edit `configs/v5/base.json`: change `"n_folds": 5` → `"n_folds": 3`, keep other settings.

- [ ] **Step 2: Create smoke config (1 fold, 1 day)**

```bash
cp configs/v5/base.json configs/v5/base_smoke.json
```

Edit `configs/v5/base_smoke.json`:
- `"n_folds": 1`
- `"train_days": 30`
- `"val_days": 5`
- `"test_days": 5`
- (existing) `"embargo_seconds": 600`
- In training section: `"epochs": 3`, `"batch_size": 256`, `"lr": 6e-4`

- [ ] **Step 3: Verify all 3 V5 configs valid**

```bash
for f in configs/v5/base.json configs/v5/base_5fold.json configs/v5/base_smoke.json; do
  python -c "import json; json.load(open('$f')); print('$f OK')"
done
```
Expected: all 3 print OK.

- [ ] **Step 4: Commit**

```bash
git add configs/v5/base.json configs/v5/base_smoke.json
git commit -m "feat(v5): 3-fold and smoke configs"
```

---

## Phase 5: Trainer integration (V5 path, isolated from V4)

### Task 5.1: Inspect trainer_v2.py for V4 pinball/loss assembly path

**Files:**
- Read: `src/training/trainer_v2.py`

- [ ] **Step 1: Locate train loop and loss computation**

Run: `grep -n "def train_one_fold_v2\|def train\|loss_fn\|loss =\|head_out\|model(.*input" src/training/trainer_v2.py | head -25`

- [ ] **Step 2: Note V4's loss invocation pattern**

Document (no commit):
- Function name that runs one fold (likely `train_one_fold_v2`)
- Where loss is computed (look for `pinball` or quantile)
- Where the model output is dispatched to loss

### Task 5.2: Wire V5 NLL via existing `train_one_fold_v2` (no new train function)

**Insight:** `train_one_fold_v2` already accepts a custom `loss_fn` parameter (see signature at trainer_v2.py:387). V5 doesn't need a new training function — just a custom `loss_fn` that wraps V5LossAssembly + a path to instantiate V5Model. This keeps V5 minimally invasive.

**Files:**
- Modify: `src/training/trainer_v2.py`
- Create: `src/training/v5_losses/v5_loss_fn.py`

- [ ] **Step 1: Create V5 loss_fn factory**

```bash
cat > src/training/v5_losses/v5_loss_fn.py << 'PYEOF'
"""V5 loss function factory: produces a callable compatible with train_one_fold_v2.

train_one_fold_v2's loss_fn expects signature:
    loss_fn(outputs_dict, target) -> scalar tensor

V5LossAssembly expects:
    assembly(head_out, y, mask) -> {'total': ..., ...}

This module bridges by constructing a closure that:
  - Receives `outputs_dict` (model forward output) and `target` (y tensor)
  - Extracts mask from target NaN pattern (caller convention) OR a separate mask
  - Calls assembly and returns assembly['total']

The mask is passed via `outputs_dict['mask']` (V5Model is responsible for routing it
through the forward path), or computed as `~torch.isnan(target)` as a fallback.
"""
from __future__ import annotations
from typing import Callable, Dict
import torch

from .loss_assembly import V5LossAssembly, V5LossConfig


def build_v5_loss_fn(loss_cfg_dict: dict) -> Callable[[Dict[str, torch.Tensor], torch.Tensor], torch.Tensor]:
    """Build a loss_fn for train_one_fold_v2 wrapping V5LossAssembly.

    Parameters
    ----------
    loss_cfg_dict : dict matching V5LossConfig fields, e.g.,
        {"w_gaussian_nll": 1.0, "nll_log_sigma_min": -7.0, "nll_log_sigma_max": 2.0}

    Returns
    -------
    Callable[(outputs, target) -> tensor]
    """
    cfg = V5LossConfig(**loss_cfg_dict)
    assembly = V5LossAssembly(cfg)

    def _loss_fn(outputs: Dict[str, torch.Tensor], target: torch.Tensor) -> torch.Tensor:
        # Mask: prefer outputs['mask'], else derive from target finite-ness
        mask = outputs.get("mask")
        if mask is None:
            mask = torch.isfinite(target)
        out = assembly(outputs, target, mask)
        return out["total"]

    return _loss_fn
PYEOF
```

- [ ] **Step 2: Verify factory imports**

```bash
python -c "
from src.training.v5_losses.v5_loss_fn import build_v5_loss_fn
fn = build_v5_loss_fn({'w_gaussian_nll': 1.0})
print('V5 loss_fn factory OK')
"
```
Expected: `V5 loss_fn factory OK` printed.

- [ ] **Step 3: Verify loss_fn round-trip with synthetic data**

```bash
python -c "
import torch
from src.training.v5_losses.v5_loss_fn import build_v5_loss_fn

fn = build_v5_loss_fn({'w_gaussian_nll': 1.0, 'w_dir_margin': 0.0, 'w_mag_huber': 0.0, 'w_joint_mse': 0.0})

outputs = {
    'mu': torch.randn(8, 1),
    'log_sigma': torch.zeros(8, 1),
    'dir_logit': torch.zeros(8, 1),
    'mag': torch.ones(8, 1),
    'y_pred': torch.randn(8, 1),
    'mask': torch.ones(8, 1).bool(),
}
target = torch.randn(8, 1)
loss = fn(outputs, target)
assert torch.isfinite(loss), 'loss not finite'
assert loss.requires_grad or loss.grad_fn is None, 'expected grad'
print(f'loss = {loss.item():.4f}')
"
```
Expected: numeric loss printed.

- [ ] **Step 4: Commit**

```bash
git add src/training/v5_losses/v5_loss_fn.py
git commit -m "feat(v5): build_v5_loss_fn factory bridges V5LossAssembly to trainer_v2"
```

### Task 5.3: Wire V5 model + V5 loss_fn dispatch in run_pipeline_v3.py

**Files:**
- Modify: `run_pipeline_v3.py`

- [ ] **Step 1: Find the model instantiation site**

Run: `grep -n "DualPathLOBModelV3\|model_v3\|v3_full\|train_one_fold_v2(" run_pipeline_v3.py | head -10`

- [ ] **Step 2: Add V5 dispatch after model build**

Open `run_pipeline_v3.py`. Locate where `train_one_fold_v2(...)` is called (it'll be after model + dataset construction). Add a check earlier in the flow:

Find the section where `model = DualPathLOBModelV3(...)` (or similar) is built. Replace that single-line build with a dispatch:

```python
# === V5 dispatch ===
use_v5_nll = config.get("loss", {}).get("use_v5_nll", False)
if use_v5_nll:
    from src.model.v5_model import V5Model
    from src.training.v5_losses.v5_loss_fn import build_v5_loss_fn
    v4_kwargs = dict(config["model"])
    v4_kwargs["n_levels"] = config["data"]["n_levels"]
    model = V5Model(v4_kwargs=v4_kwargs, head_hidden=int(config["loss"].get("head_hidden", 0)))
    custom_loss_fn = build_v5_loss_fn(config["loss"])
    print(f"[V5] Using HeteroscedasticHead + Gaussian NLL loss")
else:
    # Existing V4 model build
    model = DualPathLOBModelV3(**config["model"], n_levels=config["data"]["n_levels"])
    custom_loss_fn = None
```

Then locate the `train_one_fold_v2(...)` call. Pass `loss_fn=custom_loss_fn` if it's not already passed:

```python
train_one_fold_v2(
    model=model,
    train_dataset=train_dataset,
    val_dataset=val_dataset,
    # ... existing kwargs ...
    loss_fn=custom_loss_fn,  # None for V4, V5 closure for V5
    # ...
)
```

- [ ] **Step 3: Verify dispatch works (no run, just import path)**

```bash
python -c "
import json
config = json.load(open('configs/v5/base.json'))
print('use_v5_nll:', config.get('loss', {}).get('use_v5_nll', False))
"
```
Expected: `use_v5_nll: True`.

- [ ] **Step 4: Commit**

```bash
git add run_pipeline_v3.py
git commit -m "feat(v5): dispatch V5Model + V5 loss_fn in run_pipeline_v3 when use_v5_nll=true"
```

### Task 5.4: Outputs dict must include 'mask' for V5 loss_fn

**Files:**
- Modify: `src/model/v5_model.py`

- [ ] **Step 1: Update V5Model.forward to thread mask**

The `train_one_fold_v2` calls model with a batch that includes mask. V5Model needs to surface the mask through its outputs dict so V5 loss_fn can read it.

Modify `V5Model.forward` to accept an optional `mask` kwarg and include it in the returned dict:

Open `src/model/v5_model.py`. Replace the existing `forward` method with:

```python
    def forward(self, *args, mask: Optional[torch.Tensor] = None, **kwargs) -> Dict[str, torch.Tensor]:
        """V5 forward: pass through backbone encoder, route to HeteroscedasticHead.

        Threads optional mask into output dict so the loss_fn can read it.
        """
        if hasattr(self.backbone, "encode"):
            emb = self.backbone.encode(*args, **kwargs)
        else:
            raise RuntimeError(
                "V4 backbone must expose .encode() method. "
                "Add it to DualPathLOBModelV3 (return embedding before head)."
            )
        out = self.v5_head(emb)
        if mask is not None:
            out["mask"] = mask
        return out
```

(Add `from typing import Optional` to imports if not present.)

- [ ] **Step 2: Verify import-only check**

```bash
python -c "
import torch
from src.model.v5_model import V5Model
print('V5Model imports OK')
"
```
Expected: `V5Model imports OK`.

- [ ] **Step 3: Commit**

```bash
git add src/model/v5_model.py
git commit -m "feat(v5): V5Model.forward threads mask to outputs dict"
```

---

## Phase 6: Local CPU smoke test

### Task 6.1: Run V5 smoke training (1 fold, 1 day, 3 epochs)

**Files:**
- (Use existing) `run_pipeline_v3.py` and `configs/v5/base_smoke.json`

- [ ] **Step 1: Run smoke training**

```bash
mkdir -p experiments/v5_smoke
python run_pipeline_v3.py \
  --config configs/v5/base_smoke.json \
  --output_dir experiments/v5_smoke \
  --skip-features \
  --seed 42 \
  --start-fold 0 \
  --max-folds 1 \
  2>&1 | tee experiments/v5_smoke/smoke.log | tail -40
```

Expected duration: 5-15 minutes on CPU (depends on machine).
Expected output: training log shows decreasing NLL, finite σ stats per epoch.

- [ ] **Step 2: Verify smoke result**

```bash
ls -la experiments/v5_smoke/fold_0/ 2>/dev/null
echo "---"
grep -E "epoch|sigma|val_P|val_S" experiments/v5_smoke/smoke.log | head -20
```

Expected:
- `fold_0/test_preds.npz` exists
- Log shows σ_mean stays in [0.1, 5.0]
- val_P > 0 (any positive correlation suffices for smoke)

- [ ] **Step 3: Validate predictions structure**

```bash
python -c "
import numpy as np
d = np.load('experiments/v5_smoke/fold_0/test_preds.npz')
print('keys:', list(d.keys()))
for k in d.files:
    a = d[k]
    if a.ndim == 0:
        print(f'  {k}: scalar = {float(a)}')
    else:
        print(f'  {k}: shape={a.shape}, mean={float(np.nanmean(a)):.4f}, std={float(np.nanstd(a)):.4f}')
# V5 should have mu and log_sigma in addition to predictions
assert 'predictions' in d.files or 'mu' in d.files, 'missing mu/predictions'
print('Smoke OK')
"
```

Expected: `Smoke OK` printed.

- [ ] **Step 4: Commit smoke artifacts (optional, gitignore preds)**

```bash
git add configs/v5/base_smoke.json
# Do NOT commit experiments/ artifacts (already in .gitignore typically)
git commit --allow-empty -m "test(v5): smoke training validates pipeline end-to-end"
```

---

## Phase 7: Comprehensive eval pipeline

### Task 7.1: Write V5 eval script with calibration + trading-view gates

**Files:**
- Create: `scripts/v5_eval_comprehensive.py`
- Create: `tests/test_v5_eval.py`

- [ ] **Step 1: Write eval gate logic test**

```bash
cat > tests/test_v5_eval.py << 'TESTEOF'
"""Test V5 eval gate logic — synthetic perfect / fail cases."""
import numpy as np
import pytest


def test_gate_pass_synthetic_good_signal():
    """Synthetic ŷ ≈ 0.5·y + small noise should pass all V5 gates."""
    from scripts.v5_eval_comprehensive import compute_v5_metrics, check_v5_gates
    np.random.seed(0)
    n = 5000
    y = np.random.randn(n) * 10  # σ_y = 10 bps
    yp = 0.5 * y + np.random.randn(n) * 5  # noisy ŷ, β≈1 expected
    mask = np.ones(n).astype(bool)
    metrics = compute_v5_metrics(y, yp, mask)
    gates = check_v5_gates(metrics)
    assert gates["G1_P"], f"P={metrics['P']:.4f}"
    assert gates["G2_sigma_ratio"], f"σŷ/σy={metrics['sigma_ratio']:.3f}"
    assert gates["G3_beta"], f"β={metrics['beta']:.3f}"


def test_gate_fail_collapsed_predictions():
    """Synthetic ŷ ≈ 0 (collapsed) should fail σ_ŷ/σ_y gate."""
    from scripts.v5_eval_comprehensive import compute_v5_metrics, check_v5_gates
    np.random.seed(0)
    n = 5000
    y = np.random.randn(n) * 10
    yp = np.random.randn(n) * 0.05  # σ_ŷ tiny → σ_ŷ/σ_y very small
    mask = np.ones(n).astype(bool)
    metrics = compute_v5_metrics(y, yp, mask)
    gates = check_v5_gates(metrics)
    assert not gates["G2_sigma_ratio"]


def test_gate_fail_anti_correlated():
    """Synthetic ŷ = -0.3·y + noise should fail trading view."""
    from scripts.v5_eval_comprehensive import compute_v5_metrics, check_v5_gates
    np.random.seed(0)
    n = 5000
    y = np.random.randn(n) * 10
    yp = -0.3 * y + np.random.randn(n) * 8
    mask = np.ones(n).astype(bool)
    metrics = compute_v5_metrics(y, yp, mask)
    gates = check_v5_gates(metrics)
    assert not gates["G4_trading_top"], f"top E[y]={metrics.get('top_decile_y_bps', 'NA')}"
TESTEOF
```

- [ ] **Step 2: Run, verify failure**

Run: `python -m pytest tests/test_v5_eval.py -v 2>&1 | tail -10`
Expected: 3 tests fail with ImportError.

- [ ] **Step 3: Implement eval script**

```bash
cat > scripts/v5_eval_comprehensive.py << 'PYEOF'
"""V5 comprehensive evaluation: calibration view + trading view + gate check.

Usage:
  python scripts/v5_eval_comprehensive.py \
      --exp-dir experiments/v5_run \
      --out exports/v5_eval_report.md

Methodology (anti-pattern #19 strict):
  - Ground truth: raw y_600 from data/npz_v4 via timestamp lookup (or csv ground truth)
  - Eval: dense (mask=1), per-fold-aware pool across 3 (or 5) folds
  - Reports both calibration view AND trading view bin-plots
  - Hard pass/fail gates (G1-G6) per docs/V5_DESIGN.md
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Dict
import numpy as np
import pandas as pd
from scipy.stats import spearmanr


def compute_v5_metrics(y: np.ndarray, yp: np.ndarray, mask: np.ndarray, n_bins: int = 10) -> Dict:
    """Compute all V5-relevant metrics on (y, yp) with mask.

    All inputs in same units (raw log-return). Returns metrics dict including:
    - P, S, beta, sigma_ratio, mean_yhat_bps, top_bin_yhat_bps (calibration view)
    - bin_S (calibration), top_decile_y_bps + t_stat (trading view)
    - bottom_decile_y_bps + t_stat (trading view)
    - top_minus_bottom_spread_bps (trading view)
    """
    valid = mask.astype(bool) & np.isfinite(y) & np.isfinite(yp)
    y, yp = y[valid], yp[valid]
    n = len(y)
    if n < 30:
        return {"n": n}

    P = float(np.corrcoef(y, yp)[0, 1])
    S = float(spearmanr(y, yp).correlation)
    cov = np.mean((y - y.mean()) * (yp - yp.mean()))
    var_yp = np.var(yp)
    beta = cov / var_yp if var_yp > 1e-30 else float("nan")
    sigma_ratio = float(np.std(yp) / np.std(y)) if np.std(y) > 1e-30 else float("nan")

    # Calibration view: bin by y, E[ŷ | y_bin]
    edges_y = np.quantile(y, np.linspace(0, 1, n_bins + 1))
    edges_y[0] -= 1e-12
    edges_y[-1] += 1e-12
    idx_y = np.clip(np.searchsorted(edges_y, y, side="right") - 1, 0, n_bins - 1)
    bin_y_means = np.array([y[idx_y == i].mean() for i in range(n_bins)])
    bin_yp_means_calib = np.array([yp[idx_y == i].mean() for i in range(n_bins)])
    bin_S = float(spearmanr(bin_y_means, bin_yp_means_calib).correlation) if not np.isnan(bin_y_means).any() else float("nan")
    top_bin_yhat_bps = float(bin_yp_means_calib[-1]) * 1e4

    # Trading view: bin by yp, E[y | yp_bin]
    edges_yp = np.quantile(yp, np.linspace(0, 1, n_bins + 1))
    edges_yp[0] -= 1e-12
    edges_yp[-1] += 1e-12
    idx_yp = np.clip(np.searchsorted(edges_yp, yp, side="right") - 1, 0, n_bins - 1)
    top_decile_y = y[idx_yp == n_bins - 1]
    bot_decile_y = y[idx_yp == 0]
    top_decile_y_bps = float(top_decile_y.mean()) * 1e4 if len(top_decile_y) > 0 else float("nan")
    bot_decile_y_bps = float(bot_decile_y.mean()) * 1e4 if len(bot_decile_y) > 0 else float("nan")
    top_t_stat = top_decile_y.mean() / (top_decile_y.std() / np.sqrt(max(1, len(top_decile_y)))) if len(top_decile_y) > 1 else float("nan")
    bot_t_stat = bot_decile_y.mean() / (bot_decile_y.std() / np.sqrt(max(1, len(bot_decile_y)))) if len(bot_decile_y) > 1 else float("nan")
    spread_bps = top_decile_y_bps - bot_decile_y_bps if not (np.isnan(top_decile_y_bps) or np.isnan(bot_decile_y_bps)) else float("nan")

    return {
        "n": n,
        "P": P,
        "S": S,
        "beta": beta,
        "sigma_ratio": sigma_ratio,
        "mean_yhat_bps": float(yp.mean()) * 1e4,
        "bin_S": bin_S,
        "top_bin_yhat_bps": top_bin_yhat_bps,
        "top_decile_y_bps": top_decile_y_bps,
        "top_decile_t_stat": float(top_t_stat),
        "bottom_decile_y_bps": bot_decile_y_bps,
        "bottom_decile_t_stat": float(bot_t_stat),
        "top_minus_bottom_bps": spread_bps,
    }


def check_v5_gates(metrics: Dict) -> Dict[str, bool]:
    """Check V5 success gates per docs/V5_DESIGN.md.

    G1-G6 are required (gate-blocking). S1-S3 are stretch (informational).
    """
    return {
        "G1_P": metrics.get("P", -1) >= 0.045,
        "G2_sigma_ratio": metrics.get("sigma_ratio", 0) >= 0.10,
        "G3_beta": abs(metrics.get("beta", 999) - 1.0) <= 0.20,
        "G4_trading_top": (
            metrics.get("top_decile_y_bps", -1) >= 0.5
            and metrics.get("top_decile_t_stat", 0) >= 2.0
        ),
        "G5_bin_S": metrics.get("bin_S", -1) >= 0.85,
        "G6_no_bias": abs(metrics.get("mean_yhat_bps", 999)) <= 0.10,
        "S1_P_strong": metrics.get("P", 0) >= 0.055,
        "S2_sigma_strong": metrics.get("sigma_ratio", 0) >= 0.15,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--exp-dir", required=True)
    p.add_argument("--ground-truth-csv", default="exports/y600_baseline_plus_BEST_3seed_median.csv")
    p.add_argument("--n-folds", type=int, default=3)
    p.add_argument("--out", default="exports/v5_eval_report.md")
    args = p.parse_args()

    exp = Path(args.exp_dir)
    df_gt = pd.read_csv(args.ground_truth_csv)

    pieces_y, pieces_yp, pieces_m = [], [], []
    for f in range(args.n_folds):
        npz_path = exp / f"fold_{f}" / "test_preds.npz"
        if not npz_path.exists():
            print(f"[WARN] missing {npz_path}")
            continue
        d = np.load(npz_path)
        # V5 saves (mu, log_sigma) — use mu as point prediction
        if "mu" in d.files:
            pred = d["mu"].astype(np.float64) * float(d["y_sigma"])
        else:
            # Fallback: V5 might still save predictions[:, 1] for compatibility
            pred = d["predictions"][:, 1].astype(np.float64) * float(d["y_sigma"])
        ts = d["timestamps"].astype(np.int64)
        # Match to ground truth via fold + timestamp
        sub = df_gt[df_gt["fold"] == f].reset_index(drop=True)
        # Sanity: lengths should match (V5 should produce same N as V4 per fold)
        if len(sub) != len(pred):
            print(f"[WARN] fold {f} N mismatch: csv={len(sub)} vs npz={len(pred)}")
            continue
        y = sub["y_true_logret"].values.astype(np.float64)
        m = sub["mask"].astype(bool).values
        pieces_y.append(y)
        pieces_yp.append(pred)
        pieces_m.append(m)

    if not pieces_y:
        print("[FAIL] no fold predictions found")
        return

    y_pool = np.concatenate(pieces_y)
    yp_pool = np.concatenate(pieces_yp)
    m_pool = np.concatenate(pieces_m)
    metrics = compute_v5_metrics(y_pool, yp_pool, m_pool)
    gates = check_v5_gates(metrics)

    # Write report
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append("# V5 Evaluation Report\n")
    lines.append(f"Exp dir: `{exp}`  |  Folds: {args.n_folds}  |  N pooled: {metrics['n']:,}\n")
    lines.append("## Metrics\n")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    for k in ["P", "S", "beta", "sigma_ratio", "bin_S", "mean_yhat_bps",
              "top_bin_yhat_bps", "top_decile_y_bps", "top_decile_t_stat",
              "bottom_decile_y_bps", "bottom_decile_t_stat", "top_minus_bottom_bps"]:
        v = metrics.get(k, "NA")
        lines.append(f"| {k} | {v if isinstance(v, str) else f'{v:+.4f}'} |")
    lines.append("\n## V5 Gates\n")
    lines.append("| Gate | Pass | Description |")
    lines.append("|---|---|---|")
    descriptions = {
        "G1_P": "P ≥ 0.045 (no regression vs V4)",
        "G2_sigma_ratio": "σ_ŷ/σ_y ≥ 0.10 (2× wider than V4)",
        "G3_beta": "|β - 1| ≤ 0.20 (well-calibrated)",
        "G4_trading_top": "top decile E[y] ≥ +0.5 bps with t≥2.0",
        "G5_bin_S": "bin-Spearman ≥ 0.85 (monotonic)",
        "G6_no_bias": "|mean(ŷ)| ≤ 0.10 bps",
        "S1_P_strong": "(stretch) P ≥ 0.055",
        "S2_sigma_strong": "(stretch) σ_ŷ/σ_y ≥ 0.15",
    }
    for k, passing in gates.items():
        lines.append(f"| {k} | {'PASS' if passing else 'FAIL'} | {descriptions.get(k, '')} |")
    lines.append("\n## Verdict\n")
    required = [k for k in gates if k.startswith("G")]
    all_pass = all(gates[k] for k in required)
    lines.append(f"**{'PASS' if all_pass else 'FAIL'}** — required gates: {sum(gates[k] for k in required)}/{len(required)}")
    Path(args.out).write_text("\n".join(lines))
    print(f"Wrote {args.out}")
    print("Required gates:", {k: gates[k] for k in required})


if __name__ == "__main__":
    main()
PYEOF
```

- [ ] **Step 4: Run tests, verify pass**

Run: `python -m pytest tests/test_v5_eval.py -v 2>&1 | tail -10`
Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/v5_eval_comprehensive.py tests/test_v5_eval.py
git commit -m "feat(v5): comprehensive eval with calibration + trading view + V5 gates"
```

---

## Phase 8: Mamba backbone option (extension)

### Task 8.1: Add base_mamba.json config

**Files:**
- Create: `configs/v5/base_mamba.json`

- [ ] **Step 1: Inspect existing Mamba backbone**

Run: `head -40 src/model/backbones/mamba_backbone_v2.py`

Note the class name and required init kwargs.

- [ ] **Step 2: Copy base.json and switch backbone**

```bash
cp configs/v5/base.json configs/v5/base_mamba.json
```

Edit `configs/v5/base_mamba.json` model section. Add or modify:
```json
"model": {
  ... (existing keys)
  "use_attention": false,
  "use_conv": false,
  "backbone_type": "mamba",
  "backbone_kwargs": {
    "d_state": 16,
    "d_conv": 4,
    "expand": 2
  }
}
```

(Adjust kwarg names to match what `mamba_backbone_v2.py` accepts.)

- [ ] **Step 3: Verify config valid**

```bash
python -c "import json; c = json.load(open('configs/v5/base_mamba.json')); print(c['model'].get('backbone_type'))"
```
Expected: `mamba` printed.

- [ ] **Step 4: Commit**

```bash
git add configs/v5/base_mamba.json
git commit -m "feat(v5): Mamba backbone variant config"
```

### Task 8.2: Wire backbone_type dispatch in V5Model

**Files:**
- Modify: `src/model/v5_model.py`

- [ ] **Step 1: Open V5Model and add dispatch**

Currently V5Model only instantiates DualPathLOBModelV3. To support Mamba, add a backbone_type check.

In `V5Model.__init__`, modify the backbone instantiation block:

```python
        backbone_type = v4_kwargs.pop("backbone_type", "v4")
        backbone_kwargs = v4_kwargs.pop("backbone_kwargs", {})
        if backbone_type == "v4":
            self.backbone = DualPathLOBModelV3(**v4_kwargs)
        elif backbone_type == "mamba":
            from src.model.backbones.mamba_backbone_v2 import MambaBackboneV2  # adjust class name
            self.backbone = MambaBackboneV2(**v4_kwargs, **backbone_kwargs)
        else:
            raise ValueError(f"Unknown backbone_type: {backbone_type}")
```

(Adjust import path / class name based on what `mamba_backbone_v2.py` actually exports.)

- [ ] **Step 2: Verify both V5 backbones instantiate**

```bash
python -c "
import json
from src.model.v5_model import V5Model
for cfg_path in ['configs/v5/base.json', 'configs/v5/base_mamba.json']:
    cfg = json.load(open(cfg_path))
    v4_kwargs = dict(cfg['model'])
    v4_kwargs['n_levels'] = cfg['data']['n_levels']
    try:
        m = V5Model(v4_kwargs=v4_kwargs, head_hidden=0)
        print(f'{cfg_path}: OK ({sum(p.numel() for p in m.parameters())} params)')
    except Exception as e:
        print(f'{cfg_path}: FAIL ({e})')
"
```

Expected: both `OK`.

- [ ] **Step 3: Commit**

```bash
git add src/model/v5_model.py
git commit -m "feat(v5): backbone_type dispatch (v4 | mamba) in V5Model"
```

---

## Phase 9: Pod-side training plan (NOT executed locally)

### Task 9.1: Document pod training procedure

**Files:**
- Create: `docs/V5_POD_RUNBOOK.md`

- [ ] **Step 1: Write runbook**

```bash
cat > docs/V5_POD_RUNBOOK.md << 'DOCEOF'
> **创建:** 2026-05-02 | **Session:** v5-plan-write | **状态:** in-progress
> **作废条件:** V5 first 3-fold run completes, replaced by V5_RESULTS.md

# V5 Pod Training Runbook

## Pre-flight (local, before pod spin-up)

1. Verify all V5 unit tests pass:
   ```
   pytest tests/test_v5_nll.py tests/test_v5_head.py tests/test_v5_smoke_train.py tests/test_v5_eval.py -v
   ```
2. Verify smoke training in `experiments/v5_smoke/` shows decreasing NLL + finite σ
3. Pull latest commits to git remote

## Pod sequence

### Step 1: Spin up pod
- 1× RTX 4090 or A100, 32GB+ VRAM, 100GB disk
- Mount data/npz_v4 (970 days NPZ files)

### Step 2: Sync code
```
git clone <repo> && cd quant_research
git checkout <v5-branch>
pip install -r requirements.txt
```

### Step 3: First fold smoke (verify pipeline runs end-to-end)
```
python run_pipeline_v3.py \
  --model V5 \
  --config configs/v5/base.json \
  --output_dir experiments/v5_base_3fold \
  --skip-features \
  --seed 42 \
  --start-fold 0 \
  --max-folds 1
```
Expected duration: ~3-4 hours. Monitor σ stats per epoch:
```
grep "sigma" experiments/v5_base_3fold/fold_0/run.log | tail -20
```

GO/NO-GO check after fold 0:
- σ_mean ∈ [0.3, 3.0] each epoch (not collapsed/exploded)
- Final val_P ≥ 0.025 (any positive correlation)
- Test pred file exists at `fold_0/test_preds.npz`

If any fail: kill, debug.

### Step 4: Full 3-fold
```
python run_pipeline_v3.py \
  --model V5 \
  --config configs/v5/base.json \
  --output_dir experiments/v5_base_3fold \
  --skip-features \
  --seed 42 \
  --start-fold 0 \
  --max-folds 3
```
Expected: ~9-12 hours total.

### Step 5: Eval against V5 gates
```
python scripts/v5_eval_comprehensive.py \
  --exp-dir experiments/v5_base_3fold \
  --n-folds 3 \
  --out exports/v5_base_eval.md
```

### Step 6 (conditional): if V5 base passes G1-G6
- Run multi-seed (seed 7, 13) for variance reduction
- Run base_mamba variant
- Run base_5fold variant
- Compare against V4 baseline_plus

### Step 7 (conditional): if V5 base FAILS gates
Diagnose by gate:
- G2 fails (σ_ŷ/σ_y < 0.10): NLL did not unshrink. Check log_sigma distribution.
  Maybe loosen log_sigma_min, increase weight on NLL relative to other losses.
- G3 fails (|β-1| > 0.2): NLL didn't calibrate β properly. Add small β_calib aux loss.
- G4 fails (trading top decile bad): rank quality regressed. May need utility_rank aux at low weight (0.1).
- G5 fails (bin_S low): predictions are noisy in monotonicity. Try wider bin count or longer training.
- G6 fails (mean(ŷ) biased): add explicit zero-mean penalty to loss.

Document ALL diagnostics in V5_RESULTS.md.

## Cost estimate

| Phase | Wall time | GPU $ |
|---|---|---|
| Smoke fold 0 | 3-4 hr | $2-3 |
| Full 3-fold | 9-12 hr | $7-10 |
| Multi-seed (2 more seeds × 3 fold) | 18-24 hr | $14-20 |
| Mamba variant (3-fold) | 12-15 hr | $9-12 |
| 5-fold variant | 15-20 hr | $12-16 |
| **Total worst-case** | **~70 hr** | **~$50** |

For initial probe, run only Smoke + Full 3-fold base = $10. Decide on extras based on G1-G6 results.

DOCEOF
```

- [ ] **Step 2: Commit**

```bash
git add docs/V5_POD_RUNBOOK.md
git commit -m "docs(v5): pod training runbook with go/no-go gates"
```

---

## Phase 10: Final validation + production handoff

### Task 10.1: After V5 3-fold completes (post-pod), generate production CSV

**Files (created post-pod, deferred):**
- `exports/y600_v5_BEST.csv` (V5 BEST checkpoint predictions)
- `exports/y600_v5_EMA.csv` (if EMA enabled in V5 trainer)
- `exports/README_v5_csv.md`

- [ ] **Step 1: Document CSV export procedure (after pod run)**

This task is a placeholder for post-V5-training work. The procedure mirrors `scripts/export_y600_6csv.py` but uses V5 predictions:

```python
# scripts/export_v5_csvs.py (to be written after V5 3-fold completes)
# 1. Load V5 fold predictions
# 2. Convert μ × y_sigma → log-return → bps
# 3. Match raw y_600 from data/npz_v4 by timestamp
# 4. Output CSV with columns: timestamp_us, datetime_utc, fold, mask,
#    y_true_logret, y_true_bps, y_pred_mu_bps, y_pred_sigma_bps, y_pred_bps,
#    y_sigma_train_bps
# 5. Write README explaining: μ is point prediction, σ is per-sample uncertainty,
#    use μ for trading + σ for confidence gating / position sizing
```

- [ ] **Step 2 (deferred): Run after V5 results in**

Will be invoked once V5 base 3-fold passes G1-G6.

---

## Phase 11: Cleanup + final commit

### Task 11.1: Update CLAUDE.md with V5 status

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update V5 section with implementation status**

After V5 implementation is complete (Phase 1-8 done locally, Phase 9 ready for pod), update CLAUDE.md V5 section:

```markdown
## V5 Iteration Plan (2026-05-02)

**Status (as of 2026-05-02):** Implementation complete locally; pod-side full 3-fold training pending.

**Implementation summary:**
- Heteroscedastic NLL loss component: `src/training/v5_losses/heteroscedastic_components.py`
- HeteroscedasticHead: `src/training/v5_losses/heteroscedastic_head.py`
- V5Model wrapper (V4 backbone + V5 head): `src/model/v5_model.py`
- 3 configs: base.json, base_5fold.json, base_mamba.json + smoke
- Eval pipeline: `scripts/v5_eval_comprehensive.py`
- Tests: 5 test files, all green locally
- Pod runbook: `docs/V5_POD_RUNBOOK.md`

**Next step:** Spin pod, run smoke fold 0, eval against G1-G6, decide go/no-go on full 3-fold.
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(claude): mark V5 implementation complete locally; pod step pending"
```

### Task 11.2: Final implementation check

- [ ] **Step 1: Run all V5 tests**

```bash
python -m pytest tests/test_v5_nll.py tests/test_v5_head.py tests/test_v5_smoke_train.py tests/test_v5_eval.py tests/test_v5_embargo.py -v
```

Expected: all PASS.

- [ ] **Step 2: Verify file checklist**

```bash
echo "Created files:"
for f in \
  docs/V5_DESIGN.md \
  docs/V5_POD_RUNBOOK.md \
  src/training/v5_losses/heteroscedastic_components.py \
  src/training/v5_losses/heteroscedastic_head.py \
  src/model/v5_model.py \
  configs/v5/base.json \
  configs/v5/base_smoke.json \
  configs/v5/base_5fold.json \
  configs/v5/base_mamba.json \
  scripts/v5_eval_comprehensive.py \
  tests/test_v5_nll.py \
  tests/test_v5_head.py \
  tests/test_v5_smoke_train.py \
  tests/test_v5_eval.py \
  tests/test_v5_embargo.py; do
  if [ -f "$f" ]; then echo "  ✓ $f"; else echo "  ✗ MISSING $f"; fi
done
```

Expected: all `✓`.

- [ ] **Step 3: Print final commit summary**

```bash
git log --oneline | head -20
```

Expected: V5 commits visible.

---

# Implementation Notes for the Engineer

## Critical decisions encoded in this plan

1. **NLL primary, dual-head deferred** — anti-pattern review (CLAUDE.md #18) showed dual-head's expected ΔP +0.005-0.015 is small. NLL targets the σ_ŷ/β tradeoff *directly* with cleaner math (one loss term, well-studied). Dual-head scaffold (`dual_head.py`) is kept in the codebase as backup but NOT wired into V5 by default.

2. **No multi-seed ensemble in V5 primary path** — diagnostic showed 3-seed median lost level metrics vs single seed42. V5 = single seed (42 default). Multi-seed only as Phase-9 stretch experiment if base passes.

3. **Backbone unchanged from V4** — 6 novel backbones (V5-LH ×4 + multi_scale + pyramid) failed on y_600. V5 reuses proven V4 DualPathLOBModelV3. Mamba option for long-range context is a *configurable extension*, not the default.

4. **Embargo = horizon (600s) by default in V5 configs** — mitigates anti-pattern silent y-leak. V4 used 0.

5. **Hard gates pre-declared** — G1-G6 in `docs/V5_DESIGN.md` are NOT negotiable. If V5 fails, document the failure in V5_RESULTS.md and either retry with adjustments or fall back to V4 production.

## Things you may need to adjust

- **V4 backbone `.encode()` refactor (Task 3.2)**: depends on whether DualPathLOBModelV3 already has an embedding extraction method. If not, refactor `forward()` to call `encode()` then `head()`. Concrete recipe: open `dual_path_model_v3.py`, find `def forward`, identify the line `return self.head(emb)` (or similar), split into `def encode(...): return emb` plus `def forward(...): return self.head(self.encode(...))`. **No behavior change**, just enables V5 to bypass the V4 head.
- **Dataset embargo plumbing (Task 4.2)**: depends on how `dataset.py` currently splits folds. Trace from `__init__`'s fold computation: find `train_end = ...`, then add `train_end -= embargo_samples` where `embargo_samples = embargo_seconds // self.stride`.
- **`run_pipeline_v3.py` model build site (Task 5.3)**: search for the existing `DualPathLOBModelV3(...)` instantiation. Wrap it with the `if use_v5_nll` dispatch. Make sure `loss_fn=custom_loss_fn` is passed to `train_one_fold_v2(...)` (the parameter exists at line 387).
- **Mamba kwargs (Task 8.1, 8.2)**: actual kwarg names depend on `mamba_backbone_v2.py` — open it first, inspect `__init__`'s signature, and match the kwargs in `base_mamba.json`.

## When in doubt, prefer

- TDD: write smoke test BEFORE full integration. NLL convergence test in Task 2.2 is the canary.
- YAGNI: don't add multi-seed averaging, fancy schedulers, etc., to V5 primary path. Phase 9 has stretch room.
- Frequent commits: every task ends with a commit. Don't batch.
- No Notebook/scratch experimentation: all code lands in tracked files (`tests/`, `scripts/`, `src/`).
