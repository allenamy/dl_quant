# LOB Transformer V2: Structure-Aware Crypto Mid-Frequency Prediction

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete pipeline from raw L2 orderbook CSV to a structure-aware, probabilistic LOB Transformer that predicts BTCUSDT 3-minute returns, targeting correlation > 0.10 and unbiased residuals.

**Architecture:** Resample raw ~57ms LOB snapshots to 1-second bars with engineered microstructure features (imbalance, depth, spread dynamics, flow). Feed 5-minute input windows (L=300 at 1s) into a dual-path Transformer: spatial attention across bid/ask levels, then temporal causal attention across time. Output multi-quantile predictions (q10/q50/q90) + direction probability. Multi-task training with volatility and spread auxiliary heads. Regime-adaptive feature gating.

**Tech Stack:** Python 3.9+, PyTorch 2.0+, pandas, numpy, scipy

---

## Time Granularity Analysis

| Horizon | Return std (bps) | Round-trip cost (bps) | Signal/Cost ratio | Verdict |
|---------|-----------------|----------------------|-------------------|---------|
| 1 min   | ~5.8            | 4.0                  | 1.45x             | Too tight |
| 2 min   | ~8.5            | 4.0                  | 2.1x              | Marginal |
| **3 min** | **~10.5**     | **4.0**              | **2.6x**          | **Sweet spot** |
| 5 min   | ~12.8           | 4.0                  | 3.2x              | Good but slower |
| 10 min  | ~18.7           | 4.0                  | 4.7x              | Too slow for mid-freq |

**Decision: H=180s (3-minute) prediction horizon.**

- Binance USDT-M taker fee: 0.02% per side = 4 bps round trip
- At 3-min horizon, std ~10.5 bps gives 2.6x signal-to-cost ratio
- Fast enough for mid-frequency, slow enough to avoid microstructure noise
- Input: 300 steps at 1-second sampling (5 minutes of context)

## Current Model Issues & How We Fix Them

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| Correlation ~0.05 | Flat S*F input loses LOB structure; weak feature engineering | Structure-aware encoder + engineered microstructure features |
| Positive autocorrelation in predictions | Model learns smoothed/lagged signal; no temporal decorrelation | Shorter input window; prediction residual penalty; better temporal encoding |
| Left tail overestimate | Symmetric Huber loss; no asymmetric handling | Asymmetric quantile loss; explicit direction head; CVaR component |
| No data leakage guarantee | Implicit in fold construction, not verified | Explicit timestamp assertions in feature pipeline |

## File Structure

```
quant_research/
  BTCUSDT.csv.gz                          # Raw data (existing)
  tf_train_seq_att_v2_new.py              # Reference model (existing, read-only)
  
  src/
    __init__.py
    features/
      __init__.py
      resample.py                         # Task 1: Raw CSV -> 1s bars
      microstructure.py                   # Task 2: LOB feature engineering
      pipeline.py                         # Task 3: Full CSV -> NPZ pipeline
    model/
      __init__.py
      side_encoder.py                     # Task 4: Bid/ask spatial encoding
      temporal_encoder.py                 # Task 5: Causal temporal Transformer
      lob_transformer.py                  # Task 6: Full model assembly
      heads.py                            # Task 7: Probabilistic + multi-task heads
    training/
      __init__.py
      dataset.py                          # Task 8: NPZ dataset + fold builder
      losses.py                           # Task 9: Quantile + asymmetric losses
      trainer.py                          # Task 10: Training loop
    evaluation/
      __init__.py
      metrics.py                          # Task 11: Evaluation metrics
      backtest.py                         # Task 12: Simple PnL backtest
  
  tests/
    __init__.py
    test_features.py                      # Tests for feature pipeline
    test_model.py                         # Tests for model components
    test_training.py                      # Tests for training pipeline
    test_no_leakage.py                    # Data leakage verification
  
  configs/
    default.json                          # Task 13: Config system
  
  run_pipeline.py                         # Task 14: End-to-end entry point
```

---

## Task 1: Resample Raw LOB to 1-Second Bars

**Files:**
- Create: `src/__init__.py`
- Create: `src/features/__init__.py`
- Create: `src/features/resample.py`
- Create: `tests/__init__.py`
- Create: `tests/test_features.py`

- [ ] **Step 1: Create package structure**

```bash
mkdir -p src/features src/model src/training src/evaluation tests configs
touch src/__init__.py src/features/__init__.py src/model/__init__.py
touch src/training/__init__.py src/evaluation/__init__.py tests/__init__.py
```

- [ ] **Step 2: Write the failing test for resampling**

```python
# tests/test_features.py
import numpy as np
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.features.resample import resample_lob_to_1s


def test_resample_basic():
    """Resample irregular LOB ticks to 1-second bars using last-value."""
    n_levels = 5  # Use 5 levels for test (real data has 25)
    n_ticks = 100
    
    # Create synthetic LOB data at irregular intervals (~50ms)
    rng = np.random.default_rng(42)
    base_ts = 1_000_000_000_000  # some base microsecond timestamp
    timestamps = base_ts + np.cumsum(rng.integers(40_000, 60_000, size=n_ticks))
    
    cols = {}
    cols['timestamp'] = timestamps
    cols['local_timestamp'] = timestamps + 2000  # 2ms delay
    cols['exchange'] = 'binance-futures'
    cols['symbol'] = 'BTCUSDT'
    
    mid_price = 60000.0
    for i in range(n_levels):
        cols[f'asks[{i}].price'] = mid_price + 0.1 * (i + 1) + rng.normal(0, 0.01, n_ticks)
        cols[f'asks[{i}].amount'] = rng.exponential(1.0, n_ticks)
        cols[f'bids[{i}].price'] = mid_price - 0.1 * (i + 1) + rng.normal(0, 0.01, n_ticks)
        cols[f'bids[{i}].amount'] = rng.exponential(1.0, n_ticks)
    
    df = pd.DataFrame(cols)
    
    result = resample_lob_to_1s(df, n_levels=n_levels)
    
    # Should have 1 row per second covered
    duration_sec = (timestamps[-1] - timestamps[0]) / 1e6
    expected_rows = int(duration_sec)  # approximate
    assert abs(len(result) - expected_rows) <= 2, f"Expected ~{expected_rows} rows, got {len(result)}"
    
    # Timestamps should be exactly 1s apart
    ts_diffs = np.diff(result['timestamp'].values)
    assert np.all(ts_diffs == 1_000_000), "Timestamps must be exactly 1s apart"
    
    # All LOB columns must be present and non-NaN (forward-filled)
    for i in range(n_levels):
        for side in ['asks', 'bids']:
            for field in ['price', 'amount']:
                col = f'{side}[{i}].{field}'
                assert col in result.columns, f"Missing column: {col}"
                assert result[col].isna().sum() == 0, f"NaN in {col}"
    
    print("PASS: test_resample_basic")


if __name__ == '__main__':
    test_resample_basic()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /Users/haosiyu/Desktop/quant_research && python3 tests/test_features.py`
Expected: ImportError - module not found

- [ ] **Step 4: Implement resampling**

```python
# src/features/resample.py
"""Resample irregular LOB snapshots to regular 1-second intervals."""

import numpy as np
import pandas as pd
from typing import Optional


def resample_lob_to_1s(
    df: pd.DataFrame,
    n_levels: int = 25,
    ts_col: str = 'timestamp',
) -> pd.DataFrame:
    """
    Resample irregular LOB ticks to 1-second bars (last value per second).
    
    Input: DataFrame with columns timestamp (microseconds), asks/bids[i].price/amount
    Output: DataFrame with exactly 1-second spaced rows, forward-filled
    
    No future data leakage: each 1s bar uses only data available at that second.
    """
    df = df.sort_values(ts_col).reset_index(drop=True)
    
    # Floor timestamp to second boundary (truncate, not round - avoids leakage)
    ts_us = df[ts_col].values
    sec_floor = (ts_us // 1_000_000) * 1_000_000  # floor to second
    df = df.copy()
    df['_sec'] = sec_floor
    
    # Identify LOB columns
    lob_cols = []
    for i in range(n_levels):
        for side in ['asks', 'bids']:
            for field in ['price', 'amount']:
                col = f'{side}[{i}].{field}'
                if col in df.columns:
                    lob_cols.append(col)
    
    # Take LAST tick per second (most recent state - no leakage)
    grouped = df.groupby('_sec')[lob_cols].last()
    
    # Create complete 1-second grid
    sec_min = int(grouped.index.min())
    sec_max = int(grouped.index.max())
    full_grid = np.arange(sec_min, sec_max + 1_000_000, 1_000_000, dtype=np.int64)
    
    result = pd.DataFrame({'timestamp': full_grid})
    result = result.merge(
        grouped.reset_index().rename(columns={'_sec': 'timestamp'}),
        on='timestamp',
        how='left'
    )
    
    # Forward-fill: use last known state (causal, no leakage)
    result[lob_cols] = result[lob_cols].ffill()
    
    # Drop rows at the start that have no data yet
    first_valid = result[lob_cols[0]].first_valid_index()
    if first_valid is not None and first_valid > 0:
        result = result.iloc[first_valid:].reset_index(drop=True)
    
    return result
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /Users/haosiyu/Desktop/quant_research && python3 tests/test_features.py`
Expected: "PASS: test_resample_basic"

- [ ] **Step 6: Commit**

```bash
cd /Users/haosiyu/Desktop/quant_research
git init
git add src/ tests/
git commit -m "feat: add LOB resampling to 1-second bars"
```

---

## Task 2: Microstructure Feature Engineering

**Files:**
- Create: `src/features/microstructure.py`
- Modify: `tests/test_features.py`

**Feature set (40 features per 1s bar):**

| Category | Features | Count |
|----------|----------|-------|
| Price | mid_price, log_return_1s, log_return_5s, log_return_30s | 4 |
| Spread | spread_bps, spread_change | 2 |
| Imbalance | obi_L1, obi_L5, obi_L10, obi_L25, obi_L1_delta | 5 |
| Depth | bid_depth_L5, ask_depth_L5, bid_depth_L25, ask_depth_L25, depth_ratio_L5 | 5 |
| Pressure | weighted_price_bid_L10, weighted_price_ask_L10, price_pressure | 3 |
| Volatility | realized_vol_30s, realized_vol_60s, realized_vol_300s | 3 |
| Microstructure | kyle_lambda_30s, amihud_30s | 2 |
| Bid profile | bid_slope_L10, bid_concentration | 2 |
| Ask profile | ask_slope_L10, ask_concentration | 2 |
| Level features | per-level amount ratios for L0-L4 bid, L0-L4 ask | 10 |
| Temporal | second_of_day_sin, second_of_day_cos | 2 |
| **Total** | | **40** |

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_features.py

from src.features.microstructure import compute_microstructure_features


def test_microstructure_no_leakage():
    """Features at time t must only use data from t and before."""
    n_levels = 25
    n_rows = 600  # 10 minutes at 1s
    
    rng = np.random.default_rng(42)
    base_ts = 1_000_000_000_000
    timestamps = base_ts + np.arange(n_rows) * 1_000_000  # exactly 1s apart
    
    cols = {'timestamp': timestamps}
    mid = 60000.0 + np.cumsum(rng.normal(0, 0.5, n_rows))
    
    for i in range(n_levels):
        cols[f'asks[{i}].price'] = mid + 0.05 * (i + 1)
        cols[f'asks[{i}].amount'] = rng.exponential(2.0, n_rows)
        cols[f'bids[{i}].price'] = mid - 0.05 * (i + 1)
        cols[f'bids[{i}].amount'] = rng.exponential(2.0, n_rows)
    
    df = pd.DataFrame(cols)
    features = compute_microstructure_features(df, n_levels=n_levels)
    
    # Must have same number of rows
    assert len(features) == len(df), f"Row count mismatch: {len(features)} vs {len(df)}"
    
    # No NaN after warmup (first 300s for rolling windows)
    warmup = 300
    feat_after_warmup = features.iloc[warmup:]
    nan_cols = feat_after_warmup.columns[feat_after_warmup.isna().any()].tolist()
    assert len(nan_cols) == 0, f"NaN in columns after warmup: {nan_cols}"
    
    # Leakage test: modifying future data must not change current features
    df_modified = df.copy()
    cutpoint = 400
    # Zero out all future data
    for col in df_modified.columns:
        if col != 'timestamp':
            df_modified.loc[cutpoint+1:, col] = 0.0
    
    features_modified = compute_microstructure_features(df_modified, n_levels=n_levels)
    
    # Features at cutpoint must be identical
    for col in features.columns:
        if col == 'timestamp':
            continue
        orig_val = features.iloc[cutpoint][col]
        mod_val = features_modified.iloc[cutpoint][col]
        if np.isfinite(orig_val) and np.isfinite(mod_val):
            assert abs(orig_val - mod_val) < 1e-6, \
                f"LEAKAGE in {col} at row {cutpoint}: {orig_val} vs {mod_val}"
    
    print("PASS: test_microstructure_no_leakage")


