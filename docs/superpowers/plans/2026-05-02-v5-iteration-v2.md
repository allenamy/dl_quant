# V5 Iteration Implementation Plan (v2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build V5 by **(1) auditing & fixing the V4 last-timestep bug** that wastes 585 of 600 input timesteps, **(2) running focused fold-0 screens** of backbone × loss × data-setup to data-drive V5 base config, and **(3) producing a production model** with calibrated trading-ready ŷ. Approach is **screen-first, lock-late**: do not pre-commit to specific architecture / loss / data choices; let fold-0 numbers decide.

**Architecture:** Verify and fix V4's `h[:, -1, :]` last-timestep extraction (line 628 of `dual_path_model_v3.py`) — this is a structural bug that limits effective lookback to 15s (TCN RF). Audit all 5 existing pluggable backbones (`attention path`, `mamba`, `gru`, `ema_pool`, `itransformer`) for correctness, then screen 3 most promising. Loss: screen 4 candidates (quantile, Huber, NLL, dual-head). Data: screen 3-fold walk-forward vs single-large-split (skip 5-fold — marginal info gain at 1.67× training cost).

**Tech Stack:** PyTorch 2.0+, NumPy, Pandas, scikit-learn, pytest (TDD). Existing V4 code at `src/model/dual_path_model_v3.py`, `src/training/trainer_v2.py`, `src/training/v5_losses/` (already has dual-head scaffold). Pluggable backbones at `src/model/backbones/`.

**Background context (read before starting):**
- CLAUDE.md Anti-pattern #11 (variance collapse), #14 (multi-seed), #16 (rank-blend β), #17 (anchor discipline), #18 (raw eval), #19 (methodology consistency)
- Plan v1 (`docs/superpowers/plans/2026-05-02-v5-iteration-v1-DEPRECATED.md`) — pre-locked NLL + Mamba; **deprecated** for over-committing without screens
- V4 production candidate baseline = `seed42_SWA` from baseline_plus at P=0.0457, S=0.0571, β=1.010, σ_ŷ/σ_y=0.045
- **Key found bug**: `dual_path_model_v3.py:628` — `h_pred = h[:, -1, :]` — discards 585 of 600 timesteps' features. Effective lookback for prediction = 15s (TCN RF), not 600s as input. **This is the primary root cause of σ_ŷ shrinkage**.

## Codex Adversarial Review Patches (2026-05-02)

This plan was reviewed by codex; 4 issues found + patched IN-PLACE before execution. Search "CODEX FIX" in this doc to find each patch.

| # | Severity | Issue | Patch location |
|---|---|---|---|
| 1 | High | DANN keys forwarded to V3 backbone but V3 has no DANN support — silent crash on `use_dann=True` configs in V5 path | Task A.11 — strip DANN keys + assert `training.use_dann=False` in V5 path |
| 2 | High | Plan v2's `data.embargo_seconds` was inert; existing pipeline reads `training.embargo_days` only | Task A.9 — use existing `training.embargo_days=1` (≥ horizon); add observable regression test |
| 3 | Medium | A.1 audit could `pytest.skip` on signature mismatch, letting later phases proceed on unproven premise | Task A.1 — derive `n_feat` from real LOBDatasetV2 sample; FAIL CLOSED on errors |
| 4 | Medium | CSV exporter dropped `y_median` in de-normalization; trainer normalizes as `(y-median)/σ`, exporter computed `z·σ` only | Task D.2 — add `y_median` from npz to de-normalization; export `y_median_train_bps` for audit |

All patches preserve plan v2's screen-first methodology; they only enforce that the audits and exports are TRUSTWORTHY.

---

## V5 Success Gates (pre-declared, hard)

Full 3-fold pooled eval (raw + dense, n ≈ 48,678) MUST satisfy:

**Required (G1-G6, gate-blocking):**
- G1: Pearson ≥ 0.045 (no regression vs V4 baseline 0.0457 - margin)
- G2: σ_ŷ/σ_y ≥ 0.10 (vs V4 0.045, **2× target**)
- G3: |β - 1.0| ≤ 0.20 (β ∈ [0.80, 1.20])
- G4: top decile trading view E[y] ≥ +0.5 bps with t-stat ≥ +2.0
- G5: bin-Spearman ≥ 0.85 (vs V4 0.770)
- G6: |mean(ŷ)| ≤ 0.10 bps (less negative bias than V4 -0.08)

**Stretch (S1-S2, informational):**
- S1: Pearson ≥ 0.055
- S2: σ_ŷ/σ_y ≥ 0.20 (4×)

---

## File Structure (locked before tasks)

**Files to create:**
- `docs/V5_DESIGN_v2.md` — design rationale (audit findings + screen matrix)
- `docs/V5_BACKBONE_AUDIT.md` — backbone code-review notes (output of Phase A.2)
- `src/training/v5_losses/heteroscedastic_components.py` — Gaussian NLL
- `src/training/v5_losses/heteroscedastic_head.py` — `(μ, log_σ)` head
- `src/training/v5_losses/huber_components.py` — Huber loss on raw y
- `src/training/v5_losses/v5_loss_fn.py` — factory bridging V5LossAssembly to trainer_v2.loss_fn
- `src/model/v5_model.py` — V5 wrapper (V4 backbone + V5 head)
- `configs/v5/screen/backbone_<name>.json` — Phase B.1 screen configs (3 files)
- `configs/v5/screen/loss_<name>.json` — Phase B.2 screen configs (4 files)
- `configs/v5/screen/data_singletrain.json` — Phase B.3 single-train config
- `configs/v5/v5_final.json` — Phase C V5 final config (filled after Phase B)
- `scripts/v5_screen_orchestrator.py` — orchestrate fold-0 screens, collect metrics
- `scripts/v5_eval_comprehensive.py` — calibration + trading view + V5 gates
- `tests/test_v5_nll.py`, `tests/test_v5_head.py`, `tests/test_v5_huber.py`, `tests/test_v5_backbones.py` — unit tests

**Files to modify:**
- `src/training/dataset.py` — add `embargo_seconds` (default 0)
- `run_pipeline_v3.py` — V5 dispatch when `config.loss.use_v5_nll/huber/dualhead=true`

