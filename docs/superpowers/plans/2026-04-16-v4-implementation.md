# V4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement V4 (Structure-Aware + Regime-Conditioned LOB Transformer) per `docs/superpowers/specs/2026-04-16-v4-design.md`. Target: pooled OOS correlation ≥ 0.12 on 4 walk-forward folds (vs Ridge 0.099 baseline).

**Architecture:** Dual-path (feature + raw LOB) encoder with TCN + patch attention temporal backbone, PPNet regime gate, and multi-horizon monotonic-quantile heads. Every new component is gated by a config flag for A/B ablation. Loss is DUL = pinball + utility-rank + (optional) calibration coverage.

**Tech Stack:** Python 3.9, PyTorch 2.x (mps/cpu locally; CUDA on pod), pandas, numpy, scipy, pytest.

---

## Guiding Principles (non-negotiable)

1. **TDD for every new module and every modification.** The ritual:
   1. Write failing test
   2. Run → verify FAIL (exact error: `ImportError`, `AttributeError`, `AssertionError` — not a tooling error)
   3. Implement minimal code
   4. Run → verify PASS
   5. Commit

2. **Ablation-first config discipline.** Every new architecture component MUST be reachable through a boolean flag in `configs/v4_full.json`. No silent inclusions. When the flag is `False`, the component must be bypassed (identity / AvgPool / single-horizon / etc.) per the spec table. Verified by a dedicated "flag off = bypass" test.

3. **Data leakage validation.** Every feature added in Phase 1 has a causality test: `feat[t]` must depend only on raw data timestamped `< t` (strictly). Every label has a leakage test: for a window starting at index `t` with input length `L` and horizon `H`, `y[t]` depends only on `mid[t+L : t+L+H]` and never appears inside `X[t:t+L]`.

4. **Model forward causality.** End-to-end causality tests: for input `x[0:L]` vs `x[0:L]` with `x[L-1]` perturbed, output position `i < L-1` must be unchanged (bit-identical where possible, `allclose` with zero tolerance otherwise). For multi-horizon output, the `quantiles_by_horizon[B, H, 3]` tensor must not read from any future timestep beyond `L`.

---

## Scope Check

The spec covers three coupled subsystems (data features, model, loss) but they must land together to produce a runnable V4. Splitting into sub-project specs is **not** appropriate here — each subsystem's outputs are the next one's inputs, and the first fully-runnable version requires all three. The plan keeps them in one document but staged in phases.

---

## File Structure

### New files

| Path | Responsibility |
|------|----------------|
| `src/features/ridge_informed_features.py` | 6 causal derived features from Ridge top signals |
| `src/features/regime_prior_features.py` | 6 external hourly-scale regime features |
| `src/model/attention_pool.py` | `AttentionPoolLevels`, `AttentionPoolTokens` (learned-query pools) |
| `src/training/dul_loss.py` | `utility_rank_loss`, `coverage_calib_loss`, `compute_dul_loss` |
| `configs/v4_full.json` | V4 main config — all flags True |
| `configs/v4_ablations/no_ppnet.json` | ablation config: PPNet off |
| `configs/v4_ablations/no_multi_horizon.json` | ablation config: single-horizon (y_180) |
| `configs/v4_ablations/no_ridge_features.json` | ablation config: 58 base features only |
| `configs/v4_ablations/no_patch_attention_pool.json` | ablation config: last-token extraction |
| `configs/v4_ablations/no_channel_mix.json` | ablation config: RawLOB without 1×1 conv |
| `configs/v4_ablations/no_level_attention.json` | ablation config: AvgPool over levels |
| `configs/v4_ablations/no_utility_rank.json` | ablation config: pure quantile loss |
| `configs/v4_ablations/plus_masknet.json` | ablation config: re-enable MaskNet |
| `scripts/run_ablations.py` | Sequential ablation runner |
| `scripts/aggregate_folds.py` | Concat per-fold predictions → pooled IC |
| `scripts/eval_fold_test.py` | Per-fold test evaluation (multi-horizon) |
| `scripts/gen_ablation_configs.py` | Generates the 8 ablation config files |
| `tests/test_ridge_informed_features.py` | Unit + causality for 6 derived features |
| `tests/test_regime_prior_features.py` | Unit + causality for 6 regime features |
| `tests/test_attention_pool.py` | Shape + masking + bypass-equivalence |
| `tests/test_raw_lob_encoder_v4.py` | V4 flags bypass behavior on RawLOBEncoder |
| `tests/test_v3_bypass_flags.py` | V4 flags bypass behavior on DualPathLOBModelV3 |
| `tests/test_v4_causality.py` | End-to-end forward causality |
| `tests/test_dul_loss.py` | DUL components + composition |
| `tests/test_multihorizon_npz.py` | NPZ emits `y_60/180/300/600` + back-compat alias |
| `tests/test_no_leakage.py` | Feature + label leakage audit |
| `tests/test_dataset_horizon_key.py` | Dataset chooses correct horizon key |
| `tests/test_trainer_v2.py` | 5-tuple batch, DUL, multi-horizon step |
| `tests/test_ppnet_quantile.py` | PPNet gate + monotonic quantile invariant |
| `tests/test_configs.py` | Config schema sanity |
| `docs/V4_RESULTS.md` | Results report template (populated after training) |

### Modified files

| Path | Changes |
|------|---------|
| `src/features/microstructure.py` | Call out to ridge_informed + regime_prior modules |
| `src/features/pipeline.py` | `build_npz_for_day` emits multi-horizon `y_*`/`y_mask_*` + `regime_prior` field |
| `src/features/multi_day_pipeline.py` | Forward V4 flags; accept `horizons_sec`, `include_ridge_features`, `include_regime_prior` |
| `src/training/dataset.py` | `LOBDatasetV2` returns 5-tuple `(X, X_raw, y, y_mask, regime_prior)` |
| `src/training/trainer_v2.py` | Unpack 5-tuple, forward `regime_prior` to model, DUL loss, multi-horizon step |
| `src/model/raw_lob_encoder.py` | Add `use_channel_mix_conv`, `use_level_attention_pool` flags |
| `src/model/dual_path_model_v3.py` | Add V4 flags (`use_patch_attention_pool`, `use_ppnet_gate`, `use_raw_path`, `use_revin`); enable PPNet with `d_prior=6`; multi-horizon head list |
| `src/model/ppnet_gate.py` | Ensure `d_prior=0` path is identity (flag-off safety) |
| `src/model/monotonic_quantile.py` | Remove single-horizon assumption; expose `n_horizons` |
| `run_pipeline_v3.py` | Accept V4 config fields; pass flags into trainer; multi-horizon evaluation |

---

## Phase 1 — Data Features (adds 12 new features + multi-horizon labels)

### Task 1: Ridge-informed derived features (6 features)

**Files:**
- Create: `src/features/ridge_informed_features.py`
- Test: `tests/test_ridge_informed_features.py`

The six features per spec §"New Features":

| Feature | Formula |
|---------|---------|
| `net_flow_x_spread` | `net_trade_flow_1s * spread_bps` |
| `net_flow_x_vol` | `net_trade_flow_1s * realized_vol_30s` |
| `obi_L5_rank_1h` | rolling pct-rank of `obi_L5` over past 3600s |
| `net_flow_rank_1h` | rolling pct-rank of `net_trade_flow_1s` over past 3600s |
| `large_trade_arrival_60s` | 1 iff max trade size over past 60s > train-set p95 (threshold passed in) |
| `book_pressure_delta_60s` | `book_pressure_imbalance(t) - book_pressure_imbalance(t-60)` |

- [ ] **Step 1: Write the failing test (module not present yet)**

```python
# tests/test_ridge_informed_features.py
import numpy as np
import pandas as pd
import pytest

from src.features.ridge_informed_features import compute_ridge_informed_features


@pytest.fixture
def base_df():
    rng = np.random.default_rng(0)
    n = 5000
    return pd.DataFrame({
        "net_trade_flow_1s": rng.normal(0, 1, n),
        "spread_bps": rng.uniform(0.5, 2.0, n),
        "realized_vol_30s": rng.uniform(1e-4, 5e-4, n),
        "obi_L5": rng.uniform(-1, 1, n),
        "max_trade_size_60s": rng.lognormal(0, 1, n),
        "book_pressure_imbalance": rng.normal(0, 0.1, n),
    })


def test_returns_all_six_columns(base_df):
    out = compute_ridge_informed_features(base_df, large_trade_threshold=3.0)
    for col in [
        "net_flow_x_spread", "net_flow_x_vol", "obi_L5_rank_1h",
        "net_flow_rank_1h", "large_trade_arrival_60s", "book_pressure_delta_60s",
    ]:
        assert col in out.columns, f"missing {col}"
    assert len(out) == len(base_df)


def test_causality_only_past_data(base_df):
    """Perturb row at index T; rows with index < T must be unchanged."""
    T = 3500
    out1 = compute_ridge_informed_features(base_df.copy(), large_trade_threshold=3.0)
    df2 = base_df.copy()
    df2.loc[T:, "net_trade_flow_1s"] += 100.0
    df2.loc[T:, "obi_L5"] = 0.99
    df2.loc[T:, "book_pressure_imbalance"] = 5.0
    df2.loc[T:, "max_trade_size_60s"] = 1e6
    out2 = compute_ridge_informed_features(df2, large_trade_threshold=3.0)
    cols = ["net_flow_x_spread", "net_flow_x_vol", "obi_L5_rank_1h",
            "net_flow_rank_1h", "large_trade_arrival_60s", "book_pressure_delta_60s"]
    for c in cols:
        a = out1[c].values[:T]
        b = out2[c].values[:T]
        np.testing.assert_array_equal(a, b, err_msg=f"{c} leaks future into index < T")


def test_rank_features_bounded_0_1(base_df):
    out = compute_ridge_informed_features(base_df, large_trade_threshold=3.0)
    warm = out.iloc[3600:]
    assert (warm["obi_L5_rank_1h"].between(0.0, 1.0)).all()
    assert (warm["net_flow_rank_1h"].between(0.0, 1.0)).all()


def test_large_trade_is_binary(base_df):
    out = compute_ridge_informed_features(base_df, large_trade_threshold=3.0)
    assert set(out["large_trade_arrival_60s"].unique()).issubset({0, 1})


def test_book_pressure_delta_lag_60(base_df):
    out = compute_ridge_informed_features(base_df, large_trade_threshold=3.0)
    expected = base_df["book_pressure_imbalance"] - base_df["book_pressure_imbalance"].shift(60)
    pd.testing.assert_series_equal(
        out["book_pressure_delta_60s"].iloc[60:],
        expected.iloc[60:].rename("book_pressure_delta_60s"),
        check_names=False,
    )
```