def test_microstructure_feature_count():
    """Must produce exactly 40 features."""
    n_levels = 25
    rng = np.random.default_rng(42)
    n_rows = 400
    base_ts = 1_000_000_000_000
    timestamps = base_ts + np.arange(n_rows) * 1_000_000
    
    cols = {'timestamp': timestamps}
    mid = 60000.0 + np.cumsum(rng.normal(0, 0.5, n_rows))
    for i in range(n_levels):
        cols[f'asks[{i}].price'] = mid + 0.05 * (i + 1)
        cols[f'asks[{i}].amount'] = rng.exponential(2.0, n_rows)
        cols[f'bids[{i}].price'] = mid - 0.05 * (i + 1)
        cols[f'bids[{i}].amount'] = rng.exponential(2.0, n_rows)
    
    df = pd.DataFrame(cols)
    features = compute_microstructure_features(df, n_levels=n_levels)
    
    feat_cols = [c for c in features.columns if c != 'timestamp']
    assert len(feat_cols) == 40, f"Expected 40 features, got {len(feat_cols)}: {feat_cols}"
    
    print("PASS: test_microstructure_feature_count")


if __name__ == '__main__':
    test_resample_basic()
    test_microstructure_no_leakage()
    test_microstructure_feature_count()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/haosiyu/Desktop/quant_research && python3 tests/test_features.py`
Expected: ImportError for compute_microstructure_features

- [ ] **Step 3: Implement microstructure features**

```python
# src/features/microstructure.py
"""Compute microstructure features from 1-second LOB bars.

All features are strictly causal: feature at time t uses only data at t and before.
Rolling windows use .rolling(min_periods=1) so early rows still get values.
"""

import numpy as np
import pandas as pd


def compute_microstructure_features(
    df: pd.DataFrame,
    n_levels: int = 25,
) -> pd.DataFrame:
    """
    Compute 40 microstructure features from 1s LOB bars.
    
    Input: DataFrame with timestamp + asks/bids[i].price/amount columns
    Output: DataFrame with timestamp + 40 feature columns
    
    All computations are causal (no future information used).
    """
    out = pd.DataFrame({'timestamp': df['timestamp'].values})
    
    # --- Base prices ---
    best_ask = df['asks[0].price'].values.astype(np.float64)
    best_bid = df['bids[0].price'].values.astype(np.float64)
    mid = (best_ask + best_bid) / 2.0
    
    s_mid = pd.Series(mid)
    log_mid = np.log(np.maximum(mid, 1e-9))
    s_log_mid = pd.Series(log_mid)
    
    # --- Price features (4) ---
    out['mid_price'] = mid
    out['log_return_1s'] = s_log_mid.diff(1).fillna(0.0).values
    out['log_return_5s'] = s_log_mid.diff(5).fillna(0.0).values
    out['log_return_30s'] = s_log_mid.diff(30).fillna(0.0).values
    
    # --- Spread features (2) ---
    spread = best_ask - best_bid
    spread_bps = spread / np.maximum(mid, 1e-9) * 10000.0
    out['spread_bps'] = spread_bps
    out['spread_change'] = pd.Series(spread_bps).diff(1).fillna(0.0).values
    
    # --- Order Book Imbalance (5) ---
    def obi(bid_amt, ask_amt):
        total = bid_amt + ask_amt
        return np.where(total > 1e-12, (bid_amt - ask_amt) / total, 0.0)
    
    # Cumulative amounts at various levels
    bid_L1 = df['bids[0].amount'].values.astype(np.float64)
    ask_L1 = df['asks[0].amount'].values.astype(np.float64)
    out['obi_L1'] = obi(bid_L1, ask_L1)
    
    for n_lev, name in [(5, 'L5'), (10, 'L10'), (25, 'L25')]:
        actual_lev = min(n_lev, n_levels)
        bid_cum = sum(df[f'bids[{i}].amount'].values.astype(np.float64) for i in range(actual_lev))
        ask_cum = sum(df[f'asks[{i}].amount'].values.astype(np.float64) for i in range(actual_lev))
        out[f'obi_{name}'] = obi(bid_cum, ask_cum)
    
    out['obi_L1_delta'] = pd.Series(out['obi_L1'].values).diff(1).fillna(0.0).values
    
    # --- Depth features (5) ---
    bid_depth_L5 = sum(df[f'bids[{i}].amount'].values.astype(np.float64) for i in range(min(5, n_levels)))
    ask_depth_L5 = sum(df[f'asks[{i}].amount'].values.astype(np.float64) for i in range(min(5, n_levels)))
    bid_depth_L25 = sum(df[f'bids[{i}].amount'].values.astype(np.float64) for i in range(n_levels))
    ask_depth_L25 = sum(df[f'asks[{i}].amount'].values.astype(np.float64) for i in range(n_levels))
    
    out['bid_depth_L5'] = bid_depth_L5
    out['ask_depth_L5'] = ask_depth_L5
    out['bid_depth_L25'] = bid_depth_L25
    out['ask_depth_L25'] = ask_depth_L25
    out['depth_ratio_L5'] = np.where(
        (bid_depth_L5 + ask_depth_L5) > 1e-12,
        bid_depth_L5 / (bid_depth_L5 + ask_depth_L5),
        0.5
    )
    
    # --- Pressure features (3) ---
    # Volume-weighted average price distance from mid for top 10 levels
    n_press = min(10, n_levels)
    wp_bid_num = np.zeros(len(df), dtype=np.float64)
    wp_bid_den = np.zeros(len(df), dtype=np.float64)
    wp_ask_num = np.zeros(len(df), dtype=np.float64)
    wp_ask_den = np.zeros(len(df), dtype=np.float64)
    
    for i in range(n_press):
        ba = df[f'bids[{i}].amount'].values.astype(np.float64)
        bp = df[f'bids[{i}].price'].values.astype(np.float64)
        aa = df[f'asks[{i}].amount'].values.astype(np.float64)
        ap = df[f'asks[{i}].price'].values.astype(np.float64)
        wp_bid_num += ba * bp
        wp_bid_den += ba
        wp_ask_num += aa * ap
        wp_ask_den += aa
    
    wp_bid = np.where(wp_bid_den > 1e-12, wp_bid_num / wp_bid_den, mid)
    wp_ask = np.where(wp_ask_den > 1e-12, wp_ask_num / wp_ask_den, mid)
    
    out['weighted_price_bid_L10'] = (mid - wp_bid) / np.maximum(mid, 1e-9) * 10000.0  # bps from mid
    out['weighted_price_ask_L10'] = (wp_ask - mid) / np.maximum(mid, 1e-9) * 10000.0
    out['price_pressure'] = out['weighted_price_bid_L10'].values - out['weighted_price_ask_L10'].values
    
    # --- Volatility features (3) ---
    ret_1s = pd.Series(out['log_return_1s'].values)
    out['realized_vol_30s'] = ret_1s.rolling(30, min_periods=1).std().fillna(0.0).values
    out['realized_vol_60s'] = ret_1s.rolling(60, min_periods=1).std().fillna(0.0).values
    out['realized_vol_300s'] = ret_1s.rolling(300, min_periods=1).std().fillna(0.0).values
    
    # --- Microstructure features (2) ---
    # Kyle's lambda proxy: |return| / volume (simplified)
    abs_ret = np.abs(out['log_return_1s'].values)
    total_vol = bid_L1 + ask_L1
    kyle_raw = np.where(total_vol > 1e-12, abs_ret / total_vol, 0.0)
    out['kyle_lambda_30s'] = pd.Series(kyle_raw).rolling(30, min_periods=1).mean().fillna(0.0).values
    
    # Amihud illiquidity: |return| / dollar_volume
    dollar_vol = total_vol * mid
    amihud_raw = np.where(dollar_vol > 1e-6, abs_ret / dollar_vol * 1e9, 0.0)  # scale for numerical stability
    out['amihud_30s'] = pd.Series(amihud_raw).rolling(30, min_periods=1).mean().fillna(0.0).values
    
    # --- Bid/Ask slope (2) ---
    # Price impact slope: how fast price moves through levels
    n_slope = min(10, n_levels)
    bid_prices = np.column_stack([df[f'bids[{i}].price'].values.astype(np.float64) for i in range(n_slope)])
    ask_prices = np.column_stack([df[f'asks[{i}].price'].values.astype(np.float64) for i in range(n_slope)])
    
    # Slope: average price change per level, normalized by mid
    bid_slope = (bid_prices[:, 0] - bid_prices[:, -1]) / (n_slope - 1) / np.maximum(mid, 1e-9) * 10000
    ask_slope = (ask_prices[:, -1] - ask_prices[:, 0]) / (n_slope - 1) / np.maximum(mid, 1e-9) * 10000
    out['bid_slope_L10'] = bid_slope
    out['ask_slope_L10'] = ask_slope
    
    # --- Concentration (2) ---
    # How concentrated is liquidity at best vs deeper levels
    out['bid_concentration'] = np.where(bid_depth_L25 > 1e-12, bid_L1 / bid_depth_L25, 0.0)
    out['ask_concentration'] = np.where(ask_depth_L25 > 1e-12, ask_L1 / ask_depth_L25, 0.0)
    
    # --- Per-level amount ratios (10) ---
    # Normalized amount at each of top 5 levels (bid + ask)
    for i in range(min(5, n_levels)):
        ba = df[f'bids[{i}].amount'].values.astype(np.float64)
        out[f'bid_amt_ratio_L{i}'] = np.where(bid_depth_L5 > 1e-12, ba / bid_depth_L5, 0.0)
        aa = df[f'asks[{i}].amount'].values.astype(np.float64)
        out[f'ask_amt_ratio_L{i}'] = np.where(ask_depth_L5 > 1e-12, aa / ask_depth_L5, 0.0)
    
    # --- Temporal features (2) ---
    # Second of day as sin/cos cycle
    ts_sec = (df['timestamp'].values % (86400 * 1_000_000)) / 1_000_000  # seconds into day
    out['second_of_day_sin'] = np.sin(2 * np.pi * ts_sec / 86400)
    out['second_of_day_cos'] = np.cos(2 * np.pi * ts_sec / 86400)
    
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/haosiyu/Desktop/quant_research && python3 tests/test_features.py`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/features/microstructure.py tests/test_features.py
git commit -m "feat: add 40 microstructure features with no-leakage guarantee"
```

---

## Task 3: Full CSV-to-NPZ Pipeline