**Files NOT modified initially:** `dual_path_model_v3.py` (audit only; modify ONLY if a bug is found that V5 can't fix via config), V4 configs, V4 scripts.

---

## Total Budget Estimate

| Phase | Hours | GPU $ | Risk |
|---|---|---|---|
| A (local prep + audit) | 8-12 | $0 | Low — pure verification + code |
| B.1 (backbone screen, 3 runs) | 9-12 | $9-12 | Med — could surface infra bugs |
| B.2 (loss screen, 4 runs) | 12-16 | $12-16 | Med |
| B.3 (data setup screen, 2 runs) | 6-8 | $6-8 | Low |
| C (V5 final 3-fold) | 9-12 | $10-12 | Low (Phase B locked) |
| D (eval + deploy) | 4-6 | $0-2 | Low |
| **Total** | **48-66 hr** | **~$40** | |

If Phase B.1 fails to find ANY backbone exceeding V4 baseline by ≥ +0.005 P, escalate to "Phase B.0" (custom architecture work — out of scope of this plan, separate effort). If Phase B.2 fails to find any loss meeting G2 (σ_ŷ/σ_y ≥ 0.10), V5 = V4 as backup; document failure.

---

## Phase A: Local audit + prep (no GPU)

### Task A.1: Verify the last-timestep bug + write design doc

**Files:**
- Create: `tests/test_v5_v4bug_audit.py`
- Create: `docs/V5_DESIGN_v2.md`

- [ ] **Step 1: Write test that demonstrates the bug**

```bash
cat > tests/test_v5_v4bug_audit.py << 'TESTEOF'
"""Audit test: V4 baseline_plus path discards 585 of 600 input timesteps.

Verifies dual_path_model_v3.py line 628 takes only h[:, -1, :] when
use_attention=False AND backbone=None (= baseline_plus production config).

This is informational; not a "fix" test — just documents the structural
limitation V5 needs to address.
"""
import torch
import json


def test_baseline_plus_uses_last_timestep_only():
    """Verify that with baseline_plus config (use_attention=False, no backbone),
    only the last input timestep contributes to the output gradient.
    """
    from src.model.dual_path_model_v3 import DualPathLOBModelV3

    cfg = json.load(open("configs/y600_push/baseline_plus.json"))
    model_cfg = dict(cfg["model"])
    model_cfg["n_levels"] = cfg["data"]["n_levels"]
    # Strip kwargs DualPathLOBModelV3 doesn't accept (drop kwargs by inspection)
    # If init breaks, narrow to known good kwargs

    torch.manual_seed(0)
    model = DualPathLOBModelV3(**model_cfg)
    model.eval()

    # Build dummy input. Match expected shapes
    B, L = 1, cfg["data"]["input_len"]
    # CODEX FIX: derive n_feat from actual LOBDatasetV2 sample, NOT hardcoded.
    # If signature mismatch, FAIL CLOSED — do not skip (this is the audit gate;
    # skipping would let later steps proceed on unproven premise).
    from src.training.dataset import LOBDatasetV2
    try:
        ds = LOBDatasetV2(
            csv_path=cfg["data"].get("csv_path", ""),
            npz_dir=cfg["data"]["npz_dir"],
            n_levels=cfg["data"]["n_levels"],
            horizon_sec=cfg["data"]["horizon_sec"],
            input_len=cfg["data"]["input_len"],
            stride=cfg["data"].get("stride", 60),
            split="train",
        )
        sample = ds[0]
    except Exception as e:
        raise RuntimeError(
            f"Cannot derive n_feat from LOBDatasetV2: {e}. "
            "Audit cannot proceed without actual feature dim — fix dataset or pass n_feat explicitly. "
            "Do NOT skip this test; later phases depend on its premise."
        )

    # First element of sample tuple is x_feat with shape (L, n_feat)
    if isinstance(sample, tuple) and len(sample) >= 1:
        x_feat_sample = sample[0]
    else:
        raise RuntimeError(f"Unexpected dataset sample structure: {type(sample)}")
    if x_feat_sample.ndim != 2:
        raise RuntimeError(f"Expected x_feat shape (L, n_feat); got {x_feat_sample.shape}")
    n_feat = x_feat_sample.shape[-1]

    x_feat = torch.randn(B, L, n_feat, requires_grad=True)
    x_raw = torch.randn(B, L, model_cfg["n_levels"] if "n_levels" in model_cfg else 25, 4, requires_grad=True)
    regime_prior = torch.zeros(B, model_cfg.get("d_prior", 6))

    # FAIL CLOSED on forward errors (no skip)
    out = model(x_feat=x_feat, x_raw=x_raw, regime_prior=regime_prior)

    # The final scalar output should depend ONLY on the last timestep features
    # (under baseline_plus path with use_attention=False, no backbone)
    point_pred = out["point_pred"].sum() if "point_pred" in out else out["quantiles"][..., 1].sum()
    point_pred.backward()

    # Compute gradient magnitude at each input timestep
    grad_per_step = x_feat.grad.abs().sum(dim=(0, 2))  # (L,)
    # If last-timestep is the only contributor, grad at L-1 dominates
    last_grad = grad_per_step[-1].item()
    avg_other_grad = grad_per_step[:-15].abs().mean().item()  # exclude RF window
    print(f"last timestep grad: {last_grad:.6f}")
    print(f"avg grad of timesteps 0..L-15 (outside RF): {avg_other_grad:.6f}")
    print(f"ratio last : pre-RF avg = {last_grad / max(avg_other_grad, 1e-10):.1f}")

    # Assertion: last-timestep grad should dominate (ratio >> 1)
    # If timesteps before RF window have non-zero grad, model uses more than 15s
    # If they have zero grad, confirms last-timestep-only behavior
    assert last_grad > 0
    # Outside the RF, grad should be effectively zero (or dominated)
    assert last_grad > 10 * avg_other_grad, (
        f"Expected last-timestep dominance, but pre-RF grad is {avg_other_grad:.3e} "
        f"vs last {last_grad:.3e}. V4 may be using more than 15s — re-audit needed."
    )
TESTEOF
```

- [ ] **Step 2: Run test to confirm bug**

Run: `cd /Users/haosiyu/Desktop/quant_research && python -m pytest tests/test_v5_v4bug_audit.py -v -s 2>&1 | tail -30`

Expected output: test PASSES (confirms last-timestep dominance), printing grad magnitudes. The "ratio" should be very large (>>10), proving 585 timesteps don't influence output.

If test fails because of forward signature issue (e.g., dataset returns different structure), DO NOT skip blindly — refine test to match actual signature, then assert.

- [ ] **Step 3: Write V5_DESIGN_v2.md with audit finding**

```bash
cat > docs/V5_DESIGN_v2.md << 'DOCEOF'
> **创建:** 2026-05-02 | **Session:** v5-plan-v2 | **关键事件:** V4 last-timestep bug audited
> **状态:** in-progress | **作废条件:** Phase B screens complete, V5 base config locked

# V5 Design Rationale (v2)

## V4 → V5 motivation: structural lookback bug

V4's `baseline_plus` production config goes through this path in `dual_path_model_v3.py:614-628`:

```python
if self.backbone is not None:
    h_pred = self.backbone(h)
elif self.use_attention:
    # ... patch attention path
else:
    if self.use_conv:
        h = self.temporal_conv(h)        # (B, 600, d_model), each pos has 15s RF
    h_pred = h[:, -1, :]                 # ← BUG: discards 585 of 600 timesteps!
```

`baseline_plus` has `use_attention=False` AND no `backbone` configured → falls into the last `else` branch. **Only the LAST timestep's TCN output (with 15s causal RF) becomes the prediction embedding**. The 585 earlier timesteps are computed by the conv stack but their outputs are discarded.

**Effective lookback for prediction: 15 seconds**, not 600 seconds as the input length suggests.

This explains:
- σ_ŷ/σ_y = 0.045 (extremely narrow predictions): only 15s of context → very limited signal → MSE-optimal shrinkage
- bin-Sp = 0.770 (moderate monotonicity): predictions are noisy because of limited context
- Pearson 0.05 ceiling: 15s is genuinely too short for 600s horizon prediction

**V4 already supports the fix** — `self.backbone` (line 610) is a pluggable hook for time-aggregation backbones (`ema_pool`, `gru`, `mamba`, `itransformer`). Setting `use_attention=True` also activates the patch attention path (line 614). Both routes use the FULL 600 timesteps.

But the existing backbones were tested on y_1800 (CLAUDE.md tasks #105) and the y_600 fit hasn't been measured. **Phase B.1 of this plan does that measurement.**

## V5 design philosophy

1. **Screen first, lock late** — Phase B fold-0 screens decide architecture / loss / data setup; we don't predefine choices.
2. **Reuse V4 infrastructure** — backbone modules, dataset, trainer all already exist; V5 = new configurations + new loss + new head, no new architecture from scratch.
3. **Address root cause** — the σ_ŷ shrinkage problem comes from BOTH (a) limited effective context and (b) loss choice (quantile/MSE shrinks unconditionally). Address both, not just one.
4. **Keep V4 production unchanged** — V4 baseline_plus stays as fallback.

## Phase B screen matrix (focused, NOT exhaustive)

### B.1: Backbone screen (3 candidates vs V4 baseline)

| Variant | What it does | Hypothesis |
|---|---|---|
| V4 baseline_plus (control) | last-timestep h[:, -1, :] | 0.045 σ_ŷ baseline |
| V4 + use_attention=True | patch attention over 600 timesteps | Aggregates full lookback explicitly |
| V4 + mamba backbone | SSM over 600 timesteps | Linear-time long range |
| V4 + ema_pool backbone | EMA-weighted time pool | Simple, low param time aggregation |

**Skipped (with reason):**
- `gru` backbone — classical recurrent, large overlap with mamba result; if mamba wins, gru likely follows similar pattern; if mamba fails, separate gru run unlikely to surprise
- `itransformer`, `multi_scale`, `hierarchical_pyramid` — already failed on y_600 in V5-LH era (CLAUDE.md anti-pattern), low ROI
- `conv_backbone` — variant of TCN, marginal improvement at best

### B.2: Loss screen (4 candidates) on B.1 winner

| Variant | Loss form | Hypothesis |
|---|---|---|
| L0 quantile (control) | pinball q10/q50/q90 + utility_rank | V4 current, σ_ŷ shrinks aggressively |
| L1 Huber on raw y | smooth_l1(y, μ) | Robust to outliers, less shrinkage than MSE? |
| L2 NLL heteroscedastic | 0.5(y-μ)²/σ² + 0.5 log σ² | Per-sample uncertainty → wider σ_ŷ in confident samples |
| L3 dual-head (V5 scaffold) | dir_margin + Huber on \|y\| + joint MSE | Magnitude head forced to track \|y\| → σ_ŷ ≈ E[\|tanh(dir)\|]·σ_\|y\| |

**Skipped (with reason):**
- L4 (combined NLL + dual-head) — adds complexity without clear theory advantage over L2 or L3 alone; if both look promising, run later as Phase C ablation
- Sharpe-aware loss — directly optimizes Sharpe but unstable in batch (variance terms), high variance in low-data + low-SNR regime
- Tail-focal loss — anti-pattern #12 already showed P/S divergence

### B.3: Data setup screen (2 candidates, NO 5-fold)

| Variant | Setup | Hypothesis |
|---|---|---|
| D0 3-fold walk-forward (control) | 3 folds, 700/30/30 days each, embargo=600s | V4 current, regime variance estimated 3 ways |
| D1 single big train | 750-day train + 200-day test, embargo=600s | Maximum train data utilization for production |

**Why skip 5-fold:** Marginal information gain (5 OOS points vs 3) at 1.67× training cost. With ~970 days total, going 5-fold means each test window is ~30 days = ~600 valid samples per fold (smaller, noisier). 3-fold is sufficient for regime variance estimation; 5-fold tests the same hypothesis with worse SNR per fold. Time better spent on B.1/B.2.

## V5 success gates (pre-declared)

[same gates G1-G6 + S1-S2 as in plan v1, see Background section above]

## V5 NOT doing (avoiding anti-patterns)

- ❌ Multi-seed ensemble in primary path (anti-pattern: 3-seed median compresses σ_ŷ)
- ❌ Post-hoc rank-blend in primary path (anti-pattern #16: β=0.08 misleading)
- ❌ Modifying V4 backbone (`dual_path_model_v3.py`) for the bug — `self.backbone` hook already exists; we configure not modify
- ❌ Adding new architecture from scratch — V5-LH/multi_scale/pyramid all failed; reuse V4 modules

## Compatibility

V5 keeps V4 production unchanged. Drops in via config: `loss.use_v5_nll/huber/dualhead` flags route to V5 path; `model.backbone_kind` selects pluggable backbone.

DOCEOF
```

- [ ] **Step 4: Commit**

```bash
git add docs/V5_DESIGN_v2.md tests/test_v5_v4bug_audit.py
git commit -m "docs(v5): audit V4 last-timestep bug + design rationale v2"
```

### Task A.2: Audit existing backbone implementations

**Files:**
- Read: `src/model/backbones/ema_pool_backbone.py`
- Read: `src/model/backbones/gru_backbone.py`
- Read: `src/model/backbones/mamba_backbone_v2.py`
- Create: `tests/test_v5_backbones.py`
- Create: `docs/V5_BACKBONE_AUDIT.md`

- [ ] **Step 1: Read each backbone, log API signature**

Run, for each backbone:
```bash
for f in src/model/backbones/{ema_pool_backbone,gru_backbone,mamba_backbone_v2}.py; do
  echo "=== $f ==="
  grep -A 3 "def __init__\|def forward" "$f"
  echo ""
done
```

Expected: each has `__init__(d_model, ...)` and `forward(h: (B, L, d_model)) → (B, d_model)`.

- [ ] **Step 2: Write smoke + correctness tests for each backbone**

```bash
cat > tests/test_v5_backbones.py << 'TESTEOF'
"""Backbone smoke tests + correctness audit.

Verifies:
1. Shape: (B, L, d_model) input → (B, d_model) output
2. Backward: gradient flows
3. Determinism: same input → same output (no leaky randomness in eval)
4. Causal: output at end depends on past, not future (check via swap test)
"""
import torch
import pytest


@pytest.mark.parametrize("backbone_name", ["ema_pool", "gru", "mamba"])
def test_backbone_io_shape(backbone_name):
    """Each backbone should map (B, L, d_model) → (B, d_model)."""
    backbone = _build_backbone(backbone_name, d_model=32)
    x = torch.randn(4, 600, 32)
    out = backbone(x)
    assert out.shape == (4, 32), f"{backbone_name}: shape mismatch {out.shape}"


@pytest.mark.parametrize("backbone_name", ["ema_pool", "gru", "mamba"])
def test_backbone_backward(backbone_name):
    """Backward must produce finite gradients on all input positions."""
    backbone = _build_backbone(backbone_name, d_model=32)
    x = torch.randn(2, 100, 32, requires_grad=True)
    out = backbone(x)
    out.sum().backward()
    assert torch.isfinite(x.grad).all(), f"{backbone_name}: NaN grad"


@pytest.mark.parametrize("backbone_name", ["ema_pool", "gru", "mamba"])
def test_backbone_determinism(backbone_name):
    """In eval mode, same input → same output (no leaky randomness)."""
    backbone = _build_backbone(backbone_name, d_model=32)
    backbone.eval()
    x = torch.randn(2, 100, 32)
    out1 = backbone(x)
    out2 = backbone(x)
    assert torch.allclose(out1, out2), f"{backbone_name}: non-deterministic in eval"


@pytest.mark.parametrize("backbone_name", ["ema_pool", "gru", "mamba"])
def test_backbone_uses_more_than_last_timestep(backbone_name):
    """Critical: backbone must actually use earlier timesteps, not just last.

    If gradient at t=0 is zero, backbone is degenerate (= last-timestep slice in disguise).
    """
    backbone = _build_backbone(backbone_name, d_model=32)
    backbone.eval()
    x = torch.randn(1, 100, 32, requires_grad=True)
    out = backbone(x)
    out.sum().backward()
    grad_at_t0 = x.grad[0, 0, :].abs().sum().item()
    grad_at_last = x.grad[0, -1, :].abs().sum().item()
    # Both should be non-zero (if backbone uses full sequence)
    assert grad_at_t0 > 0, f"{backbone_name}: t=0 has zero grad — only uses last timestep!"
    # Ratio: last/early can be large for causal backbones, but t=0 should be > 0
    print(f"{backbone_name}: grad at t=0={grad_at_t0:.4e}, grad at t=-1={grad_at_last:.4e}, ratio={grad_at_last/grad_at_t0:.1f}")


def _build_backbone(name, d_model):
    """Helper: instantiate each backbone with reasonable defaults."""
    if name == "ema_pool":
        from src.model.backbones.ema_pool_backbone import EMAPoolBackbone
        return EMAPoolBackbone(d_model=d_model)
    elif name == "gru":
        from src.model.backbones.gru_backbone import GRUBackbone
        return GRUBackbone(d_model=d_model)
    elif name == "mamba":
        try:
            from src.model.backbones.mamba_backbone_v2 import MambaBackboneV2
        except ImportError:
            try:
                from src.model.backbones.mamba_backbone_v2 import MambaBackbone
                return MambaBackbone(d_model=d_model)
            except ImportError:
                pytest.skip("Mamba backbone import failed (mamba-ssm not installed locally)")
        return MambaBackboneV2(d_model=d_model)
    else:
        pytest.fail(f"Unknown backbone {name}")
TESTEOF
```

- [ ] **Step 3: Run audit tests**

Run: `python -m pytest tests/test_v5_backbones.py -v -s 2>&1 | tail -30`

Expected: All tests PASS for `ema_pool` and `gru`. `mamba` may skip if `mamba-ssm` not locally installed (it's a CUDA-only library).

**If any test FAILS** for `ema_pool` or `gru`: log the failure to `docs/V5_BACKBONE_AUDIT.md` and consider it BUGGY — exclude from Phase B.1 screen.

- [ ] **Step 4: Document findings**

```bash
cat > docs/V5_BACKBONE_AUDIT.md << 'DOCEOF'
> **创建:** 2026-05-02 | **Session:** v5-plan-v2 | **状态:** in-progress
> **作废条件:** Phase B.1 完成,有真实 fold-0 数据替代 audit 推断

# V5 Backbone Audit

## Method

Each backbone in `src/model/backbones/` (excluding `__init__`, `__pycache__`) was tested for:

1. **Shape contract**: (B, L, d_model) input → (B, d_model) output
2. **Gradient flow**: backward produces finite gradients
3. **Determinism**: eval mode reproducible
4. **Effective lookback**: gradient at t=0 is non-zero (else degenerate to last-timestep)

## Results (filled in by Phase A.2)

| Backbone | Shape ✓ | Backward ✓ | Determinism ✓ | t=0 grad > 0 ✓ | Verdict |
|---|---|---|---|---|---|
| ema_pool | TBD | TBD | TBD | TBD | TBD |
| gru | TBD | TBD | TBD | TBD | TBD |
| mamba_v2 | TBD | TBD | TBD | TBD | TBD (skip if mamba-ssm not local) |

## Integration audit: how backbone connects to V4

Per `dual_path_model_v3.py:610-612`:
```python
if self.backbone is not None:
    h_pred = self.backbone(h)  # h: (B, L, d_model) → h_pred: (B, d_model)
```

Backbone REPLACES the entire `temporal_conv → last-timestep` path. Path A (manual feature) and Path B (raw LOB) fusion happens UPSTREAM of backbone:

```
x_feat → MaskNet → GDCN → input_proj → h_craft (B, L, d_model)
x_raw  → RawLOBEncoder                  → h_raw (B, L, d_raw)
fusion: concat(h_craft, h_raw) → linear → h (B, L, d_model)

         ↓ this h goes into backbone
self.backbone(h) → h_pred (B, d_model)  ← V5 fix point
         ↓
PPNet gate → MonotonicQuantileHead → q10/q50/q90
```

**Implication for Phase B.1**: backbone screen is well-isolated — only step is what to do with `h` (B, L, d_model). All upstream (RevIN, MaskNet, GDCN, RawLOBEncoder, fusion) and downstream (PPNet, head) stay V4-identical.

## Alternative fusion strategies (deferred for V5.5+)

The current "plug-and-replace temporal stack" fusion is the simplest. Alternatives we are NOT exploring in V5:

- **TCN front + backbone back (Conformer-style)**: keep `temporal_conv` for local features, add backbone for global aggregation. More params, more compute.
- **Multi-scale parallel branches**: TCN + Mamba in parallel, concat outputs. Doubles param count.
- **Attention pool over backbone hidden states**: not just last hidden but weighted sum.

If Phase B.1 finds a clear winner among single-backbone substitution, V5.5 (next iteration) can explore these alternatives. **For V5, stick with single-backbone substitution** to keep the screen interpretable.

## Recommendations for Phase B.1

Based on audit (Phase A.2 results):

- **Include**: backbones that pass all 4 audit criteria
- **Exclude**: any with shape/backward/determinism bugs or t=0 grad ≈ 0
- **Add**: V4 + use_attention=True path (no backbone, but uses full 600 timesteps via patch attention)

DOCEOF
```

- [ ] **Step 5: Commit**

```bash
git add tests/test_v5_backbones.py docs/V5_BACKBONE_AUDIT.md
git commit -m "test(v5): audit existing backbones for correctness + integration notes"
```

### Task A.3: Implement Gaussian NLL loss (TDD)

**Files:**
- Create: `tests/test_v5_nll.py`
- Create: `src/training/v5_losses/heteroscedastic_components.py`

- [ ] **Step 1: Write failing tests**

```bash
cat > tests/test_v5_nll.py << 'TESTEOF'
"""Unit tests for V5 Gaussian NLL component."""
import math
import torch


def test_gaussian_nll_perfect_prediction():
    from src.training.v5_losses.heteroscedastic_components import loss_gaussian_nll
    y = torch.tensor([0.0, 1.0, -1.0, 2.5])
    mu = y.clone()
    log_sigma = torch.zeros_like(y)
    mask = torch.ones_like(y).bool()
    loss = loss_gaussian_nll(mu, log_sigma, y, mask)
    expected = 0.5 * math.log(2 * math.pi)
    assert abs(loss.item() - expected) < 1e-5


def test_gaussian_nll_high_confidence_penalizes_error():
    from src.training.v5_losses.heteroscedastic_components import loss_gaussian_nll
    y = torch.tensor([1.0])
    mu = torch.tensor([0.0])
    mask = torch.ones_like(y).bool()
    loss_high_conf = loss_gaussian_nll(mu, torch.tensor([-2.0]), y, mask)
    loss_low_conf = loss_gaussian_nll(mu, torch.tensor([2.0]), y, mask)
    assert loss_high_conf.item() > loss_low_conf.item()


def test_gaussian_nll_mask_handling():
    from src.training.v5_losses.heteroscedastic_components import loss_gaussian_nll
    y = torch.tensor([1e10, 0.0, -1e10, 1.0])
    mu = torch.zeros_like(y)
    log_sigma = torch.zeros_like(y)
    mask = torch.tensor([False, True, False, True])
    loss = loss_gaussian_nll(mu, log_sigma, y, mask)
    expected = 0.25 + 0.5 * math.log(2 * math.pi)
    assert abs(loss.item() - expected) < 1e-5


def test_gaussian_nll_log_sigma_clip():
    from src.training.v5_losses.heteroscedastic_components import loss_gaussian_nll
    y = torch.tensor([1.0])
    mu = torch.tensor([0.0])
    mask = torch.ones_like(y).bool()
    extreme_log_sigma = torch.tensor([-100.0], requires_grad=True)
    loss = loss_gaussian_nll(mu, extreme_log_sigma, y, mask, log_sigma_min=-7.0, log_sigma_max=2.0)
    assert torch.isfinite(loss).all()
    loss.backward()
    assert torch.isfinite(extreme_log_sigma.grad).all()


def test_gaussian_nll_no_valid_returns_zero_with_grad():
    from src.training.v5_losses.heteroscedastic_components import loss_gaussian_nll
    y = torch.tensor([1.0, 2.0])
    mu = torch.tensor([0.5, 0.5], requires_grad=True)
    log_sigma = torch.zeros_like(y)
    mask = torch.zeros_like(y).bool()
    loss = loss_gaussian_nll(mu, log_sigma, y, mask)
    assert loss.item() == 0.0
    loss.backward()
    assert mu.grad is not None
TESTEOF
```

- [ ] **Step 2: Run tests, verify failure**

Run: `python -m pytest tests/test_v5_nll.py -v 2>&1 | tail -10`
Expected: 5 tests fail with ImportError.

- [ ] **Step 3: Implement**

```bash
cat > src/training/v5_losses/heteroscedastic_components.py << 'PYEOF'
"""Heteroscedastic NLL loss component for V5.

Gaussian NLL: model outputs (μ, log_σ) per sample; loss is
   L = 0.5 · (y-μ)² / σ² + 0.5 · log(σ²) + 0.5·log(2π)

log_σ is clipped to [log_sigma_min, log_sigma_max] inside the loss to prevent
σ → 0 (loss → ∞) or σ → ∞ (μ degenerate to 0).
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
    """Gaussian NLL loss with masking and log_sigma clipping."""
    if mask.dtype != torch.bool:
        mask = mask.bool()
    valid = mask & torch.isfinite(y) & torch.isfinite(mu) & torch.isfinite(log_sigma)
    n = valid.sum()
    if n == 0:
        return (mu * 0.0).sum()

    log_sigma_clipped = torch.clamp(log_sigma, min=log_sigma_min, max=log_sigma_max)
    inv_var = torch.exp(-2.0 * log_sigma_clipped)
    sq_err = (y - mu) ** 2

    per_sample = 0.5 * sq_err * inv_var + log_sigma_clipped
    if include_const:
        per_sample = per_sample + 0.5 * math.log(2 * math.pi)

    per_sample_clean = torch.where(valid, per_sample, torch.zeros_like(per_sample))
    return per_sample_clean.sum() / n.clamp(min=1).float()
PYEOF
```

- [ ] **Step 4: Run tests, verify pass**

Run: `python -m pytest tests/test_v5_nll.py -v 2>&1 | tail -10`
Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_v5_nll.py src/training/v5_losses/heteroscedastic_components.py
git commit -m "feat(v5): Gaussian NLL loss with log_sigma clipping"
```

### Task A.4: Implement Huber loss on raw y (TDD)

**Files:**
- Create: `tests/test_v5_huber.py`
- Create: `src/training/v5_losses/huber_components.py`

- [ ] **Step 1: Write failing tests**

```bash
cat > tests/test_v5_huber.py << 'TESTEOF'
"""Unit tests for V5 Huber loss on raw y."""
import torch


def test_huber_zero_at_perfect():
    from src.training.v5_losses.huber_components import loss_huber_y
    y = torch.tensor([0.0, 1.0, -1.0, 2.5])
    mu = y.clone()
    mask = torch.ones_like(y).bool()
    loss = loss_huber_y(mu, y, mask, delta=1.0)
    assert abs(loss.item()) < 1e-6


def test_huber_quadratic_in_inner_region():
    """For |y-μ| < δ, loss = 0.5·(y-μ)² (quadratic)."""
    from src.training.v5_losses.huber_components import loss_huber_y
    y = torch.tensor([0.0])
    mu = torch.tensor([0.5])  # diff = 0.5, δ = 1.0 → inner region
    mask = torch.ones_like(y).bool()
    loss = loss_huber_y(mu, y, mask, delta=1.0)
    expected = 0.5 * 0.5 ** 2
    assert abs(loss.item() - expected) < 1e-6


def test_huber_linear_in_outer_region():
    """For |y-μ| > δ, loss = δ·(|y-μ| - 0.5δ) (linear)."""
    from src.training.v5_losses.huber_components import loss_huber_y
    y = torch.tensor([0.0])
    mu = torch.tensor([3.0])  # diff = 3, δ = 1.0 → outer region
    mask = torch.ones_like(y).bool()
    loss = loss_huber_y(mu, y, mask, delta=1.0)
    expected = 1.0 * (3.0 - 0.5)
    assert abs(loss.item() - expected) < 1e-6


def test_huber_robust_to_outlier_vs_mse():
    """Huber loss should be smaller than MSE for extreme outliers (key property)."""
    from src.training.v5_losses.huber_components import loss_huber_y
    y = torch.tensor([0.0, 0.0, 0.0, 0.0, 100.0])  # one extreme outlier
    mu = torch.zeros_like(y)
    mask = torch.ones_like(y).bool()
    huber_loss = loss_huber_y(mu, y, mask, delta=1.0).item()
    mse_loss = ((y - mu) ** 2).mean().item()
    assert huber_loss < mse_loss / 2  # Huber bounds outlier impact


def test_huber_mask_handling():
    from src.training.v5_losses.huber_components import loss_huber_y
    y = torch.tensor([1e10, 0.0, 0.0, 1.0])
    mu = torch.zeros_like(y)
    mask = torch.tensor([False, True, True, True])
    loss = loss_huber_y(mu, y, mask, delta=1.0)
    # Only y=0,0,1 contribute; (0-0)² + (0-0)² + (0.5·1²) avg
    # = (0 + 0 + 0.5) / 3
    expected = 0.5 / 3
    assert abs(loss.item() - expected) < 1e-5
TESTEOF
```

- [ ] **Step 2: Run tests (expect fail)**

Run: `python -m pytest tests/test_v5_huber.py -v 2>&1 | tail -10`
Expected: 5 fail with ImportError.

- [ ] **Step 3: Implement**

```bash
cat > src/training/v5_losses/huber_components.py << 'PYEOF'
"""Huber loss on raw y for V5.

Huber loss: smooth interpolation between MSE (inner) and MAE (outer).
   L = 0.5·(y-μ)²   if |y-μ| ≤ δ
   L = δ·(|y-μ| - 0.5δ)   if |y-μ| > δ

For low-SNR finance (heavy tails), Huber's outlier robustness reduces gradient
contributions from extreme returns, leading to more stable optimization than
pure MSE while preserving magnitude prediction (unlike q50 pinball which
shrinks to median = unconditional mean).
"""
from __future__ import annotations
import torch


def loss_huber_y(
    mu: torch.Tensor,
    y: torch.Tensor,
    mask: torch.Tensor,
    delta: float = 1.0,
) -> torch.Tensor:
    """Huber loss between μ (prediction) and y (target) with masking.

    Parameters
    ----------
    mu, y : same-shape tensors
    mask : bool tensor, same shape
    delta : Huber transition threshold (in same units as y)
    """
    if mask.dtype != torch.bool:
        mask = mask.bool()
    valid = mask & torch.isfinite(y) & torch.isfinite(mu)
    n = valid.sum()
    if n == 0:
        return (mu * 0.0).sum()

    diff = y - mu
    abs_diff = diff.abs()
    quad = 0.5 * diff * diff
    lin = delta * (abs_diff - 0.5 * delta)
    per_sample = torch.where(abs_diff <= delta, quad, lin)
    per_sample_clean = torch.where(valid, per_sample, torch.zeros_like(per_sample))
    return per_sample_clean.sum() / n.clamp(min=1).float()
PYEOF
```

- [ ] **Step 4: Run tests (expect pass)**

Run: `python -m pytest tests/test_v5_huber.py -v 2>&1 | tail -10`
Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_v5_huber.py src/training/v5_losses/huber_components.py
git commit -m "feat(v5): Huber loss on raw y for robust magnitude prediction"
```

### Task A.5: Implement HeteroscedasticHead (TDD)

**Files:**
- Create: `tests/test_v5_head.py`
- Create: `src/training/v5_losses/heteroscedastic_head.py`

- [ ] **Step 1: Write tests**

```bash
cat > tests/test_v5_head.py << 'TESTEOF'
"""Unit tests for HeteroscedasticHead."""
import torch


def test_head_output_shapes():
    from src.training.v5_losses.heteroscedastic_head import HeteroscedasticHead
    head = HeteroscedasticHead(d_emb=32, n_horizons=1, hidden=0)
    emb = torch.randn(4, 32)
    out = head(emb)
    assert "mu" in out and "log_sigma" in out and "y_pred" in out
    assert out["mu"].shape == (4, 1)
    assert out["log_sigma"].shape == (4, 1)
    assert torch.allclose(out["y_pred"], out["mu"])


def test_head_initial_log_sigma_reasonable():
    from src.training.v5_losses.heteroscedastic_head import HeteroscedasticHead
    torch.manual_seed(0)
    head = HeteroscedasticHead(d_emb=32, n_horizons=1, hidden=0)
    emb = torch.randn(100, 32)
    with torch.no_grad():
        out = head(emb)
    sigma = torch.exp(out["log_sigma"])
    assert 0.3 < sigma.mean().item() < 3.0


def test_head_with_hidden_bottleneck():
    from src.training.v5_losses.heteroscedastic_head import HeteroscedasticHead
    head = HeteroscedasticHead(d_emb=32, n_horizons=1, hidden=16, dropout=0.1)
    emb = torch.randn(4, 32)
    out = head(emb)
    assert out["mu"].shape == (4, 1)


def test_head_backward_stable():
    from src.training.v5_losses.heteroscedastic_head import HeteroscedasticHead
    head = HeteroscedasticHead(d_emb=8, n_horizons=1, hidden=0)
    emb = torch.randn(4, 8) * 100
    out = head(emb)
    loss = out["mu"].sum() + out["log_sigma"].sum()
    loss.backward()
    for p in head.parameters():
        assert torch.isfinite(p.grad).all()
TESTEOF
```

- [ ] **Step 2: Run (fail), then implement**

```bash
python -m pytest tests/test_v5_head.py -v 2>&1 | tail -10
```

```bash
cat > src/training/v5_losses/heteroscedastic_head.py << 'PYEOF'
"""V5 HeteroscedasticHead: outputs (μ, log_σ) per sample."""
from __future__ import annotations
from typing import Dict
import torch
import torch.nn as nn


class HeteroscedasticHead(nn.Module):
    def __init__(self, d_emb: int, n_horizons: int = 1, hidden: int = 0, dropout: float = 0.1):
        super().__init__()
        self.d_emb = d_emb
        self.n_horizons = n_horizons

        if hidden > 0:
            self.mu_trunk = nn.Sequential(
                nn.Linear(d_emb, hidden), nn.LeakyReLU(0.1), nn.Dropout(dropout)
            )
            self.log_sigma_trunk = nn.Sequential(
                nn.Linear(d_emb, hidden), nn.LeakyReLU(0.1), nn.Dropout(dropout)
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
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, a=0.1, nonlinearity="leaky_relu")
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
        nn.init.normal_(self.mu_proj.weight, mean=0.0, std=1e-3)
        nn.init.normal_(self.log_sigma_proj.weight, mean=0.0, std=1e-3)
        nn.init.zeros_(self.log_sigma_proj.bias)

    def forward(self, emb: torch.Tensor) -> Dict[str, torch.Tensor]:
        h_mu = self.mu_trunk(emb)
        h_ls = self.log_sigma_trunk(emb)
        mu = self.mu_proj(h_mu)
        log_sigma = self.log_sigma_proj(h_ls)
        return {"mu": mu, "log_sigma": log_sigma, "y_pred": mu}
PYEOF
```

- [ ] **Step 3: Run pass + commit**

```bash
python -m pytest tests/test_v5_head.py -v 2>&1 | tail -10
git add tests/test_v5_head.py src/training/v5_losses/heteroscedastic_head.py
git commit -m "feat(v5): HeteroscedasticHead outputs (mu, log_sigma)"
```

### Task A.6: Wire all 4 losses into V5LossAssembly

**Files:**
- Modify: `src/training/v5_losses/loss_assembly.py`
- Modify: `src/training/v5_losses/__init__.py`

- [ ] **Step 1: Open loss_assembly.py and add NLL + Huber paths**

In `src/training/v5_losses/loss_assembly.py`, find the existing `V5LossConfig` dataclass. Add fields for NLL + Huber:

After `w_beta_consistency: float = 0.0`, add:
```python
    # V5 heteroscedastic NLL path
    w_gaussian_nll: float = 0.0
    nll_log_sigma_min: float = -7.0
    nll_log_sigma_max: float = 2.0
    # V5 Huber-on-raw-y path (single head, robust MSE)
    w_huber_y: float = 0.0
    huber_y_delta: float = 1.0
```

In imports (after existing components imports):
```python
from .heteroscedastic_components import loss_gaussian_nll
from .huber_components import loss_huber_y
```

In `V5LossAssembly.__call__`, after the `w_beta_consistency` block and BEFORE `out["total"] = total`:

```python
        if cfg.w_gaussian_nll > 0:
            l = loss_gaussian_nll(
                head_out["mu"], head_out["log_sigma"], y, mask,
                log_sigma_min=cfg.nll_log_sigma_min,
                log_sigma_max=cfg.nll_log_sigma_max,
            )
            out["gaussian_nll"] = l
            total = total + cfg.w_gaussian_nll * l

        if cfg.w_huber_y > 0:
            # For Huber, head_out['mu'] is the prediction; if NLL not active, mu = y_pred
            mu_for_huber = head_out.get("mu", head_out.get("y_pred"))
            l = loss_huber_y(mu_for_huber, y, mask, delta=cfg.huber_y_delta)
            out["huber_y"] = l
            total = total + cfg.w_huber_y * l
```

- [ ] **Step 2: Verify smoke check**

```bash
python -c "
import torch
from src.training.v5_losses.loss_assembly import V5LossAssembly, V5LossConfig

# NLL only
cfg = V5LossConfig(w_dir_margin=0, w_mag_huber=0, w_joint_mse=0, w_gaussian_nll=1.0)
a = V5LossAssembly(cfg)
out = a({'mu': torch.zeros(4, 1), 'log_sigma': torch.zeros(4, 1),
         'dir_logit': torch.zeros(4, 1), 'mag': torch.zeros(4, 1), 'y_pred': torch.zeros(4, 1)},
        torch.randn(4, 1), torch.ones(4, 1).bool())
assert 'gaussian_nll' in out
assert torch.isfinite(out['total']).item()
print('NLL: OK')

# Huber only
cfg = V5LossConfig(w_dir_margin=0, w_mag_huber=0, w_joint_mse=0, w_huber_y=1.0)
a = V5LossAssembly(cfg)
out = a({'mu': torch.zeros(4, 1), 'log_sigma': torch.zeros(4, 1),
         'dir_logit': torch.zeros(4, 1), 'mag': torch.zeros(4, 1), 'y_pred': torch.zeros(4, 1)},
        torch.randn(4, 1), torch.ones(4, 1).bool())
assert 'huber_y' in out
print('Huber: OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add src/training/v5_losses/loss_assembly.py
git commit -m "feat(v5): wire Gaussian NLL + Huber-on-y into V5LossAssembly"
```

### Task A.7: V5 loss_fn factory

**Files:**
- Create: `src/training/v5_losses/v5_loss_fn.py`

- [ ] **Step 1: Write factory**

```bash
cat > src/training/v5_losses/v5_loss_fn.py << 'PYEOF'
"""Factory: build a loss_fn compatible with train_one_fold_v2.

train_one_fold_v2 expects: loss_fn(outputs_dict, target) -> scalar tensor

V5LossAssembly expects: assembly(head_out, y, mask) -> {'total': ...}
"""
from __future__ import annotations
from typing import Callable, Dict
import torch

from .loss_assembly import V5LossAssembly, V5LossConfig


def build_v5_loss_fn(loss_cfg_dict: dict) -> Callable[[Dict[str, torch.Tensor], torch.Tensor], torch.Tensor]:
    cfg = V5LossConfig(**loss_cfg_dict)
    assembly = V5LossAssembly(cfg)

    def _loss_fn(outputs: Dict[str, torch.Tensor], target: torch.Tensor) -> torch.Tensor:
        mask = outputs.get("mask")
        if mask is None:
            mask = torch.isfinite(target)
        out = assembly(outputs, target, mask)
        return out["total"]

    return _loss_fn
PYEOF
```

- [ ] **Step 2: Smoke + commit**

```bash
python -c "
import torch
from src.training.v5_losses.v5_loss_fn import build_v5_loss_fn
fn = build_v5_loss_fn({'w_gaussian_nll': 1.0, 'w_huber_y': 0.0})
out = {'mu': torch.randn(4, 1), 'log_sigma': torch.zeros(4, 1),
       'dir_logit': torch.zeros(4, 1), 'mag': torch.ones(4, 1), 'y_pred': torch.randn(4, 1),
       'mask': torch.ones(4, 1).bool()}
loss = fn(out, torch.randn(4, 1))
print(f'OK loss={loss.item():.4f}')
"
git add src/training/v5_losses/v5_loss_fn.py
git commit -m "feat(v5): build_v5_loss_fn factory bridges V5LossAssembly to trainer_v2"
```

### Task A.8: V5Model wrapper

**Files:**
- Create: `src/model/v5_model.py`

- [ ] **Step 1: Check V4 has .encode() or refactor to add it**

Run: `grep -n "def encode\|def forward" src/model/dual_path_model_v3.py | head -5`

If `encode` doesn't exist, refactor V4 to expose it.

Open `src/model/dual_path_model_v3.py`, find the `def forward(self, ...)` method around line 515. Locate the line near the end where `h_pred` flows into `self.head` (search for `self.head(` or the final quantile output).

Refactor: extract the body up to (but not including) the head call into a new method `def encode(self, ...) -> torch.Tensor` returning `h_pred`. Keep `forward` calling `encode` then `head`. **No behavior change.**

Concretely (pseudocode):
```python
def encode(self, x_feat, x_raw=None, regime_prior=None, ...):
    # ... [body of forward, up to but NOT including self.head(...)]
    return h_pred

def forward(self, x_feat, x_raw=None, regime_prior=None, ...):
    h_pred = self.encode(x_feat, x_raw, regime_prior, ...)
    # apply self.head(...) and return its dict
```

- [ ] **Step 2: Verify V4 smoke still works post-refactor**

```bash
python -c "
import json
from src.model.dual_path_model_v3 import DualPathLOBModelV3
cfg = json.load(open('configs/y600_push/baseline_plus.json'))
m = DualPathLOBModelV3(**cfg['model'], n_levels=cfg['data']['n_levels'])
print(f'V4 backbone OK: {sum(p.numel() for p in m.parameters())} params')
assert hasattr(m, 'encode'), '.encode() missing after refactor'
print('encode() present')
"
```

- [ ] **Step 3: Implement V5Model**

```bash
cat > src/model/v5_model.py << 'PYEOF'
"""V5Model: V4 backbone + HeteroscedasticHead (or other V5 heads).

Wraps DualPathLOBModelV3, calls .encode() to get embedding, replaces V4 head
with V5 head. V4 backbone params unchanged.
"""
from __future__ import annotations
from typing import Dict, Optional
import torch
import torch.nn as nn

from src.model.dual_path_model_v3 import DualPathLOBModelV3
from src.training.v5_losses.heteroscedastic_head import HeteroscedasticHead


class V5Model(nn.Module):
    def __init__(self, v4_kwargs: dict, head_hidden: int = 0, head_dropout: float = 0.1):
        super().__init__()
        v4_kwargs = dict(v4_kwargs)
        self.n_horizons = int(v4_kwargs.get("n_horizons", 1))
        self.backbone = DualPathLOBModelV3(**v4_kwargs)
        d_emb = self._discover_d_emb()
        self.v5_head = HeteroscedasticHead(
            d_emb=d_emb, n_horizons=self.n_horizons,
            hidden=head_hidden, dropout=head_dropout,
        )

    def _discover_d_emb(self) -> int:
        b = self.backbone
        for attr in ["d_emb", "d_fused", "d_out", "d_model"]:
            if hasattr(b, attr):
                v = getattr(b, attr)
                if isinstance(v, int):
                    return v
        if hasattr(b, "head"):
            for m in b.head.modules():
                if isinstance(m, nn.Linear):
                    return m.in_features
        return 32

    def forward(self, *args, mask: Optional[torch.Tensor] = None, **kwargs) -> Dict[str, torch.Tensor]:
        if not hasattr(self.backbone, "encode"):
            raise RuntimeError("V4 backbone missing .encode(); refactor required")
        emb = self.backbone.encode(*args, **kwargs)
        out = self.v5_head(emb)
        if mask is not None:
            out["mask"] = mask
        return out
PYEOF
```

- [ ] **Step 4: Smoke check + commit**

```bash
python -c "
import json
from src.model.v5_model import V5Model
cfg = json.load(open('configs/y600_push/baseline_plus.json'))
v4_kwargs = dict(cfg['model'])
v4_kwargs['n_levels'] = cfg['data']['n_levels']
m = V5Model(v4_kwargs=v4_kwargs)
print(f'V5 OK: {sum(p.numel() for p in m.parameters())} params')
"
# git add depends on whether you modified dual_path_model_v3.py for .encode()
git add src/model/v5_model.py
# git add src/model/dual_path_model_v3.py  # if refactored
git commit -m "feat(v5): V5Model wraps V4 backbone, exposes HeteroscedasticHead"
```

### Task A.9: Add embargo + screen configs

**Files:**
- Modify: NONE (use existing `training.embargo_days` plumbed at run_pipeline_v3.py:400-414)
- Create: `tests/test_v5_embargo_observable.py` (split-sample-count regression test)
- Create: `configs/v5/screen/backbone_v4base.json`
- Create: `configs/v5/screen/backbone_attention.json`
- Create: `configs/v5/screen/backbone_mamba.json`
- Create: `configs/v5/screen/backbone_emapool.json`

**CODEX FIX**: existing pipeline already reads `training.embargo_days` (run_pipeline_v3.py:400). Plan v1's `data.embargo_seconds` would be SILENTLY IGNORED, producing fake-embargo runs. **Fix: use `training.embargo_days = 1`** (= 86400s ≫ 600s horizon, conservative over-purge but safe). NO new code in dataset.py.

- [ ] **Step 1: Verify embargo_days IS plumbed (audit, no code change)**

Run: `grep -n "embargo_days" run_pipeline_v3.py`
Expected: 4+ hits at lines 400, 401, 407, 414. Confirms `training.embargo_days` flows to fold builder.

If grep misses any line, embargo plumbing is NOT trusted; STOP, raise to design owner before proceeding.

- [ ] **Step 2: Write split-sample-count regression test**

```bash
cat > tests/test_v5_embargo_observable.py << 'TESTEOF'
"""Regression test: training.embargo_days actually changes train sample count.

Codex review found the original plan v2 silently set data.embargo_seconds, which
the pipeline ignored. This test ensures any future refactor preserves embargo
observable through training.embargo_days.
"""
import json
import pytest


def _build_loader_train_count(config: dict, fold_idx: int = 0) -> int:
    """Helper: build train loader for given config + fold, return sample count."""
    # The exact loader build path depends on run_pipeline_v3 internals.
    # Skip this test if helpers not exposed; document the gap rather than skipping silently.
    try:
        from run_pipeline_v3 import build_fold_datasets
    except ImportError:
        pytest.fail(
            "build_fold_datasets not importable from run_pipeline_v3. "
            "If pipeline doesn't expose dataset builder, add a tiny helper or "
            "instrument the embargo path directly."
        )
    train_ds, _val_ds, _test_ds = build_fold_datasets(config, fold_idx)
    return len(train_ds)


def test_embargo_observable_changes_train_count():
    """embargo_days=1 must produce a strictly smaller train set than embargo_days=0."""
    cfg = json.load(open("configs/y600_push/baseline_plus.json"))
    cfg.setdefault("training", {})

    cfg["training"]["embargo_days"] = 0
    n_no_embargo = _build_loader_train_count(cfg, fold_idx=0)

    cfg["training"]["embargo_days"] = 1
    n_with_embargo = _build_loader_train_count(cfg, fold_idx=0)

    print(f"embargo=0 train: {n_no_embargo}")
    print(f"embargo=1 train: {n_with_embargo}")
    assert n_with_embargo < n_no_embargo, (
        f"Embargo silently ignored: embargo=1 train ({n_with_embargo}) "
        f">= embargo=0 train ({n_no_embargo}). Fix pipeline before any V5 run."
    )
TESTEOF
```

- [ ] **Step 3: Run regression test**

Run: `python -m pytest tests/test_v5_embargo_observable.py -v -s 2>&1 | tail -10`

If `build_fold_datasets` does not exist, the test FAILS LOUDLY (not skipped). In that case, before continuing the plan, refactor `run_pipeline_v3.py` to expose `build_fold_datasets(config, fold_idx) → (train, val, test)` helper. **Do NOT skip this test.**

- [ ] **Step 4: Build 4 backbone screen configs (use training.embargo_days)**

```bash
mkdir -p configs/v5/screen

# Config 1: V4 baseline (control) — no embargo (matches V4 production exactly)
cp configs/y600_push/baseline_plus.json configs/v5/screen/backbone_v4base.json

# Config 2-4: V5 candidates with embargo_days=1 (conservative, > horizon=600s)
for variant in attention mamba emapool; do
  cp configs/y600_push/baseline_plus.json configs/v5/screen/backbone_${variant}.json
done

python << 'PYEOF'
import json
# attention
c = json.load(open('configs/v5/screen/backbone_attention.json'))
c['model']['use_attention'] = True
c['model']['use_patch_attention_pool'] = True
c.setdefault('training', {})['embargo_days'] = 1  # ← CODEX FIX: use existing key
json.dump(c, open('configs/v5/screen/backbone_attention.json', 'w'), indent=2)
print('attention config written')

# mamba
c = json.load(open('configs/v5/screen/backbone_mamba.json'))
c['model']['use_attention'] = False
c['model']['use_conv'] = False
c['model']['backbone_kind'] = 'mamba'
c['model']['backbone_kwargs'] = {'d_state': 16, 'd_conv': 4, 'expand': 2}
c.setdefault('training', {})['embargo_days'] = 1
json.dump(c, open('configs/v5/screen/backbone_mamba.json', 'w'), indent=2)
print('mamba config written')

# ema_pool
c = json.load(open('configs/v5/screen/backbone_emapool.json'))
c['model']['use_attention'] = False
c['model']['use_conv'] = False
c['model']['backbone_kind'] = 'ema_pool'
c['model']['backbone_kwargs'] = {'alpha': 0.1}
c.setdefault('training', {})['embargo_days'] = 1
json.dump(c, open('configs/v5/screen/backbone_emapool.json', 'w'), indent=2)
print('ema_pool config written')
PYEOF
```

(Adjust `backbone_kind` / `backbone_kwargs` based on what `dual_path_model_v3.py` accepts. Inspect lines 376-400 for the existing backbone dispatch logic.)

- [ ] **Step 5: Verify all 4 configs valid JSON + embargo set**

```bash
for f in configs/v5/screen/backbone_*.json; do
  python -c "
import json
c = json.load(open('$f'))
print('$f embargo_days:', c.get('training', {}).get('embargo_days', 0))
"
done
```
Expected: backbone_v4base = 0, others = 1.

- [ ] **Step 5: Commit**

```bash
git add src/training/dataset.py configs/v5/screen/backbone_*.json
git commit -m "feat(v5): add embargo + 4 backbone screen configs"
```

### Task A.10: Build screen orchestrator script

**Files:**
- Create: `scripts/v5_screen_orchestrator.py`

- [ ] **Step 1: Write orchestrator**

```bash
cat > scripts/v5_screen_orchestrator.py << 'PYEOF'
"""V5 fold-0 screen orchestrator.

Usage (on pod after sync):
    python scripts/v5_screen_orchestrator.py \
        --phase B1 \
        --output_dir experiments/v5_screen \
        --skip-existing

Phases:
    B1: backbone screen (4 configs) — fold 0 only
    B2: loss screen (4 losses on B1 winner) — fold 0 only
    B3: data screen (single-train comparison) — 1 run

For each run, calls run_pipeline_v3.py with the config + outputs to subdir.
After all runs in phase, computes pooled-fold-0 metrics for comparison.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


PHASE_CONFIGS = {
    "B1": [
        ("v4base", "configs/v5/screen/backbone_v4base.json"),
        ("attention", "configs/v5/screen/backbone_attention.json"),
        ("mamba", "configs/v5/screen/backbone_mamba.json"),
        ("emapool", "configs/v5/screen/backbone_emapool.json"),
    ],
    "B2": [],  # filled after B1 winner identified
    "B3": [
        ("singletrain", "configs/v5/screen/data_singletrain.json"),
    ],
}


def run_one(name: str, config_path: str, out_dir: Path, seed: int, skip_existing: bool):
    """Run fold-0 only for one config."""
    sub_out = out_dir / name
    sub_out.mkdir(parents=True, exist_ok=True)
    if skip_existing and (sub_out / "fold_0" / "test_preds.npz").exists():
        print(f"[SKIP] {name}: already done")
        return
    cmd = [
        "python", "run_pipeline_v3.py",
        "--config", config_path,
        "--output_dir", str(sub_out),
        "--skip-features",
        "--seed", str(seed),
        "--start-fold", "0",
        "--max-folds", "1",
    ]
    print(f"[RUN] {name}: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        print(f"[FAIL] {name}: returncode {result.returncode}")
    else:
        print(f"[OK] {name}: done")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--phase", choices=["B1", "B2", "B3"], required=True)
    p.add_argument("--output_dir", default="experiments/v5_screen")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--skip-existing", action="store_true")
    args = p.parse_args()

    out_dir = Path(args.output_dir) / args.phase
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.phase not in PHASE_CONFIGS or not PHASE_CONFIGS[args.phase]:
        sys.exit(f"Phase {args.phase} not configured (B2 needs B1 winner first)")

    for name, config_path in PHASE_CONFIGS[args.phase]:
        if not Path(config_path).exists():
            print(f"[WARN] config missing: {config_path}; skip {name}")
            continue
        run_one(name, config_path, out_dir, args.seed, args.skip_existing)

    print(f"\nPhase {args.phase} complete. Run eval next:")
    print(f"  python scripts/v5_eval_comprehensive.py --exp-dir {out_dir}/<name> --n-folds 1 --out exports/{args.phase}_<name>.md")


if __name__ == "__main__":
    main()
PYEOF
```

- [ ] **Step 2: Commit (don't run yet — pod task)**

```bash
git add scripts/v5_screen_orchestrator.py
git commit -m "feat(v5): screen orchestrator for fold-0 backbone/loss/data comparisons"
```

### Task A.11: Update run_pipeline_v3.py for V5 dispatch

**Files:**
- Modify: `run_pipeline_v3.py`

- [ ] **Step 1: Find model build site**

Run: `grep -n "DualPathLOBModelV3\|model = \|train_one_fold_v2(" run_pipeline_v3.py | head -10`

- [ ] **Step 2: Add V5 dispatch**

Wrap the model instantiation:

```python
# Determine V5 mode from config
loss_cfg = config.get("loss", {})
v5_loss_active = (
    loss_cfg.get("w_gaussian_nll", 0) > 0 or
    loss_cfg.get("w_huber_y", 0) > 0 or
    loss_cfg.get("use_v5_dual_head", False)
)

# CODEX FIX (DANN): V3 allowlist forwards DANN keys but V5Model wraps V3 which has
# no use_dann/lambda_grl/n_domains support. Strip DANN keys from V5 path explicitly
# to avoid silent crash at construction or during trainer's lambda_grl access.
DANN_KEYS = {"use_dann", "n_domains", "dann_hidden_dim"}

if v5_loss_active:
    from src.model.v5_model import V5Model
    from src.training.v5_losses.v5_loss_fn import build_v5_loss_fn
    v4_kwargs = dict(config["model"])
    # Strip DANN keys (not supported in V3 backbone)
    stripped = [k for k in DANN_KEYS if v4_kwargs.pop(k, None) is not None]
    if stripped:
        print(f"[V5] Stripped unsupported DANN keys: {stripped}")
    # Also: V5 path must not enable DANN at training level
    if config.get("training", {}).get("use_dann", False):
        raise RuntimeError(
            "V5 path is incompatible with use_dann=True (V3 backbone has no DANN support). "
            "Set training.use_dann=False or remove DANN from this config."
        )
    v4_kwargs["n_levels"] = config["data"]["n_levels"]
    model = V5Model(v4_kwargs=v4_kwargs, head_hidden=int(loss_cfg.get("head_hidden", 0)))
    custom_loss_fn = build_v5_loss_fn(loss_cfg)
    print("[V5] V5Model + V5 loss_fn dispatched")
else:
    # V4 path (unchanged) — DANN handling stays whatever V4 does
    model = DualPathLOBModelV3(**config["model"], n_levels=config["data"]["n_levels"])
    custom_loss_fn = None
```

Pass `loss_fn=custom_loss_fn` to `train_one_fold_v2(...)`. The `train_one_fold_v2` already accepts this parameter (line 387).

**Also pass `use_dann=False` explicitly when V5 path is active**, to override any inherited config flag:
```python
trainer_kwargs = {
    "loss_fn": custom_loss_fn,
    # other existing kwargs...
}
if v5_loss_active:
    trainer_kwargs["use_dann"] = False  # CODEX FIX: V5 incompatible with DANN
```

- [ ] **Step 3: Verify dispatch**

```bash
python -c "
import json
cfg = json.load(open('configs/y600_push/baseline_plus.json'))
v5_active = (cfg.get('loss', {}).get('w_gaussian_nll', 0) > 0
             or cfg.get('loss', {}).get('w_huber_y', 0) > 0)
print(f'V4 baseline V5 active? {v5_active}')
# Expected: False (no v5 loss flags in V4 config)
"
```

- [ ] **Step 4: Commit**

```bash
git add run_pipeline_v3.py
git commit -m "feat(v5): dispatch V5Model + V5 loss_fn when V5 loss flags set in config"
```

---

## Phase B: Pod fold-0 screens (~$30)

### Task B.1: Backbone screen (4 configs, fold 0 only)

**Files:**
- (Use existing) `scripts/v5_screen_orchestrator.py`, `configs/v5/screen/backbone_*.json`

**Phase B.1 runs ON POD** (not local). Local prep produces all configs and orchestrator; engineer spins pod and executes there.

- [ ] **Step 1: Pod setup**

```
ssh <pod>
cd quant_research && git pull
pip install -r requirements.txt
# (optional) verify mamba-ssm installed for backbone_mamba.json
python -c "import mamba_ssm; print('mamba-ssm OK')"
```

- [ ] **Step 2: Run B.1 orchestrator**

```
python scripts/v5_screen_orchestrator.py \
    --phase B1 \
    --output_dir experiments/v5_screen \
    --skip-existing 2>&1 | tee experiments/v5_screen/B1.log
```

Expected: 4 fold-0 runs, ~3-4 hr each, total ~12-16 hr. Total pod cost: ~$10-12.

- [ ] **Step 3: Eval each B.1 result**

For each backbone variant in {v4base, attention, mamba, emapool}:
```
python scripts/v5_eval_comprehensive.py \
    --exp-dir experiments/v5_screen/B1/<variant> \
    --n-folds 1 \
    --out exports/v5_screen_B1_<variant>.md
```

- [ ] **Step 4: Compare and lock B.1 winner**

The "winner" is determined by composite ranking on fold-0 metrics:
- **Required**: P ≥ 0.045 AND σ_ŷ/σ_y > 0.06 (above V4 baseline 0.045)
- **Tiebreaker**: top decile trading view E[y] (higher better)

Manually edit `docs/V5_DESIGN_v2.md` and add Phase B.1 results table:
```markdown
## Phase B.1 Results (filled in after pod run)

| Config | fold-0 P | fold-0 σ_ŷ/σ_y | β | top decile E[y] | Pass G2? | Verdict |
|---|---|---|---|---|---|---|
| v4base (control) | ? | ? | ? | ? | ? | ? |
| attention | ? | ? | ? | ? | ? | ? |
| mamba | ? | ? | ? | ? | ? | ? |
| emapool | ? | ? | ? | ? | ? | ? |

Winner: <name> — chosen because <reason>
```

- [ ] **Step 5: Commit results doc**

```
git add docs/V5_DESIGN_v2.md exports/v5_screen_B1_*.md
git commit -m "results(v5): Phase B.1 backbone screen complete; winner=<name>"
```

### Task B.2: Loss screen on B.1 winner (4 losses, fold 0 only)

Pre-condition: B.1 winner identified.

- [ ] **Step 1: Build 4 loss screen configs based on B.1 winner**

```bash
WINNER=<name from B.1>  # e.g., "attention", "mamba"

# L0: control (existing quantile + utility_rank from B.1 winner)
cp configs/v5/screen/backbone_${WINNER}.json configs/v5/screen/loss_quantile.json

# L1: Huber on raw y
cp configs/v5/screen/backbone_${WINNER}.json configs/v5/screen/loss_huber.json
python -c "
import json
c = json.load(open('configs/v5/screen/loss_huber.json'))
c.setdefault('loss', {})
c['loss'].update({'w_huber_y': 1.0, 'huber_y_delta': 1.0,
                   'w_gaussian_nll': 0.0, 'w_dir_margin': 0.0,
                   'w_mag_huber': 0.0, 'w_joint_mse': 0.0})
# Disable existing dul_config (V4 quantile + utility_rank)
c['training'].pop('dul_config', None)
json.dump(c, open('configs/v5/screen/loss_huber.json', 'w'), indent=2)
print('loss_huber config written')
"

# L2: Gaussian NLL
cp configs/v5/screen/backbone_${WINNER}.json configs/v5/screen/loss_nll.json
python -c "
import json
c = json.load(open('configs/v5/screen/loss_nll.json'))
c.setdefault('loss', {})
c['loss'].update({'w_gaussian_nll': 1.0, 'nll_log_sigma_min': -7.0, 'nll_log_sigma_max': 2.0,
                   'w_huber_y': 0.0, 'w_dir_margin': 0.0,
                   'w_mag_huber': 0.0, 'w_joint_mse': 0.0})
c['training'].pop('dul_config', None)
json.dump(c, open('configs/v5/screen/loss_nll.json', 'w'), indent=2)
print('loss_nll config written')
"

# L3: V5 dual-head (existing scaffold)
cp configs/v5/screen/backbone_${WINNER}.json configs/v5/screen/loss_dualhead.json
python -c "
import json
c = json.load(open('configs/v5/screen/loss_dualhead.json'))
c.setdefault('loss', {})
c['loss'].update({'w_dir_margin': 0.3, 'w_mag_huber': 0.3, 'w_joint_mse': 0.5,
                   'w_huber_y': 0.0, 'w_gaussian_nll': 0.0,
                   'use_v5_dual_head': True, 'mag_huber_delta': 2.0,
                   'joint_huber_delta': 0.0})
c['training'].pop('dul_config', None)
json.dump(c, open('configs/v5/screen/loss_dualhead.json', 'w'), indent=2)
print('loss_dualhead config written')
"
```

- [ ] **Step 2: Update orchestrator with B.2 configs**

```bash
# Edit scripts/v5_screen_orchestrator.py, replace PHASE_CONFIGS["B2"] = [] with:
python -c "
import re
content = open('scripts/v5_screen_orchestrator.py').read()
new_b2 = '''    \"B2\": [
        (\"quantile\", \"configs/v5/screen/loss_quantile.json\"),
        (\"huber\", \"configs/v5/screen/loss_huber.json\"),
        (\"nll\", \"configs/v5/screen/loss_nll.json\"),
        (\"dualhead\", \"configs/v5/screen/loss_dualhead.json\"),
    ],'''
content = content.replace('\"B2\": [],  # filled after B1 winner identified', new_b2)
open('scripts/v5_screen_orchestrator.py', 'w').write(content)
print('B2 config registered')
"
```

- [ ] **Step 3: Run B.2 on pod**

```
python scripts/v5_screen_orchestrator.py \
    --phase B2 \
    --output_dir experiments/v5_screen \
    --skip-existing 2>&1 | tee experiments/v5_screen/B2.log
```

- [ ] **Step 4: Eval each B.2 result**

```
for v in quantile huber nll dualhead; do
    python scripts/v5_eval_comprehensive.py \
        --exp-dir experiments/v5_screen/B2/$v \
        --n-folds 1 \
        --out exports/v5_screen_B2_$v.md
done
```

- [ ] **Step 5: Determine B.2 winner**

Use V5 G1-G6 gates on each loss config. Add results table to V5_DESIGN_v2.md:

```markdown
## Phase B.2 Results

| Loss | P | σ_ŷ/σ_y | β | bin-S | top decile E[y] | Pass G2? | Pass G4? |
|---|---|---|---|---|---|---|---|
| quantile (control) | ? | ? | ? | ? | ? | ? | ? |
| huber | ? | ? | ? | ? | ? | ? | ? |
| nll | ? | ? | ? | ? | ? | ? | ? |
| dualhead | ? | ? | ? | ? | ? | ? | ? |

Winner: <name> — chosen because <highest weighted gate score>
```

Tiebreaker if multiple pass: σ_ŷ/σ_y largest wins.

- [ ] **Step 6: Commit**

```
git add configs/v5/screen/loss_*.json scripts/v5_screen_orchestrator.py docs/V5_DESIGN_v2.md exports/v5_screen_B2_*.md
git commit -m "results(v5): Phase B.2 loss screen complete; winner=<name>"
```

### Task B.3: Data setup screen (single-train vs 3-fold)

**Files:**
- Create: `configs/v5/screen/data_singletrain.json`

- [ ] **Step 1: Build single-train config**

```bash
cp configs/v5/screen/loss_<B2_winner>.json configs/v5/screen/data_singletrain.json
python -c "
import json
c = json.load(open('configs/v5/screen/data_singletrain.json'))
# Override CV split to single-train + single-test
c.setdefault('cv', {})
c['cv']['mode'] = 'single_split'
c['cv']['train_days'] = 750
c['cv']['val_days'] = 30
c['cv']['test_days'] = 200  # ~7 months out-of-sample
c['data']['embargo_seconds'] = 600
json.dump(c, open('configs/v5/screen/data_singletrain.json', 'w'), indent=2)
print('singletrain config written')
"
```

(May need to extend `dataset.py` to accept `cv.mode='single_split'`. If not yet supported, add a fallback in `run_pipeline_v3.py` that reads `cv.mode` and reroutes train/val/test boundaries.)

- [ ] **Step 2: Run B.3 on pod**

```
python scripts/v5_screen_orchestrator.py \
    --phase B3 \
    --output_dir experiments/v5_screen 2>&1 | tee experiments/v5_screen/B3.log
```

Expected: 1 run, ~5-7 hr (longer test period, longer eval). Cost ~$4.

- [ ] **Step 3: Eval B.3**

```
python scripts/v5_eval_comprehensive.py \
    --exp-dir experiments/v5_screen/B3/singletrain \
    --n-folds 1 \
    --out exports/v5_screen_B3_singletrain.md
```

- [ ] **Step 4: Decide D.0 (3-fold) vs D.1 (single-train)**

Compare metrics from B3 single-train against pooled metrics from B2 winner (3-fold). Single-train is better iff:
- P comparable (within ±0.005)
- σ_ŷ/σ_y comparable (within ±0.015)
- β comparable (|β_diff| < 0.10)
- AND wall-clock + ops simplicity favor single-train

Add to V5_DESIGN_v2.md:
```markdown
## Phase B.3 Result

| Setup | P | σ_ŷ/σ_y | β | wall-clock |
|---|---|---|---|---|
| 3-fold (B.2 winner) | ? | ? | ? | 3× train |
| single-train | ? | ? | ? | 1× train + larger test |

Verdict: <chosen setup> — <reason>
```

- [ ] **Step 5: Commit**

```
git add configs/v5/screen/data_singletrain.json docs/V5_DESIGN_v2.md exports/v5_screen_B3*.md
git commit -m "results(v5): Phase B.3 data screen complete; setup=<name>"
```

---

## Phase C: V5 final training

### Task C.1: Build v5_final config from screens

**Files:**
- Create: `configs/v5/v5_final.json`

- [ ] **Step 1: Compose final config from B winners**

```bash
# Replace WINNER paths with actual selected names
BACKBONE_WINNER=<from B1>
LOSS_WINNER=<from B2>
DATA_WINNER=<from B3>

cp configs/v5/screen/loss_${LOSS_WINNER}.json configs/v5/v5_final.json
# If data winner is single-train, also merge cv settings
if [ "$DATA_WINNER" = "singletrain" ]; then
    python -c "
import json
final = json.load(open('configs/v5/v5_final.json'))
single = json.load(open('configs/v5/screen/data_singletrain.json'))
final['cv'] = single['cv']
final.setdefault('training', {})['embargo_days'] = 1  # CODEX FIX: training.embargo_days, NOT data.embargo_seconds
json.dump(final, open('configs/v5/v5_final.json', 'w'), indent=2)
print('v5_final.json composed (single-train)')
"
fi
# (If data winner is 3-fold, no cv changes needed; embargo already set in screen config)
```

- [ ] **Step 2: Verify config valid**

```bash
python -c "
import json
c = json.load(open('configs/v5/v5_final.json'))
print('cv mode:', c.get('cv', {}).get('mode', '3-fold'))
print('loss config:')
for k, v in c.get('loss', {}).items():
    print(f'  {k}: {v}')
print('embargo_days:', c.get('training', {}).get('embargo_days', 0))
"
```

- [ ] **Step 3: Commit**

```bash
git add configs/v5/v5_final.json
git commit -m "feat(v5): compose v5_final.json from screen winners"
```

### Task C.2: Run V5 final training (3-fold OR single-train)

**Pod task.**

- [ ] **Step 1: Run final training**

```
# 3-fold (if D.0 won)
python run_pipeline_v3.py \
    --config configs/v5/v5_final.json \
    --output_dir experiments/v5_final \
    --skip-features \
    --seed 42 \
    --start-fold 0 \
    --max-folds 3 \
    2>&1 | tee experiments/v5_final/run.log

# Single-train (if D.1 won) — only 1 "fold"
python run_pipeline_v3.py \
    --config configs/v5/v5_final.json \
    --output_dir experiments/v5_final \
    --skip-features \
    --seed 42 \
    --start-fold 0 \
    --max-folds 1 \
    2>&1 | tee experiments/v5_final/run.log
```

Expected: ~9-12 hr (3-fold) or ~5-7 hr (single-train). Cost ~$8-12.

- [ ] **Step 2: Verify outputs**

```
ls experiments/v5_final/fold_*/test_preds.npz
```
Expected: prediction file(s) exist.

- [ ] **Step 3: Commit run log**

```
git add experiments/v5_final/run.log
git commit -m "results(v5): V5 final training complete"
```

---

## Phase D: Comprehensive eval + production deploy

### Task D.1: Run V5 gate-level eval

- [ ] **Step 1: Run comprehensive eval**

```
python scripts/v5_eval_comprehensive.py \
    --exp-dir experiments/v5_final \
    --n-folds 3 \
    --out exports/v5_final_eval.md
```

- [ ] **Step 2: Check all 6 gates**

Open `exports/v5_final_eval.md`. Verify:
- [ ] G1: Pearson ≥ 0.045
- [ ] G2: σ_ŷ/σ_y ≥ 0.10
- [ ] G3: |β - 1.0| ≤ 0.20
- [ ] G4: top decile E[y] ≥ +0.5 bps with t ≥ 2.0
- [ ] G5: bin-Spearman ≥ 0.85
- [ ] G6: |mean(ŷ)| ≤ 0.10 bps

If ANY fail: document in V5_DESIGN_v2.md "Failure analysis" section, do NOT deploy. Diagnose and decide between Phase B retry, V5 abandonment (V4 stays production), or V5.5 (next iteration).

If ALL pass: continue to D.2.

### Task D.2: Build production CSV

**Files:**
- Create: `scripts/export_v5_csv.py`
- Create: `exports/y600_v5_production.csv`
- Create: `exports/README_y600_v5.md`

- [ ] **Step 1: Write export script**

```bash
cat > scripts/export_v5_csv.py << 'PYEOF'
"""Export V5 prediction CSV for colleague backtest.

Output schema:
  timestamp_us, datetime_utc, fold, mask,
  y_true_logret, y_true_bps,
  y_pred_mu_bps,        # primary signal: μ in bps
  y_pred_sigma_bps,     # uncertainty: σ in bps (NLL only; 0 for non-NLL losses)
  y_sigma_train_bps     # training-period y σ for context

Usage: python scripts/export_v5_csv.py --exp-dir experiments/v5_final --out exports/y600_v5_production.csv
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--exp-dir", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--n-folds", type=int, default=3)
    args = p.parse_args()

    rows = []
    for fold in range(args.n_folds):
        npz_path = Path(args.exp_dir) / f"fold_{fold}" / "test_preds.npz"
        if not npz_path.exists():
            print(f"[WARN] missing {npz_path}; skip fold {fold}")
            continue
        d = np.load(npz_path)
        ts = d["timestamps"]
        mask = d["mask"]
        y_true_z = d.get("targets")
        sigma_train = float(d["y_sigma"])
        # CODEX FIX: trainer normalizes as (y - median) / sigma; de-normalization
        # MUST add y_median back. Dropping it shifts y_true and predictions by
        # a constant offset (typically near 0 but non-zero for some periods).
        y_median = float(d["y_median"]) if "y_median" in d.files else 0.0

        # V5 may store mu, log_sigma. Fallback to predictions[:, 1] = q50 for non-NLL.
        if "mu" in d.files:
            mu = d["mu"].astype(np.float64).ravel()
        else:
            mu = d["predictions"][:, 1].astype(np.float64)
        if "log_sigma" in d.files:
            sigma = np.exp(d["log_sigma"].astype(np.float64).ravel())
        else:
            sigma = np.zeros_like(mu)

        for i in range(len(ts)):
            dt_utc = datetime.fromtimestamp(int(ts[i]) / 1e6, tz=timezone.utc)
            # De-normalize: z * sigma + median (CODEX FIX)
            y_lr = (float(y_true_z[i]) * sigma_train + y_median) if y_true_z is not None else float("nan")
            mu_lr = float(mu[i]) * sigma_train + y_median
            # σ is a scale (uncertainty), no median offset needed
            sig_lr = float(sigma[i]) * sigma_train
            rows.append({
                "timestamp_us": int(ts[i]),
                "datetime_utc": dt_utc.strftime("%Y-%m-%d %H:%M:%S.%f"),
                "fold": fold,
                "mask": bool(mask[i]),
                "y_true_logret": y_lr,
                "y_true_bps": y_lr * 1e4,
                "y_pred_mu_bps": mu_lr * 1e4,
                "y_pred_sigma_bps": sig_lr * 1e4,
                "y_sigma_train_bps": sigma_train * 1e4,
                "y_median_train_bps": y_median * 1e4,  # for audit/debug
            })
    df = pd.DataFrame(rows)
    Path(args.out).parent.mkdir(exist_ok=True, parents=True)
    df.to_csv(args.out, index=False, float_format="%.8g")
    print(f"Wrote {args.out} ({len(df):,} rows, {df['mask'].sum():,} valid)")


if __name__ == "__main__":
    main()
PYEOF
```

- [ ] **Step 2: Run export**

```
python scripts/export_v5_csv.py \
    --exp-dir experiments/v5_final \
    --n-folds 3 \
    --out exports/y600_v5_production.csv
```

- [ ] **Step 3: Write colleague README**

```bash
cat > exports/README_y600_v5.md << 'DOCEOF'
# y_600 V5 Production CSV

## File: y600_v5_production.csv

### Columns

- `timestamp_us`: epoch microseconds (UTC)
- `datetime_utc`: human-readable
- `fold`: walk-forward fold index (0 = earliest test period)
- `mask`: True = use this row, False = exclude
- `y_true_logret`: realized log-return at horizon 600s (true outcome)
- `y_true_bps`: same in bps (= log-return × 1e4)
- `y_pred_mu_bps`: V5 primary signal (μ from heteroscedastic head, or q50 fallback)
- `y_pred_sigma_bps`: per-sample uncertainty (σ from NLL head; 0 if non-NLL loss used)
- `y_sigma_train_bps`: training-period y σ for context
- `y_median_train_bps`: training-period y median (used in de-normalization; for audit)

### Recommended use

**Position size = K · y_pred_mu_bps** (β-calibrated; mu directly represents PnL units)

**Confidence gating**: skip trade if y_pred_mu_bps² / y_pred_sigma_bps² < threshold (information ratio)

**Threshold strategy**: trade only when |y_pred_mu_bps| > 1 bps (high-confidence subset)

### Validation summary

(filled in after Phase D evaluation)

| Metric | Value | V5 gate | Pass? |
|---|---|---|---|
| Pearson | ? | ≥ 0.045 | ? |
| Spearman | ? | (info) | ? |
| β | ? | ∈ [0.80, 1.20] | ? |
| σ_ŷ/σ_y | ? | ≥ 0.10 | ? |
| top decile E[y] | ? bps | ≥ +0.5 bps | ? |
| top decile t-stat | ? | ≥ +2.0 | ? |
| bin-Spearman | ? | ≥ 0.85 | ? |
| |mean(ŷ)| | ? bps | ≤ 0.10 bps | ? |

### Disclaimers

- This CSV is **walk-forward OOS predictions** (each fold's predictions come from a model trained only on data BEFORE that fold's test period — no test leakage).
- Training data ends ~2025-Q1; current date is 2026-Q2. **Predictions are historical OOS, not live.**
- For live deployment, retrain on full updated data through current date.
DOCEOF
```

- [ ] **Step 3: Commit**

```bash
git add scripts/export_v5_csv.py exports/y600_v5_production.csv exports/README_y600_v5.md
git commit -m "feat(v5): production CSV export + colleague README"
```

### Task D.3: Update CLAUDE.md with V5 final status

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update V5 section with final results**

In CLAUDE.md, find the V5 Iteration Plan section. Replace status block with final summary:

```markdown
## V5 Iteration (2026-05-XX completed)

**Status:** [PASS/FAIL based on D.1] — V5 [is/is NOT] new production candidate.

**Implementation:**
- Backbone: <B.1 winner>
- Loss: <B.2 winner>
- Data setup: <B.3 winner>
- Final config: `configs/v5/v5_final.json`
- Production CSV: `exports/y600_v5_production.csv`

**Final 3-fold pooled metrics (raw + dense):**
- P = ?, S = ?, β = ?, σ_ŷ/σ_y = ?
- bin-Sp = ?, top decile E[y] = ? bps with t = ?

**Comparison to V4 baseline_plus seed42_SWA:**
| Metric | V4 | V5 | Δ |
|---|---|---|---|
| P | 0.0457 | ? | ? |
| σ_ŷ/σ_y | 0.045 | ? | ? |
| β | 1.010 | ? | ? |
| top decile E[y] | +1.26 bps | ? bps | ? |
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(claude): V5 final status with 3-fold metrics"
```

---

## Implementation Notes

### Critical decisions encoded in this plan

1. **Audit-first** — Phase A.1/A.2 verifies the V4 last-timestep bug before designing fixes. Plan v1 assumed without verifying.

2. **Screen, don't lock** — Phase B.1/B.2/B.3 are data-driven. We don't pre-commit to NLL/Mamba/5-fold. Each axis screened independently with control config.

3. **Backbone audit before screen** — A.2 audits existing modules for bugs (shape, gradient, determinism, t=0 grad). Buggy backbones excluded from screen, saving GPU time.

4. **Skip 5-fold (justified)** — 5-fold = 1.67× cost for marginal information gain on 970-day dataset. 3-fold sufficient for regime variance estimation; better to spend on B.1/B.2.

5. **Skip GRU/iTransformer/multi_scale/pyramid** — already showed null on y_600 in earlier failed experiments. Document in design doc; reconsider only if Phase B.1 finds no working backbone.

6. **Single-train (D.1) is genuine candidate** — not a strawman. If P/σ_ŷ/β comparable to 3-fold, single-train wins on data utilization + ops simplicity.

7. **Huber loss IS in the screen** — addresses anti-pattern: "MSE-leaning Huber wasn't excluded." L1 in Phase B.2.

### Things you may need to adjust during execution

- **Backbone instantiation kwargs**: `mamba_kwargs`, `ema_pool_alpha`, etc. — depend on actual `__init__` signatures. Inspect each backbone file at A.2 step 1; adjust configs accordingly.
- **`encode()` refactor in V4 backbone (A.8)**: pure refactor, no behavior change. Verify with V4 forward smoke before V5Model uses it.
- **Dataset embargo plumbing (A.9)**: depends on existing `dataset.py` split logic. Find `train_end =` and apply embargo there.
- **Single-split CV mode (B.3)**: may need new code in dataset.py to handle non-walk-forward splits. Add `if cv.mode == 'single_split'` branch.
- **`run_pipeline_v3.py` model dispatch (A.11)**: respect existing V4 path; add V5 wrap.

### When in doubt, prefer

- TDD: smoke test before full integration. Backbone audit (A.2) is the canary for Phase B.
- Skip if no theoretical win expected. Less is more in low-SNR.
- Frequent commits: every task ends with a commit; don't batch.
- Skin in the game: Phase B costs ~$30 GPU; B.1/B.2 each are 4 runs of ~$3 each; if a config keeps failing, kill it early to save budget.
- Run pod tasks with `--skip-existing` so retries don't redo what's done.

### Out-of-scope (deferred to V5.5+ or another plan)

- Multi-asset (different problem, separate plan)
- Self-supervised pretraining (research scope, multi-month)
- Dataset refresh to 2026-current (depends on data availability)
- New architectures from scratch (V5-LH/multi_scale/pyramid all failed; new arch needs separate exploration)
- RL trading policy (different framing, separate plan)
