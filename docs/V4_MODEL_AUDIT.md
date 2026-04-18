# V4 Rigorous Audit — What's Actually Working, What Is Not, What To Fix

_Derivations + empirical role + implementation correctness for every active component in the V4 no_attention winning config. Plus design improvements for anything not rigorous._

---

## 1. Active forward path (V4 no_attention @ 700d, 60K params — the current best)

Shape trace with batch B=1024, input_len L=600, n_features F=64, n_levels=20, d_model=32, d_raw=16, d_prior=6:

```
x_feat  : (B, 600, 64)    x_raw : (B, 600, 20, 4)    regime_prior : (B, 6)
   │                         │                              │
   ▼                         ▼                              │
[1] RevIN normalize         [5] RawLOBEncoder               │
    x - μ_win / σ_win           reshape (B*L, 4, 20)        │
    (B, 600, 64)                Conv1d(4,16,k=1)            │
   │                            Conv1d(16,16,k=3)+GELU      │
   ▼                            Conv1d(16,32,k=3)+GELU      │
[2] (MaskNet skipped)           AttentionPool1D over levels │
   │                            Linear(32, 16)              │
   ▼                            reshape (B, 600, 16)        │
[3] GDCN in 64-dim              ─────────────┐              │
    (x0 * W(xl)) * σ(Wg(xl))                 │              │
    + xl, 1 gated-cross layer                │              │
    (B, 600, 64)                             │              │
   │                                         │              │
   ▼                                         │              │
[4] input_proj Linear(64, 32)                │              │
    (B, 600, 32) = h_craft                   │              │
   │                 ┌───────────────────────┘              │
   ▼                 ▼                                      │
[6] Fusion Linear(32+16, 32) → (B, 600, 32) = h              │
   │                                                        │
   ▼                                                        │
[7] TCN — 3 × CausalConv1dBlock(d=32, k=3, dil={1,2,4})     │
    LayerNorm → F.pad(left=2,4,8) → Conv → GELU → residual  │
    (B, 600, 32)                                            │
   │                                                        │
   ▼                                                        │
[8] Attention SKIPPED (use_attention=False)                 │
   │                                                        │
   ▼                                                        │
[9] h_pred = h[:, -1, :]  ← LAST TIMESTEP ONLY              │
    (B, 32)                                                 │
   │                     ┌──────────────────────────────────┘
   ▼                     ▼
[10] PPNetGate: h_pred * (σ(MLP(regime_prior)) × 2) ∈ [0, 2]
     (B, 32)
   │
   ▼
[11] MonotonicQuantileHead:
     base = MLP_base(h)                    → (B,)
     δ = softplus(MLP_delta(h)) ≥ 0.01     → (B, 2)
     q10 = base - δ_low    q50 = base    q90 = base + δ_high
     ensured q10 < q50 < q90 by construction
```

### 1.1 Parameter accounting (reported 60K, **22K is dead**)

| Component | Active | Params | Actually on hot path? |
|-----------|:------:|-------:|:---------------------:|
| RevIN (γ, β per-feature) | ✅ | 128 | yes |
| MaskNet | ❌ | 0 (not built) | skipped via flag |
| GDCN 1 layer @ 64-dim | ✅ | ~8,200 | yes |
| input_proj Linear(64, 32) | ✅ | 2,080 | yes |
| RawLOBEncoder (Conv + pool + proj) | ✅ | ~3,100 | yes |
| Fusion Linear(48, 32) | ✅ | 1,568 | yes |
| TCN (3 blocks) | ✅ | ~9,400 | yes |
| **PatchEmbedding (dead)** | ⚠️ | ~13,120 | **built but never called** |
| **CausalPatchAttention (dead)** | ⚠️ | ~9,000 | **built but never called** |
| PPNetGate MLP | ✅ | ~1,250 | yes |
| MonotonicQuantileHead × 1 | ✅ | ~2,200 | yes |
| **Total active** | | **~27,900** | |
| **Total dead (patch stack)** | | **~22,120** | Agent 1 finding B6 |
| Reported (n_horizons=1) | | 59,347 | |

**Finding A:** ~40% of reported parameters are DEAD in the winning config. They're constructed in `DualPathLOBModelV3.__init__` regardless of flag state (`dual_path_model_v3.py:290-300`), so they sit in AdamW's optimizer state and get momentum updates that go nowhere. Not a correctness bug — just waste of memory + optimizer noise. One-line fix: wrap the patch construction in `if use_attention:`.

