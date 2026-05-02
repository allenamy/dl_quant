> **创建:** 2026-05-02 14:30 UTC+8 | **Session:** v5-plan-v2-task-A.2
> **关键事件:** Audit `ema_pool` / `gru` / `mamba_v2` backbones for V5 Phase B.1 screen; ran 4×3 pytest matrix on local PyTorch 1.4 CPU.
> **上一版本:** docs/superpowers/plans/2026-05-02-v5-iteration-v2.md (plan v2 spec)
> **状态:** in-progress | **作废条件:** Phase B.1 完成,有真实 fold-0 数据替代此 audit 推断

# V5 Backbone Audit (Task A.2)

## TL;DR

| Backbone | Verdict | One-line reason |
|---|---|---|
| `ema_pool` | **PASS — include in Phase B.1** | All 4 audit checks pass; recency-weighted with full-window connectivity. |
| `gru` | **CONCERN — keep, but flag as risk** | Architecturally connects t=0 → output, but *at random init* the gradient and the forward signal underflow to ~0 for L≥50. Trainability beyond the conv RF (~15s) at L=600 is not guaranteed. |
| `mamba_v2` | **DEFERRED — re-audit on pod** | `mamba-ssm` requires CUDA; cannot validate locally. 4 dynamic tests XFAIL'd with explicit reason. |

`gru` is **not excluded** from B.1 — exponential vanishing-gradient at random init is a known RNN property and may be partially mitigated by training. But this audit predicts that GRU on y_1800 at L=600 will likely be unable to use t < L−15 evidence in practice, so its expected uplift over V4 baseline is small. Phase B.1 should keep it as a control to confirm/refute the prediction; if GRU underperforms `ema_pool` by ≥0.005 P, that is consistent with this audit and not surprising.

## Method

For each backbone candidate (`ema_pool`, `gru`, `mamba`) we check four properties via `tests/test_v5_backbones.py`. The CRITICAL one is #4 — if a backbone's gradient at t=0 is numerically zero, the backbone is degenerate to a last-timestep slice in disguise (i.e., the V4 baseline bug Phase B.1 is meant to fix).

1. **Shape contract**: input `(B=4, L=600, d_model=32)` produces output `(B, d_model)` = `(4, 32)` and is finite.
2. **Backward**: input gradient is finite + non-zero in train mode.
3. **Determinism**: in `eval()` mode, two forward passes on the same input produce bit-identical outputs (no leaky stochasticity).
4. **t=0 grad > 0**: at random init, in eval mode (no dropout), `|x.grad[0,0,:]|.sum() > 1e-9` for L=100. Threshold 1e-9 is well below any reasonable signal but above float32 noise.

Test file: `tests/test_v5_backbones.py`. Run:
```bash
python -m pytest tests/test_v5_backbones.py -v -s
```

## Results (12 pytest cases on local CPU PyTorch 1.4)

| Backbone | Shape | Backward | Determinism | t=0 grad > 0 | Verdict |
|---|---|---|---|---|---|
| `ema_pool` | PASS | PASS | PASS | **PASS** (g0=1.02e-2, g_last=1.61e+0, ratio=159) | INCLUDE |
| `gru` | PASS | PASS | PASS | **FAIL** (g0=4.92e-18, g_last=5.49e+0) | INCLUDE WITH CAVEAT |
| `mamba_v2` | XFAIL | XFAIL | XFAIL | XFAIL | DEFER TO POD |

Summary line from the run: `1 failed, 7 passed, 4 xfailed in 0.75s`.

XFAIL reason (mamba): `mamba-ssm CUDA kernels unavailable in this environment (local CPU PyTorch 1.4). Re-run on pod to validate.` Static-source inspection of `mamba_backbone_v2.py` confirms shape contract `(B,L,d_model) → (B,d_model)` (line 59 returns `out[:, -1, :]`) and lazy-import guard. Dynamic verification deferred to pod.

### Detailed gradient measurement (t=0 grad test, eval mode, L=100, d_model=32)