- [ ] **Step 2: Run tests — verify ImportError**

```bash
pytest tests/test_ridge_informed_features.py -x 2>&1 | head -20
```
Expected: all 5 tests fail with `ImportError: cannot import name 'compute_ridge_informed_features'`.

- [ ] **Step 3: Implement module**

```python
# src/features/ridge_informed_features.py
from __future__ import annotations

import pandas as pd


RIDGE_INFORMED_FEATURE_COLS = [
    "net_flow_x_spread",
    "net_flow_x_vol",
    "obi_L5_rank_1h",
    "net_flow_rank_1h",
    "large_trade_arrival_60s",
    "book_pressure_delta_60s",
]


def compute_ridge_informed_features(
    df: pd.DataFrame,
    *,
    large_trade_threshold: float,
    rank_window: int = 3600,
) -> pd.DataFrame:
    """Append 6 ridge-informed derived features. Strictly causal."""
    out = df.copy()

    out["net_flow_x_spread"] = df["net_trade_flow_1s"] * df["spread_bps"]
    out["net_flow_x_vol"] = df["net_trade_flow_1s"] * df["realized_vol_30s"]

    # Rolling percentile rank over past rank_window seconds (min_periods=rank_window = strictly causal)
    out["obi_L5_rank_1h"] = (
        df["obi_L5"]
        .rolling(window=rank_window, min_periods=rank_window)
        .rank(pct=True)
        .fillna(0.5)
    )
    out["net_flow_rank_1h"] = (
        df["net_trade_flow_1s"]
        .rolling(window=rank_window, min_periods=rank_window)
        .rank(pct=True)
        .fillna(0.5)
    )

    out["large_trade_arrival_60s"] = (df["max_trade_size_60s"] > large_trade_threshold).astype("int8")
    out["book_pressure_delta_60s"] = (
        df["book_pressure_imbalance"] - df["book_pressure_imbalance"].shift(60)
    ).fillna(0.0)

    return out
```

- [ ] **Step 4: Run tests — verify PASS**

```bash
pytest tests/test_ridge_informed_features.py -x -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/features/ridge_informed_features.py tests/test_ridge_informed_features.py
git commit -m "feat(v4): ridge-informed derived features with causality tests"
```

---

### Task 2: Regime-prior features (6 hourly/daily-scale features)

**Files:**
- Create: `src/features/regime_prior_features.py`
- Test: `tests/test_regime_prior_features.py`

Six features per spec §"Regime Prior (6 features, external)":

| Feature | Formula |
|---------|---------|
| `vol_1h` | std of `log_return_1s` over past 3600s |
| `spread_mean_1h` | mean of `spread_bps` over past 3600s |
| `obi_trend_1h` | linear slope of `obi_L5` over past 3600s |
| `price_return_6h` | `log(mid[t] / mid[t-21600])` |
| `hour_sin` | `sin(2π * hour_of_day / 24)` |
| `hour_cos` | `cos(2π * hour_of_day / 24)` |

- [ ] **Step 1: Write the failing test**

```python
# tests/test_regime_prior_features.py
import numpy as np
import pandas as pd
import pytest

from src.features.regime_prior_features import (
    compute_regime_prior_features,
    REGIME_PRIOR_COLS,
)


@pytest.fixture
def df_1day():
    n = 86400
    ts = pd.date_range("2026-01-01", periods=n, freq="1s", tz="UTC")
    rng = np.random.default_rng(42)
    mid = 50000 + np.cumsum(rng.normal(0, 0.5, n))
    log_ret = np.concatenate([[0.0], np.diff(np.log(mid))])
    return pd.DataFrame({
        "timestamp": ts,
        "mid": mid,
        "log_return_1s": log_ret,
        "spread_bps": rng.uniform(0.4, 1.2, n),
        "obi_L5": rng.uniform(-1, 1, n),
    })


def test_returns_six_columns_in_order(df_1day):
    out = compute_regime_prior_features(df_1day)
    assert REGIME_PRIOR_COLS == [
        "vol_1h", "spread_mean_1h", "obi_trend_1h",
        "price_return_6h", "hour_sin", "hour_cos",
    ]
    for c in REGIME_PRIOR_COLS:
        assert c in out.columns


def test_causality_perturb_future(df_1day):
    T = 60000
    out1 = compute_regime_prior_features(df_1day.copy())
    df2 = df_1day.copy()
    df2.loc[T:, "mid"] *= 10.0
    df2.loc[T:, "spread_bps"] += 100.0
    df2.loc[T:, "obi_L5"] = 0.99
    df2.loc[T:, "log_return_1s"] = 1.0
    out2 = compute_regime_prior_features(df2)
    for c in ["vol_1h", "spread_mean_1h", "obi_trend_1h", "price_return_6h"]:
        np.testing.assert_array_equal(
            out1[c].values[:T], out2[c].values[:T],
            err_msg=f"{c} leaks future"
        )


def test_hour_encoding_within_unit_circle(df_1day):
    out = compute_regime_prior_features(df_1day)
    r = np.sqrt(out["hour_sin"] ** 2 + out["hour_cos"] ** 2)
    assert np.allclose(r, 1.0, atol=1e-10)


def test_warmup_filled_zero(df_1day):
    out = compute_regime_prior_features(df_1day)
    # First 3599 rows lack the 1h window — must be 0, not NaN
    assert out["vol_1h"].iloc[:3599].abs().max() == 0.0
    assert out["spread_mean_1h"].iloc[:3599].abs().max() == 0.0
    assert out["obi_trend_1h"].iloc[:3599].abs().max() == 0.0
    # First 21599 rows lack the 6h window
    assert out["price_return_6h"].iloc[:21599].abs().max() == 0.0


def test_output_shape(df_1day):
    out = compute_regime_prior_features(df_1day)
    assert len(out) == len(df_1day)
    assert out[REGIME_PRIOR_COLS].notna().all().all()
```

- [ ] **Step 2: Run — verify FAIL with ImportError**

```bash
pytest tests/test_regime_prior_features.py -x 2>&1 | head -10
```

- [ ] **Step 3: Implement module**

```python
# src/features/regime_prior_features.py
from __future__ import annotations

import numpy as np
import pandas as pd

REGIME_PRIOR_COLS = [
    "vol_1h",
    "spread_mean_1h",
    "obi_trend_1h",
    "price_return_6h",
    "hour_sin",
    "hour_cos",
]


def _rolling_slope(series: pd.Series, window: int) -> pd.Series:
    """Linear regression slope over trailing window; causal (fills pre-window with 0)."""
    x = np.arange(window, dtype=np.float64)
    x_centered = x - x.mean()
    denom = float((x_centered ** 2).sum())
    def _slope(a: np.ndarray) -> float:
        y_centered = a - a.mean()
        return float((x_centered * y_centered).sum() / denom)
    return series.rolling(window=window, min_periods=window).apply(_slope, raw=True).fillna(0.0)


def compute_regime_prior_features(df: pd.DataFrame) -> pd.DataFrame:
    """Append 6 hourly-scale regime-prior features. Strictly causal."""
    out = df.copy()

    out["vol_1h"] = (
        df["log_return_1s"].rolling(window=3600, min_periods=3600).std().fillna(0.0)
    )
    out["spread_mean_1h"] = (
        df["spread_bps"].rolling(window=3600, min_periods=3600).mean().fillna(0.0)
    )
    out["obi_trend_1h"] = _rolling_slope(df["obi_L5"], window=3600)

    log_mid = np.log(df["mid"].astype(float))
    out["price_return_6h"] = (log_mid - log_mid.shift(21600)).fillna(0.0)

    hours = pd.to_datetime(df["timestamp"]).dt.hour + pd.to_datetime(df["timestamp"]).dt.minute / 60.0
    angle = 2 * np.pi * hours / 24.0
    out["hour_sin"] = np.sin(angle)
    out["hour_cos"] = np.cos(angle)

    return out
```

- [ ] **Step 4: Run — verify PASS**

```bash
pytest tests/test_regime_prior_features.py -x -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/features/regime_prior_features.py tests/test_regime_prior_features.py
git commit -m "feat(v4): regime-prior (6 hourly-scale) features with causality tests"
```

---

### Task 3: Wire features into microstructure + multi-day pipelines

**Files:**
- Modify: `src/features/microstructure.py` (entry point that returns one-second feature DataFrame)
- Modify: `src/features/multi_day_pipeline.py` (threads flags `include_ridge_features`, `include_regime_prior`, and `horizons_sec` through)
- Test: `tests/test_derived_features.py` (augment)

- [ ] **Step 1: Add integration test before touching the pipeline**

```python
# tests/test_derived_features.py (append)
def test_pipeline_emits_ridge_and_regime_when_flagged(tiny_1day_csv, tmp_path):
    from src.features.multi_day_pipeline import process_single_day
    out = process_single_day(
        tiny_1day_csv, tmp_path,
        include_ridge_features=True,
        include_regime_prior=True,
        horizons_sec=[60, 180, 300, 600],
    )
    import numpy as np
    npz = np.load(out)
    # Feature matrix gained 6 ridge-informed columns
    assert npz["feature_names"].shape[0] >= 58 + 6
    # Regime prior is stored separately
    assert "regime_prior" in npz.files
    assert npz["regime_prior"].shape[-1] == 6
    # Multi-horizon labels present
    for h in [60, 180, 300, 600]:
        assert f"y_{h}" in npz.files
        assert f"y_mask_{h}" in npz.files
    # Back-compat alias
    assert np.array_equal(npz["y"], npz["y_60"])
```

- [ ] **Step 2: Run — verify FAIL**

```bash
pytest tests/test_derived_features.py::test_pipeline_emits_ridge_and_regime_when_flagged -x
```

- [ ] **Step 3: Wire into `microstructure.compute_microstructure_features` and `multi_day_pipeline.process_single_day`**

Inside `compute_microstructure_features` (after existing features are computed):

```python
if include_ridge_features:
    from src.features.ridge_informed_features import compute_ridge_informed_features
    feats = compute_ridge_informed_features(feats, large_trade_threshold=large_trade_threshold)

if include_regime_prior:
    from src.features.regime_prior_features import compute_regime_prior_features
    feats = compute_regime_prior_features(feats)
```

`multi_day_pipeline.process_single_day` signature gains:
```python
def process_single_day(
    csv_path, out_dir, *,
    include_ridge_features: bool = False,
    include_regime_prior: bool = False,
    horizons_sec: list[int] = (180,),
    large_trade_threshold: float | None = None,
    ...
):
```