---

## 2. What's actually working (ranked from 100d smoke ablations)

Each row is the Pearson delta when that module is turned OFF (so positive = module helps):

| Module | Pearson delta when removed | Interpretation |
|--------|:--------------------------:|----------------|
| **PPNet regime gate** | **−0.077** (F_noppnet: 0.029 → −0.048) | Single biggest contributor. Hour-of-day + vol + OBI-trend gating is real signal. |
| **Path B (raw LOB encoder)** | **−0.052** (C_noraw: 0.029 → −0.023) | 1×1 conv + spatial conv + level attention pool on the 20-level orderbook tensor encodes structure that handcrafted features miss. **This is specifically the DL-over-linear value add.** |
| **Level attention pool (in RawLOBEncoder)** | −0.044 (F_noLvlAttn: 0.076 → 0.032) | Learned per-level attention beats average pool over 20 levels. |
| **Utility rank loss** | −0.040 (H_norank: 0.029 → −0.011) | Pairwise rank regularization helps generalization. |
| **RevIN** | −0.019 (D_norevin: 0.029 → 0.010) | Per-window normalization handles non-stationarity. |
| **TCN (3 dilated convs)** | −0.008 (G_noconv smoke: 0.076 → 0.068, noisy at 100d) | Marginal at best. **See §3.3 below.** |
| **GDCN** | −0.015 (C_nogdcn: 0.076 → 0.061) | Helps some, but occupies 24% of param budget. Overkill per-dollar-param. |
| **Patch attention** (ADDED = hurts) | **+0.055** when removed | Biggest anti-contributor. Confirmed: removing it gave V4 its first win. |

---

## 3. Per-module rigor audit with derivations

### 3.1 RevIN (Reversible Instance Normalization)

**Formula:** at training time,
```
μ_t = mean_L(x_t)    σ_t = std_L(x_t) + ε      (per sample)
x_normed = γ ⊙ (x_t − μ_t) / σ_t + β
```
At test time the output is NOT denormalized back (we train on standardized targets separately).

**Correctness:** implementation matches paper (Kim et al. ICLR 2022).

**Causality subtlety:** `μ_t, σ_t` are computed over the FULL input window L=600. This means each timestep's normalized value depends on the whole window. When the model only reads `h[:, -1, :]` (as in no_attention), this is SAFE because the window is strictly past relative to the prediction target. **But it would leak if we ever tried to predict at non-terminal positions.** Document in docstring.

**Empirical role:** confirmed helping (+0.019). Likely compensates for cross-day feature drift.

### 3.2 GDCN (Gated Deep Cross Network) — **design deviation from spec**

**Formula:** per layer l
```
cross_l = x_0 ⊙ (W_l x_l + b_l)
gate_l = σ(W_g x_l + b_g)
x_{l+1} = cross_l ⊙ gate_l + x_l
```

**Correctness:** matches paper (CIKM 2023, arXiv 2311.04635) — gated cross with residual.

**Issue 1 (spec deviation):** spec says "GDCN in 32-dim space AFTER Linear(64→32) projection" for "preserves crossing information after compression". Code has GDCN BEFORE projection, in 64-dim space. Parameter count: 2 × 64 × 64 ≈ 8.2K vs 2 × 32 × 32 ≈ 2K → **4× more params than spec'd**, on 108K windows → stress on the overfitting budget.

**Issue 2:** with `n_cross_layers=1` (config default), only ONE gated cross layer. GDCN paper recommends 3-4 for real cross-learning. At 1 layer it's more like "input gating" than "cross network". Either increase to 3 (more params, more capacity) OR drop to 0 and replace with a simple gated Linear (far fewer params).

**Empirical role:** helps (+0.015) but not commensurate with param cost. In the 64-dim-vs-32-dim ablation (not run), likely we can get same lift with 1/4 params.

### 3.3 **TCN receptive field — biggest structural finding** ⚠️

**Formula:** 3 stacked `CausalConv1dBlock` with kernel=3, dilations {1, 2, 4}, stride=1.

Stacked receptive field with stride=1:
```
RF = 1 + Σ_i (k_i − 1) · dil_i = 1 + 2·(1+2+4) = 15 timesteps = 15 seconds
```

**⚠️ Finding:** in the no_attention config, `h_pred = h[:, -1, :]` — the last timestep of TCN output. Because the TCN's receptive field is only **15 seconds**, that last-timestep representation only sees the last 15 seconds of data. **The first 585 seconds of the 600-second input window are EFFECTIVELY DISCARDED.**

