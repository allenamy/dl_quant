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