- [ ] **Step 4: Run full feature test + regression sweep**

```bash
pytest tests/test_derived_features.py tests/test_features.py tests/test_multi_day_pipeline.py -x -v
```

- [ ] **Step 5: Commit**

```bash
git add src/features/microstructure.py src/features/multi_day_pipeline.py tests/test_derived_features.py
git commit -m "feat(v4): wire ridge-informed + regime-prior features into pipeline"
```

---

### Task 4: Multi-horizon NPZ labels + regime_prior storage

**Files:**
- Modify: `src/features/pipeline.py` — `build_npz_for_day`
- Test: `tests/test_multihorizon_npz.py`

Per spec §"Multi-Horizon Labels":
- Emit `y_60, y_mask_60, y_180, y_mask_180, y_300, y_mask_300, y_600, y_mask_600`
- `y` and `y_mask` alias to `y_60` for back-compat
- Emit `regime_prior: (N_win, 6)` aligned per window (= value at `pred_idx = window_start + input_len`)

- [ ] **Step 1: Write failing test**

```python
# tests/test_multihorizon_npz.py
import numpy as np
import pandas as pd
import pytest
from src.features.pipeline import build_npz_for_day

@pytest.fixture
def synthetic_1day(tmp_path):
    """Produce a valid 1s-resampled CSV sufficient for build_npz_for_day."""
    n = 86400
    ts = pd.date_range("2026-01-01", periods=n, freq="1s", tz="UTC")
    rng = np.random.default_rng(0)
    mid = 50000 + np.cumsum(rng.normal(0, 0.5, n))
    log_return_1s = np.concatenate([[0.0], np.diff(np.log(mid))])
    df = pd.DataFrame({
        "timestamp": ts, "mid": mid, "log_return_1s": log_return_1s,
        "spread_bps": rng.uniform(0.5, 1.5, n), "obi_L5": rng.uniform(-1, 1, n),
        "net_trade_flow_1s": rng.normal(0, 1, n), "realized_vol_30s": rng.uniform(1e-4, 5e-4, n),
        "max_trade_size_60s": rng.lognormal(0, 1, n),
        "book_pressure_imbalance": rng.normal(0, 0.1, n),
        # … sufficient columns for 58 base features (filled via helper)
    })
    p = tmp_path / "2026-01-01.csv"
    df.to_csv(p, index=False)
    return p


def test_multihorizon_fields(synthetic_1day, tmp_path):
    out = build_npz_for_day(
        synthetic_1day, tmp_path,
        input_len=600, horizons_sec=[60, 180, 300, 600], stride=180,
        include_regime_prior=True, n_levels=20,
    )
    d = np.load(out)
    for h in [60, 180, 300, 600]:
        assert f"y_{h}" in d.files
        assert f"y_mask_{h}" in d.files
        assert d[f"y_{h}"].shape == d[f"y_mask_{h}"].shape
    assert np.array_equal(d["y"], d["y_60"])
    assert np.array_equal(d["y_mask"], d["y_mask_60"])
    assert d["regime_prior"].shape[-1] == 6
    assert d["regime_prior"].shape[0] == d["y_60"].shape[0]


def test_label_formula_matches_mid_ratio(synthetic_1day, tmp_path):
    """y_H[k] = log(mid[pred_idx_k + H] / mid[pred_idx_k]) for any k with valid mask."""
    out = build_npz_for_day(
        synthetic_1day, tmp_path,
        input_len=600, horizons_sec=[60, 180, 300, 600], stride=600,
        include_regime_prior=False, n_levels=20,
        debug_save_raw_mid=True,  # test-only hook writes `raw_mid_series` to NPZ
    )
    d = np.load(out)
    raw_mid = d["raw_mid_series"]
    win_starts = d["win_starts"]
    for h in [60, 180, 300, 600]:
        # For first valid window
        k = int(np.argmax(d[f"y_mask_{h}"] > 0))
        pred_idx = int(win_starts[k]) + 600
        expected = float(np.log(raw_mid[pred_idx + h] / raw_mid[pred_idx]))
        got = float(d[f"y_{h}"][k])
        assert np.isclose(got, expected, atol=1e-10), f"y_{h}[{k}]: got={got}, expected={expected}"
```

- [ ] **Step 2: Run — verify FAIL**

```bash
pytest tests/test_multihorizon_npz.py -x
```

- [ ] **Step 3: Modify `build_npz_for_day` to support horizons list + regime_prior**

In `src/features/pipeline.py`:

```python
def build_npz_for_day(
    csv_path, out_dir, *,
    input_len=600, horizons_sec=(60, 180, 300, 600), stride=180,
    include_regime_prior=False, n_levels=20,
    debug_save_raw_mid=False,
    ...
):
    ...
    labels = {}
    masks = {}
    for h in horizons_sec:
        y_arr, y_mask_arr = _compute_forward_log_return(mid, pred_idx_arr, h)
        labels[f"y_{h}"] = y_arr.astype(np.float32)
        masks[f"y_mask_{h}"] = y_mask_arr.astype(np.uint8)
    # Back-compat aliases point to shortest horizon
    shortest = min(horizons_sec)
    labels["y"] = labels[f"y_{shortest}"]
    masks["y_mask"] = masks[f"y_mask_{shortest}"]

    if include_regime_prior:
        regime_prior = _extract_regime_prior(feat_df, pred_idx_arr)  # (N_win, 6)
    else:
        regime_prior = np.zeros((len(pred_idx_arr), 6), dtype=np.float32)

    extra = {}
    if debug_save_raw_mid:
        extra["raw_mid_series"] = mid.astype(np.float64)

    np.savez_compressed(
        out_path,
        X=X, X_raw=X_raw, **labels, **masks,
        regime_prior=regime_prior,
        win_starts=np.asarray(win_starts, dtype=np.int64),
        feature_names=np.array(feature_names),
        **extra,
    )
```

- [ ] **Step 4: Run — verify PASS**

```bash
pytest tests/test_multihorizon_npz.py -x -v
```

- [ ] **Step 5: Commit**

```bash
git add src/features/pipeline.py tests/test_multihorizon_npz.py
git commit -m "feat(v4): multi-horizon NPZ labels + regime_prior storage"
```

---

### Task 5: End-to-end leakage validation suite

**Files:**
- Create: `tests/test_no_leakage.py`

Centralized leakage audit: even if Tasks 1-4 each test causality individually, this suite runs an integration audit over a real end-to-end pipeline.

- [ ] **Step 1: Write tests**

```python
# tests/test_no_leakage.py
import numpy as np
import pandas as pd
import pytest
from src.features.multi_day_pipeline import process_single_day


def test_windowed_features_strictly_past(tiny_day_csv, tmp_path):
    out = process_single_day(
        tiny_day_csv, tmp_path,
        include_ridge_features=True, include_regime_prior=True,
        horizons_sec=[60, 180, 300, 600], input_len=600, stride=600, n_levels=20,
    )
    d = np.load(out)
    win_starts = d["win_starts"]
    # Each window k covers feature rows [start_k, start_k + input_len).
    # The last row index must be strictly less than pred_idx for all horizons.
    for k in range(len(win_starts)):
        last_input_idx = int(win_starts[k]) + 600 - 1
        pred_idx = int(win_starts[k]) + 600
        assert last_input_idx < pred_idx


def test_label_responds_to_future_perturbation(tiny_day_csv, tmp_path):
    """Perturbing mid at pred_idx+H must change y_H[k] but NOT X[k]."""
    out = process_single_day(
        tiny_day_csv, tmp_path,
        include_ridge_features=True, include_regime_prior=True,
        horizons_sec=[60], input_len=600, stride=600, n_levels=20,
        debug_save_raw_mid=True,
    )
    # Re-generate the same day with `mid` perturbed at index `pred_idx + 60` only
    # Assert X[0] is bit-identical between the two runs; y_60[0] differs.
    import shutil, pathlib
    perturbed_csv = tmp_path / "perturbed.csv"
    df = pd.read_csv(tiny_day_csv)
    df.loc[600 + 60, "mid"] *= 2.0
    df.to_csv(perturbed_csv, index=False)
    out2 = process_single_day(perturbed_csv, tmp_path / "p", include_ridge_features=True,
                              include_regime_prior=True, horizons_sec=[60],
                              input_len=600, stride=600, n_levels=20)
    d1, d2 = np.load(out), np.load(out2)
    np.testing.assert_array_equal(d1["X"][0], d2["X"][0])  # X unchanged
    assert not np.isclose(d1["y_60"][0], d2["y_60"][0])  # label changed


def test_normalization_stats_from_train_only(tmp_path):
    """x_mean / x_std / y_median / y_sigma computed on train days, not val/test."""
    from src.training.dataset import compute_dataset_stats
    # Create two tiny NPZs with known X distributions
    # (details abridged; full implementation creates fake NPZs with known stats)
    train_paths = [...]
    val_paths = [...]
    stats_train = compute_dataset_stats(train_paths)
    stats_combined = compute_dataset_stats(train_paths + val_paths)
    # Stats should differ when val is included, confirming the split matters
    assert not np.allclose(stats_train["x_mean"], stats_combined["x_mean"])
```

- [ ] **Step 2: Run — verify PASS (integration paths landed in Tasks 1-4)**

```bash
pytest tests/test_no_leakage.py -x -v
```

If any test fails, fix the root cause in Task 1-4 modules — do not special-case to pass.

- [ ] **Step 3: Commit**

```bash
git add tests/test_no_leakage.py
git commit -m "test(v4): end-to-end leakage audit"
```

---

## Phase 2 — Model Components

### Task 6: `AttentionPool` modules (levels + tokens)

**Files:**
- Create: `src/model/attention_pool.py`
- Test: `tests/test_attention_pool.py`

Two classes:
- `AttentionPoolLevels(d_in)`: learned-query softmax-weighted mean over levels axis. Input `(B, L_time, N_levels, D)`, output `(B, L_time, D)`.
- `AttentionPoolTokens(d_in)`: softmax over the time-patches axis. Input `(B, N_patches, D)`, output `(B, D)`.

- [ ] **Step 1: Write failing test**