```
ema_pool : |grad@t=0| = 1.0155e-02 , |grad@t=-1| = 1.6095e+00 , ratio  = 158.5
gru      : |grad@t=0| = 4.9194e-18 , |grad@t=-1| = 5.4866e+00 , ratio  = ~1e+18
mamba_v2 : XFAIL (no CUDA locally)
```

`ema_pool`'s ratio of 158 is mathematically consistent with `decay=0.95, L=100`: `weight(t=0) / weight(t=-1) = 0.95^99 ≈ 0.0059 ≈ 1/170`. The recency-weighted EMA puts ~0.6% of total weight on t=0, but that is non-zero and the gradient flows through.

`gru`'s ratio of ~10^18 is the well-known RNN vanishing-gradient pathology at random init. A scan over sequence length confirms exponential decay:

```
GRU random-init |grad@t=0| vs L:
  L=20  : 8.75e-3   (healthy, ratio ~590)
  L=30  : 3.67e-5
  L=50  : 4.39e-9
  L=100 : 7.13e-19  (numerically zero)
  L=600 : 0.00e+0   (literal zero)
```

Forward-pass connectivity is also impaired: a perturbation `x[0,0,:] += 1.0` produces `|Δoutput|_max = 5.96e-8` at L=100 (= float32 epsilon ≈ 1.2e-7), meaning the forward pass cannot distinguish x[0,0,:] from any other value at production sequence length. This is **consistent** with the gradient finding — both forward and backward signals at t=0 are below float32 representable magnitude.

**Important caveat**: this is the **random-init** state. Training can re-shape GRU weights to extend effective lookback (e.g. via gate biases that promote retention), but the audit data above sets the prior: GRU at L=600 *starts* effectively last-timestep + conv RF (~15s) and would have to *learn* to use earlier context. That is a real cost in training compute on a low-SNR task.

## Integration audit: how a backbone connects to V4

`src/model/dual_path_model_v3.py:606-628` is the temporal-backbone branch of the V4/V5 forward pass. The relevant excerpt:

```python
# 3. Temporal backbone.
# Default conv_lasts: inline temporal_conv (RF=15s) + last-timestep
# slice (V4 behaviour, bit-identical when backbone_kind="conv_lasts").
# Other backbones (ema_pool/gru/mamba) bypass the inline conv path.
if self.backbone is not None:
    # Pluggable backbone consumes (B, L, d_model) → (B, d_model).
    h_pred = self.backbone(h)
elif self.use_attention:
    ...
else:
    # Legacy V4 default: dilated causal conv + last-timestep slice.
    if self.use_conv:
        h = self.temporal_conv(h)
    h_pred = h[:, -1, :]
```

Wiring (`__init__` lines 373–400):

- `backbone_kind="conv_lasts"` → `self.backbone = None`, V4 baseline path (default).
- `backbone_kind="ema_pool"` → `EMAPoolBackbone(d_model, dropout, decay)` instantiated.
- `backbone_kind="gru"` → `GRUBackbone(d_model, hidden, n_layers, dropout)` instantiated.
- `backbone_kind="mamba"` → `MambaBackboneV2(d_model, d_state, expand, dropout)` (raises `ImportError` on CPU).

**Important properties of the integration:**

1. The backbone receives `h` *after* MaskNet+GDCN (Path A), RawLOBEncoder fusion (Path B), and optional multi-scale residual injection. It does **not** receive the raw LOB tensor. Each backbone replaces both the dilated conv stack *and* the last-timestep slice.
2. Each backbone outputs `(B, d_model)`, which then flows into optional regime FiLM, PPNet gate, and the quantile head. So the audit's Property 1 (shape contract) is load-bearing — a backbone that returned `(B, L, d_model)` would silently cause a downstream shape error in `regime_film` / `ppnet_gate` / quantile head.
3. The conv stack inside `ema_pool_backbone.py` and `gru_backbone.py` is a **separate** dilated conv (kernel=3, dilation 1/2/4, RF=15) — not the V4 `self.temporal_conv`. So in the `ema_pool`/`gru` paths, the V4 inline `temporal_conv` is bypassed and replaced by the backbone's internal conv. The dilated conv RF (~15 timesteps) is identical in both cases.