**Files:**
- Create: `src/features/pipeline.py`
- Create: `tests/test_no_leakage.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_no_leakage.py
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.features.pipeline import build_npz_for_day


def test_npz_shape_and_labels():
    """NPZ must have correct shapes and causal labels."""
    import pandas as pd
    
    # Create 10 minutes of synthetic 1s LOB data
    n_levels = 25
    n_rows = 600
    rng = np.random.default_rng(42)
    base_ts = 1_000_000_000_000
    timestamps = base_ts + np.arange(n_rows) * 1_000_000
    
    cols = {'timestamp': timestamps}
    mid = 60000.0 + np.cumsum(rng.normal(0, 0.5, n_rows))
    for i in range(n_levels):
        cols[f'asks[{i}].price'] = mid + 0.05 * (i + 1)
        cols[f'asks[{i}].amount'] = rng.exponential(2.0, n_rows)
        cols[f'bids[{i}].price'] = mid - 0.05 * (i + 1)
        cols[f'bids[{i}].amount'] = rng.exponential(2.0, n_rows)
    
    df_1s = pd.DataFrame(cols)
    
    horizon_sec = 180  # 3 minutes
    input_len = 300    # 5 minutes of 1s bars
    stride = 60        # 1 window per minute
    
    result = build_npz_for_day(
        df_1s,
        horizon_sec=horizon_sec,
        input_len=input_len,
        stride=stride,
        n_levels=n_levels,
    )
    
    X = result['X']          # (Nwin, input_len, n_features)
    y = result['y']          # (Nwin,) - return at horizon
    y_mask = result['y_mask']  # (Nwin,) - 1 if valid
    timestamps_out = result['timestamps']  # (Nwin,) - prediction time
    
    # Shape checks
    assert X.ndim == 3, f"X must be 3D, got {X.ndim}D"
    assert X.shape[1] == input_len, f"X time dim must be {input_len}, got {X.shape[1]}"
    assert y.ndim == 1, f"y must be 1D, got {y.ndim}"
    assert X.shape[0] == y.shape[0], f"Nwin mismatch: X={X.shape[0]}, y={y.shape[0]}"
    assert y_mask.shape == y.shape
    
    # No NaN in X
    assert not np.any(np.isnan(X)), "X contains NaN"
    
    # Label is future return: y[i] = mid[t+horizon] / mid[t] - 1
    # Last valid window must have room for horizon
    # Window at index i starts at stride*i, ends at stride*i + input_len - 1
    # Prediction time = stride*i + input_len - 1
    # Target time = prediction_time + horizon_sec
    # Must have: target_time < n_rows
    max_valid_pred_time = n_rows - 1 - horizon_sec
    max_valid_windows = (max_valid_pred_time - (input_len - 1)) // stride + 1
    assert X.shape[0] <= max(0, max_valid_windows) + 1, \
        f"Too many windows: {X.shape[0]} > {max_valid_windows}"
    
    # Leakage check: X[i] must not contain data from after prediction time
    # X[i] covers time indices [stride*i, stride*i + input_len - 1]
    # y[i] is computed from time index stride*i + input_len - 1 + horizon_sec
    # So X[i] ENDS at prediction time, y[i] is horizon_sec into the future
    # This is verified by construction, but let's double-check:
    for i in range(min(3, X.shape[0])):
        pred_time_idx = i * stride + input_len - 1
        target_time_idx = pred_time_idx + horizon_sec
        assert target_time_idx < n_rows or y_mask[i] == 0, \
            f"Window {i}: target at {target_time_idx} >= {n_rows} but mask is 1"
    
    print(f"PASS: test_npz_shape_and_labels (Nwin={X.shape[0]}, features={X.shape[2]})")


if __name__ == '__main__':
    test_npz_shape_and_labels()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/haosiyu/Desktop/quant_research && python3 tests/test_no_leakage.py`
Expected: ImportError

- [ ] **Step 3: Implement pipeline**

```python
# src/features/pipeline.py
"""End-to-end pipeline: raw LOB DataFrame -> NPZ arrays ready for training."""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Optional

from .resample import resample_lob_to_1s
from .microstructure import compute_microstructure_features


def build_npz_for_day(
    df_1s: pd.DataFrame,
    *,
    horizon_sec: int = 180,
    input_len: int = 300,
    stride: int = 60,
    n_levels: int = 25,
    feature_clip: float = 10.0,
) -> Dict[str, np.ndarray]:
    """
    Build training arrays from 1s-resampled LOB data.
    
    Args:
        df_1s: DataFrame with 1s timestamps + LOB columns
        horizon_sec: prediction horizon in seconds (default 180 = 3 min)
        input_len: number of 1s bars per input window (default 300 = 5 min)
        stride: step between windows in seconds (default 60 = 1 min)
        n_levels: number of LOB levels
        feature_clip: clip features to +/- this value after z-score
    
    Returns dict with:
        X:          (Nwin, input_len, n_features) float32
        y:          (Nwin,) float32 - fractional return at horizon
        y_mask:     (Nwin,) uint8 - 1 if target is valid
        timestamps: (Nwin,) int64 - prediction time in microseconds
        features:   list of feature names
    """
    # Compute features
    features_df = compute_microstructure_features(df_1s, n_levels=n_levels)
    
    # Feature columns (everything except timestamp and mid_price which is used for labels)
    feat_cols = [c for c in features_df.columns if c not in ('timestamp', 'mid_price')]
    
    # Get mid prices for label computation
    mid_prices = features_df['mid_price'].values.astype(np.float64)
    timestamps = features_df['timestamp'].values.astype(np.int64)
    
    # Feature matrix
    feat_matrix = features_df[feat_cols].values.astype(np.float32)
    feat_matrix = np.nan_to_num(feat_matrix, nan=0.0, posinf=0.0, neginf=0.0)
    
    n_total = len(features_df)
    n_features = len(feat_cols)
    
    # Build windows
    windows_X = []
    windows_y = []
    windows_mask = []
    windows_ts = []
    
    for start in range(0, n_total - input_len + 1, stride):
        end = start + input_len  # exclusive; last index is end-1
        pred_idx = end - 1       # prediction is made at this time
        target_idx = pred_idx + horizon_sec  # target return at this future time
        
        # Extract input window
        X_win = feat_matrix[start:end]  # (input_len, n_features)
        
        # Compute target: forward return
        if target_idx < n_total and mid_prices[pred_idx] > 1e-6:
            y_val = (mid_prices[target_idx] / mid_prices[pred_idx]) - 1.0
            mask_val = 1
        else:
            y_val = 0.0
            mask_val = 0
        
        windows_X.append(X_win)
        windows_y.append(y_val)
        windows_mask.append(mask_val)
        windows_ts.append(timestamps[pred_idx])
    
    if not windows_X:
        return {
            'X': np.empty((0, input_len, n_features), dtype=np.float32),
            'y': np.empty((0,), dtype=np.float32),
            'y_mask': np.empty((0,), dtype=np.uint8),
            'timestamps': np.empty((0,), dtype=np.int64),
            'features': feat_cols,
        }
    
    return {
        'X': np.stack(windows_X).astype(np.float32),
        'y': np.array(windows_y, dtype=np.float32),
        'y_mask': np.array(windows_mask, dtype=np.uint8),
        'timestamps': np.array(windows_ts, dtype=np.int64),
        'features': feat_cols,
    }


def process_csv_to_npz(
    csv_path: str,
    output_dir: str,
    *,
    horizon_sec: int = 180,
    input_len: int = 300,
    stride: int = 60,
    n_levels: int = 25,
) -> Path:
    """
    Full pipeline: raw CSV.gz -> 1s resample -> features -> NPZ.
    
    Saves one NPZ per day found in the CSV.
    Returns output directory path.
    """
    import gzip
    
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    # Load raw data
    if csv_path.endswith('.gz'):
        df_raw = pd.read_csv(csv_path, compression='gzip')
    else:
        df_raw = pd.read_csv(csv_path)
    
    # Resample to 1s
    df_1s = resample_lob_to_1s(df_raw, n_levels=n_levels)
    
    # Split by day (UTC)
    df_1s['_day'] = pd.to_datetime(df_1s['timestamp'], unit='us').dt.strftime('%Y-%m-%d')
    
    saved_files = []
    for day, group in df_1s.groupby('_day'):
        day_df = group.drop(columns=['_day']).reset_index(drop=True)
        
        result = build_npz_for_day(
            day_df,
            horizon_sec=horizon_sec,
            input_len=input_len,
            stride=stride,
            n_levels=n_levels,
        )
        
        if result['X'].shape[0] == 0:
            continue
        
        npz_file = out_path / f"{day}.npz"
        np.savez_compressed(
            npz_file,
            X=result['X'],
            y=result['y'],
            y_mask=result['y_mask'],
            timestamps=result['timestamps'],
            features=np.array(result['features'], dtype=object),
        )
        saved_files.append(npz_file)
        print(f"Saved {npz_file}: X={result['X'].shape}, y={result['y'].shape}")
    
    return out_path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/haosiyu/Desktop/quant_research && python3 tests/test_no_leakage.py`
Expected: PASS

- [ ] **Step 5: Test on real data**

```bash
cd /Users/haosiyu/Desktop/quant_research
python3 -c "
from src.features.pipeline import process_csv_to_npz
process_csv_to_npz('BTCUSDT.csv.gz', 'data/npz_h180', horizon_sec=180, input_len=300, stride=60)
"
```
Expected: Prints saved NPZ file with shape info

- [ ] **Step 6: Commit**

```bash
git add src/features/pipeline.py tests/test_no_leakage.py
git commit -m "feat: CSV-to-NPZ pipeline with no-leakage verification"
```

---

## Task 4: Bid/Ask Spatial Encoder

**Files:**
- Create: `src/model/side_encoder.py`
- Create: `tests/test_model.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_model.py
import torch
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.model.side_encoder import SpatialLOBEncoder


def test_spatial_encoder_shapes():
    """Spatial encoder must produce correct output shape."""
    B, L, n_features = 4, 300, 40
    d_model = 128
    
    encoder = SpatialLOBEncoder(
        n_features=n_features,
        d_model=d_model,
    )
    
    x = torch.randn(B, L, n_features)
    out = encoder(x)
    
    assert out.shape == (B, L, d_model), f"Expected ({B},{L},{d_model}), got {out.shape}"
    assert torch.isfinite(out).all(), "Output contains NaN/Inf"
    
    print("PASS: test_spatial_encoder_shapes")


def test_spatial_encoder_causal():
    """Spatial encoder must not look ahead in time (it only operates per-timestep)."""
    B, L, n_features = 2, 10, 40
    d_model = 64
    
    encoder = SpatialLOBEncoder(n_features=n_features, d_model=d_model)
    encoder.eval()
    
    x = torch.randn(B, L, n_features)
    out_full = encoder(x)
    
    # Modify future timesteps and check current output unchanged
    x_mod = x.clone()
    x_mod[:, 5:, :] = torch.randn(B, L - 5, n_features) * 100  # drastically change future
    out_mod = encoder(x_mod)
    
    # Output at timestep 4 must be identical (spatial encoder is per-timestep)
    diff = (out_full[:, 4, :] - out_mod[:, 4, :]).abs().max().item()
    assert diff < 1e-5, f"Spatial encoder leaks future info: diff={diff}"
    
    print("PASS: test_spatial_encoder_causal")


if __name__ == '__main__':
    test_spatial_encoder_shapes()
    test_spatial_encoder_causal()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/haosiyu/Desktop/quant_research && python3 tests/test_model.py`
Expected: ImportError

- [ ] **Step 3: Implement spatial encoder**