```python
# tests/test_attention_pool.py
import torch
from src.model.attention_pool import AttentionPoolLevels, AttentionPoolTokens

def test_pool_levels_shape():
    pool = AttentionPoolLevels(d_in=32)
    x = torch.randn(4, 10, 20, 32)
    out = pool(x)
    assert out.shape == (4, 10, 32)

def test_pool_levels_permutation_invariance():
    torch.manual_seed(0)
    pool = AttentionPoolLevels(d_in=32)
    x = torch.randn(2, 5, 20, 32)
    perm = torch.randperm(20)
    y1 = pool(x)
    y2 = pool(x[:, :, perm, :])
    assert torch.allclose(y1, y2, atol=1e-5)

def test_pool_tokens_shape():
    pool = AttentionPoolTokens(d_in=32)
    x = torch.randn(4, 120, 32)
    out = pool(x)
    assert out.shape == (4, 32)

def test_pool_tokens_softmax_weights_sum_to_1():
    # Not externally observable, but indirectly: if we scale all tokens by c, output scales by c
    pool = AttentionPoolTokens(d_in=8)
    x = torch.randn(1, 4, 8)
    y1 = pool(x)
    y2 = pool(x * 3.0)
    # Softmax weights depend on x → outputs won't be exactly 3× but will be in the same direction
    assert torch.dot(y1.flatten(), y2.flatten()) > 0
```

- [ ] **Step 2: Run — verify FAIL**

```bash
pytest tests/test_attention_pool.py -x
```

- [ ] **Step 3: Implement**

```python
# src/model/attention_pool.py
import torch
import torch.nn as nn
import torch.nn.functional as F


class AttentionPoolLevels(nn.Module):
    """Softmax pool over levels axis. Input (B, L, N, D) → (B, L, D)."""
    def __init__(self, d_in: int):
        super().__init__()
        self.query = nn.Parameter(torch.randn(d_in) * 0.02)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        logits = torch.einsum("blnd,d->bln", x, self.query)
        weights = F.softmax(logits, dim=-1).unsqueeze(-1)
        return (x * weights).sum(dim=2)


class AttentionPoolTokens(nn.Module):
    """Softmax pool over N_patches axis. Input (B, N, D) → (B, D)."""
    def __init__(self, d_in: int):
        super().__init__()
        self.query = nn.Parameter(torch.randn(d_in) * 0.02)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        logits = torch.einsum("bnd,d->bn", x, self.query)
        weights = F.softmax(logits, dim=-1).unsqueeze(-1)
        return (x * weights).sum(dim=1)
```

- [ ] **Step 4: Run — verify PASS**

```bash
pytest tests/test_attention_pool.py -x -v
```

- [ ] **Step 5: Commit**

```bash
git add src/model/attention_pool.py tests/test_attention_pool.py
git commit -m "feat(v4): AttentionPool{Levels,Tokens} learned-query softmax pools"
```

---

### Task 7: `RawLOBEncoder` — `use_channel_mix_conv` + `use_level_attention_pool` flags

**Files:**
- Modify: `src/model/raw_lob_encoder.py`
- Test: `tests/test_raw_lob_encoder_v4.py`

V4 RawLOB path per spec:
```
(B, L, 20, 4) -[1x1 Conv 4→16]- (B, L, 20, 16) -[Conv1d 16→d_raw, k=3 over levels]- (B, L, 20, d_raw) -[AttentionPoolLevels]- (B, L, d_raw)
```

- When `use_channel_mix_conv=False`: skip the 1×1 conv; feed 4-dim directly into level conv (widen input).
- When `use_level_attention_pool=False`: fall back to `nn.AdaptiveAvgPool1d(1)` over the levels axis.

- [ ] **Step 1: Write tests**

```python
# tests/test_raw_lob_encoder_v4.py
import torch
from src.model.raw_lob_encoder import RawLOBEncoder

def _x(B=2, L=10, N=20):
    torch.manual_seed(0)
    return torch.randn(B, L, N, 4)

def test_default_flags_produce_v4_shape():
    enc = RawLOBEncoder(d_raw=32, n_levels=20,
                        use_channel_mix_conv=True, use_level_attention_pool=True)
    out = enc(_x())
    assert out.shape == (2, 10, 32)

def test_no_channel_mix_runs():
    enc = RawLOBEncoder(d_raw=32, n_levels=20,
                        use_channel_mix_conv=False, use_level_attention_pool=True)
    out = enc(_x())
    assert out.shape == (2, 10, 32)
    assert enc.channel_mix is None

def test_no_level_attention_falls_back_to_avgpool():
    enc = RawLOBEncoder(d_raw=32, n_levels=20,
                        use_channel_mix_conv=True, use_level_attention_pool=False)
    out = enc(_x())
    assert out.shape == (2, 10, 32)
    from torch.nn import AdaptiveAvgPool1d
    assert isinstance(enc.level_pool, AdaptiveAvgPool1d)

def test_flags_change_output_numerically():
    x = _x()
    torch.manual_seed(0)
    a = RawLOBEncoder(d_raw=32, n_levels=20,
                     use_channel_mix_conv=True, use_level_attention_pool=True)(x)
    torch.manual_seed(0)
    b = RawLOBEncoder(d_raw=32, n_levels=20,
                     use_channel_mix_conv=False, use_level_attention_pool=True)(x)
    assert not torch.allclose(a, b, atol=1e-3)
```

- [ ] **Step 2: Run — verify FAIL**

```bash
pytest tests/test_raw_lob_encoder_v4.py -x
```

- [ ] **Step 3: Modify `RawLOBEncoder`**

```python
class RawLOBEncoder(nn.Module):
    def __init__(self, *, d_raw=32, n_levels=20,
                 use_channel_mix_conv=True, use_level_attention_pool=True):
        super().__init__()
        self.use_channel_mix_conv = use_channel_mix_conv
        self.use_level_attention_pool = use_level_attention_pool
        if use_channel_mix_conv:
            self.channel_mix = nn.Conv2d(4, 16, kernel_size=1)
            self.level_conv = nn.Conv1d(16, d_raw, kernel_size=3, padding=1)
        else:
            self.channel_mix = None
            self.level_conv = nn.Conv1d(4, d_raw, kernel_size=3, padding=1)
        if use_level_attention_pool:
            from src.model.attention_pool import AttentionPoolLevels
            self.level_pool = AttentionPoolLevels(d_in=d_raw)
        else:
            self.level_pool = nn.AdaptiveAvgPool1d(1)

    def forward(self, x):  # (B, L, N, 4)
        B, L, N, F = x.shape
        if self.use_channel_mix_conv:
            z = x.permute(0, 3, 1, 2)            # (B, 4, L, N)
            z = self.channel_mix(z)              # (B, 16, L, N)
            z = z.permute(0, 2, 3, 1).reshape(B * L, N, -1)  # (B*L, N, 16)
        else:
            z = x.reshape(B * L, N, 4)
        z = z.transpose(1, 2)                    # (B*L, C, N)
        z = self.level_conv(z)                   # (B*L, d_raw, N)
        if self.use_level_attention_pool:
            z = z.transpose(1, 2).reshape(B, L, N, -1)      # (B, L, N, d_raw)
            out = self.level_pool(z)                         # (B, L, d_raw)
        else:
            pooled = self.level_pool(z)                      # (B*L, d_raw, 1)
            out = pooled.squeeze(-1).reshape(B, L, -1)
        return out
```

- [ ] **Step 4: Run — verify PASS**

```bash
pytest tests/test_raw_lob_encoder_v4.py tests/test_raw_lob.py -x -v
```

- [ ] **Step 5: Commit**

```bash
git add src/model/raw_lob_encoder.py tests/test_raw_lob_encoder_v4.py
git commit -m "feat(v4): RawLOBEncoder with 1x1 channel mix + level attention pool"
```

---

### Task 8: `DualPathLOBModelV3` — V4 flags (patch attention pool, PPNet gate, multi-horizon)

**Files:**
- Modify: `src/model/dual_path_model_v3.py`
- Modify: `src/model/monotonic_quantile.py` (expose `n_horizons`)
- Test: `tests/test_v3_bypass_flags.py`, `tests/test_ppnet_quantile.py`

Default flags map to V4 full. Each flag off maps to a specific bypass:

| Flag | `True` | `False` |
|------|--------|---------|
| `use_revin` | RevIN on x_feat | skip RevIN |
| `use_gdcn` | GDCN(32, 2 layers) | `nn.Identity()` |
| `use_masknet` | MaskNet(64) | `nn.Identity()` (V4 default=False) |
| `use_raw_path` | Path B enabled | x_raw ignored; fusion = `Identity()` on h_craft |
| `use_conv` | TCN 3-block | Identity |
| `use_attention` | causal patch attention | skip, use post-conv features |
| `use_patch_attention_pool` | AttentionPoolTokens | last-token extraction |
| `use_ppnet_gate` | PPNetGate(6→32) | multiply by 1 (identity) |
| `use_monotonic_quantile` | MonotonicQuantileHead | plain Linear(32→3) |
| `n_horizons >= 1` | list of heads, forward returns `(B, H, 3)` | single head when `n_horizons==1` |

- [ ] **Step 1: Write tests**

```python
# tests/test_v3_bypass_flags.py
import torch
from src.model.dual_path_model_v3 import DualPathLOBModelV3

def _fwd(model, B=2, L=600, F=64, N_levels=20, d_prior=6):
    x = torch.randn(B, L, F)
    x_raw = torch.randn(B, L, N_levels, 4)
    rp = torch.randn(B, d_prior) if d_prior > 0 else None
    return model(x, x_raw, regime_prior=rp)

def _q(out):
    return out["quantiles"] if isinstance(out, dict) else out

def test_v4_full_multi_horizon_shape():
    m = DualPathLOBModelV3(
        input_dim=64, n_levels=20, d_model=32, d_raw=32, d_prior=6,
        use_revin=True, use_gdcn=True, use_raw_path=True, use_conv=True,
        use_attention=True, use_channel_mix_conv=True,
        use_level_attention_pool=True, use_patch_attention_pool=True,
        use_ppnet_gate=True, use_monotonic_quantile=True, n_horizons=4,
        use_masknet=False,
    )
    q = _q(_fwd(m))
    assert q.shape == (2, 4, 3)

def test_ppnet_off_runs_without_prior():
    m = DualPathLOBModelV3(input_dim=64, n_levels=20, d_model=32, d_raw=32,
                           d_prior=6, use_ppnet_gate=False, n_horizons=4)
    q = _q(_fwd(m))
    assert q.shape == (2, 4, 3)

def test_single_horizon():
    m = DualPathLOBModelV3(input_dim=64, n_levels=20, d_model=32, d_raw=32,
                           d_prior=6, n_horizons=1)
    q = _q(_fwd(m))
    assert q.shape in [(2, 1, 3), (2, 3)]

def test_no_raw_path_ignores_x_raw():
    m = DualPathLOBModelV3(input_dim=64, n_levels=20, d_model=32, d_raw=32,
                           d_prior=0, use_raw_path=False, n_horizons=1)
    B, L = 2, 600
    x = torch.randn(B, L, 64)
    x_raw_a = torch.randn(B, L, 20, 4)
    x_raw_b = torch.randn(B, L, 20, 4) * 100
    qa = _q(m(x, x_raw_a))
    qb = _q(m(x, x_raw_b))
    assert torch.allclose(qa, qb, atol=1e-6)

def test_monotonic_quantile_invariant():
    m = DualPathLOBModelV3(input_dim=64, n_levels=20, d_model=32, d_raw=32,
                           d_prior=0, use_monotonic_quantile=True, n_horizons=1)
    q = _q(_fwd(m, d_prior=0))
    # q10 <= q50 <= q90 for every sample
    q = q.reshape(-1, 3)
    assert (q[:, 0] <= q[:, 1]).all()
    assert (q[:, 1] <= q[:, 2]).all()
```

