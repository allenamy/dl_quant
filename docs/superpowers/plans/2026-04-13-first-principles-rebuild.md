# BTCUSDT Mid-Frequency Prediction: First-Principles Rebuild

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** From first principles, rebuild the BTCUSDT 3-min return prediction system with complexity-justified architecture, proper data scale, and honest baselines — targeting stable out-of-sample correlation > 0.05 for a solo/small team.

**Architecture:** Progressive complexity ladder: Ridge → MLP → single-head lightweight Transformer. Dual-path input (hand-crafted features + low-dim LOB tensor). Single quantile loss. 30-90 day multi-day temporal CV.

**Tech Stack:** Python 3.9+, PyTorch 2.0+, scikit-learn, LightGBM, pandas, numpy, scipy

---

## Part I: Deep Analysis of 8 Critical Questions

### 1. 39 Hand-Crafted Features: Too Coarse? Raw LOB Structure Lost?

**Verdict: Features are decent for 3-min horizon, but have two fixable gaps.**

#### What the 39 features preserve well
- Aggregate supply/demand balance (OBI at 4 depth tiers)
- Price momentum (3 return lookbacks: 1s, 5s, 30s)
- Volatility regime (3 rolling windows: 30s, 60s, 300s)
- Market quality (spread, Kyle's lambda, Amihud)
- Near-book granularity (levels 0-4 individual amount ratios)
- Time-of-day cyclical encoding

#### What is lost

| Lost Information | Severity at 3-min | Details |
|---|---|---|
| Levels 5-24 individual amounts (40 values) | **Low** | Only sums survive via `depth_L25`. Cannot distinguish 10 BTC spread across levels 5-24 from 10 BTC concentrated at level 12. But deep levels replenish multiple times in 3 min. |
| Depth profile shape/curvature | **Low-Medium** | Is liquidity linearly increasing or bulging? Gaps in the book? Lost in aggregation. Matters for sub-minute prediction, less for 3-min. |
| Level 5-9 individual prices | **Low** | Only via `weighted_price_L10` average. Whether levels 5-9 are tight (dense book) or wide (thin book) is invisible. |
| Inter-level correlations | **Minimal** | Spoofing patterns, adjacent-level clustering — washed out at 3-min horizon. |
| **Order flow / temporal deltas** | **HIGH** | **Only `obi_L1_delta` and `spread_change` capture book dynamics.** No `delta_depth`, `delta_pressure`, `net_order_flow`. This is the biggest gap. |

#### Critical finding: SpatialLOBEncoder grouping is semantically broken

`set_feature_groups()` is **never called** in training. The "bid/ask/global" split is just first-third / middle-third / last-third of the 39 features by index position:
- "Bid group" (indices 0-12): log returns, spread, OBI, bid_depth_L5, **ask_depth_L5**...
- "Ask group" (indices 13-25): **bid_slope**, **bid_concentration**, realized_vols...
- "Global group" (indices 26-38): amount ratios, temporal features

**Bid features are scattered across all three groups.** The cross-attention is attending over three arbitrary feature bags, not structured bid/ask sides. It has zero structural advantage over a simple MLP.

#### Recommendation (Priority order)

1. **Fix SpatialLOBEncoder grouping** — call `set_feature_groups()` with semantically correct indices. Zero cost, potentially significant.
2. **Add 5-8 order flow features** — `delta_bid_depth_L5(1s)`, `delta_ask_depth_L5(1s)`, `net_order_flow`, `delta_obi_L5(5s)`, `delta_spread(5s)`. These are the strongest predictors at 3-min horizons per Kolm et al. (2023).
3. **Optional: parallel raw path** — (B, L, 10, 4) tensor for top 10 levels with Conv2d spatial encoder. Low priority — incremental gain at 3-min is small compared to items 1-2.

---

### 2. Single-Day Data: The Fatal Flaw

**Verdict: This is the #1 blocker. Everything else is secondary.**

Current situation: 1 day (2024-10-10), 8,611 windows, train=6,027.
- Train covers 00:00-16:48 (Asia + Europe)
- Val covers 16:48-20:24 (Europe-US crossover)
- Test covers 20:24-24:00 (US session)
- These are fundamentally different market regimes → val corr +0.088, test corr -0.102

#### Data source: tardis.dev (the only viable option)

| Source | L2 Orderbook? | Format Match? | Cost (30d) | Cost (90d) |
|---|---|---|---|---|
| **tardis.dev** | Yes, exact | **Perfect** (zero transform) | ~$5-15 | ~$15-40 |
| Binance official | **No** | N/A | Free but useless | N/A |
| Kaiko | Yes | Needs adapter | $2,000+/mo | $2,000+/mo |
| CoinAPI | Yes, limited | Needs adapter | $79+/mo | $79+/mo |
| DIY collection | Future only | You define it | Free + wait | Free + 90d wait |

The existing `BTCUSDT.csv.gz` uses tardis.dev's exact column convention (`asks[i].price`, `bids[i].amount`, microsecond timestamps). Zero code changes needed.

#### Size estimates

| Metric | 30 days | 90 days |
|---|---|---|
| Download (gzipped) | ~5 GB | ~15 GB |
| NPZ (stride=60) | ~1 GB, ~43K windows | ~3 GB, ~129K windows |
| CV folds (14/5/5) | 1 fold | 3 rolling folds |
| Processing time | ~2-3 hours | ~6-9 hours |

#### Download procedure

```python
from tardis_dev import datasets

datasets.download(
    exchange="binance-futures",
    data_types=["book_snapshot_25"],
    from_date="2026-01-01",
    to_date="2026-01-30",
    symbols=["BTCUSDT"],
    api_key="YOUR_API_KEY",
    download_dir="./data/raw",
)
```

**Recommendation: Start with 30 days. It gives 43K windows (vs current 6K), covers all time-of-day patterns, all day-of-week patterns, and enables proper temporal CV. Expand to 90 days after validating the pipeline.**

---

### 3. RegimeAwareFeatureGate: Conceptually Unjustified

**Verdict: Remove it. The idea is sound but the implementation timescale is wrong.**

#### Parameter count: 1,484 params (0.7% of 219K) — not a param budget issue

#### The real problem: timescale mismatch

The gate operates on `x_mean = cumsum / counts` — a causal running mean over a 5-minute window. But market regimes (trending/mean-reverting, high/low volatility) are identifiable on timescales of **30 minutes to hours**:
- Volatility regimes persist for 2-8 hours (e.g., Asian low-vol → European high-vol)
- Trending vs. mean-reverting regimes last 30 min to several hours
- Macro regime shifts (risk-on/off) last days to weeks

A 5-minute window is far too short to reliably detect any of these. The gate is more likely learning a feature-scaling heuristic than actual regime detection.

#### The 50/50 mix is arbitrary

`combined_gate = 0.5 * regime_gate + 0.5 * d_gate` — hardcoded. If regime detection is noise (likely), half the gating signal is garbage. At minimum the mixing ratio should be learnable, but better to remove entirely.

#### What would actually work for regime detection

If regime-awareness is desired later:
- Use a **separate slow model** (e.g., HMM or rolling vol/corr classifier on hourly data) to label regimes
- Pass the regime label as an **input feature**, not a learned gate
- Or: condition on explicit regime features (rolling 1h vol, funding rate, open interest) rather than trying to learn regime detection from a 5-min window

**Recommendation: Replace with simple `nn.LayerNorm(n_features)`. Revisit regime detection only after establishing a working baseline with multi-day data.**

---

### 4. SpatialLOBEncoder: Good Idea, Broken Execution

**Verdict: The structural concept (bid vs ask vs global attention) is valuable. The implementation needs two fixes.**

#### Problem 1: Semantic grouping is wrong (see Point 1)
The default splits by index position, not by LOB semantics. Fix by calling `set_feature_groups()`.

#### Problem 2: MHA over 3 tokens is overkill

Cross-attention over 3 group tokens (bid, ask, global) is architecturally heavy for what it does. With only 3 tokens, the attention weights are a 3×3 matrix — there are only 9 possible attention patterns. A simpler architecture achieves the same:

```python
# Current: 3 projections + MHA + FFN + merge ≈ 70K params
# Alternative: 3 projections + concatenate + MLP ≈ 15K params
h_bid = proj_bid(x_bid)      # (B*L, d_model)
h_ask = proj_ask(x_ask)      # (B*L, d_model)
h_global = proj_global(x_global)  # (B*L, d_model)
h = Linear(cat([h_bid, h_ask, h_global]), d_model)  # much simpler
```

The cross-attention adds value when there are many tokens (e.g., 25 levels), but with only 3 groups the quadratic attention mechanism is solving a trivially small problem.

**Recommendation:**
1. Fix feature grouping immediately (call `set_feature_groups()` with correct indices)
2. Consider simplifying to concat + Linear for the spatial merge
3. If adding a raw LOB path later, the cross-attention architecture becomes more justified (25 level-tokens instead of 3)

---

### 5. CausalTemporalEncoder: Reasonable but Heavy

**Verdict: Conv frontend is well-motivated. Depth=2 Transformer with RoPE is over-engineered for the current data scale.**

#### Conv frontend: justified
- Causal depthwise-separable convolutions with exponential dilation (1, 2) capture local temporal patterns efficiently
- Kernel=9 at dilation=2 gives a receptive field of 17 timesteps (~17 seconds) — reasonable for capturing short-term dynamics
- Only ~3K params — cheap and effective

#### RoPE: unnecessary for fixed L=300
- RoPE's primary benefit is length extrapolation — but your sequences are always exactly L=300
- For fixed-length inputs, learned positional embeddings (300 × head_dim = 4,800 params) or no positional encoding (rely on conv frontend) would be simpler
- No evidence RoPE helps for financial time series at fixed lengths

#### Depth=2: likely overkill
- Each Transformer block is ~50K params (QKV projection + FFN)
- With 6K training samples, even depth=1 may be too much
- The conv frontend already provides temporal modeling; the Transformer adds long-range attention

**Recommendation: Start with depth=1 (or conv-only, no Transformer). Switch to learned embeddings or rely on conv for position encoding. Add depth only if ablation on 30-day data shows improvement.**

---

### 6. Training Pipeline Issues

**Verdict: Multiple interacting problems create a vicious cycle.**

#### Stride=10 causes 97% window overlap → inflated sample count
- 290/300 bars shared between adjacent windows
- Nominal 8,611 samples but effective unique samples ≈ 290 (86,400s / 300s)
- Model learns "continue the previous prediction" → residual autocorr 0.94
- **Fix: stride ≥ 60 (1 minute), preferably 180 (matching horizon)**

#### Val loss vs val correlation for checkpointing
- The V2 model correctly uses val_correlation (the baseline uses val_loss)
- But with overlapping samples and single-day data, val_correlation is unreliable
- Need multi-day data with proper temporal splits to get meaningful correlation estimates

#### Target normalization
- MAD-sigma normalization is reasonable but single-day median/MAD may not generalize
- Need to compute normalization stats from training set only (the pipeline already does this)

#### LR schedule
- Warmup + cosine decay is reasonable
- But ReduceLROnPlateau (baseline) may be more robust for noisy settings where cosine schedule can overshoot

**Recommendation: Increase stride to 60-180. Use multi-day temporal CV. Consider ReduceLROnPlateau as an alternative to cosine decay.**

---

### 7. Multi-Task Loss Interference

**Verdict: Yes, the seesaw effect is almost certainly happening. Simplify to single loss.**

#### Current loss: `quantile(1.0) + asymmetric_huber(1.0) + direction_CE(0.3) + uncertainty_NLL(0.05)`

| Component | Gradient Direction | Conflict Risk |
|---|---|---|
| Quantile (q10/q50/q90) | Push q50 toward conditional median | Low conflict |
| Asymmetric Huber | Extra penalty on overestimating negatives | Mild conflict with quantile's symmetric q50 |
| Direction CE | Discretize to {down, flat, up} at 2 bps | **HIGH conflict** — 40% of samples are "flat" (noise), direction gradients push shared backbone toward classification features |
| Uncertainty NLL | Minimize `log(var) + (y-ŷ)²/var` | **Degenerate** — easiest to minimize by predicting large variance everywhere. Weight 0.05 means it barely trains. |

#### Evidence of interference from current results
- Residual autocorrelation 0.94 = model outputs near-constant values → classic "safe compromise" when conflicting losses prevent learning any single task well
- Direction accuracy 40.7% → worse than always predicting "flat" (~50% for the dominant class)
- Uncertainty-error correlation -0.03 → uncertainty head learned nothing
- Val/test correlation flip (+0.088 → -0.102) → model overfit to noise, possibly because multi-task gradients amplified spurious correlations

#### Academic perspective
GradNorm (Chen et al., 2018) showed that naively weighted multi-task losses lead to seesaw effects where one task dominates and others degrade. With a weak signal (corr ~0.05), the model has barely enough capacity to learn one task. Asking it to learn four simultaneously with conflicting gradients is counterproductive.

**Recommendation: Start with quantile loss only (q10/q50/q90). The median q50 serves as the point prediction. Remove direction and uncertainty heads entirely. Add asymmetric Huber only after the quantile baseline is established, and only if left-tail bias persists.**

---

### 8. Model Complexity vs. Financial Noise: The Core Question

**Verdict: The current model is fundamentally over-engineered for the statistical reality of this problem.**

#### The signal-to-noise arithmetic

- BTCUSDT 3-min return std: ~10.5 bps
- Achievable correlation (reference): ~0.05
- Signal explains: 0.05² = **0.25% of variance**
- Remaining 99.75% is noise

#### Params-per-sample ratio

| Scenario | Params | Unique Samples | Ratio | Verdict |
|---|---|---|---|---|
| Current (1 day, stride=10) | 219K | ~290 effective | **755:1** | Catastrophic |
| Current (1 day, stride=60) | 219K | ~1,435 | 153:1 | Still catastrophic |
| 30 days, stride=60 | 219K | ~43K | 5:1 | Still too high |
| 30 days, stride=60 | 5K | ~43K | 0.12:1 | Reasonable |
| 90 days, stride=60 | 219K | ~129K | 1.7:1 | Marginal |
| 90 days, stride=60 | 5K | ~129K | 0.04:1 | Good |

For financial signals at 0.25% R², you need **at least 100 unique samples per effective parameter**, ideally 1000+. This means:
- With 43K samples (30 days) → target ≤ 430 effective params (ridge/linear territory)
- With 129K samples (90 days) → target ≤ 1,290 effective params (shallow MLP territory)
- Regularization (dropout, weight decay, early stopping) can stretch this by ~5-10x, but 219K is still 1-2 orders of magnitude too large

#### Why complex models fail in finance (specifically)

1. **Microstructure noise is extreme.** At 3-min horizons, most price variation is noise from order flow randomness, not from predictable information. A complex model has enough capacity to memorize noise patterns.

2. **Regime constantly shifts.** A pattern that works in Asian hours breaks in US hours. A model trained on trending days fails on mean-reverting days. Complex models learn regime-specific patterns that don't generalize.

3. **Label leakage is subtle.** Overlapping windows (stride=10), temporal features from the same day, normalization stats from the full dataset — all create subtle forms of information leakage that complex models exploit.

4. **Feedback loops.** If enough traders use similar signals, the signal disappears or inverts. Simple, widely-known features (OBI, spread, vol) have already been partially traded away. Complex models may find "signals" that are actually just noise patterns.

5. **Non-stationarity.** The distribution of features and the feature-return relationship change over time. A 219K-param model can learn the precise distribution of the training period, which is exactly wrong for future data.

#### The uncomfortable truth

In quantitative finance, **the hard part is not model architecture — it is finding signal**. If a linear model can't find the signal, a Transformer won't either (it will just overfit more confidently). The correct development order is:

1. Find features with genuine predictive power (using simple models)
2. Verify the signal is stable across time periods
3. Add model complexity only to capture specific nonlinearities that simple models miss
4. Every increment of complexity must show statistically significant OOS improvement

---

## Part II: Synthesized Strategy for Solo/Small Team

### What we're NOT doing (and why)

| Approach | Why Not |
|---|---|
| Extreme HFT (sub-second) | Requires co-location, FPGA, massive infra investment |
| 219K-param multi-task Transformer | Over-engineered for signal strength, overfits at current data scale |
| Regime detection from 5-min windows | Timescale mismatch — regimes shift over hours, not minutes |
| Uncertainty estimation | No evidence the current data/model can learn it meaningfully |
| Direction classification | Weak signal, creates gradient conflict with regression |

### What we ARE doing

**Core principle: Earn every unit of complexity with out-of-sample evidence.**

```
Phase 0: Data                    → 30 days from tardis.dev
Phase 1: Linear baselines        → Ridge regression, feature importance
Phase 2: Feature improvement      → Fix grouping, add order flow features
Phase 3: Shallow neural net       → MLP → Conv → minimal attention
Phase 4: Calibration & deployment → Quantile outputs, proper backtesting
```

### Target metrics

| Metric | Target | Current |
|---|---|---|
| OOS Correlation | > 0.05 (stable across folds) | -0.102 (single day, meaningless) |
| Residual Autocorr (lag-1) | < 0.3 | 0.94 |
| Left Tail Bias | < |0.5| | +1.32 |
| Sharpe (annualized) | > 1.0 after costs | No trades |
| Model params | < 10K | 219K |

---

## Part III: Implementation Plan

### Task 1: Data Acquisition (30 Days from tardis.dev)

**Files:**
- Create: `scripts/download_tardis.py`
- Modify: `configs/default.json` (update stride, paths)

- [ ] **Step 1: Install tardis-dev client**

```bash
pip install tardis-dev
```

- [ ] **Step 2: Create download script**

```python
# scripts/download_tardis.py
"""Download BTCUSDT L2 orderbook data from tardis.dev."""

import argparse
import sys

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--from-date", default="2026-01-01")
    parser.add_argument("--to-date", default="2026-01-30")
    parser.add_argument("--output-dir", default="data/raw")
    args = parser.parse_args()

    try:
        from tardis_dev import datasets
    except ImportError:
        print("pip install tardis-dev")
        sys.exit(1)

    datasets.download(
        exchange="binance-futures",
        data_types=["book_snapshot_25"],
        from_date=args.from_date,
        to_date=args.to_date,
        symbols=["BTCUSDT"],
        api_key=args.api_key,
        download_dir=args.output_dir,
    )
    print(f"Download complete -> {args.output_dir}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Download data**

```bash
python scripts/download_tardis.py --api-key YOUR_KEY --from-date 2026-01-01 --to-date 2026-01-30
```

- [ ] **Step 4: Process through existing pipeline (adjust stride)**

```bash
# Process each day's CSV into NPZ with stride=60 (not 10!)
python -c "
import glob
from src.features.pipeline import process_csv_to_npz

for f in sorted(glob.glob('data/raw/*book_snapshot_25*.csv.gz')):
    print(f'Processing {f}...')
    process_csv_to_npz(f, 'data/npz_h180_s60',
                       horizon_sec=180, input_len=300,
                       stride=60, n_levels=25)
print('Done.')
"
```

- [ ] **Step 5: Verify data**

```bash
python -c "
import numpy as np
from pathlib import Path

npz_dir = Path('data/npz_h180_s60')
files = sorted(npz_dir.glob('*.npz'))
print(f'Days: {len(files)}')
total_windows = 0
for f in files:
    d = np.load(f)
    n = d['X'].shape[0]
    total_windows += n
    print(f'  {f.stem}: X={d[\"X\"].shape}, y={d[\"y\"].shape}, valid={d[\"y_mask\"].sum()}/{n}')
print(f'Total windows: {total_windows}')
"
```

Expected: ~30 files, ~43K total windows.

- [ ] **Step 6: Update config for stride=60**

Update `configs/default.json`:
```json
{
    "data": {
        "csv_path": "data/raw",
        "npz_dir": "data/npz_h180_s60",
        "n_levels": 25,
        "horizon_sec": 180,
        "input_len": 300,
        "stride": 60
    }
}
```

- [ ] **Step 7: Commit**

```bash
git add scripts/download_tardis.py configs/default.json
git commit -m "feat: add tardis.dev download script, set stride=60"
```

---

### Task 2: Add Order Flow Features

**Files:**
- Modify: `src/features/microstructure.py`
- Modify: `tests/test_features.py`

- [ ] **Step 1: Write failing test for order flow features**

```python
# Add to tests/test_features.py

def test_order_flow_features_exist():
    """Verify order flow (temporal delta) features are computed."""
    # ... create synthetic data as in existing test_resample_basic ...
    from src.features.microstructure import compute_microstructure_features
    from src.features.resample import resample_lob_to_1s

    n_levels = 5
    n_ticks = 500
    rng = np.random.default_rng(42)
    base_ts = 1_000_000_000_000
    timestamps = base_ts + np.cumsum(rng.integers(40_000, 60_000, size=n_ticks))

    cols = {'timestamp': timestamps}
    mid_price = 60000.0
    for i in range(n_levels):
        cols[f'asks[{i}].price'] = mid_price + 0.1 * (i + 1) + rng.normal(0, 0.01, n_ticks)
        cols[f'asks[{i}].amount'] = rng.exponential(1.0, n_ticks)
        cols[f'bids[{i}].price'] = mid_price - 0.1 * (i + 1) + rng.normal(0, 0.01, n_ticks)
        cols[f'bids[{i}].amount'] = rng.exponential(1.0, n_ticks)

    # Pad to 25 levels with dummy data
    for i in range(n_levels, 25):
        cols[f'asks[{i}].price'] = mid_price + 0.1 * (i + 1) + rng.normal(0, 0.01, n_ticks)
        cols[f'asks[{i}].amount'] = rng.exponential(0.1, n_ticks)
        cols[f'bids[{i}].price'] = mid_price - 0.1 * (i + 1) + rng.normal(0, 0.01, n_ticks)
        cols[f'bids[{i}].amount'] = rng.exponential(0.1, n_ticks)

    df = pd.DataFrame(cols)
    bars = resample_lob_to_1s(df, n_levels=25)
    features = compute_microstructure_features(bars, n_levels=25)

    # Check order flow features exist
    expected_flow_features = [
        'delta_bid_depth_L5',
        'delta_ask_depth_L5',
        'net_order_flow_L5',
        'delta_obi_L5_5s',
        'delta_pressure_5s',
    ]
    for feat in expected_flow_features:
        assert feat in features.columns, f"Missing order flow feature: {feat}"
        assert features[feat].isna().sum() == 0, f"NaN in {feat}"

    print("PASS: test_order_flow_features_exist")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /ldap_home/siyu.hao/siyu_project/dl_qt/dl_quant && python -m pytest tests/test_features.py::test_order_flow_features_exist -v
```

Expected: FAIL — features not in columns.

- [ ] **Step 3: Add order flow features to microstructure.py**

Add after the existing temporal features section (before `out = out.fillna(0.0)`):

```python
    # ==================================================================
    # 12. ORDER FLOW features (5) — temporal deltas of book state
    # ==================================================================
    bid_depth_5_s = pd.Series(bid_depth_5)
    ask_depth_5_s = pd.Series(ask_depth_5)

    # 1-second depth changes
    out["delta_bid_depth_L5"] = bid_depth_5_s.diff(1).values
    out["delta_ask_depth_L5"] = ask_depth_5_s.diff(1).values

    # Net order flow: positive = bid-side adding, ask-side removing (bullish)
    out["net_order_flow_L5"] = (
        bid_depth_5_s.diff(1).values - ask_depth_5_s.diff(1).values
    )

    # 5-second OBI change (captures medium-term flow direction)
    obi_L5_s = pd.Series(out["obi_L5"].values)
    out["delta_obi_L5_5s"] = obi_L5_s.diff(5).values

    # 5-second pressure change
    pressure_s = pd.Series(out["price_pressure"].values)
    out["delta_pressure_5s"] = pressure_s.diff(5).values
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /ldap_home/siyu.hao/siyu_project/dl_qt/dl_quant && python -m pytest tests/test_features.py -v
```

Expected: all tests PASS, including the new one. Feature count now 44 (39 + 5).

- [ ] **Step 5: Commit**

```bash
git add src/features/microstructure.py tests/test_features.py
git commit -m "feat: add 5 order flow features (delta_depth, net_flow, delta_obi, delta_pressure)"
```

---

### Task 3: Fix SpatialLOBEncoder Feature Grouping

**Files:**
- Create: `src/features/feature_groups.py`
- Modify: `run_pipeline.py`
- Modify: `tests/test_model.py`

- [ ] **Step 1: Write failing test**

```python
# Add to tests/test_model.py

def test_feature_group_assignment():
    """Verify bid/ask/global groups contain semantically correct features."""
    from src.features.feature_groups import get_feature_groups

    groups = get_feature_groups()
    bid_names = groups["bid_names"]
    ask_names = groups["ask_names"]
    global_names = groups["global_names"]

    # Bid features should contain bid-side quantities
    assert "obi_L1" in bid_names
    assert "bid_depth_L5" in bid_names
    assert "bid_concentration" in bid_names
    assert "bid_amt_ratio_L0" in bid_names

    # Ask features should contain ask-side quantities
    assert "ask_depth_L5" in ask_names
    assert "ask_concentration" in ask_names
    assert "ask_amt_ratio_L0" in ask_names

    # Global features should contain market-wide quantities
    assert "log_return_1s" in global_names
    assert "spread_bps" in global_names
    assert "realized_vol_30s" in global_names
    assert "second_of_day_sin" in global_names

    # No overlap
    all_names = bid_names + ask_names + global_names
    assert len(all_names) == len(set(all_names)), "Feature groups overlap!"

    print("PASS: test_feature_group_assignment")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_model.py::test_feature_group_assignment -v
```

- [ ] **Step 3: Create feature_groups.py**

```python
# src/features/feature_groups.py
"""Semantic feature group definitions for SpatialLOBEncoder."""


def get_feature_groups():
    """Return semantically correct bid/ask/global feature groups.

    Returns dict with keys: bid_names, ask_names, global_names,
    and corresponding index lists for a given feature name list.
    """
    bid_names = [
        # Imbalance (bid-dominated)
        "obi_L1", "obi_L5", "obi_L10", "obi_L25", "obi_L1_delta",
        # Depth
        "bid_depth_L5", "bid_depth_L25",
        # Pressure
        "weighted_price_bid_L10",
        # Slopes
        "bid_slope_L10",
        # Concentration
        "bid_concentration",
        # Per-level
        "bid_amt_ratio_L0", "bid_amt_ratio_L1", "bid_amt_ratio_L2",
        "bid_amt_ratio_L3", "bid_amt_ratio_L4",
        # Order flow (bid-side)
        "delta_bid_depth_L5",
    ]

    ask_names = [
        # Depth
        "ask_depth_L5", "ask_depth_L25",
        # Pressure
        "weighted_price_ask_L10",
        # Slopes
        "ask_slope_L10",
        # Concentration
        "ask_concentration",
        # Per-level
        "ask_amt_ratio_L0", "ask_amt_ratio_L1", "ask_amt_ratio_L2",
        "ask_amt_ratio_L3", "ask_amt_ratio_L4",
        # Order flow (ask-side)
        "delta_ask_depth_L5",
    ]

    global_names = [
        # Price
        "log_return_1s", "log_return_5s", "log_return_30s",
        # Spread
        "spread_bps", "spread_change",
        # Depth ratio (cross-side)
        "depth_ratio_L5",
        # Price pressure (cross-side)
        "price_pressure",
        # Volatility
        "realized_vol_30s", "realized_vol_60s", "realized_vol_300s",
        # Microstructure
        "kyle_lambda_30s", "amihud_30s",
        # Temporal
        "second_of_day_sin", "second_of_day_cos",
        # Order flow (cross-side)
        "net_order_flow_L5", "delta_obi_L5_5s", "delta_pressure_5s",
    ]

    return {
        "bid_names": bid_names,
        "ask_names": ask_names,
        "global_names": global_names,
    }


def get_feature_group_indices(feature_names):
    """Map feature group names to indices in a given feature name list.

    Parameters
    ----------
    feature_names : list[str]
        Ordered list of feature names (as produced by the pipeline).

    Returns
    -------
    dict with bid_idx, ask_idx, global_idx (lists of int).
    """
    groups = get_feature_groups()
    name_to_idx = {name: i for i, name in enumerate(feature_names)}

    bid_idx = [name_to_idx[n] for n in groups["bid_names"] if n in name_to_idx]
    ask_idx = [name_to_idx[n] for n in groups["ask_names"] if n in name_to_idx]
    global_idx = [name_to_idx[n] for n in groups["global_names"] if n in name_to_idx]

    return {"bid_idx": bid_idx, "ask_idx": ask_idx, "global_idx": global_idx}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_model.py::test_feature_group_assignment -v
```

- [ ] **Step 5: Commit**

```bash
git add src/features/feature_groups.py tests/test_model.py
git commit -m "feat: add semantic bid/ask/global feature group definitions"
```

---

### Task 4: Build Progressive Baseline Framework

**Files:**
- Create: `src/baselines/linear_baseline.py`
- Create: `src/baselines/evaluate_baselines.py`
- Create: `tests/test_baselines.py`

- [ ] **Step 1: Write failing test for linear baseline**

```python
# tests/test_baselines.py
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_ridge_baseline():
    """Ridge regression baseline should run and produce correlation."""
    from src.baselines.linear_baseline import RidgeBaseline

    rng = np.random.default_rng(42)
    n_train, n_test = 1000, 200
    T, F = 300, 40

    # Inject a weak linear signal
    X_train = rng.standard_normal((n_train, T, F)).astype(np.float32)
    coef = rng.standard_normal(F) * 0.01
    y_train = X_train[:, -1, :] @ coef + rng.standard_normal(n_train) * 0.1
    y_train = y_train.astype(np.float32)

    X_test = rng.standard_normal((n_test, T, F)).astype(np.float32)
    y_test = X_test[:, -1, :] @ coef + rng.standard_normal(n_test) * 0.1
    y_test = y_test.astype(np.float32)

    model = RidgeBaseline(alpha=1.0)
    model.fit(X_train, y_train)
    pred = model.predict(X_test)

    assert pred.shape == (n_test,)
    corr = np.corrcoef(pred, y_test)[0, 1]
    assert corr > 0.1, f"Ridge should find the linear signal, got corr={corr:.3f}"
    print(f"PASS: test_ridge_baseline (corr={corr:.3f})")


def test_temporal_ridge_baseline():
    """Ridge with temporal aggregates should use more than just last step."""
    from src.baselines.linear_baseline import TemporalRidgeBaseline

    rng = np.random.default_rng(42)
    n_train, n_test = 1000, 200
    T, F = 300, 40

    X_train = rng.standard_normal((n_train, T, F)).astype(np.float32)
    y_train = rng.standard_normal(n_train).astype(np.float32)

    X_test = rng.standard_normal((n_test, T, F)).astype(np.float32)
    y_test = rng.standard_normal(n_test).astype(np.float32)

    model = TemporalRidgeBaseline(alpha=1.0)
    model.fit(X_train, y_train)
    pred = model.predict(X_test)

    assert pred.shape == (n_test,)
    # With random data, corr should be near 0 (no overfitting due to ridge)
    corr = np.corrcoef(pred, y_test)[0, 1]
    assert abs(corr) < 0.2, f"Should not overfit random data, got corr={corr:.3f}"
    print(f"PASS: test_temporal_ridge_baseline (corr={corr:.3f})")


if __name__ == '__main__':
    test_ridge_baseline()
    test_temporal_ridge_baseline()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_baselines.py -v
```

- [ ] **Step 3: Implement linear baselines**

```python
# src/baselines/linear_baseline.py
"""Linear baselines for LOB return prediction."""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import Ridge


class RidgeBaseline:
    """Ridge regression on the last timestep's features.

    Uses only x[:, -1, :] (the most recent 1-second snapshot)
    as features for predicting the return.
    """

    def __init__(self, alpha: float = 1.0):
        self.model = Ridge(alpha=alpha)

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """X: (N, T, F), y: (N,)"""
        features = X[:, -1, :]  # (N, F)
        self.model.fit(features, y)

    def predict(self, X: np.ndarray) -> np.ndarray:
        features = X[:, -1, :]
        return self.model.predict(features)

    @property
    def coef_(self) -> np.ndarray:
        return self.model.coef_


class TemporalRidgeBaseline:
    """Ridge regression with temporal aggregates.

    Features: last value, mean over window, std over window,
    first-minus-last (trend) for each raw feature.
    Total: F * 4 features.
    """

    def __init__(self, alpha: float = 1.0):
        self.model = Ridge(alpha=alpha)

    def _extract(self, X: np.ndarray) -> np.ndarray:
        """X: (N, T, F) -> (N, F*4)"""
        last = X[:, -1, :]                    # (N, F)
        mean = X.mean(axis=1)                 # (N, F)
        std = X.std(axis=1)                   # (N, F)
        trend = X[:, -1, :] - X[:, 0, :]      # (N, F)
        return np.concatenate([last, mean, std, trend], axis=1)

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        features = self._extract(X)
        self.model.fit(features, y)

    def predict(self, X: np.ndarray) -> np.ndarray:
        features = self._extract(X)
        return self.model.predict(features)
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_baselines.py -v
```

Expected: all PASS.

- [ ] **Step 5: Create baseline evaluation script**

```python
# src/baselines/evaluate_baselines.py
"""Evaluate progressive baselines on multi-day LOB data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy import stats

from src.baselines.linear_baseline import RidgeBaseline, TemporalRidgeBaseline
from src.training.dataset import LOBDataset, build_time_series_folds
from src.evaluation.metrics import evaluate_predictions


def run_baselines(npz_dir: str, output_path: str) -> None:
    npz_dir = Path(npz_dir)
    days = sorted([f.stem for f in npz_dir.glob("*.npz")])
    print(f"Found {len(days)} days")

    if len(days) < 24:
        # Simple split: 70/15/15
        n = len(days)
        n_train = int(n * 0.7)
        n_val = int(n * 0.15)
        folds = [{"train": days[:n_train],
                  "val": days[n_train:n_train+n_val],
                  "test": days[n_train+n_val:]}]
    else:
        folds = build_time_series_folds(days, 14, 5, 5, 5)

    results = []

    for fold_idx, fold in enumerate(folds):
        print(f"\n=== Fold {fold_idx} ===")
        print(f"  train: {fold['train'][0]}..{fold['train'][-1]} ({len(fold['train'])} days)")
        print(f"  test:  {fold['test'][0]}..{fold['test'][-1]} ({len(fold['test'])} days)")

        train_ds = LOBDataset(str(npz_dir), fold["train"], normalize=False)
        test_ds = LOBDataset(str(npz_dir), fold["test"], normalize=False)

        # Normalize X
        x_mean, x_std = train_ds.compute_stats()
        X_train = (train_ds.X - x_mean) / (x_std + 1e-8)
        X_test = (test_ds.X - x_mean) / (x_std + 1e-8)
        np.clip(X_train, -10, 10, out=X_train)
        np.clip(X_test, -10, 10, out=X_test)

        # Normalize y
        y_train_valid = train_ds.y[train_ds.mask > 0]
        y_med = float(np.median(y_train_valid))
        y_mad = float(np.median(np.abs(y_train_valid - y_med)))
        y_sigma = max(1.4826 * y_mad, 1e-9)
        y_train = (train_ds.y - y_med) / y_sigma
        y_test = (test_ds.y - y_med) / y_sigma
        np.clip(y_train, -5, 5, out=y_train)
        np.clip(y_test, -5, 5, out=y_test)

        mask_train = train_ds.mask
        mask_test = test_ds.mask

        baselines = {
            "constant_zero": None,
            "ridge_last_step": RidgeBaseline(alpha=1.0),
            "ridge_last_step_a10": RidgeBaseline(alpha=10.0),
            "ridge_last_step_a100": RidgeBaseline(alpha=100.0),
            "temporal_ridge_a1": TemporalRidgeBaseline(alpha=1.0),
            "temporal_ridge_a10": TemporalRidgeBaseline(alpha=10.0),
        }

        for name, model in baselines.items():
            if model is None:
                pred = np.zeros(len(y_test))
            else:
                train_mask = mask_train > 0
                model.fit(X_train[train_mask], y_train[train_mask])
                pred = model.predict(X_test)

            metrics = evaluate_predictions(
                pred=pred, target=y_test,
                mask=mask_test, uncertainty=None, quantiles_pred=None,
            )
            print(f"  {name:30s} | corr={metrics.get('correlation', 0):.4f} "
                  f"| R2={metrics.get('r2', 0):.4f} "
                  f"| autocorr={metrics.get('residual_autocorr_lag1', 0):.4f}")
            results.append({
                "fold": fold_idx,
                "model": name,
                **{k: float(v) if isinstance(v, (float, np.floating)) else v
                   for k, v in metrics.items()},
            })

    # Save
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--npz-dir", default="data/npz_h180_s60")
    parser.add_argument("--output", default="experiments/baselines/results.json")
    args = parser.parse_args()
    run_baselines(args.npz_dir, args.output)
```

- [ ] **Step 6: Commit**

```bash
mkdir -p src/baselines && touch src/baselines/__init__.py
git add src/baselines/ tests/test_baselines.py
git commit -m "feat: add ridge regression baselines with temporal aggregates"
```

---

### Task 5: Simplified Neural Model (Single-Head, Single-Loss)

**Files:**
- Create: `src/model/lightweight_model.py`
- Create: `tests/test_lightweight_model.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_lightweight_model.py
import torch
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_lightweight_model_forward():
    """LightweightLOBModel forward pass produces correct shapes."""
    from src.model.lightweight_model import LightweightLOBModel

    B, L, F = 4, 300, 44  # 44 features after adding order flow
    x = torch.randn(B, L, F)

    model = LightweightLOBModel(
        n_features=F, d_model=32, nhead=4, d_ff=64,
        dropout=0.1, n_quantiles=3,
    )

    out = model(x)
    assert out["quantiles"].shape == (B, 3)
    assert out["point_pred"].shape == (B,)

    # Should NOT have direction_logits or uncertainty
    assert "direction_logits" not in out
    assert "uncertainty" not in out

    total_params = sum(p.numel() for p in model.parameters())
    print(f"Total params: {total_params:,}")
    assert total_params < 30_000, f"Model too large: {total_params:,} params (target <30K)"
    print(f"PASS: test_lightweight_model_forward ({total_params:,} params)")


def test_lightweight_model_causal():
    """Model output at time t should not depend on inputs at time t+1."""
    from src.model.lightweight_model import LightweightLOBModel

    B, L, F = 2, 300, 44
    model = LightweightLOBModel(n_features=F, d_model=32, nhead=4, d_ff=64)
    model.eval()

    x = torch.randn(B, L, F)
    out1 = model(x)["point_pred"].detach()

    # Perturb future (last 50 steps)
    x2 = x.clone()
    x2[:, 250:, :] = torch.randn(B, 50, F)
    out2 = model(x2, pred_step=249)["point_pred"].detach()

    out1_at_249 = model(x, pred_step=249)["point_pred"].detach()

    # Predictions at step 249 should be identical
    assert torch.allclose(out1_at_249, out2, atol=1e-5), "Causality violation!"
    print("PASS: test_lightweight_model_causal")


if __name__ == '__main__':
    test_lightweight_model_forward()
    test_lightweight_model_causal()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_lightweight_model.py -v
```

- [ ] **Step 3: Implement lightweight model**

```python
# src/model/lightweight_model.py
"""Lightweight LOB model: LayerNorm + Conv frontend + single Transformer layer.

Design principles:
- Single loss (quantile only) → no gradient conflict
- No regime gate → replaced by LayerNorm
- Simple spatial merge → concat + linear instead of cross-attention
- Single Transformer layer → 1 attention layer is enough for weak signals
- Target: <30K params
"""

from __future__ import annotations

import math
import torch
import torch.nn as nn
import torch.nn.functional as F


class CausalConv1d(nn.Module):
    """Single causal depthwise-separable conv block."""

    def __init__(self, d_model: int, kernel_size: int = 5,
                 dilation: int = 1, dropout: float = 0.1):
        super().__init__()
        self.pad = (kernel_size - 1) * dilation
        self.norm = nn.LayerNorm(d_model)
        self.dw = nn.Conv1d(d_model, d_model, kernel_size,
                            dilation=dilation, groups=d_model, bias=True)
        self.pw = nn.Conv1d(d_model, d_model, 1, bias=True)
        self.act = nn.GELU()
        self.drop = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        h = self.norm(x).transpose(1, 2)
        h = F.pad(h, (self.pad, 0))
        h = self.dw(h)
        h = h[..., :x.size(1)]
        h = self.pw(h)
        h = self.act(h)
        h = self.drop(h).transpose(1, 2)
        return h + residual


class LightweightLOBModel(nn.Module):
    """Lightweight model for LOB return prediction.

    Architecture:
        LayerNorm → Linear projection → CausalConv x2 →
        single TransformerEncoderLayer → quantile head

    Parameters: ~15-25K depending on d_model.
    """

    def __init__(
        self,
        n_features: int = 44,
        d_model: int = 32,
        nhead: int = 4,
        d_ff: int = 64,
        dropout: float = 0.1,
        n_quantiles: int = 3,
        max_len: int = 512,
    ):
        super().__init__()

        # Input normalization + projection
        self.input_norm = nn.LayerNorm(n_features)
        self.input_proj = nn.Linear(n_features, d_model)

        # Causal conv frontend (2 layers, dilation 1 and 2)
        self.conv1 = CausalConv1d(d_model, kernel_size=5, dilation=1, dropout=dropout)
        self.conv2 = CausalConv1d(d_model, kernel_size=5, dilation=2, dropout=dropout)

        # Learned positional embedding (fixed length, no RoPE needed)
        self.pos_emb = nn.Parameter(torch.zeros(1, max_len, d_model))
        nn.init.normal_(self.pos_emb, std=0.02)

        # Single Transformer layer
        self.attn_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, dim_feedforward=d_ff,
            dropout=dropout, batch_first=True, activation="gelu",
            norm_first=True,
        )

        # Causal mask (registered as buffer)
        self._max_len = max_len

        # Quantile head only (no direction, no uncertainty)
        self.head = nn.Sequential(
            nn.LayerNorm(d_model),
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, n_quantiles),
        )

    def forward(
        self, x: torch.Tensor, pred_step: int = -1,
    ) -> dict[str, torch.Tensor]:
        B, L, F = x.shape

        # Normalize and project
        h = self.input_norm(x)
        h = self.input_proj(h)  # (B, L, d_model)

        # Causal conv
        h = self.conv1(h)
        h = self.conv2(h)

        # Positional embedding
        h = h + self.pos_emb[:, :L, :]

        # Causal attention mask
        mask = torch.triu(
            torch.ones(L, L, device=h.device, dtype=torch.bool), diagonal=1
        )
        h = self.attn_layer(h, src_mask=mask, is_causal=True)

        # Extract prediction timestep
        h_pred = h[:, pred_step, :]  # (B, d_model)

        # Quantile output
        quantiles = self.head(h_pred)  # (B, n_quantiles)
        point_pred = quantiles[:, 1]   # median (q50)

        return {"quantiles": quantiles, "point_pred": point_pred}
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_lightweight_model.py -v
```

Expected: all PASS, total params < 30K.

- [ ] **Step 5: Commit**

```bash
git add src/model/lightweight_model.py tests/test_lightweight_model.py
git commit -m "feat: add lightweight single-head LOB model (<30K params, quantile-only)"
```

---

### Task 6: Single-Loss Training Loop

**Files:**
- Create: `src/training/trainer_v2.py`

- [ ] **Step 1: Write failing test**

```python
# Add to tests/test_training.py

def test_quantile_only_training():
    """Training with quantile loss only should work without direction/uncertainty."""
    from src.model.lightweight_model import LightweightLOBModel
    from src.training.trainer_v2 import train_one_fold_simple
    from torch.utils.data import TensorDataset
    import torch, tempfile, os

    B, L, F = 100, 50, 20  # small for test
    X = torch.randn(B, L, F)
    y = torch.randn(B)
    mask = torch.ones(B)

    train_ds = TensorDataset(X[:70], y[:70], mask[:70])
    val_ds = TensorDataset(X[70:], y[70:], mask[70:])

    model = LightweightLOBModel(n_features=F, d_model=16, nhead=2,
                                 d_ff=32, n_quantiles=3)

    with tempfile.TemporaryDirectory() as tmpdir:
        result = train_one_fold_simple(
            model=model, train_dataset=train_ds, val_dataset=val_ds,
            out_dir=tmpdir, epochs=3, batch_size=32, lr=1e-3,
        )
        assert "val_corr" in result
        assert os.path.exists(os.path.join(tmpdir, "best_model.pt"))

    print(f"PASS: test_quantile_only_training (corr={result['val_corr']:.4f})")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_training.py::test_quantile_only_training -v
```

- [ ] **Step 3: Implement simplified trainer**

```python
# src/training/trainer_v2.py
"""Simplified training loop for lightweight models. Single quantile loss."""

from __future__ import annotations

import json
import math
import os
from typing import Any, Dict

import numpy as np
import torch
from torch.utils.data import DataLoader

from .losses import quantile_loss


class OnlineCorrelation:
    """Welford-style online Pearson correlation tracker."""

    def __init__(self):
        self.n = 0
        self.sp = 0.0; self.st = 0.0
        self.spp = 0.0; self.stt = 0.0; self.spt = 0.0

    def update(self, p: np.ndarray, t: np.ndarray):
        p = np.asarray(p, dtype=np.float64).ravel()
        t = np.asarray(t, dtype=np.float64).ravel()
        self.n += len(p)
        self.sp += p.sum(); self.st += t.sum()
        self.spp += (p*p).sum(); self.stt += (t*t).sum()
        self.spt += (p*t).sum()

    def corr(self) -> float:
        if self.n <= 1: return 0.0
        n = self.n
        cov = (self.spt - self.sp*self.st/n) / n
        vp = (self.spp - self.sp**2/n) / n
        vt = (self.stt - self.st**2/n) / n
        d = math.sqrt(vp * vt) if vp > 0 and vt > 0 else 0.0
        return cov / d if d > 0 else 0.0


def train_one_fold_simple(
    *,
    model: torch.nn.Module,
    train_dataset,
    val_dataset,
    out_dir: str,
    device: str = "cpu",
    epochs: int = 50,
    batch_size: int = 64,
    lr: float = 3e-4,
    weight_decay: float = 1e-3,
    patience: int = 10,
    grad_clip: float = 1.0,
) -> Dict[str, Any]:
    """Train with quantile loss only. Checkpoint by val correlation."""

    os.makedirs(out_dir, exist_ok=True)
    dev = torch.device(device)
    model = model.to(dev)

    train_loader = DataLoader(train_dataset, batch_size=batch_size,
                              shuffle=True, drop_last=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr,
                                  weight_decay=weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="max", factor=0.5, patience=5, min_lr=1e-6,
    )

    best_corr = -1.0
    best_metrics: Dict[str, Any] = {}
    no_improve = 0

    for epoch in range(1, epochs + 1):
        # Train
        model.train()
        train_losses = []
        for x, y, mask in train_loader:
            x, y, mask = x.to(dev), y.to(dev), mask.to(dev)
            out = model(x)

            idx = mask.bool().nonzero(as_tuple=True)[0]
            if len(idx) == 0:
                continue
            loss = quantile_loss(out["quantiles"][idx], y[idx])

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
            optimizer.step()
            train_losses.append(loss.item())

        # Validate
        model.eval()
        metrics = OnlineCorrelation()
        val_losses = []
        with torch.no_grad():
            for x, y, mask in val_loader:
                x, y, mask = x.to(dev), y.to(dev), mask.to(dev)
                out = model(x)
                idx = mask.bool().nonzero(as_tuple=True)[0]
                if len(idx) == 0:
                    continue
                loss = quantile_loss(out["quantiles"][idx], y[idx])
                val_losses.append(loss.item())
                metrics.update(
                    out["point_pred"][idx].cpu().numpy(),
                    y[idx].cpu().numpy(),
                )

        val_corr = metrics.corr()
        scheduler.step(val_corr)

        avg_tl = np.mean(train_losses) if train_losses else float("inf")
        avg_vl = np.mean(val_losses) if val_losses else float("inf")
        lr_now = optimizer.param_groups[0]["lr"]
        print(f"Epoch {epoch:3d}/{epochs} | lr={lr_now:.1e} | "
              f"train_loss={avg_tl:.4f} | val_loss={avg_vl:.4f} | "
              f"corr={val_corr:+.4f}")

        if val_corr > best_corr + 1e-4:
            best_corr = val_corr
            no_improve = 0
            best_metrics = {"best_epoch": epoch, "val_corr": val_corr,
                           "val_loss": avg_vl}
            torch.save(model.state_dict(),
                       os.path.join(out_dir, "best_model.pt"))
        else:
            no_improve += 1

        if no_improve >= patience:
            print(f"Early stopping at epoch {epoch}")
            break

    with open(os.path.join(out_dir, "metrics.json"), "w") as f:
        json.dump(best_metrics, f, indent=2)
    return best_metrics
```

- [ ] **Step 4: Run test**

```bash
python -m pytest tests/test_training.py::test_quantile_only_training -v
```

- [ ] **Step 5: Commit**

```bash
git add src/training/trainer_v2.py tests/test_training.py
git commit -m "feat: add simplified trainer with quantile-only loss"
```

---

### Task 7: End-to-End Pipeline Script

**Files:**
- Create: `run_baselines.py`

- [ ] **Step 1: Create the runner**

```python
# run_baselines.py
"""Run progressive baselines + lightweight model on multi-day data."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np
import torch

from src.training.dataset import LOBDataset, build_time_series_folds
from src.baselines.linear_baseline import RidgeBaseline, TemporalRidgeBaseline
from src.model.lightweight_model import LightweightLOBModel
from src.training.trainer_v2 import train_one_fold_simple
from src.evaluation.metrics import evaluate_predictions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--npz-dir", default="data/npz_h180_s60")
    parser.add_argument("--output-dir", default="experiments/progressive")
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()

    npz_dir = Path(args.npz_dir)
    days = sorted([f.stem for f in npz_dir.glob("*.npz")])
    print(f"Found {len(days)} days: {days[0]}..{days[-1]}")

    if args.device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device = args.device

    # Build folds
    if len(days) >= 24:
        folds = build_time_series_folds(days, 14, 5, 5, 5)
    else:
        n = len(days)
        nt = int(n * 0.7); nv = int(n * 0.15)
        folds = [{"train": days[:nt], "val": days[nt:nt+nv],
                  "test": days[nt+nv:]}]

    all_results = []

    for fi, fold in enumerate(folds):
        print(f"\n{'='*60}\nFold {fi}: train={len(fold['train'])}d "
              f"val={len(fold['val'])}d test={len(fold['test'])}d\n{'='*60}")

        # Load data
        train_ds = LOBDataset(str(npz_dir), fold["train"], normalize=False)
        val_ds = LOBDataset(str(npz_dir), fold["val"], normalize=False)
        test_ds = LOBDataset(str(npz_dir), fold["test"], normalize=False)

        x_mean, x_std = train_ds.compute_stats()

        # Normalize
        def normalize_X(X):
            X = (X - x_mean) / (x_std + 1e-8)
            return np.clip(X, -10, 10)

        X_train = normalize_X(train_ds.X)
        X_val = normalize_X(val_ds.X)
        X_test = normalize_X(test_ds.X)

        y_valid = train_ds.y[train_ds.mask > 0]
        y_med = float(np.median(y_valid))
        y_mad = float(np.median(np.abs(y_valid - y_med)))
        y_sig = max(1.4826 * y_mad, 1e-9)

        def normalize_y(y):
            return np.clip((y - y_med) / y_sig, -5, 5)

        y_train = normalize_y(train_ds.y)
        y_val = normalize_y(val_ds.y)
        y_test = normalize_y(test_ds.y)

        # ---- Linear Baselines ----
        for name, model in [
            ("ridge_a1", RidgeBaseline(1.0)),
            ("ridge_a10", RidgeBaseline(10.0)),
            ("temporal_ridge_a10", TemporalRidgeBaseline(10.0)),
        ]:
            mask_tr = train_ds.mask > 0
            model.fit(X_train[mask_tr], y_train[mask_tr])
            pred = model.predict(X_test)
            m = evaluate_predictions(pred, y_test, test_ds.mask)
            print(f"  {name:30s} | corr={m.get('correlation',0):.4f} "
                  f"| autocorr={m.get('residual_autocorr_lag1',0):.4f}")
            all_results.append({"fold": fi, "model": name, **{
                k: float(v) if isinstance(v, (float, np.floating)) else v
                for k, v in m.items()
            }})

        # ---- Lightweight Neural ----
        n_feat = X_train.shape[-1]
        nn_model = LightweightLOBModel(
            n_features=n_feat, d_model=32, nhead=4, d_ff=64,
            dropout=0.15, n_quantiles=3,
        )
        print(f"  Neural model: {sum(p.numel() for p in nn_model.parameters()):,} params")

        # Wrap as datasets
        from torch.utils.data import TensorDataset
        train_td = TensorDataset(
            torch.FloatTensor(X_train), torch.FloatTensor(y_train),
            torch.FloatTensor(train_ds.mask))
        val_td = TensorDataset(
            torch.FloatTensor(X_val), torch.FloatTensor(y_val),
            torch.FloatTensor(val_ds.mask))
        test_td = TensorDataset(
            torch.FloatTensor(X_test), torch.FloatTensor(y_test),
            torch.FloatTensor(test_ds.mask))

        fold_dir = os.path.join(args.output_dir, f"fold_{fi}")
        train_one_fold_simple(
            model=nn_model, train_dataset=train_td, val_dataset=val_td,
            out_dir=fold_dir, device=device, epochs=50,
            batch_size=128, lr=1e-3, patience=10,
        )

        # Test evaluation
        nn_model.load_state_dict(torch.load(
            os.path.join(fold_dir, "best_model.pt"),
            map_location=device, weights_only=True))
        nn_model.eval()
        nn_model.to(device)

        preds = []
        with torch.no_grad():
            test_loader = torch.utils.data.DataLoader(
                test_td, batch_size=128, shuffle=False)
            for x, y, mask in test_loader:
                out = nn_model(x.to(device))
                preds.append(out["point_pred"].cpu().numpy())
        pred_nn = np.concatenate(preds)

        m = evaluate_predictions(pred_nn, y_test, test_ds.mask)
        print(f"  {'lightweight_nn':30s} | corr={m.get('correlation',0):.4f} "
              f"| autocorr={m.get('residual_autocorr_lag1',0):.4f}")
        all_results.append({"fold": fi, "model": "lightweight_nn", **{
            k: float(v) if isinstance(v, (float, np.floating)) else v
            for k, v in m.items()
        }})

    # Save
    out_path = os.path.join(args.output_dir, "all_results.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nAll results saved to {out_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add run_baselines.py
git commit -m "feat: add progressive baseline + lightweight model runner"
```

---

### Task 8: Decision Gate — What to Do Next

After running the baselines on 30-day data, you will have one of these outcomes:

| Outcome | Interpretation | Next Step |
|---|---|---|
| Ridge corr > 0.03, stable across folds | **Linear signal exists.** The features have predictive power. | Proceed to neural models. Focus on capturing nonlinearities. |
| Ridge corr ≈ 0, neural corr > 0.03 | **Nonlinear signal only.** Features interact in ways ridge can't capture. | Good — neural model adds value. Carefully tune capacity. |
| Ridge corr ≈ 0, neural corr ≈ 0 | **No signal in current features.** Model capacity is not the bottleneck. | Go back to feature engineering. Add more order flow features, try different horizons, check for data quality issues. |
| Ridge corr > neural corr | **Neural model overfits.** Too much capacity for the signal. | Reduce d_model, increase dropout, increase regularization. |

**Do NOT proceed to Phase 3 (more complex models) until Phase 1-2 baselines show stable positive correlation on held-out days.**

---

## Summary: What Changed and Why

| Before | After | Rationale |
|---|---|---|
| 1 day data | 30 days | Minimum for meaningful temporal CV |
| stride=10 (97% overlap) | stride=60 (80% overlap) | Reduce effective sample inflation, lower autocorrelation |
| 219K params, 4 heads | <30K params, 1 head (quantile) | Match capacity to signal strength |
| RegimeAwareFeatureGate | LayerNorm | 5-min window can't detect hour-scale regimes |
| 4-component loss | Quantile loss only | Eliminate gradient conflict, seesaw effect |
| RoPE | Learned positional embedding | Fixed L=300, no extrapolation needed |
| Depth=2 Transformer | Depth=1 + conv frontend | Sufficient capacity for weak signal |
| Broken bid/ask/global split | Semantic feature groups | Zero-cost fix for cross-attention |
| No linear baselines | Ridge → MLP → Neural ladder | Earn complexity with evidence |
| 39 features | 44 features (+5 order flow) | Biggest gap was temporal book dynamics |