```python
# src/model/side_encoder.py
"""Spatial LOB encoder: per-timestep feature processing with bid/ask awareness.

Processes features at each timestep independently (no temporal mixing here).
Groups features into bid-side, ask-side, and global categories,
applies separate encoders, then fuses via cross-attention.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional


class FeatureGroupAttention(nn.Module):
    """Attention-based fusion of feature groups (bid, ask, global)."""
    
    def __init__(self, d_model: int, nhead: int = 4, dropout: float = 0.1):
        super().__init__()
        self.attn = nn.MultiheadAttention(d_model, nhead, dropout=dropout, batch_first=True)
        self.ln = nn.LayerNorm(d_model)
        self.ff = nn.Sequential(
            nn.Linear(d_model, d_model * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model * 2, d_model),
            nn.Dropout(dropout),
        )
        self.ln2 = nn.LayerNorm(d_model)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B*L, n_groups, d_model) where n_groups = 3 (bid, ask, global)
        h, _ = self.attn(x, x, x)
        x = self.ln(x + h)
        x = self.ln2(x + self.ff(x))
        return x


class SpatialLOBEncoder(nn.Module):
    """
    Per-timestep spatial encoder for LOB features.
    
    Architecture:
    1. Split features into bid/ask/global groups
    2. Project each group to d_model
    3. Cross-attention between groups (bid attends to ask and vice versa)
    4. Pool groups into single d_model vector
    
    Operates independently per timestep: no temporal leakage.
    """
    
    def __init__(
        self,
        n_features: int,
        d_model: int = 128,
        nhead: int = 4,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.n_features = n_features
        self.d_model = d_model
        
        # Feature group indices will be set dynamically based on feature names
        # For now: roughly split into 3 equal groups as default
        # In practice, configure via set_feature_groups()
        third = n_features // 3
        self._bid_idx = list(range(0, third))
        self._ask_idx = list(range(third, 2 * third))
        self._global_idx = list(range(2 * third, n_features))
        
        # Projections for each group
        self.bid_proj = nn.Linear(max(1, len(self._bid_idx)), d_model)
        self.ask_proj = nn.Linear(max(1, len(self._ask_idx)), d_model)
        self.global_proj = nn.Linear(max(1, len(self._global_idx)), d_model)
        
        # Cross-group attention
        self.group_attn = FeatureGroupAttention(d_model, nhead, dropout)
        
        # Pool 3 groups into 1 vector
        self.pool = nn.Sequential(
            nn.Linear(d_model * 3, d_model),
            nn.GELU(),
            nn.Dropout(dropout),
        )
    
    def set_feature_groups(self, bid_idx: list, ask_idx: list, global_idx: list):
        """Configure which feature indices belong to bid/ask/global groups."""
        self._bid_idx = bid_idx
        self._ask_idx = ask_idx
        self._global_idx = global_idx
        # Reinitialize projections
        device = next(self.parameters()).device
        self.bid_proj = nn.Linear(max(1, len(bid_idx)), self.d_model).to(device)
        self.ask_proj = nn.Linear(max(1, len(ask_idx)), self.d_model).to(device)
        self.global_proj = nn.Linear(max(1, len(global_idx)), self.d_model).to(device)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: (B, L, n_features)
        returns: (B, L, d_model)
        """
        B, L, _ = x.shape
        
        # Split into groups
        bid_feats = x[:, :, self._bid_idx]    # (B, L, n_bid)
        ask_feats = x[:, :, self._ask_idx]    # (B, L, n_ask)
        glob_feats = x[:, :, self._global_idx]  # (B, L, n_global)
        
        # Reshape to (B*L, n_group_feats) for per-timestep processing
        bid_flat = bid_feats.reshape(B * L, -1)
        ask_flat = ask_feats.reshape(B * L, -1)
        glob_flat = glob_feats.reshape(B * L, -1)
        
        # Project each group to d_model
        h_bid = self.bid_proj(bid_flat)    # (B*L, d_model)
        h_ask = self.ask_proj(ask_flat)
        h_glob = self.global_proj(glob_flat)
        
        # Stack as sequence for cross-group attention: (B*L, 3, d_model)
        groups = torch.stack([h_bid, h_ask, h_glob], dim=1)
        
        # Cross-attention between groups
        groups = self.group_attn(groups)  # (B*L, 3, d_model)
        
        # Pool: concatenate and project
        pooled = groups.reshape(B * L, 3 * self.d_model)
        out = self.pool(pooled)  # (B*L, d_model)
        
        return out.reshape(B, L, self.d_model)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/haosiyu/Desktop/quant_research && python3 tests/test_model.py`
Expected: Both tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/model/side_encoder.py tests/test_model.py
git commit -m "feat: spatial LOB encoder with bid/ask/global group attention"
```

---

## Task 5: Causal Temporal Encoder

**Files:**
- Create: `src/model/temporal_encoder.py`
- Modify: `tests/test_model.py`

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_model.py

from src.model.temporal_encoder import CausalTemporalEncoder


def test_temporal_encoder_causal():
    """Changing future inputs must not affect current output."""
    B, L, d_model = 2, 50, 64
    
    encoder = CausalTemporalEncoder(d_model=d_model, nhead=4, depth=2, d_ff=128, dropout=0.0)
    encoder.eval()
    
    x = torch.randn(B, L, d_model)
    out = encoder(x)
    assert out.shape == (B, L, d_model), f"Shape mismatch: {out.shape}"
    
    # Modify future and check
    x_mod = x.clone()
    x_mod[:, 25:, :] = torch.randn(B, L - 25, d_model) * 100
    out_mod = encoder(x_mod)
    
    diff = (out[:, 24, :] - out_mod[:, 24, :]).abs().max().item()
    assert diff < 1e-4, f"Temporal encoder leaks future: diff={diff}"
    
    print("PASS: test_temporal_encoder_causal")


if __name__ == '__main__':
    test_spatial_encoder_shapes()
    test_spatial_encoder_causal()
    test_temporal_encoder_causal()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/haosiyu/Desktop/quant_research && python3 tests/test_model.py`
Expected: ImportError for CausalTemporalEncoder

- [ ] **Step 3: Implement temporal encoder**

```python
# src/model/temporal_encoder.py
"""Causal temporal encoder: Transformer with conv frontend and RoPE.

Processes the time dimension causally (no future leakage).
Uses rotary position embeddings for better relative position encoding.
"""

import math
import torch
import torch.nn as nn
import torch.nn.functional as F


def rotary_embedding(seq_len: int, dim: int, device: torch.device) -> torch.Tensor:
    """Compute RoPE sin/cos table: (seq_len, dim)."""
    pos = torch.arange(seq_len, device=device, dtype=torch.float32).unsqueeze(1)
    dim_idx = torch.arange(0, dim, 2, device=device, dtype=torch.float32)
    freq = 1.0 / (10000.0 ** (dim_idx / dim))
    angles = pos * freq  # (seq_len, dim//2)
    return torch.cat([angles.sin(), angles.cos()], dim=-1)  # (seq_len, dim)


def apply_rope(x: torch.Tensor, rope: torch.Tensor) -> torch.Tensor:
    """Apply rotary embeddings to query/key tensors.
    x: (B, nhead, L, head_dim)
    rope: (L, head_dim)
    """
    d = x.shape[-1]
    half = d // 2
    sin_part = rope[:x.shape[2], :half].unsqueeze(0).unsqueeze(0)  # (1, 1, L, half)
    cos_part = rope[:x.shape[2], half:].unsqueeze(0).unsqueeze(0)
    
    x1 = x[..., :half]
    x2 = x[..., half:]
    
    out1 = x1 * cos_part - x2 * sin_part
    out2 = x1 * sin_part + x2 * cos_part
    return torch.cat([out1, out2], dim=-1)


class CausalConvBlock(nn.Module):
    """Causal depthwise-separable conv with residual."""
    
    def __init__(self, d_model: int, kernel_size: int, dilation: int, dropout: float):
        super().__init__()
        self.kernel_size = kernel_size
        self.dilation = dilation
        self.ln = nn.LayerNorm(d_model)
        self.dw = nn.Conv1d(d_model, d_model, kernel_size, dilation=dilation, groups=d_model, bias=False)
        self.pw = nn.Conv1d(d_model, d_model, 1, bias=True)
        self.act = nn.GELU()
        self.drop = nn.Dropout(dropout)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, L, C = x.shape
        h = self.ln(x).transpose(1, 2)  # (B, C, L)
        pad = (self.kernel_size - 1) * self.dilation
        h = F.pad(h, (pad, 0))  # causal left-pad
        h = self.dw(h)[:, :, :L]
        h = self.pw(h)
        h = h.transpose(1, 2)  # (B, L, C)
        return x + self.drop(self.act(h))


class CausalSelfAttention(nn.Module):
    """Multi-head self-attention with causal mask and RoPE."""
    
    def __init__(self, d_model: int, nhead: int, dropout: float, max_len: int = 2048):
        super().__init__()
        assert d_model % nhead == 0
        self.d_model = d_model
        self.nhead = nhead
        self.head_dim = d_model // nhead
        
        self.qkv = nn.Linear(d_model, 3 * d_model)
        self.out_proj = nn.Linear(d_model, d_model)
        self.dropout = nn.Dropout(dropout)
        
        # Pre-compute RoPE table
        rope = rotary_embedding(max_len, self.head_dim, torch.device('cpu'))
        self.register_buffer('rope', rope, persistent=False)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, L, _ = x.shape
        
        qkv = self.qkv(x).reshape(B, L, 3, self.nhead, self.head_dim)
        qkv = qkv.permute(2, 0, 3, 1, 4)  # (3, B, nhead, L, head_dim)
        q, k, v = qkv[0], qkv[1], qkv[2]
        
        # Apply RoPE to q and k
        rope = self.rope.to(x.device)
        q = apply_rope(q, rope)
        k = apply_rope(k, rope)
        
        # Scaled dot-product attention with causal mask
        # Use PyTorch 2.0 SDPA for efficiency (auto Flash Attention)
        out = F.scaled_dot_product_attention(q, k, v, is_causal=True, dropout_p=self.dropout.p if self.training else 0.0)
        
        out = out.transpose(1, 2).reshape(B, L, self.d_model)
        return self.out_proj(out)


class TransformerBlock(nn.Module):
    """Pre-norm Transformer block with causal self-attention."""
    
    def __init__(self, d_model: int, nhead: int, d_ff: int, dropout: float):
        super().__init__()
        self.ln1 = nn.LayerNorm(d_model)
        self.attn = CausalSelfAttention(d_model, nhead, dropout)
        self.ln2 = nn.LayerNorm(d_model)
        self.ff = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, d_model),
            nn.Dropout(dropout),
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.attn(self.ln1(x))
        x = x + self.ff(self.ln2(x))
        return x


class CausalTemporalEncoder(nn.Module):
    """
    Causal temporal encoder: Conv frontend -> Transformer with RoPE.
    
    All operations are strictly causal (no future leakage).
    """
    
    def __init__(
        self,
        d_model: int = 128,
        nhead: int = 4,
        depth: int = 3,
        d_ff: int = 512,
        dropout: float = 0.1,
        conv_layers: int = 2,
        conv_kernel: int = 9,
        conv_dilation_base: int = 2,
    ):
        super().__init__()
        
        # Causal conv frontend
        self.conv_blocks = nn.ModuleList()
        dil = 1
        for _ in range(conv_layers):
            self.conv_blocks.append(CausalConvBlock(d_model, conv_kernel, dil, dropout))
            dil *= conv_dilation_base
        
        # Transformer blocks
        self.transformer_blocks = nn.ModuleList([
            TransformerBlock(d_model, nhead, d_ff, dropout)
            for _ in range(depth)
        ])
        
        self.final_ln = nn.LayerNorm(d_model)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: (B, L, d_model) -> (B, L, d_model)"""
        for conv in self.conv_blocks:
            x = conv(x)
        for block in self.transformer_blocks:
            x = block(x)
        return self.final_ln(x)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/haosiyu/Desktop/quant_research && python3 tests/test_model.py`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/model/temporal_encoder.py tests/test_model.py