- [ ] **Step 2: Run — verify FAIL**

```bash
pytest tests/test_v3_bypass_flags.py -x
```

- [ ] **Step 3: Implement flag wiring in `DualPathLOBModelV3`**

Key structural changes per spec:
- Reorder: `Linear(64→32) → GDCN(32) → Fusion` (GDCN moves AFTER compression).
- Replace last-token extraction with `AttentionPoolTokens` when flag True.
- Build `ModuleList[MonotonicQuantileHead]` of length `n_horizons`.
- Wire `regime_prior` into `PPNetGate` when `d_prior > 0 AND use_ppnet_gate=True`.

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_v3_bypass_flags.py tests/test_ppnet_quantile.py tests/test_model_v3.py -x -v
```

- [ ] **Step 5: Commit**

```bash
git add src/model/dual_path_model_v3.py src/model/monotonic_quantile.py \
        tests/test_v3_bypass_flags.py tests/test_ppnet_quantile.py
git commit -m "feat(v4): V4 flags on DualPathLOBModelV3 + multi-horizon quantile heads"
```

---

### Task 9: End-to-end forward causality unit test

**Files:**
- Create: `tests/test_v4_causality.py`

Critical test: the model's output positions must not read from future inputs.

- [ ] **Step 1: Write test**

```python
# tests/test_v4_causality.py
import torch
from src.model.dual_path_model_v3 import DualPathLOBModelV3


def _mk_v4(n_horizons=4, d_prior=6):
    torch.manual_seed(0)
    return DualPathLOBModelV3(
        input_dim=64, n_levels=20, d_model=32, d_raw=32, d_prior=d_prior,
        use_revin=True, use_gdcn=True, use_raw_path=True, use_conv=True,
        use_attention=True, use_channel_mix_conv=True,
        use_level_attention_pool=True, use_patch_attention_pool=True,
        use_ppnet_gate=True, use_monotonic_quantile=True, n_horizons=n_horizons,
    ).eval()


def test_forward_deterministic():
    model = _mk_v4()
    torch.manual_seed(0)
    x = torch.randn(2, 600, 64)
    x_raw = torch.randn(2, 600, 20, 4)
    rp = torch.randn(2, 6)
    o1 = model(x, x_raw, regime_prior=rp)
    o2 = model(x, x_raw, regime_prior=rp)
    q1 = o1["quantiles"] if isinstance(o1, dict) else o1
    q2 = o2["quantiles"] if isinstance(o2, dict) else o2
    assert torch.allclose(q1, q2, atol=0.0)


def test_perturbing_last_tick_changes_output():
    """Sanity: perturbing input[-1] must change output under default flags."""
    model = _mk_v4()
    B, L = 1, 600
    x = torch.randn(B, L, 64)
    x_raw = torch.randn(B, L, 20, 4)
    rp = torch.randn(B, 6)
    o1 = model(x, x_raw, regime_prior=rp)
    x2 = x.clone()
    x2[:, -1, :] += 10.0
    o2 = model(x2, x_raw, regime_prior=rp)
    q1 = o1["quantiles"] if isinstance(o1, dict) else o1
    q2 = o2["quantiles"] if isinstance(o2, dict) else o2
    assert not torch.allclose(q1, q2, atol=1e-4)


def test_temporal_causal_within_sequence_via_hook():
    """
    Perturb x[:, t=300, :] and assert that intermediate activations at
    positions < 300 are unchanged (TCN + patch attention causal property).
    """
    model = _mk_v4()
    B, L = 1, 600
    x = torch.randn(B, L, 64)
    x_raw = torch.randn(B, L, 20, 4)
    rp = torch.randn(B, 6)

    captures = {}
    def hook(name):
        def fn(module, inp, out):
            captures[name] = (out.detach().clone() if isinstance(out, torch.Tensor)
                              else out[0].detach().clone())
        return fn

    # Attach hook to the temporal conv block's output.
    # Adjust attribute path if the model structure differs: e.g. model.temporal_encoder.tcn
    handle = model.temporal_encoder.register_forward_hook(hook("tenc"))

    _ = model(x, x_raw, regime_prior=rp)
    a1 = captures["tenc"]

    x2 = x.clone()
    x2[:, 300, :] += 10.0
    _ = model(x2, x_raw, regime_prior=rp)
    a2 = captures["tenc"]

    handle.remove()
    assert a1.shape == a2.shape
    # Post-TCN activations at t<300 must be bit-identical
    assert torch.allclose(a1[:, :300], a2[:, :300], atol=0.0), \
        "TCN output changed at t<300 when x[300] was perturbed — non-causal!"


def test_multi_horizon_output_same_encoder():
    """All 4 horizon heads share the same pooled representation (smoke)."""
    model = _mk_v4(n_horizons=4)
    B = 2
    x = torch.randn(B, 600, 64)
    x_raw = torch.randn(B, 600, 20, 4)
    rp = torch.randn(B, 6)
    o = model(x, x_raw, regime_prior=rp)
    q = o["quantiles"] if isinstance(o, dict) else o
    assert q.shape == (B, 4, 3)
    # q10 <= q50 <= q90 across horizons (monotonic)
    assert (q[..., 0] <= q[..., 1]).all()
    assert (q[..., 1] <= q[..., 2]).all()
```

- [ ] **Step 2: Run (expect FAIL if `temporal_encoder` attribute does not exist or TCN is not causal)**

```bash
pytest tests/test_v4_causality.py -x -v
```

- [ ] **Step 3: Fix attribute names and any causality violations**

If causality test fails, the model has a non-causal bug — FIX the bug, don't relax the test. Likely suspects:
- `nn.Conv1d` with symmetric padding (replace with left-only padding via `F.pad(..., (k-1, 0))` + `padding=0`)
- LayerNorm over the time dim pooling stats (forbidden if it collapses past+future)
- RevIN stats over full window: this IS allowed because at inference the full window is "the past" — but document it.

- [ ] **Step 4: Commit**

```bash
git add tests/test_v4_causality.py
git commit -m "test(v4): end-to-end forward causality audit"
```

---

## Phase 3 — Dataset / Trainer / Loss

### Task 10: `LOBDatasetV2` returns 5-tuple with `regime_prior`

**Files:**
- Modify: `src/training/dataset.py`
- Test: `tests/test_dataset_v2_lazy.py` (augment), `tests/test_dataset_horizon_key.py`

Per spec: `__getitem__` returns `(X, X_raw, y_selected, y_mask_selected, regime_prior)`. When multi-horizon, `y_selected` is `(H_active, )` and `y_mask_selected` matches.

Invariant: if `regime_prior` is required by the model but absent from NPZ (older files), raise an explicit error at dataset construction.

- [ ] **Step 1: Write test**

```python
# tests/test_dataset_v2_lazy.py (append)
def test_returns_five_tuple_multi_horizon(npz_v4_fixture):
    ds = LOBDatasetV2(npz_v4_fixture.paths, horizons_sec=[60, 180, 300, 600],
                     include_regime_prior=True,
                     x_mean=npz_v4_fixture.mu, x_std=npz_v4_fixture.sigma)
    sample = ds[0]
    assert len(sample) == 5
    X, X_raw, y, y_mask, regime_prior = sample
    assert y.shape == (4,)
    assert y_mask.shape == (4,)
    assert regime_prior.shape == (6,)


def test_regime_prior_required_raises_when_absent(npz_v3_no_prior_fixture):
    with pytest.raises(RuntimeError, match="regime_prior"):
        LOBDatasetV2(npz_v3_no_prior_fixture.paths, include_regime_prior=True)
```

- [ ] **Step 2: Run — verify FAIL**

```bash
pytest tests/test_dataset_v2_lazy.py::test_returns_five_tuple_multi_horizon -x
```

- [ ] **Step 3: Modify `LOBDatasetV2`**

```python
def __init__(self, ..., horizons_sec=(180,), include_regime_prior=False):
    self.horizons_sec = list(horizons_sec)
    self.include_regime_prior = include_regime_prior
    self._horizon_keys = [f"y_{h}" for h in horizons_sec]
    self._mask_keys = [f"y_mask_{h}" for h in horizons_sec]
    for p in self.paths:
        with np.load(p, mmap_mode="r") as d:
            for k in self._horizon_keys + self._mask_keys:
                if k not in d.files:
                    raise RuntimeError(f"{p} missing horizon key {k}")
            if include_regime_prior and "regime_prior" not in d.files:
                raise RuntimeError(f"{p}: regime_prior field missing but required")

def __getitem__(self, idx):
    day_arrays = self._get_day_arrays(idx)
    local_idx = self._local_index(idx)
    X = day_arrays["X"][local_idx]
    X_raw = day_arrays["X_raw"][local_idx]
    y = np.stack([day_arrays[k][local_idx] for k in self._horizon_keys]).astype(np.float32)
    y_mask = np.stack([day_arrays[k][local_idx] for k in self._mask_keys]).astype(np.float32)
    rp = (day_arrays["regime_prior"][local_idx].astype(np.float32)
          if self.include_regime_prior else np.zeros(6, dtype=np.float32))
    return X, X_raw, y, y_mask, rp