This explains *why* removing patch attention helped: patch attention over 120 tokens was aggregating the full 600s context (global), but was noisy/overfit. Now we're using only 15s of context (local), which is cleaner but **short-sighted for a 180s-horizon prediction**.

**Hypothesis:** the val_corr ceiling at 0.066 may be partly imposed by this short context. Longer-term patterns (e.g., trade-flow imbalance over 60-180s) can't be captured by a 15s RF.

**Proposed fix (Intervention A):** extend TCN dilations to {1, 2, 4, 8, 16, 32, 64} (7 blocks, kernel=3) → RF = 1 + 2·(1+2+4+8+16+32+64) = 255 seconds ≈ 4 min. Still causal, still no attention overhead. Adds ~22K params (7 × 3100) → model grows back to ~50K total, still small. Should dramatically widen the effective context.

**Alternative (Intervention B):** re-introduce patch attention but with **patch_size=30** (20 patches instead of 120) and **single head**. Fewer tokens means less overfitting opportunity; still global context.

### 3.4 RawLOBEncoder — param waste

**Structure:** `Conv1d(4→16, k=1) → Conv1d(16→16, k=3) → Conv1d(16→32, k=3) → AttnPool → Linear(32→16)`

**Finding:** the spatial stack grows to 32 channels, then the final `Linear(32, 16)` projects HALF AWAY. With d_raw=16 (config default), the 32-dim spatial representation is compressed 2:1 at the end. Why? No good reason — d_raw=32 would be cleaner and uses <1K more params.

**Proposed fix:** set `d_raw=32` in config; update `Fusion` to `Linear(32+32, 32)`. +~500 params for potentially cleaner fusion. Low-risk ablation.

### 3.5 PPNet gate — sound

**Formula:** `gate = 2 · σ(MLP(regime_prior))` ∈ [0, 2] per dimension. Applied element-wise to h_pred.

**Correctness:** matches PEPNet (KDD 2023, arXiv 2302.01115). Scale ∈ [0, 2] lets the gate both suppress (<1) and amplify (>1) dimensions based on regime.

**Empirical role:** BIGGEST positive contributor (+0.077). Very robust.

**Improvement (small):** the 6 regime_prior features include `hour_sin, hour_cos` (calendar), `vol_1h`, `spread_mean_1h`, `obi_trend_1h`, `price_return_6h`. Agent 2 noted that separate regime-conditional training is sometimes better than soft gating. Could A/B test "hard" regime routing (4 vol-regime experts) vs PPNet soft gate. Defer.

### 3.6 MonotonicQuantileHead — sound

**Formula:** `base = MLP_b(h); δ = softplus(MLP_d(h)).clamp(min=0.01)`. Then `q10 = base − δ_low, q50 = base, q90 = base + δ_high`.

**Correctness:** guaranteed monotone by construction. Clamp protects float32 tie-breaking.

**Issue:** the width of the prediction interval is `δ_low + δ_high`, independently of the input magnitude. At low-magnitude target samples, δ might overestimate uncertainty; at high-magnitude samples, δ might underestimate. Consider normalizing by `|base|` or using a learned multiplicative structure. But this is polish, not a bottleneck.

### 3.7 Patch attention — correctly causal, confirmed harmful (dead-code in winner)

**Finding:** causal mask via `triu(..., diagonal=1)` is correct. Pre-norm residual block is standard. But **empirically hurts** (we tested, removing it gave +0.055 Pearson). Keep disabled; clean up so it isn't constructed when `use_attention=False`.

---

## 4. Loss function rigor

### 4.1 Pinball loss (active, λ=1)

**Formula:**
```
err_q = y − q      
loss = max(τ·err, (τ−1)·err)
```
For τ ∈ {0.1, 0.5, 0.9}. Correct implementation. Mean over (B, n_τ).

**Gradient properties:** piecewise linear. Clean.

### 4.2 Utility rank loss (active, λ=0.3)

**Formula:** for α=1 (config):
```
s_i = q50_i − 1·(q50_i − q10_i) = q10_i       ← ranks by lower tail
for sampled pairs (i, j):
    desired = sign(y_i − y_j)
    pred_diff = s_i − s_j
    loss_ij = softplus(−desired · pred_diff + margin)
```

**Correctness:** softplus is numerically stable logistic-on-pairwise. Self-pair handling (`j = (j+1) % n` when collision) is correct.