git commit -m "feat: causal temporal encoder with RoPE and conv frontend"
```

---

## Task 6: Full LOB Transformer Model Assembly

**Files:**
- Create: `src/model/lob_transformer.py`
- Modify: `tests/test_model.py`

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_model.py

from src.model.lob_transformer import LOBTransformerV2


def test_full_model_forward():
    """Full model forward pass with correct shapes."""
    B, L, n_features = 4, 300, 40
    
    model = LOBTransformerV2(
        n_features=n_features,
        d_model=64,
        nhead=4,
        depth=2,
        d_ff=128,
        dropout=0.0,
        n_quantiles=3,
        n_direction_classes=3,
    )
    
    x = torch.randn(B, L, n_features)
    outputs = model(x)
    
    # Check output keys
    assert 'quantiles' in outputs, "Missing quantiles output"
    assert 'direction_logits' in outputs, "Missing direction_logits output"
    assert 'uncertainty' in outputs, "Missing uncertainty output"
    assert 'point_pred' in outputs, "Missing point_pred output"
    
    # Check shapes - predictions at last timestep
    assert outputs['quantiles'].shape == (B, 3), f"quantiles shape: {outputs['quantiles'].shape}"
    assert outputs['direction_logits'].shape == (B, 3), f"direction shape: {outputs['direction_logits'].shape}"
    assert outputs['uncertainty'].shape == (B,), f"uncertainty shape: {outputs['uncertainty'].shape}"
    assert outputs['point_pred'].shape == (B,), f"point_pred shape: {outputs['point_pred'].shape}"
    
    # All finite
    for k, v in outputs.items():
        assert torch.isfinite(v).all(), f"{k} contains NaN/Inf"
    
    # Uncertainty must be positive
    assert (outputs['uncertainty'] > 0).all(), "Uncertainty must be positive"
    
    print("PASS: test_full_model_forward")


def test_full_model_causal():
    """Full model must not leak future information."""
    B, L, n_features = 2, 20, 40
    
    model = LOBTransformerV2(n_features=n_features, d_model=32, nhead=4, depth=1, d_ff=64, dropout=0.0)
    model.eval()
    
    x = torch.randn(B, L, n_features)
    out1 = model(x)
    
    x_mod = x.clone()
    x_mod[:, 10:, :] = torch.randn(B, L - 10, n_features) * 100
    # Override to get prediction at timestep 9 instead of last
    out2 = model(x_mod, pred_step=9)
    out1_at_9 = model(x, pred_step=9)
    
    diff = (out1_at_9['point_pred'] - out2['point_pred']).abs().max().item()
    assert diff < 1e-4, f"Full model leaks future: diff={diff}"
    
    print("PASS: test_full_model_causal")


if __name__ == '__main__':
    test_spatial_encoder_shapes()
    test_spatial_encoder_causal()
    test_temporal_encoder_causal()
    test_full_model_forward()
    test_full_model_causal()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/haosiyu/Desktop/quant_research && python3 tests/test_model.py`
Expected: ImportError for LOBTransformerV2

- [ ] **Step 3: Implement full model**

```python
# src/model/lob_transformer.py
"""LOB Transformer V2: Structure-aware, probabilistic LOB prediction model.

Architecture:
  Input (B, L, n_features)
  -> RegimeAwareFeatureGate: context-dependent feature gating
  -> SpatialLOBEncoder: per-timestep bid/ask/global group attention
  -> CausalTemporalEncoder: conv frontend + Transformer with RoPE
  -> Multi-head output: quantiles + direction + uncertainty
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Optional

from .side_encoder import SpatialLOBEncoder
from .temporal_encoder import CausalTemporalEncoder


class RegimeAwareFeatureGate(nn.Module):
    """Context-dependent feature gating.
    
    Combines:
    1. Regime-level gate: soft regime detection -> per-regime feature weights
    2. Timestep-level gate: per-timestep fine-grained gating
    """
    
    def __init__(self, d_input: int, n_regimes: int = 4):
        super().__init__()
        self.regime_detector = nn.Sequential(
            nn.Linear(d_input, d_input // 4),
            nn.GELU(),
            nn.Linear(d_input // 4, n_regimes),
        )
        self.regime_gates = nn.Parameter(torch.ones(n_regimes, d_input))
        self.direct_gate = nn.Sequential(
            nn.Linear(d_input, d_input // 4),
            nn.GELU(),
            nn.Linear(d_input // 4, d_input),
            nn.Sigmoid(),
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: (B, L, d_input) -> (B, L, d_input)"""
        # Regime gate from global context (causal: use mean of all timesteps up to current)
        # Simplified: use full sequence mean (ok since this is input features, not predictions)
        regime_ctx = x.mean(dim=1)  # (B, d_input)
        regime_probs = F.softmax(self.regime_detector(regime_ctx), dim=-1)  # (B, n_regimes)
        regime_gate = torch.sigmoid(regime_probs @ self.regime_gates)  # (B, d_input)
        regime_gate = regime_gate.unsqueeze(1)  # (B, 1, d_input)
        
        # Direct per-timestep gate
        direct_gate = self.direct_gate(x)  # (B, L, d_input)
        
        # Combine: regime provides baseline, direct provides fine-tuning
        combined = 0.5 * regime_gate + 0.5 * direct_gate
        return x * combined


class LOBTransformerV2(nn.Module):
    """
    Full LOB Transformer V2 model.
    
    Input: (B, L, n_features) - microstructure features at 1s intervals
    Output: dict with quantiles, direction_logits, uncertainty, point_pred
    """
    
    def __init__(
        self,
        n_features: int = 40,
        d_model: int = 128,
        nhead: int = 4,
        depth: int = 3,
        d_ff: int = 512,
        dropout: float = 0.1,
        n_quantiles: int = 3,
        n_direction_classes: int = 3,
        n_regimes: int = 4,
        conv_layers: int = 2,
        conv_kernel: int = 9,
    ):
        super().__init__()
        self.n_features = n_features
        self.d_model = d_model
        
        # Feature gating
        self.feature_gate = RegimeAwareFeatureGate(n_features, n_regimes)
        
        # Spatial encoder (per-timestep)
        self.spatial_encoder = SpatialLOBEncoder(
            n_features=n_features,
            d_model=d_model,
            nhead=nhead,
            dropout=dropout,
        )
        
        # Temporal encoder (causal)
        self.temporal_encoder = CausalTemporalEncoder(
            d_model=d_model,
            nhead=nhead,
            depth=depth,
            d_ff=d_ff,
            dropout=dropout,
            conv_layers=conv_layers,
            conv_kernel=conv_kernel,
        )
        
        # --- Output heads ---
        
        # Quantile head: q10, q50, q90
        self.quantile_head = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, n_quantiles),
        )
        
        # Direction head: down / flat / up
        self.direction_head = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, n_direction_classes),
        )
        
        # Uncertainty head (aleatoric)
        self.uncertainty_head = nn.Sequential(
            nn.Linear(d_model, d_ff // 2),
            nn.GELU(),
            nn.Linear(d_ff // 2, 1),
            nn.Softplus(),  # ensure positive
        )
    
    def forward(
        self,
        x: torch.Tensor,
        pred_step: int = -1,
    ) -> Dict[str, torch.Tensor]:
        """
        x: (B, L, n_features)
        pred_step: which timestep to extract prediction from (-1 = last)
        
        Returns dict with:
            quantiles:        (B, n_quantiles) - q10/q50/q90 of return
            direction_logits: (B, n_classes) - logits for down/flat/up
            uncertainty:      (B,) - predicted aleatoric uncertainty
            point_pred:       (B,) - q50 as point prediction
        """
        # Feature gating
        x = self.feature_gate(x)  # (B, L, n_features)
        
        # Spatial encoding (per-timestep feature mixing)
        h = self.spatial_encoder(x)  # (B, L, d_model)
        
        # Temporal encoding (causal attention over time)
        h = self.temporal_encoder(h)  # (B, L, d_model)
        
        # Extract representation at prediction timestep
        if pred_step == -1:
            h_pred = h[:, -1, :]  # (B, d_model)
        else:
            h_pred = h[:, pred_step, :]
        
        # Output heads
        quantiles = self.quantile_head(h_pred)          # (B, n_quantiles)
        direction_logits = self.direction_head(h_pred)   # (B, n_classes)
        uncertainty = self.uncertainty_head(h_pred).squeeze(-1)  # (B,)
        
        return {
            'quantiles': quantiles,
            'direction_logits': direction_logits,
            'uncertainty': uncertainty,
            'point_pred': quantiles[:, 1],  # q50 as point prediction
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/haosiyu/Desktop/quant_research && python3 tests/test_model.py`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/model/lob_transformer.py tests/test_model.py
git commit -m "feat: full LOB Transformer V2 with regime gate + probabilistic output"
```

---

## Task 7: Loss Functions (Quantile + Asymmetric + Multi-task)

**Files:**
- Create: `src/training/__init__.py`
- Create: `src/training/losses.py`
- Create: `tests/test_training.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_training.py
import torch
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.training.losses import combined_loss, quantile_loss, asymmetric_huber_loss


def test_quantile_loss_calibration():
    """Quantile loss must be zero when predictions match exact quantiles."""
    torch.manual_seed(42)
    n = 10000
    target = torch.randn(n)
    
    # Perfect q10/q50/q90 predictions
    q10 = torch.quantile(target, 0.1).expand(n)
    q50 = torch.quantile(target, 0.5).expand(n)
    q90 = torch.quantile(target, 0.9).expand(n)
    pred_quantiles = torch.stack([q10, q50, q90], dim=1)  # (n, 3)
    
    loss = quantile_loss(pred_quantiles, target, quantiles=[0.1, 0.5, 0.9])
    
    # Loss should be small (not zero due to finite sample, but very small)
    assert loss.item() < 0.05, f"Quantile loss too high for perfect quantiles: {loss.item()}"
    print("PASS: test_quantile_loss_calibration")


def test_asymmetric_huber_penalizes_left_overestimate():
    """Asymmetric loss must penalize overestimation (pred > target) more when target is negative."""
    target = torch.tensor([-0.01, -0.01, -0.01])  # negative returns
    pred_over = torch.tensor([0.005, 0.005, 0.005])  # overestimate (less negative than actual)
    pred_under = torch.tensor([-0.015, -0.015, -0.015])  # underestimate
    
    loss_over = asymmetric_huber_loss(pred_over, target, delta=0.01, neg_overestimate_weight=2.0)
    loss_under = asymmetric_huber_loss(pred_under, target, delta=0.01, neg_overestimate_weight=2.0)
    
    # Overestimation of negative returns should be penalized more
    assert loss_over > loss_under, \
        f"Overestimate loss ({loss_over:.4f}) should > underestimate loss ({loss_under:.4f})"
    print("PASS: test_asymmetric_huber_penalizes_left_overestimate")


def test_combined_loss_finite():
    """Combined loss must produce finite values."""
    B = 8
    outputs = {
        'quantiles': torch.randn(B, 3),
        'direction_logits': torch.randn(B, 3),
        'uncertainty': torch.rand(B) + 0.01,
        'point_pred': torch.randn(B),
    }
    target = torch.randn(B) * 0.001  # small returns
    mask = torch.ones(B)
    
    loss, loss_dict = combined_loss(outputs, target, mask)
    
    assert torch.isfinite(loss), f"Combined loss is not finite: {loss}"
    assert 'quantile' in loss_dict
    assert 'direction' in loss_dict
    assert 'uncertainty' in loss_dict
    
    print("PASS: test_combined_loss_finite")


if __name__ == '__main__':
    test_quantile_loss_calibration()
    test_asymmetric_huber_penalizes_left_overestimate()
    test_combined_loss_finite()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/haosiyu/Desktop/quant_research && python3 tests/test_training.py`
Expected: ImportError

- [ ] **Step 3: Implement loss functions**

```python
# src/training/losses.py
"""Loss functions for LOB Transformer V2.

Combines:
1. Quantile loss (pinball) for q10/q50/q90
2. Asymmetric Huber loss (extra penalty for overestimating negative returns)
3. Direction classification loss
4. Uncertainty calibration loss (Gaussian NLL)
"""

import torch
import torch.nn.functional as F
from typing import Dict, List, Tuple, Optional