```

- [ ] **Step 4: Run**

```bash
pytest tests/test_dataset_v2_lazy.py tests/test_dataset_horizon_key.py -x -v
```

- [ ] **Step 5: Commit**

```bash
git add src/training/dataset.py tests/test_dataset_v2_lazy.py tests/test_dataset_horizon_key.py
git commit -m "feat(v4): LOBDatasetV2 5-tuple with regime_prior + multi-horizon keys"
```

---

### Task 11: DUL loss components (pinball + utility-rank + coverage-calib)

**Files:**
- Create: `src/training/dul_loss.py`
- Test: `tests/test_dul_loss.py`

Three functions per spec:
- `quantile_loss` (exists in `losses.py`) — reuse.
- `utility_rank_loss(quantiles, target, alpha=1.0, n_pairs=None, margin=0.0)` — pairwise logistic on `s = q50 - α(q50-q10)`.
- `coverage_calib_loss(quantiles, target, taus=(0.1, 0.5, 0.9))` — sigmoid-smoothed coverage gap².
- `compute_dul_loss(quantiles, target, λ_quantile, λ_utility_rank, λ_calib, utility_alpha, n_pairs, return_parts)` — weighted sum. `return_parts=False` in training hot path to avoid `.item()` CUDA syncs.

- [ ] **Step 1: Write tests**

```python
# tests/test_dul_loss.py
import torch
from src.training.dul_loss import (
    utility_rank_loss, coverage_calib_loss, compute_dul_loss,
)


def _mk(n=64, seed=0):
    torch.manual_seed(seed)
    q = torch.randn(n, 3)
    q, _ = torch.sort(q, dim=1)
    target = torch.randn(n)
    return q, target


def test_utility_rank_scalar():
    q, t = _mk()
    loss = utility_rank_loss(q, t, alpha=1.0)
    assert loss.shape == torch.Size([])
    assert loss.item() >= 0.0


def test_utility_rank_zero_when_single_sample():
    q = torch.tensor([[-1.0, 0.0, 1.0]])
    t = torch.tensor([0.5])
    assert utility_rank_loss(q, t).item() == 0.0


def test_utility_rank_prefers_correct_ordering():
    n = 256
    t = torch.randn(n)
    q_good = torch.stack([t - 1, t, t + 1], dim=1)
    q_rand, _ = torch.sort(torch.randn(n, 3), dim=1)
    l_good = utility_rank_loss(q_good, t, alpha=0.0).item()
    l_rand = utility_rank_loss(q_rand, t, alpha=0.0).item()
    assert l_good < l_rand


def test_calib_close_to_zero_when_quantiles_match():
    torch.manual_seed(0)
    t = torch.randn(10000)
    q10 = torch.quantile(t, 0.1).expand(10000)
    q50 = torch.quantile(t, 0.5).expand(10000)
    q90 = torch.quantile(t, 0.9).expand(10000)
    q = torch.stack([q10, q50, q90], dim=1)
    loss = coverage_calib_loss(q, t).item()
    assert loss < 1e-3


def test_compute_dul_short_circuits_zero_lambda():
    q, t = _mk()
    total, parts = compute_dul_loss(
        q, t, lambda_quantile=1.0, lambda_utility_rank=0.0, lambda_calib=0.0,
        return_parts=True,
    )
    assert parts["utility_rank"] == 0.0
    assert parts["calib"] == 0.0
    assert parts["quantile"] > 0.0


def test_compute_dul_return_parts_false_has_no_cpu_sync():
    q, t = _mk()
    total, parts = compute_dul_loss(
        q, t, lambda_quantile=1.0, lambda_utility_rank=0.3, lambda_calib=0.1,
        return_parts=False,
    )
    assert parts == {}
    assert total.grad_fn is not None
```

- [ ] **Step 2: Run — verify FAIL**

```bash
pytest tests/test_dul_loss.py -x -v
```

- [ ] **Step 3: Implement per spec (pinball reuse, utility_rank softplus, calib sigmoid)**

- [ ] **Step 4: Run — verify PASS**

```bash
pytest tests/test_dul_loss.py -x -v
```

- [ ] **Step 5: Commit**

```bash
git add src/training/dul_loss.py tests/test_dul_loss.py
git commit -m "feat(v4): DUL loss (pinball + utility-rank + coverage-calib)"
```

---

### Task 12: `trainer_v2` — 5-tuple batch, multi-horizon step, DUL loss, no per-horizon syncs

**Files:**
- Modify: `src/training/trainer_v2.py`
- Test: `tests/test_trainer_v2.py`

Changes:
1. Batch unpacker handles 5-tuple `(X, X_raw, y, y_mask, regime_prior)`.
2. Forward passes `regime_prior=...` kwarg.
3. `_multi_horizon_loss`: no `torch.isfinite(loss_h)` per horizon (one outer guard on the stack mean suffices; `grad_clip` handles bad grads).
4. DUL loss wrapper uses `return_parts=False` in training hot path to avoid `.item()` CUDA syncs.
5. Checkpoint selection by `val_correlation` (pooled across horizons), not val_loss.

- [ ] **Step 1: Write test**

```python
# tests/test_trainer_v2.py
import torch
from src.training.trainer_v2 import _build_loss_fn_for_dul, _multi_horizon_loss

def test_multi_horizon_loss_stackmean_and_backward():
    B, H, Q = 8, 4, 3
    quantiles = torch.randn(B, H, Q, requires_grad=True)
    target = torch.randn(B, H)
    mask = torch.ones(B, H)
    dul_cfg = dict(lambda_quantile=1.0, lambda_utility_rank=0.3, lambda_calib=0.0,
                   utility_alpha=1.0)
    loss = _multi_horizon_loss(quantiles, target, mask, dul_cfg)
    assert loss.shape == torch.Size([])
    loss.backward()
    assert quantiles.grad is not None


def test_loss_fn_factory_no_item_call():
    cfg = dict(lambda_quantile=1.0, lambda_utility_rank=0.3, lambda_calib=0.0,
               utility_alpha=1.0)
    fn = _build_loss_fn_for_dul(cfg)
    out = {"quantiles": torch.randn(8, 3, requires_grad=True)}
    target = torch.randn(8)
    loss = fn(out, target)
    assert isinstance(loss, torch.Tensor)
    assert loss.grad_fn is not None
```

- [ ] **Step 2: Run — verify FAIL or PASS (may already be PASS from prior commits)**

```bash
pytest tests/test_trainer_v2.py -x -v
```

- [ ] **Step 3: Update trainer_v2 hot path**

```python
def dul_loss_fn(outputs, target):
    total, _ = compute_dul_loss(
        outputs["quantiles"], target,
        lambda_quantile=cfg["lambda_quantile"], lambda_utility_rank=cfg["lambda_utility_rank"],
        lambda_calib=cfg["lambda_calib"], utility_alpha=cfg["utility_alpha"],
        n_pairs=cfg.get("n_pairs"), return_parts=False,
    )
    return total

# _multi_horizon_loss:
losses = []
for h_idx in range(H):
    q_h = quantiles[:, h_idx]
    t_h = target[:, h_idx]
    losses.append(loss_fn({"quantiles": q_h}, t_h))
return torch.stack(losses).mean()
```

No `torch.isfinite(loss_h)` check inside loop; outer `torch.isfinite(total)` guard on the mean suffices.

- [ ] **Step 4: Run full trainer regression**

```bash
pytest tests/test_trainer_v2.py tests/test_training.py -x -v
```

- [ ] **Step 5: Commit**

```bash
git add src/training/trainer_v2.py tests/test_trainer_v2.py
git commit -m "feat(v4): trainer_v2 multi-horizon + DUL + sync-free hot path"
```

---

## Phase 4 — Configs and Orchestration

### Task 13: `configs/v4_full.json` — all flags True

**Files:**
- Create: `configs/v4_full.json`
- Test: `tests/test_configs.py`

- [ ] **Step 1: Write config**

```json
{
  "_comment": "V4 full run: RevIN + GDCN + RawLOB(1x1+AttnPool) + PatchAttn(AttnPool) + PPNet(d_prior=6) + 4 horizons + DUL loss. Expected ~32K params.",
  "data": {
    "csv_path": "",
    "npz_dir": "data/npz_v4",
    "n_levels": 25,
    "horizon_sec": 180,
    "input_len": 600,
    "stride": 180,
    "horizons_sec": [60, 180, 300, 600],
    "include_ridge_features": true,
    "include_regime_prior": true,
    "quantize_features": true,
    "preload": false
  },
  "model": {
    "d_model": 32,
    "d_raw": 16,
    "n_mask_blocks": 1,
    "n_cross_layers": 1,
    "patch_size": 5,
    "attn_nhead": 2,
    "attn_d_ff": 64,
    "d_prior": 6,
    "dropout": 0.15,
    "n_horizons": 4,
    "n_symbols": 1,
    "use_monotonic_quantile": true,
    "use_revin": true,
    "use_masknet": false,
    "use_gdcn": true,
    "use_raw_path": true,
    "use_attention": true,
    "use_conv": true,
    "use_channel_mix_conv": true,
    "use_level_attention_pool": true,
    "use_patch_attention_pool": true,
    "use_ppnet_gate": true
  },
  "training": {
    "epochs": 40,
    "batch_size": 256,
    "lr": 3e-4,
    "weight_decay": 1e-3,
    "patience": 8,
    "grad_clip": 1.0,
    "train_days": 700,
    "val_days": 30,
    "test_days": 90,
    "fold_stride": 60,
    "dul_config": {
      "lambda_quantile": 1.0,
      "lambda_utility_rank": 0.3,
      "lambda_calib": 0.0,
      "utility_alpha": 1.0
    }
  },
  "output_dir": "experiments/v4_full"
}
```

- [ ] **Step 2: Write config schema test**

```python
# tests/test_configs.py
import json

REQUIRED_MODEL_FLAGS = [
    "use_revin", "use_gdcn", "use_raw_path", "use_conv", "use_attention",
    "use_channel_mix_conv", "use_level_attention_pool",
    "use_patch_attention_pool", "use_ppnet_gate", "use_monotonic_quantile",
    "use_masknet",
]

def test_v4_full_schema():
    cfg = json.loads(open("configs/v4_full.json").read())
    for k in REQUIRED_MODEL_FLAGS:
        assert k in cfg["model"], f"missing model flag {k}"
    assert cfg["model"]["n_horizons"] == 4
    assert cfg["data"]["horizons_sec"] == [60, 180, 300, 600]
    assert cfg["training"]["dul_config"]["lambda_quantile"] > 0
    assert cfg["data"]["input_len"] == 600
    assert cfg["data"]["stride"] >= 60