## Critical observations / surprises

1. **Mamba_v2 takes `out[:, -1, :]` after the SSM** (line 59). On the surface this looks like the same V4 last-timestep bug, but Mamba's state-space dynamics mix earlier timesteps into the final hidden state — architecturally `out[t=-1]` depends on every input from t=0 to t=L-1. The audit cannot dynamically verify this on local CPU; pod re-run is mandatory.

2. **`gru` is determinism-PASS in eval but numerically degenerate at random init for L≥50.** The classical "GRU is more stable than RNN" claim is about training dynamics, not random-init forward magnitudes. With `n_layers=1, hidden=32, d_model=32, dropout=0.0` (the GRUBackbone defaults), the recurrence's contractive properties at random init drive gradient (and forward) signal at distant timesteps below float32 resolution. The conv stack in front of GRU has RF=15, so the GRU sees an already-receptive-conditioned input — but its own contribution beyond ~15-30 effective timesteps is bounded by the recurrent dynamics.

3. **No backbone has a determinism leak** in eval mode. ema_pool's normalised EMA is deterministic by construction; GRU is deterministic on CPU once dropout is off; Mamba's eval determinism cannot be locally verified but the source has no obvious stochastic ops.

4. The plan v2 expectation that `gru` would PASS all four checks is **not borne out** by this audit. This is a real finding worth recording — it does NOT mean GRU is unusable, but it tightens the prior on GRU's expected uplift on y_1800.

## Alternative fusion strategies (deferred for V5.5+)

Currently each backbone replaces the conv+last-ts pair entirely. Three alternatives have been considered but are out of scope for V5 Phase B.1:

1. **Conv → backbone serial fusion**: keep V4's `temporal_conv` (RF=15) before the backbone, so the backbone operates on conv features rather than raw `h`. Already implicit in `ema_pool` and `gru` (they have their own conv stack), but not in `mamba_v2`.
2. **Backbone + last-ts dual head**: aggregate `[backbone(h); h[:, -1, :]]` so V4 short-range capacity is preserved. Would help if the backbone underperforms on short-horizon residuals.
3. **Multi-scale parallel encoders**: see `multi_scale_backbone.py` and `hierarchical_pyramid.py` (already audit-deferred per task scope; reported FAILED on y_600 — see anti-pattern #18).

These are V5.5 candidates; do not introduce in B.1.

## Recommendations for Phase B.1

Based on audit results:

- **Include**: `V4 baseline` (`conv_lasts`, control), `use_attention=True` (V4 ablation, no backbone), `ema_pool` (full-pass).
- **Include with caveat**: `gru`. Document expected risk (random-init vanishing) in the Phase B.1 report. If GRU underperforms `ema_pool` by ≥0.005 P, attribute partly to this prior.
- **Defer**: `mamba_v2` to pod (re-run `tests/test_v5_backbones.py` there to flip XFAIL→XPASS and confirm Property 4 dynamically before the pod screen).
- **Hard prerequisite for any pod screen**: re-run the audit on pod with the same test file. If `mamba_v2` fails t=0 grad > 0 on pod (which would mean `out[:, -1, :]` after Mamba2 is *architecturally* a last-ts slice — unlikely but possible if Mamba2's CUDA kernel does not propagate state correctly at the boundary), exclude it.

## Test inventory

```
tests/test_v5_backbones.py
  - test_backbone_io_shape          (parametrized over [ema_pool, gru, mamba])
  - test_backbone_backward          (parametrized; train mode)
  - test_backbone_determinism       (parametrized; eval mode)
  - test_backbone_uses_more_than_last_timestep (parametrized; CRITICAL)
```

`mamba` cases use `pytest.xfail(strict=False)` with an explicit reason string, not silent skip — re-run on pod will turn XFAIL into XPASS or surface a real failure.