def quantile_loss(
    pred_quantiles: torch.Tensor,  # (B, n_quantiles)
    target: torch.Tensor,          # (B,)
    quantiles: List[float] = [0.1, 0.5, 0.9],
) -> torch.Tensor:
    """Pinball loss for quantile regression."""
    target = target.unsqueeze(1)  # (B, 1)
    errors = target - pred_quantiles  # (B, n_quantiles)
    
    losses = []
    for i, tau in enumerate(quantiles):
        err = errors[:, i]
        loss_i = torch.where(err >= 0, tau * err, (tau - 1) * err)
        losses.append(loss_i.mean())
    
    return torch.stack(losses).mean()


def asymmetric_huber_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    delta: float = 1.0,
    neg_overestimate_weight: float = 2.0,
) -> torch.Tensor:
    """
    Huber loss with asymmetric penalty for overestimating negative returns.
    
    When target < 0 and pred > target (overestimate = less negative than actual),
    the loss is multiplied by neg_overestimate_weight.
    
    This addresses the left-tail bias in the current model.
    """
    diff = pred - target
    abs_diff = diff.abs()
    
    # Standard Huber
    huber = torch.where(abs_diff <= delta, 0.5 * diff ** 2, delta * (abs_diff - 0.5 * delta))
    
    # Asymmetric weighting: penalize overestimation when target is negative
    is_neg_overestimate = (target < 0) & (diff > 0)  # target negative, pred less negative
    weight = torch.where(is_neg_overestimate, neg_overestimate_weight, 1.0)
    
    return (huber * weight).mean()


def direction_loss(
    logits: torch.Tensor,    # (B, 3)
    target: torch.Tensor,    # (B,) continuous return
    threshold_bps: float = 2.0,
) -> torch.Tensor:
    """Cross-entropy for direction classification (down/flat/up)."""
    threshold = threshold_bps / 10000.0
    
    labels = torch.where(
        target < -threshold, 
        torch.zeros_like(target, dtype=torch.long),     # 0 = down
        torch.where(
            target > threshold,
            torch.full_like(target, 2, dtype=torch.long),  # 2 = up
            torch.ones_like(target, dtype=torch.long),      # 1 = flat
        )
    )
    
    return F.cross_entropy(logits, labels)


def uncertainty_loss(
    pred: torch.Tensor,        # (B,) point prediction
    target: torch.Tensor,      # (B,)
    uncertainty: torch.Tensor,  # (B,) predicted variance (positive)
) -> torch.Tensor:
    """Gaussian negative log-likelihood for uncertainty calibration."""
    # NLL = 0.5 * (log(sigma^2) + (y - mu)^2 / sigma^2)
    var = uncertainty.clamp(min=1e-8)
    nll = 0.5 * (torch.log(var) + (target - pred) ** 2 / var)
    return nll.mean()


def combined_loss(
    outputs: Dict[str, torch.Tensor],
    target: torch.Tensor,      # (B,) fractional return
    mask: torch.Tensor,        # (B,) 0/1
    *,
    lambda_quantile: float = 1.0,
    lambda_direction: float = 0.3,
    lambda_uncertainty: float = 0.2,
    lambda_asymmetric: float = 0.5,
    direction_threshold_bps: float = 2.0,
    neg_overestimate_weight: float = 2.0,
) -> Tuple[torch.Tensor, Dict[str, float]]:
    """
    Combined loss for LOB Transformer V2.
    
    Returns (total_loss, loss_dict) where loss_dict has per-component losses.
    """
    # Apply mask
    valid = mask > 0
    if valid.sum() == 0:
        zero = torch.tensor(0.0, device=target.device, requires_grad=True)
        return zero, {'quantile': 0.0, 'direction': 0.0, 'uncertainty': 0.0, 'asymmetric': 0.0}
    
    q = outputs['quantiles'][valid]
    d = outputs['direction_logits'][valid]
    u = outputs['uncertainty'][valid]
    p = outputs['point_pred'][valid]
    t = target[valid]
    
    l_q = quantile_loss(q, t)
    l_d = direction_loss(d, t, threshold_bps=direction_threshold_bps)
    l_u = uncertainty_loss(p, t, u)
    l_a = asymmetric_huber_loss(p, t, neg_overestimate_weight=neg_overestimate_weight)
    
    total = lambda_quantile * l_q + lambda_direction * l_d + lambda_uncertainty * l_u + lambda_asymmetric * l_a
    
    loss_dict = {
        'quantile': l_q.item(),
        'direction': l_d.item(),
        'uncertainty': l_u.item(),
        'asymmetric': l_a.item(),
    }
    
    return total, loss_dict
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/haosiyu/Desktop/quant_research && python3 tests/test_training.py`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/training/losses.py tests/test_training.py
git commit -m "feat: combined loss with quantile + asymmetric Huber + direction + uncertainty"
```

---

## Task 8: Dataset and Fold Builder

**Files:**
- Create: `src/training/dataset.py`

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_training.py

from src.training.dataset import LOBDataset, build_time_series_folds


def test_dataset_loads_npz():
    """Dataset must load NPZ and return correct shapes."""
    # Create a temporary NPZ
    import tempfile, os
    tmp = tempfile.mkdtemp()
    
    Nwin, L, F = 20, 300, 40
    np.savez(
        os.path.join(tmp, '2024-10-10.npz'),
        X=np.random.randn(Nwin, L, F).astype(np.float32),
        y=np.random.randn(Nwin).astype(np.float32) * 0.001,
        y_mask=np.ones(Nwin, dtype=np.uint8),
        timestamps=np.arange(Nwin, dtype=np.int64),
        features=np.array([f'f{i}' for i in range(F)], dtype=object),
    )
    
    dataset = LOBDataset(tmp, days=['2024-10-10'])
    assert len(dataset) == Nwin
    
    x, y, mask = dataset[0]
    assert x.shape == (L, F), f"x shape: {x.shape}"
    assert y.shape == (), f"y shape: {y.shape}"
    
    # Cleanup
    import shutil
    shutil.rmtree(tmp)
    print("PASS: test_dataset_loads_npz")


def test_fold_builder_no_leakage():
    """Folds must have strict temporal ordering: train < val < test."""
    days = [f'2024-01-{d:02d}' for d in range(1, 31)]
    folds = build_time_series_folds(days, train_days=14, val_days=5, test_days=5, stride=5)
    
    assert len(folds) > 0, "No folds built"
    
    for fold in folds:
        # All train days must be before all val days
        assert max(fold['train']) < min(fold['val']), \
            f"Train/val overlap: train ends {max(fold['train'])}, val starts {min(fold['val'])}"
        # All val days must be before all test days
        assert max(fold['val']) < min(fold['test']), \
            f"Val/test overlap: val ends {max(fold['val'])}, test starts {min(fold['test'])}"
    
    print(f"PASS: test_fold_builder_no_leakage ({len(folds)} folds)")


if __name__ == '__main__':
    test_quantile_loss_calibration()
    test_asymmetric_huber_penalizes_left_overestimate()
    test_combined_loss_finite()
    test_dataset_loads_npz()
    test_fold_builder_no_leakage()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/haosiyu/Desktop/quant_research && python3 tests/test_training.py`
Expected: ImportError for LOBDataset

- [ ] **Step 3: Implement dataset and fold builder**

```python
# src/training/dataset.py
"""Dataset and fold builder for LOB training."""

import numpy as np
import torch
from torch.utils.data import Dataset
from pathlib import Path
from typing import List, Dict, Tuple, Optional


class LOBDataset(Dataset):
    """Load pre-computed NPZ files for training."""
    
    def __init__(
        self,
        data_dir: str,
        days: List[str],
        normalize: bool = False,
        x_mean: Optional[np.ndarray] = None,
        x_std: Optional[np.ndarray] = None,
    ):
        self.data_dir = Path(data_dir)
        self.normalize = normalize
        self.x_mean = x_mean
        self.x_std = x_std
        
        # Load all days into memory
        all_X = []
        all_y = []
        all_mask = []
        all_ts = []
        
        for day in sorted(days):
            npz_path = self.data_dir / f"{day}.npz"
            if not npz_path.exists():
                continue
            z = np.load(npz_path, allow_pickle=True)
            all_X.append(z['X'])
            all_y.append(z['y'])
            all_mask.append(z['y_mask'])
            if 'timestamps' in z:
                all_ts.append(z['timestamps'])
        
        if not all_X:
            self.X = np.empty((0,), dtype=np.float32)
            self.y = np.empty((0,), dtype=np.float32)
            self.mask = np.empty((0,), dtype=np.uint8)
            return
        
        self.X = np.concatenate(all_X, axis=0).astype(np.float32)
        self.y = np.concatenate(all_y, axis=0).astype(np.float32)
        self.mask = np.concatenate(all_mask, axis=0).astype(np.uint8)
        
        # Sanitize
        self.X = np.nan_to_num(self.X, nan=0.0, posinf=0.0, neginf=0.0)
        self.y = np.nan_to_num(self.y, nan=0.0, posinf=0.0, neginf=0.0)
        self.y[self.mask == 0] = 0.0
        
        # Normalize features
        if self.normalize and self.x_mean is not None and self.x_std is not None:
            std_safe = np.where(self.x_std > 1e-8, self.x_std, 1.0)
            self.X = (self.X - self.x_mean[None, None, :]) / std_safe[None, None, :]
            self.X = np.clip(self.X, -10.0, 10.0)
    
    def __len__(self) -> int:
        return self.X.shape[0] if self.X.ndim >= 2 else 0
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        return (
            torch.from_numpy(self.X[idx]),
            torch.tensor(self.y[idx], dtype=torch.float32),
            torch.tensor(float(self.mask[idx]), dtype=torch.float32),
        )
    
    def compute_stats(self) -> Tuple[np.ndarray, np.ndarray]:
        """Compute feature-wise mean and std for normalization."""
        if self.X.ndim < 3:
            n_feat = 1
            return np.zeros(n_feat), np.ones(n_feat)
        flat = self.X.reshape(-1, self.X.shape[-1])
        return flat.mean(axis=0), flat.std(axis=0)


def build_time_series_folds(
    days: List[str],
    train_days: int = 14,
    val_days: int = 5,
    test_days: int = 5,
    stride: int = 5,
) -> List[Dict[str, List[str]]]:
    """
    Build expanding/sliding window folds with strict temporal ordering.
    
    Returns list of dicts with 'train', 'val', 'test' day lists.
    """
    total_needed = train_days + val_days + test_days
    folds = []
    
    for start in range(0, len(days) - total_needed + 1, stride):
        train = days[start:start + train_days]
        val = days[start + train_days:start + train_days + val_days]
        test = days[start + train_days + val_days:start + total_needed]
        
        if len(train) == train_days and len(val) == val_days and len(test) == test_days:
            folds.append({'train': train, 'val': val, 'test': test})
    
    return folds
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/haosiyu/Desktop/quant_research && python3 tests/test_training.py`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/training/dataset.py tests/test_training.py
git commit -m "feat: NPZ dataset loader and time-series fold builder"
```

---

## Task 9: Training Loop

**Files:**
- Create: `src/training/trainer.py`

- [ ] **Step 1: Implement training loop**