**Issue:** **α=1 ranks by q10, not q50**. This means the ranking signal comes from a very risk-averse interpretation. Since SNR is < 1%, the q10 estimate is substantially noisier than q50. **Consider α=0** (rank by q50) — simpler signal, probably equally effective.

**Proposed experiment:** smoke with `utility_alpha=0` vs 1.0 vs 0.5. Cheap (one config flip).

### 4.3 Coverage calibration loss (not active, λ=0)

**Formula:**
```
c_τ = mean_i σ(k · (q_τ(i) − y_i))     (k=20, sigmoid-smoothed coverage)
loss = Σ_τ (c_τ − τ)²
```

**Correctness:** differentiable surrogate for coverage penalty. Not enabled (λ=0 in config). Not a current issue.

### 4.4 DUL weighted composition

```
L_total = 1.0 · L_pinball + 0.3 · L_rank + 0 · L_calib
```

**Issue:** the weight 0.3 was picked from spec, not tuned. Magnitudes are comparable (pinball ~0.55, softplus_mean ~0.5), so 0.3 effectively gives rank loss ~30% of total gradient. Reasonable but uncalibrated. Deferred tuning.

---

## 5. Feature construction — causality verified, quality unverified

**Base features** (58): from `src/features/microstructure.py` — spread_bps, OBI at levels 1/5/10, trade flow 1s, realized vol 10s/30s/60s/300s, book pressure imbalance, etc. All computed with `.rolling(window=W, min_periods=W)` or `.shift()` — strictly causal. Verified in `tests/test_features.py`.

**Ridge-informed features** (6): interactions like `net_trade_flow · spread_bps`, rolling rank of OBI over 1h. Strictly causal (tests `test_ridge_informed_features.py` confirm).

**Regime prior features** (6): `vol_1h`, `spread_mean_1h`, `obi_trend_1h` slope, `price_return_6h`, `hour_sin`, `hour_cos`. Causal (tests `test_regime_prior_features.py`).

**No issues found** in feature causality. Quality (how much signal each carries) is not audited here — would require Ridge feature importance on the V4 feature set.

**Label**: `y_H = log(mid[pred_idx + H] / mid[pred_idx])` in `src/features/pipeline.py:326-344`. Strictly forward-looking. Correct.

---

## 6. Design improvements (ranked by rigor + impact)

### Immediate (cheap, rigorous)

1. **Clean up dead patch-attention params** (§1.1): 1-line fix → saves 22K optimizer state + faster AdamW step.
2. **`utility_alpha` sweep** (§4.2): run 3 smoke variants with α ∈ {0.0, 0.5, 1.0}. Picks the most aligned rank signal.
3. **`d_raw` = 32** (§3.4): no projection loss in raw path.

### Core (higher risk, higher potential)

4. **Wider TCN receptive field** (§3.3, biggest structural finding): dilations {1,2,4,8,16,32,64}, 7 blocks. Extends temporal context from 15s to 255s. **Most likely to break the 0.066 val_corr ceiling**.
5. **GDCN in 32-dim space after projection** (§3.2): reduces GDCN params 4×, frees budget for wider TCN. Test at the same time as #4.
6. **y_60 as auxiliary loss** (see separate T4 code commit): leverages the fact that y_60 target has 2× more signal than y_180; shared backbone gets richer training.

### Hardening (not a lift, but correctness)

7. **RevIN docstring** (§3.1): annotate that it's window-aware, unsafe for non-terminal readouts.
8. **Label alignment unit test** (§5): add explicit perturbation test — perturb mid[pred_idx+H-1], assert y[k] changes (shouldn't); perturb mid[pred_idx+H], assert y[k] changes (should). Currently implicit.

### Already-run-don't-repeat

- Removing patch attention ✅ (did: +0.055)
- Removing any single "helper" module (each hurt, confirmed signal)
- Multi-horizon parallel heads ❌ (hurt convergence)
- Mixup / smaller model / higher dropout ❌ (all worse at 700d)

---

## 7. What to stop doing

- **Stop adding parallel heads with equal weight** — already proved it dilutes gradient.
- **Stop ranking by q10 without α ablation** — we set α=1 on first design, never tested.
- **Stop trusting 100d val_corr rankings** — val set only 10 days; variance is high, small effects drown in noise. Use 700d for any final ranking.
- **Stop optimizing architecture without data-engineering parallel track** — literature says labels/inputs matter more than architecture at this SNR.