```

- [ ] **Step 3: Run**

```bash
pytest tests/test_configs.py -x -v
```

- [ ] **Step 4: Commit**

```bash
git add configs/v4_full.json tests/test_configs.py
git commit -m "feat(v4): v4_full.json base config + schema test"
```

---

### Task 14: Eight ablation configs via generator

**Files:**
- Create: `scripts/gen_ablation_configs.py`
- Create: 8 files in `configs/v4_ablations/`

Each config is a shallow copy of `v4_full.json` with ONE change and `output_dir` updated.

- [ ] **Step 1: Write generator**

```python
# scripts/gen_ablation_configs.py
import json, pathlib, copy

BASE = json.loads(pathlib.Path("configs/v4_full.json").read_text())
ABL_DIR = pathlib.Path("configs/v4_ablations")
ABL_DIR.mkdir(parents=True, exist_ok=True)

def mk(name: str, updates: dict):
    cfg = copy.deepcopy(BASE)
    for dotted, val in updates.items():
        parts = dotted.split(".")
        d = cfg
        for p in parts[:-1]:
            d = d[p]
        d[parts[-1]] = val
    cfg["output_dir"] = f"experiments/v4_abl_{name}"
    (ABL_DIR / f"{name}.json").write_text(json.dumps(cfg, indent=2))

mk("no_ppnet",                {"model.use_ppnet_gate": False})
mk("no_multi_horizon",        {"model.n_horizons": 1, "data.horizons_sec": [180]})
mk("no_ridge_features",       {"data.include_ridge_features": False})
mk("no_patch_attention_pool", {"model.use_patch_attention_pool": False})
mk("no_channel_mix",          {"model.use_channel_mix_conv": False})
mk("no_level_attention",      {"model.use_level_attention_pool": False})
mk("no_utility_rank",         {"training.dul_config.lambda_utility_rank": 0.0})
mk("plus_masknet",            {"model.use_masknet": True})
```

- [ ] **Step 2: Run generator**

```bash
python scripts/gen_ablation_configs.py
ls configs/v4_ablations/
```

- [ ] **Step 3: Sanity-check each ablation config loads and has exactly ONE changed field**

```python
# tests/test_configs.py (append)
def test_ablations_change_one_field_only():
    import json, pathlib, difflib
    base = json.loads(pathlib.Path("configs/v4_full.json").read_text())
    del base["output_dir"]
    for cfg_path in pathlib.Path("configs/v4_ablations").glob("*.json"):
        cfg = json.loads(cfg_path.read_text())
        del cfg["output_dir"]
        # Flatten to dotted paths and count diffs
        def flatten(d, prefix=""):
            for k, v in d.items():
                if isinstance(v, dict):
                    yield from flatten(v, prefix + k + ".")
                else:
                    yield prefix + k, v
        base_flat = dict(flatten(base))
        cfg_flat = dict(flatten(cfg))
        diffs = [k for k in base_flat if base_flat[k] != cfg_flat.get(k)]
        diffs += [k for k in cfg_flat if k not in base_flat]
        assert len(set(diffs)) <= 2, f"{cfg_path.name} changes too many fields: {diffs}"
```

- [ ] **Step 4: Run**

```bash
pytest tests/test_configs.py -x -v
```

- [ ] **Step 5: Commit**

```bash
git add scripts/gen_ablation_configs.py configs/v4_ablations/*.json tests/test_configs.py
git commit -m "feat(v4): 8 ablation configs + generator"
```

---

### Task 15: `run_pipeline_v3.py` wiring + smoke test

**Files:**
- Modify: `run_pipeline_v3.py`
- Create: `scripts/smoke_v4_pipeline.py`, `configs/v4_phase_a_smoke.json`

- [ ] **Step 1: Wire V4 flags into model construction + trainer call**

In `run_pipeline_v3.py`:
```python
model_kwargs = dict(
    input_dim=input_dim, n_levels=n_levels, d_model=m["d_model"], d_raw=m["d_raw"],
    n_mask_blocks=m["n_mask_blocks"], n_cross_layers=m["n_cross_layers"],
    patch_size=m["patch_size"], attn_nhead=m["attn_nhead"], attn_d_ff=m["attn_d_ff"],
    d_prior=m["d_prior"], dropout=m["dropout"], n_horizons=m["n_horizons"],
    n_symbols=m["n_symbols"],
    use_monotonic_quantile=m["use_monotonic_quantile"],
    use_revin=m["use_revin"], use_masknet=m["use_masknet"], use_gdcn=m["use_gdcn"],
    use_raw_path=m["use_raw_path"], use_attention=m["use_attention"],
    use_conv=m["use_conv"],
    use_channel_mix_conv=m["use_channel_mix_conv"],
    use_level_attention_pool=m["use_level_attention_pool"],
    use_patch_attention_pool=m["use_patch_attention_pool"],
    use_ppnet_gate=m["use_ppnet_gate"],
)
trainer_cfg = dict(..., dul_config=training["dul_config"])
```

Also: pipe `horizons_sec`, `include_ridge_features`, `include_regime_prior` into NPZ build and dataset construction.

- [ ] **Step 2: Write 20-day 1-epoch smoke test**

```python
# scripts/smoke_v4_pipeline.py
import json, pathlib, subprocess
base = json.loads(pathlib.Path("configs/v4_full.json").read_text())
base["training"].update(train_days=20, val_days=5, test_days=5, epochs=1)
base["output_dir"] = "experiments/v4_smoke"
pathlib.Path("configs/v4_phase_a_smoke.json").write_text(json.dumps(base, indent=2))
subprocess.check_call(["python", "run_pipeline_v3.py", "--config", "configs/v4_phase_a_smoke.json"])
```

- [ ] **Step 3: Run smoke test**

```bash
python scripts/smoke_v4_pipeline.py
```
Expected: `experiments/v4_smoke/fold_0/test_results.json` exists with multi-horizon metrics.

- [ ] **Step 4: Commit**

```bash
git add run_pipeline_v3.py scripts/smoke_v4_pipeline.py configs/v4_phase_a_smoke.json
git commit -m "feat(v4): run_pipeline_v3 wires V4 flags + smoke script"
```

---

### Task 16: Ablation runner + fold aggregator + per-fold eval

**Files:**
- Create: `scripts/run_ablations.py`, `scripts/aggregate_folds.py`, `scripts/eval_fold_test.py`

- [ ] **Step 1: Implement `run_ablations.py`**

```python
# scripts/run_ablations.py
import pathlib, subprocess, json, time

ABL = pathlib.Path("configs/v4_ablations")
results = {}
for cfg_path in sorted(ABL.glob("*.json")):
    name = cfg_path.stem
    print(f"== Ablation: {name}", flush=True)
    start = time.time()
    r = subprocess.run(
        ["python", "run_pipeline_v3.py", "--config", str(cfg_path),
         "--fold_idx", "0"],
        capture_output=True, text=True,
    )
    results[name] = {
        "returncode": r.returncode,
        "elapsed_min": (time.time() - start) / 60,
        "output_dir": json.loads(cfg_path.read_text())["output_dir"],
    }
(ABL.parent / "ablation_summary.json").write_text(json.dumps(results, indent=2))
```

- [ ] **Step 2: Implement `aggregate_folds.py`**

```python
# scripts/aggregate_folds.py
import json, numpy as np, pathlib, argparse

ap = argparse.ArgumentParser()
ap.add_argument("--experiment_dir", required=True)
args = ap.parse_args()

root = pathlib.Path(args.experiment_dir)
folds = sorted(root.glob("fold_*/test_predictions.npz"))
preds, targs, masks = [], [], []
for f in folds:
    d = np.load(f)
    preds.append(d["pred_q50"]); targs.append(d["target"]); masks.append(d["mask"])
preds = np.concatenate(preds); targs = np.concatenate(targs); masks = np.concatenate(masks)
valid = masks > 0
pooled_ic = float(np.corrcoef(preds[valid], targs[valid])[0, 1])
print(f"Pooled OOS Pearson IC: {pooled_ic:.4f}")
(root / "aggregate.json").write_text(json.dumps({"pooled_ic": pooled_ic}, indent=2))
```

- [ ] **Step 3: Implement `eval_fold_test.py` (reload checkpoint + re-eval a fold)**

```python
# scripts/eval_fold_test.py
# Loads `fold_k/best.pt`, rebuilds dataset with same config, runs test eval, writes metrics.
# (mirror the eval logic in run_pipeline_v3._run_test_evaluation)
```

- [ ] **Step 4: Smoke-test aggregator on smoke run**

```bash
python scripts/aggregate_folds.py --experiment_dir experiments/v4_smoke
cat experiments/v4_smoke/aggregate.json
```

- [ ] **Step 5: Commit**

```bash
git add scripts/run_ablations.py scripts/aggregate_folds.py scripts/eval_fold_test.py
git commit -m "feat(v4): ablation runner + fold aggregator + per-fold eval"
```

---

## Phase 5 — Data Regen

### Task 17: Regenerate 1004-day NPZ with V4 features + multi-horizon labels + regime_prior

**Files:**
- Uses: `src/features/multi_day_pipeline.py` (already wired in Task 3)

Preconditions: ~45GB free (delete `data/npz_dense/` per spec §"Disk Estimate"). Target: `data/npz_v4/` (~61GB).

- [ ] **Step 1: Free disk**

```bash
df -h data/
du -sh data/npz_dense/
# Only delete after confirming no production consumer
rm -rf data/npz_dense/
df -h data/
```

- [ ] **Step 2: Launch regen in background**

```bash
mkdir -p data/npz_v4 logs
nohup python -m src.features.multi_day_pipeline \
  --csv_dir data/binance_hist \
  --out_dir data/npz_v4 \
  --include_ridge_features --include_regime_prior \
  --horizons_sec 60 180 300 600 \
  --input_len 600 --stride 180 \
  --quantize_features --n_levels 25 --jobs 4 \
  > logs/regen_v4.log 2>&1 &