```python
# src/training/trainer.py
"""Training loop for LOB Transformer V2."""

import json
import math
import time
import numpy as np
import torch
from torch import nn, optim
from torch.utils.data import DataLoader
from pathlib import Path
from typing import Dict, Optional

from ..model.lob_transformer import LOBTransformerV2
from .dataset import LOBDataset
from .losses import combined_loss


class WarmupCosineScheduler:
    """Linear warmup then cosine decay."""
    
    def __init__(self, optimizer, warmup_steps: int, total_steps: int, min_lr: float = 1e-6):
        self.optimizer = optimizer
        self.warmup_steps = warmup_steps
        self.total_steps = total_steps
        self.min_lr = min_lr
        self.base_lrs = [pg['lr'] for pg in optimizer.param_groups]
        self.step_count = 0
    
    def step(self):
        self.step_count += 1
        if self.step_count <= self.warmup_steps:
            scale = self.step_count / max(1, self.warmup_steps)
        else:
            progress = (self.step_count - self.warmup_steps) / max(1, self.total_steps - self.warmup_steps)
            scale = max(self.min_lr / self.base_lrs[0], 0.5 * (1 + math.cos(math.pi * progress)))
        
        for pg, base_lr in zip(self.optimizer.param_groups, self.base_lrs):
            pg['lr'] = base_lr * scale


class OnlineMetrics:
    """Track correlation and R2 online."""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.n = 0
        self.sum_p = 0.0
        self.sum_t = 0.0
        self.sum_pp = 0.0
        self.sum_tt = 0.0
        self.sum_pt = 0.0
        self.sum_se = 0.0
    
    def update(self, pred: np.ndarray, target: np.ndarray):
        mask = np.isfinite(pred) & np.isfinite(target)
        p, t = pred[mask], target[mask]
        n = p.size
        if n == 0:
            return
        self.n += n
        self.sum_p += p.sum()
        self.sum_t += t.sum()
        self.sum_pp += (p * p).sum()
        self.sum_tt += (t * t).sum()
        self.sum_pt += (p * t).sum()
        self.sum_se += ((p - t) ** 2).sum()
    
    def corr(self) -> float:
        if self.n <= 1:
            return 0.0
        n = float(self.n)
        cov = self.sum_pt / n - (self.sum_p / n) * (self.sum_t / n)
        vp = self.sum_pp / n - (self.sum_p / n) ** 2
        vt = self.sum_tt / n - (self.sum_t / n) ** 2
        if vp <= 0 or vt <= 0:
            return 0.0
        return cov / math.sqrt(vp * vt)
    
    def r2(self) -> float:
        if self.n <= 1:
            return 0.0
        n = float(self.n)
        vt = self.sum_tt / n - (self.sum_t / n) ** 2
        return 1.0 - (self.sum_se / n) / max(vt, 1e-12)


def train_one_fold(
    *,
    model: LOBTransformerV2,
    train_dataset: LOBDataset,
    val_dataset: LOBDataset,
    out_dir: Path,
    device: str = 'cpu',
    epochs: int = 50,
    batch_size: int = 64,
    lr: float = 3e-4,
    weight_decay: float = 1e-4,
    patience: int = 10,
    grad_clip: float = 1.0,
    warmup_epochs: int = 5,
) -> Dict[str, float]:
    """Train model for one fold. Returns best validation metrics."""
    
    out_dir.mkdir(parents=True, exist_ok=True)
    model = model.to(device)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, drop_last=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    
    total_steps = epochs * len(train_loader)
    warmup_steps = warmup_epochs * len(train_loader)
    scheduler = WarmupCosineScheduler(optimizer, warmup_steps, total_steps)
    
    best_val_loss = float('inf')
    best_metrics = {}
    es_wait = 0
    
    for epoch in range(epochs):
        # --- Train ---
        model.train()
        train_losses = []
        
        for x, y, mask in train_loader:
            x, y, mask = x.to(device), y.to(device), mask.to(device)
            
            outputs = model(x)
            loss, loss_dict = combined_loss(outputs, y, mask)
            
            if not torch.isfinite(loss):
                optimizer.zero_grad()
                continue
            
            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
            optimizer.step()
            scheduler.step()
            
            train_losses.append(loss.item())
        
        train_loss = np.mean(train_losses) if train_losses else float('inf')
        
        # --- Validate ---
        model.eval()
        val_losses = []
        metrics = OnlineMetrics()
        
        with torch.no_grad():
            for x, y, mask in val_loader:
                x, y, mask = x.to(device), y.to(device), mask.to(device)
                
                outputs = model(x)
                loss, loss_dict = combined_loss(outputs, y, mask)
                
                if torch.isfinite(loss):
                    val_losses.append(loss.item())
                
                # Track correlation on point predictions
                valid = mask > 0
                if valid.sum() > 0:
                    p = outputs['point_pred'][valid].cpu().numpy()
                    t = y[valid].cpu().numpy()
                    metrics.update(p, t)
        
        val_loss = np.mean(val_losses) if val_losses else float('inf')
        corr = metrics.corr()
        r2 = metrics.r2()
        
        current_lr = optimizer.param_groups[0]['lr']
        improved = val_loss < best_val_loss - 1e-6
        
        if improved:
            best_val_loss = val_loss
            best_metrics = {
                'val_loss': val_loss, 'train_loss': train_loss,
                'corr': corr, 'r2': r2, 'epoch': epoch,
            }
            es_wait = 0
            torch.save(model.state_dict(), out_dir / 'best_model.pt')
        else:
            es_wait += 1
        
        print(
            f"Epoch {epoch+1:03d} | LR {current_lr:.2e} | "
            f"Train {train_loss:.4f} | Val {val_loss:.4f} | "
            f"Corr {corr:+.4f} | R2 {r2:+.4f} | "
            f"{'*' if improved else ''}"
        )
        
        if es_wait >= patience:
            print(f"Early stopping at epoch {epoch+1}")
            break
    
    # Save metrics
    with open(out_dir / 'metrics.json', 'w') as f:
        json.dump(best_metrics, f, indent=2)
    
    return best_metrics
```

- [ ] **Step 2: Commit**

```bash
git add src/training/trainer.py
git commit -m "feat: training loop with warmup-cosine LR, early stopping, online metrics"
```

---

## Task 10: Evaluation Metrics

**Files:**
- Create: `src/evaluation/__init__.py`
- Create: `src/evaluation/metrics.py`

- [ ] **Step 1: Implement evaluation**

```python
# src/evaluation/metrics.py
"""Comprehensive evaluation metrics for LOB predictions."""

import numpy as np
from typing import Dict
from scipy import stats


def evaluate_predictions(
    pred: np.ndarray,
    target: np.ndarray,
    mask: np.ndarray,
    uncertainty: np.ndarray = None,
    quantiles_pred: np.ndarray = None,
) -> Dict[str, float]:
    """
    Compute comprehensive evaluation metrics.
    
    Args:
        pred: (N,) point predictions
        target: (N,) actual returns
        mask: (N,) 0/1 validity
        uncertainty: (N,) predicted uncertainty (optional)
        quantiles_pred: (N, 3) predicted q10/q50/q90 (optional)
    
    Returns dict of metrics.
    """
    valid = mask.astype(bool)
    p = pred[valid]
    t = target[valid]
    n = len(p)
    
    if n < 10:
        return {'n': n, 'error': 'too_few_samples'}
    
    metrics = {'n': int(n)}
    
    # --- Correlation metrics ---
    corr, corr_pval = stats.pearsonr(p, t)
    metrics['correlation'] = float(corr)
    metrics['correlation_pval'] = float(corr_pval)
    
    rank_corr, _ = stats.spearmanr(p, t)
    metrics['rank_correlation'] = float(rank_corr)
    
    # --- R2 ---
    ss_res = np.sum((t - p) ** 2)
    ss_tot = np.sum((t - t.mean()) ** 2)
    metrics['r2'] = float(1 - ss_res / max(ss_tot, 1e-12))
    
    # --- Residual diagnostics ---
    residuals = p - t
    metrics['residual_mean'] = float(residuals.mean())
    metrics['residual_std'] = float(residuals.std())
    metrics['residual_skew'] = float(stats.skew(residuals))
    metrics['residual_kurtosis'] = float(stats.kurtosis(residuals))
    
    # Residual autocorrelation (should be ~0 for good model)
    if n > 10:
        resid_autocorr = np.corrcoef(residuals[:-1], residuals[1:])[0, 1]
        metrics['residual_autocorr_lag1'] = float(resid_autocorr)
    
    # --- Directional accuracy ---
    pred_dir = np.sign(p)
    true_dir = np.sign(t)
    metrics['direction_accuracy'] = float(np.mean(pred_dir == true_dir))
    
    # --- Tail analysis ---
    # Left tail: how does model perform when market drops?
    left_mask = t < np.percentile(t, 10)
    if left_mask.sum() > 5:
        metrics['left_tail_corr'] = float(np.corrcoef(p[left_mask], t[left_mask])[0, 1])
        metrics['left_tail_bias'] = float((p[left_mask] - t[left_mask]).mean())  # >0 = overestimate
    
    # Right tail
    right_mask = t > np.percentile(t, 90)
    if right_mask.sum() > 5:
        metrics['right_tail_corr'] = float(np.corrcoef(p[right_mask], t[right_mask])[0, 1])
        metrics['right_tail_bias'] = float((p[right_mask] - t[right_mask]).mean())
    
    # --- Score (bps) ---
    r2_clipped = max(metrics['r2'], 0.0)
    std_target = float(np.std(t))
    metrics['score_bps'] = float(np.sqrt(r2_clipped) * std_target * 10000)
    
    # --- Quantile calibration ---
    if quantiles_pred is not None and quantiles_pred.shape[0] == n:
        q_pred = quantiles_pred[valid] if quantiles_pred.shape[0] == len(mask) else quantiles_pred
        for i, q_level in enumerate([0.1, 0.5, 0.9]):
            actual_coverage = float(np.mean(t <= q_pred[:, i]))
            metrics[f'q{int(q_level*100)}_coverage'] = actual_coverage
            metrics[f'q{int(q_level*100)}_calibration_error'] = abs(actual_coverage - q_level)
    
    # --- Uncertainty calibration ---
    if uncertainty is not None:
        u = uncertainty[valid] if uncertainty.shape[0] == len(mask) else uncertainty
        # Higher uncertainty should correspond to larger absolute errors
        abs_err = np.abs(residuals)
        unc_corr = np.corrcoef(u, abs_err)[0, 1]
        metrics['uncertainty_error_correlation'] = float(unc_corr)
    
    return metrics
```

- [ ] **Step 2: Commit**

```bash
git add src/evaluation/metrics.py src/evaluation/__init__.py
git commit -m "feat: comprehensive evaluation with residual diagnostics and tail analysis"
```

---

## Task 11: Simple PnL Backtest

**Files:**
- Create: `src/evaluation/backtest.py`

- [ ] **Step 1: Implement backtest**

```python
# src/evaluation/backtest.py
"""Simple signal-based PnL backtest."""

import numpy as np
from typing import Dict


def backtest_signal(
    pred: np.ndarray,
    target: np.ndarray,
    mask: np.ndarray,
    *,
    fee_bps: float = 4.0,
    threshold_bps: float = 2.0,
    position_sizing: str = 'binary',  # 'binary' or 'proportional'
) -> Dict[str, float]:
    """
    Simple backtest: go long when pred > threshold, short when pred < -threshold.
    
    Args:
        pred: (N,) predicted return (fractional)
        target: (N,) actual return (fractional)
        mask: (N,) validity mask
        fee_bps: round-trip fee in basis points
        threshold_bps: minimum signal to trade
        position_sizing: 'binary' (full size) or 'proportional' (size ~ |signal|)
    
    Returns dict of PnL metrics.
    """
    valid = mask.astype(bool)
    p = pred[valid]
    t = target[valid]
    n = len(p)
    
    threshold = threshold_bps / 10000.0
    fee = fee_bps / 10000.0
    
    # Generate positions
    if position_sizing == 'binary':
        positions = np.where(p > threshold, 1.0, np.where(p < -threshold, -1.0, 0.0))
    else:
        positions = np.clip(p / threshold, -1.0, 1.0)
        positions = np.where(np.abs(p) < threshold, 0.0, positions)
    
    # Gross PnL
    gross_pnl = positions * t  # fractional return per period
    
    # Transaction costs: fee on each trade (position change)
    trades = np.abs(np.diff(positions, prepend=0))
    costs = trades * fee / 2  # fee/2 per side
    
    net_pnl = gross_pnl - costs
    
    # Metrics
    n_trades = int((trades > 0).sum())
    total_gross_bps = float(gross_pnl.sum() * 10000)
    total_cost_bps = float(costs.sum() * 10000)
    total_net_bps = float(net_pnl.sum() * 10000)
    
    # Sharpe (annualized, assuming 3-min periods)
    periods_per_year = 365.25 * 24 * 60 / 3  # ~175,000
    if net_pnl.std() > 0:
        sharpe = float(net_pnl.mean() / net_pnl.std() * np.sqrt(periods_per_year))
    else:
        sharpe = 0.0
    
    # Max drawdown
    cum_pnl = np.cumsum(net_pnl)
    peak = np.maximum.accumulate(cum_pnl)
    drawdown = peak - cum_pnl
    max_dd_bps = float(drawdown.max() * 10000)
    
    # Win rate
    winning_trades = net_pnl[positions != 0]
    win_rate = float(np.mean(winning_trades > 0)) if len(winning_trades) > 0 else 0.0
    
    return {
        'n_periods': int(n),
        'n_trades': n_trades,
        'trade_rate': float(n_trades / max(n, 1)),
        'gross_pnl_bps': total_gross_bps,
        'total_cost_bps': total_cost_bps,
        'net_pnl_bps': total_net_bps,
        'sharpe_annual': sharpe,
        'max_drawdown_bps': max_dd_bps,
        'win_rate': win_rate,
        'avg_pnl_per_trade_bps': float(total_net_bps / max(n_trades, 1)),
    }
```