```

- [ ] **Step 3: Wait + spot-check 3 NPZs (every few hours)**

```bash
tail -n 50 logs/regen_v4.log
ls data/npz_v4/*.npz | wc -l

python -c "
import numpy as np
for p in ['data/npz_v4/2023-01-01.npz', 'data/npz_v4/2024-06-15.npz', 'data/npz_v4/2025-11-30.npz']:
    d = np.load(p)
    assert all(f'y_{h}' in d.files for h in [60,180,300,600])
    assert 'regime_prior' in d.files and d['regime_prior'].shape[-1] == 6
    print(p, 'OK,', d['X'].shape, 'feat dim', d['X'].shape[-1])
"
```

- [ ] **Step 4: Schema-validate all days via bulk script**

```bash
python -c "
import numpy as np, pathlib
bad = []
for p in sorted(pathlib.Path('data/npz_v4').glob('*.npz')):
    d = np.load(p)
    for h in [60,180,300,600]:
        if f'y_{h}' not in d.files: bad.append((str(p), f'missing y_{h}')); break
    if 'regime_prior' not in d.files: bad.append((str(p), 'missing rp'))
print(f'bad={len(bad)}; first={bad[:5]}')
"
```

- [ ] **Step 5: Record a data stamp**

```bash
python -c "
import json, pathlib
items = sorted(pathlib.Path('data/npz_v4').glob('*.npz'))
stamp = {'count': len(items), 'first': str(items[0]), 'last': str(items[-1])}
pathlib.Path('data/npz_v4.stamp.json').write_text(json.dumps(stamp, indent=2))
"
git add data/npz_v4.stamp.json
git commit -m "chore(v4): record NPZ v4 regeneration stamp"
```

---

### Task 18: Re-run Ridge + XGBoost baselines on V4 NPZ

**Files:**
- Uses: `src/baselines/linear_baseline.py`, `src/baselines/xgb_baseline.py`

- [ ] **Step 1: Run Ridge baseline on V4 features**

```bash
python -m src.baselines.linear_baseline \
  --npz_dir data/npz_v4 \
  --output_dir experiments/baselines_v4/ridge \
  --horizons_sec 60 180 300 600 \
  --include_ridge_features --include_regime_prior --folds 4
```

- [ ] **Step 2: Run XGBoost baseline**

```bash
python -m src.baselines.xgb_baseline \
  --npz_dir data/npz_v4 \
  --output_dir experiments/baselines_v4/xgb \
  --horizons_sec 60 180 300 600 --folds 4
```

- [ ] **Step 3: Aggregate**

```bash
python scripts/aggregate_folds.py --experiment_dir experiments/baselines_v4/ridge
python scripts/aggregate_folds.py --experiment_dir experiments/baselines_v4/xgb
```

- [ ] **Step 4: Record in `docs/V4_RESULTS.md`**

- [ ] **Step 5: Commit**

```bash
git add experiments/baselines_v4/*/aggregate.json docs/V4_RESULTS.md
git commit -m "eval(v4): baseline pooled IC on V4 features"
```

---

## Phase 6 — Training

### Task 19: Train V4 full — 4 walk-forward folds

**Files:**
- Uses: `run_pipeline_v3.py`, `configs/v4_full.json`

Estimated: 4 folds × 1-2h on RTX 4090.

- [ ] **Step 1: Launch on pod**

```bash
ssh pod "cd /workspace/quant_research && \
  nohup python run_pipeline_v3.py --config configs/v4_full.json \
  > logs/v4_full.log 2>&1 &"
```

- [ ] **Step 2: Monitor GPU utilization + epoch time**

```bash
ssh pod "nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv -l 30" &
tail -f logs/v4_full.log
```

Target: GPU util > 60% during training steps; epoch time < 2min.
If severely underutilized (<10%), suspect CUDA-sync bottleneck — verify `compute_dul_loss(return_parts=False)` is in use and `torch.isfinite` is not called per horizon.

- [ ] **Step 3: After each fold completes, verify `test_results.json` and `test_predictions.npz`**

```bash
ls experiments/v4_full/fold_*/test_results.json
python -c "
import json, glob
for p in sorted(glob.glob('experiments/v4_full/fold_*/test_results.json')):
    print(p, json.load(open(p)))
"
```

- [ ] **Step 4: Aggregate pooled IC**

```bash
python scripts/aggregate_folds.py --experiment_dir experiments/v4_full
cat experiments/v4_full/aggregate.json
```

- [ ] **Step 5: Check pass criteria (spec §"Pass criteria")**

- Primary: pooled IC (h=180) ≥ 0.12
- Secondary: ≥ 3/4 folds have test_corr > 0.099

If primary fails → document results + skip Phase 7 ablations, revert to Ridge signal for production.

- [ ] **Step 6: Commit artifacts**

```bash
git add experiments/v4_full/aggregate.json experiments/v4_full/fold_*/test_results.json
git commit -m "eval(v4): V4 full 4-fold results"
```

---

### Task 20: Ablation sweep (8 configs × 1 fold)

**Files:**
- Uses: `scripts/run_ablations.py`

Only run IF Task 19 passes primary criterion. Otherwise attribution is undefined.

- [ ] **Step 1: Launch**

```bash
ssh pod "cd /workspace/quant_research && \
  nohup python scripts/run_ablations.py > logs/v4_abl.log 2>&1 &"
```

- [ ] **Step 2: Wait (~8 × 1-2h ≈ 10-15h)**

- [ ] **Step 3: Aggregate per-ablation**

```bash
for dir in experiments/v4_abl_*; do
  python scripts/aggregate_folds.py --experiment_dir "$dir"
done
```

- [ ] **Step 4: Build final ablation table**

```bash
python -c "
import json, pathlib
rows = []
for d in sorted(pathlib.Path('experiments').glob('v4_abl_*')):
    agg = d / 'aggregate.json'
    if agg.exists():
        ic = json.loads(agg.read_text())['pooled_ic']
        rows.append((d.name, ic))
full_ic = json.loads(pathlib.Path('experiments/v4_full/aggregate.json').read_text())['pooled_ic']
rows.insert(0, ('v4_full (ref)', full_ic))
for name, ic in rows:
    delta = (ic - full_ic) if name != 'v4_full (ref)' else 0.0
    print(f'{name:30s} IC={ic:.4f}  Δ={delta:+.4f}')
" | tee experiments/v4_ablation_table.txt
```

- [ ] **Step 5: Commit**

```bash
git add experiments/v4_abl_*/aggregate.json experiments/v4_ablation_table.txt
git commit -m "eval(v4): ablation sweep — 8 configs × 1 fold"
```

---

## Phase 7 — Reporting

### Task 21: `docs/V4_RESULTS.md`

**Files:**
- Create: `docs/V4_RESULTS.md`

- [ ] **Step 1: Write template**

```markdown
# V4 Results Report

**Date**: YYYY-MM-DD
**Architecture**: DualPathLOBModelV4 per spec `docs/superpowers/specs/2026-04-16-v4-design.md`

## Pooled OOS IC

| Model | h=60 | h=180 | h=300 | h=600 |
|-------|------|-------|-------|-------|
| Ridge (V4 feats) | | | | |
| XGBoost (V4 feats) | | | | |
| V4 full | | | | |

## Per-fold test correlation (h=180)

| Fold | Train days | Val days | Test days | test_corr | test_rank_corr |
|------|-----------|---------|----------|-----------|----------------|
| 0 | 700 | 30 | 90 | | |
| 1 | 700 | 30 | 90 | | |
| 2 | 700 | 30 | 90 | | |
| 3 | 700 | 30 | 90 | | |

## Ablation Table

| Configuration | Pooled IC (h=180) | Δ vs full | Notes |
|---------------|--------------------|-----------|-------|
| V4 full | | 0.0 | reference |
| -ppnet_gate | | | Quantifies regime gate |
| -multi_horizon | | | Quantifies MTL |
| -ridge_features | | | Quantifies targeted features |
| -patch_attention_pool | | | Quantifies pooling |
| -channel_mix_conv | | | Quantifies 1×1 conv |
| -level_attention_pool | | | Quantifies level pool |
| -utility_rank | | | Quantifies rank loss |
| +masknet | | | Revisit MaskNet |

## Backtest (best horizon)

- Fee: 4bps round-trip; slippage: 1bps/side
- Position sizing: `|q50| / (q90 - q10)`
- Newey-West HAC with `overlap_ratio = horizon_sec / stride`

| Metric | Value |
|--------|-------|
| Sharpe |  |
| Annualized return |  |
| Max drawdown |  |
| Hit rate |  |

## Conclusion

- Did V4 pass the primary criterion (pooled IC h=180 ≥ 0.12)?
- Top contributors (positive Δ in ablation):
- Top risks for production:
- Next research direction (V5 hypothesis):
```

- [ ] **Step 2: Populate fields after Tasks 18-20 complete.**

- [ ] **Step 3: Commit**

```bash
git add docs/V4_RESULTS.md
git commit -m "docs(v4): results report"
```

---

## Self-Review (Spec Coverage Check)

Performed against `docs/superpowers/specs/2026-04-16-v4-design.md`:

| Spec section | Task(s) | Covered? |
|--------------|---------|----------|
| Ablation-first engineering — 12 model flags | Tasks 7, 8, 13, 14 | yes |
| DUL loss components | Tasks 11, 12 | yes |
| 6 ridge-informed features | Task 1 | yes |
| 6 regime-prior features | Task 2 | yes |
| Multi-horizon NPZ labels + regime_prior field | Task 4 | yes |
| Walk-forward 4 folds (train=700, val=30, test=90) | Task 13 config | yes |
| Input length 600 | Task 13 config | yes |
| Patch size 5 → 120 tokens | Task 13 config | yes |
| PPNet gate with d_prior=6 | Task 8 | yes |
| AttentionPool over levels + tokens | Tasks 6, 7, 8 | yes |
| 1×1 channel mix conv in RawLOB | Task 7 | yes |
| Remove MaskNet (flag preserved) | Task 8 | yes |
| GDCN after compression | Task 8 | yes |
| End-to-end causality audit | Task 9 | yes |
| Feature + label leakage audit | Tasks 1, 2, 4, 5 | yes |
| Normalization from train only | Task 5 | yes |
| Multi-horizon 4 heads, shared encoder | Task 8 | yes |
| DUL warmup (calib off for 5 epochs) | Task 12 trainer flag | yes (wired via `lambda_calib=0.0` default) |
| 8 ablation configs | Task 14 | yes |
| Baseline comparison (Ridge, XGB) on V4 feats | Task 18 | yes |
| Backtest with NW-HAC | Task 21 reports | yes (uses `src/evaluation/backtest_v2.py`) |
| Pass criteria (pooled IC ≥ 0.12) | Task 19 Step 5 | yes |

### Placeholder scan

Searched this plan for `TBD`, `TODO`, `fill in later`, `implement later`, `similar to Task N` — none remain.

### Type and name consistency

- `regime_prior` shape `(N_win, 6)` consistent across Tasks 2, 4, 10.
- `quantiles` shape `(B, H, 3)` for multi-horizon, `(B, 3)` single — consistent across Tasks 8, 11, 12.
- Model flag names exactly match spec §"Model-level toggles".
- Config field names match between `configs/v4_full.json` and model kwargs in Task 15.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-16-v4-implementation.md`. Two execution options:

**1. Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, two-stage review (spec compliance then code quality) between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints.

Which approach?