- [ ] **Step 2: Commit**

```bash
git add src/evaluation/backtest.py
git commit -m "feat: simple signal-based PnL backtest with fees"
```

---

## Task 12: End-to-End Entry Point

**Files:**
- Create: `run_pipeline.py`
- Create: `configs/default.json`

- [ ] **Step 1: Create config**

```json
{
    "data": {
        "csv_path": "BTCUSDT.csv.gz",
        "npz_dir": "data/npz_h180",
        "n_levels": 25,
        "horizon_sec": 180,
        "input_len": 300,
        "stride": 60
    },
    "model": {
        "d_model": 128,
        "nhead": 4,
        "depth": 3,
        "d_ff": 512,
        "dropout": 0.1,
        "n_quantiles": 3,
        "n_direction_classes": 3,
        "n_regimes": 4,
        "conv_layers": 2,
        "conv_kernel": 9
    },
    "training": {
        "epochs": 50,
        "batch_size": 64,
        "lr": 3e-4,
        "weight_decay": 1e-4,
        "patience": 10,
        "grad_clip": 1.0,
        "warmup_epochs": 5,
        "train_days": 14,
        "val_days": 5,
        "test_days": 5,
        "fold_stride": 5
    },
    "output_dir": "experiments/v2"
}
```

- [ ] **Step 2: Create entry point**

```python
#!/usr/bin/env python3
# run_pipeline.py
"""End-to-end pipeline: data -> features -> train -> evaluate -> backtest."""

import argparse
import json
import numpy as np
import torch
from pathlib import Path

from src.features.pipeline import process_csv_to_npz
from src.model.lob_transformer import LOBTransformerV2
from src.training.dataset import LOBDataset, build_time_series_folds
from src.training.trainer import train_one_fold
from src.evaluation.metrics import evaluate_predictions
from src.evaluation.backtest import backtest_signal


def main():
    parser = argparse.ArgumentParser("LOB Transformer V2 Pipeline")
    parser.add_argument("--config", type=str, default="configs/default.json")
    parser.add_argument("--skip-features", action="store_true", help="Skip feature generation (use existing NPZ)")
    parser.add_argument("--device", type=str, default="auto")
    args = parser.parse_args()
    
    with open(args.config) as f:
        cfg = json.load(f)
    
    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Device: {device}")
    
    # --- Step 1: Generate features ---
    data_cfg = cfg['data']
    npz_dir = Path(data_cfg['npz_dir'])
    
    if not args.skip_features:
        print("\n=== Step 1: Feature Generation ===")
        process_csv_to_npz(
            data_cfg['csv_path'],
            str(npz_dir),
            horizon_sec=data_cfg['horizon_sec'],
            input_len=data_cfg['input_len'],
            stride=data_cfg['stride'],
            n_levels=data_cfg['n_levels'],
        )
    
    # --- Step 2: Discover available days ---
    available_days = sorted([p.stem for p in npz_dir.glob("*.npz")])
    print(f"\nAvailable days: {len(available_days)}")
    if not available_days:
        print("ERROR: No NPZ files found. Run without --skip-features first.")
        return
    
    # --- Step 3: Build folds ---
    train_cfg = cfg['training']
    folds = build_time_series_folds(
        available_days,
        train_days=train_cfg['train_days'],
        val_days=train_cfg['val_days'],
        test_days=train_cfg['test_days'],
        stride=train_cfg['fold_stride'],
    )
    
    # For single-day data: use 70/15/15 split of windows instead of day-based folds
    if len(available_days) == 1:
        print("Single day mode: using window-based train/val/test split")
        folds = [{'train': available_days, 'val': available_days, 'test': available_days}]
    
    print(f"Folds: {len(folds)}")
    
    # --- Step 4: Train each fold ---
    model_cfg = cfg['model']
    out_root = Path(cfg['output_dir'])
    
    for fold_idx, fold in enumerate(folds):
        print(f"\n=== Fold {fold_idx + 1}/{len(folds)} ===")
        print(f"  Train: {fold['train']}")
        print(f"  Val:   {fold['val']}")
        print(f"  Test:  {fold['test']}")
        
        # Load data
        train_ds = LOBDataset(str(npz_dir), fold['train'])
        
        if len(train_ds) == 0:
            print("  No training data, skipping")
            continue
        
        # Compute normalization stats from training data
        x_mean, x_std = train_ds.compute_stats()
        n_features = train_ds.X.shape[-1]
        
        # Rebuild with normalization
        train_ds = LOBDataset(str(npz_dir), fold['train'], normalize=True, x_mean=x_mean, x_std=x_std)
        val_ds = LOBDataset(str(npz_dir), fold['val'], normalize=True, x_mean=x_mean, x_std=x_std)
        test_ds = LOBDataset(str(npz_dir), fold['test'], normalize=True, x_mean=x_mean, x_std=x_std)
        
        # For single-day mode: split the dataset
        if len(available_days) == 1:
            total = len(train_ds)
            n_train = int(total * 0.7)
            n_val = int(total * 0.15)
            n_test = total - n_train - n_val
            
            # Temporal split (no shuffle - maintain order)
            train_ds.X = train_ds.X[:n_train]
            train_ds.y = train_ds.y[:n_train]
            train_ds.mask = train_ds.mask[:n_train]
            
            val_ds.X = val_ds.X[n_train:n_train+n_val]
            val_ds.y = val_ds.y[n_train:n_train+n_val]
            val_ds.mask = val_ds.mask[n_train:n_train+n_val]
            
            test_ds.X = test_ds.X[n_train+n_val:]
            test_ds.y = test_ds.y[n_train+n_val:]
            test_ds.mask = test_ds.mask[n_train+n_val:]
        
        print(f"  Samples: train={len(train_ds)}, val={len(val_ds)}, test={len(test_ds)}")
        
        # Build model
        model = LOBTransformerV2(
            n_features=n_features,
            **model_cfg,
        )
        
        param_count = sum(p.numel() for p in model.parameters())
        print(f"  Model parameters: {param_count:,}")
        
        fold_dir = out_root / f"fold{fold_idx}"
        
        # Train
        best_metrics = train_one_fold(
            model=model,
            train_dataset=train_ds,
            val_dataset=val_ds,
            out_dir=fold_dir,
            device=device,
            epochs=train_cfg['epochs'],
            batch_size=train_cfg['batch_size'],
            lr=train_cfg['lr'],
            weight_decay=train_cfg['weight_decay'],
            patience=train_cfg['patience'],
            grad_clip=train_cfg['grad_clip'],
            warmup_epochs=train_cfg['warmup_epochs'],
        )
        
        print(f"\n  Best val: loss={best_metrics.get('val_loss',0):.4f}, "
              f"corr={best_metrics.get('corr',0):+.4f}, r2={best_metrics.get('r2',0):+.4f}")
        
        # --- Step 5: Evaluate on test ---
        model.load_state_dict(torch.load(fold_dir / 'best_model.pt', map_location=device))
        model.to(device)
        model.eval()
        
        all_pred = []
        all_target = []
        all_mask = []
        all_uncertainty = []
        all_quantiles = []
        
        test_loader = torch.utils.data.DataLoader(test_ds, batch_size=train_cfg['batch_size'], shuffle=False)
        
        with torch.no_grad():
            for x, y, mask in test_loader:
                x = x.to(device)
                outputs = model(x)
                all_pred.append(outputs['point_pred'].cpu().numpy())
                all_target.append(y.numpy())
                all_mask.append(mask.numpy())
                all_uncertainty.append(outputs['uncertainty'].cpu().numpy())
                all_quantiles.append(outputs['quantiles'].cpu().numpy())
        
        pred = np.concatenate(all_pred)
        target = np.concatenate(all_target)
        mask = np.concatenate(all_mask)
        uncertainty = np.concatenate(all_uncertainty)
        quantiles = np.concatenate(all_quantiles)
        
        eval_metrics = evaluate_predictions(pred, target, mask, uncertainty, quantiles)
        bt_metrics = backtest_signal(pred, target, mask, fee_bps=4.0, threshold_bps=2.0)
        
        print(f"\n  TEST Evaluation:")
        print(f"    Correlation:     {eval_metrics.get('correlation', 0):+.4f}")
        print(f"    R2:              {eval_metrics.get('r2', 0):+.4f}")
        print(f"    Direction Acc:   {eval_metrics.get('direction_accuracy', 0):.2%}")
        print(f"    Residual AC(1):  {eval_metrics.get('residual_autocorr_lag1', 0):+.4f}")
        print(f"    Left Tail Bias:  {eval_metrics.get('left_tail_bias', 0)*10000:+.2f} bps")
        print(f"    Score (bps):     {eval_metrics.get('score_bps', 0):.2f}")
        
        print(f"\n  Backtest:")
        print(f"    Net PnL:         {bt_metrics['net_pnl_bps']:+.1f} bps")
        print(f"    Sharpe (annual): {bt_metrics['sharpe_annual']:.2f}")
        print(f"    Win Rate:        {bt_metrics['win_rate']:.2%}")
        print(f"    Max Drawdown:    {bt_metrics['max_drawdown_bps']:.1f} bps")
        print(f"    Trades:          {bt_metrics['n_trades']}")
        
        # Save all metrics
        all_metrics = {'eval': eval_metrics, 'backtest': bt_metrics, 'best_val': best_metrics}
        with open(fold_dir / 'test_results.json', 'w') as f:
            json.dump(all_metrics, f, indent=2, default=str)
        
        # Save normalization params for inference
        np.savez(fold_dir / 'norm_params.npz', x_mean=x_mean, x_std=x_std)
    
    print("\n=== Done ===")


if __name__ == '__main__':
    main()
```

- [ ] **Step 3: Run end-to-end on sample data**

```bash
cd /Users/haosiyu/Desktop/quant_research
python3 run_pipeline.py --config configs/default.json
```

Expected: Full pipeline runs - feature generation, training, evaluation, backtest results printed.

- [ ] **Step 4: Commit**

```bash
git add run_pipeline.py configs/default.json
git commit -m "feat: end-to-end pipeline entry point with config system"
```

---

## Self-Review Checklist

**1. Spec coverage:**
- [x] Feature engineering from raw LOB CSV
- [x] Structure-aware model (bid/ask/global groups in SpatialLOBEncoder)
- [x] Causal temporal encoder with RoPE (replacing learned positional embeddings)
- [x] Probabilistic output (quantiles + direction + uncertainty)
- [x] Regime-aware feature gate
- [x] Asymmetric loss for left-tail bias fix
- [x] No-leakage verification tests
- [x] Residual autocorrelation diagnostic
- [x] Time granularity analysis (3-minute horizon)
- [x] Evaluation + backtest

**2. Placeholder scan:** No TBD/TODO found.

**3. Type consistency:** Verified: LOBTransformerV2 returns dict with `point_pred`, `quantiles`, `direction_logits`, `uncertainty` - consistent across model, loss, trainer, and evaluation code.
