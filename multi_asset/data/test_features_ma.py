"""Tests for the per-asset feature builder (Phase 2).

TDD-first. The CAUSALITY test is the load-bearing one: a feature builder with
any look-ahead leakage would let a perturbation at bar t leak into rows < t.

Runs without the share mount: the default fixture is a synthetic panel that
mimics the bar schema. A real-day smoke test is opt-in via env
    MA_FEAT_REAL_DAY=20250105
(only runs on jpline where the share is mounted).

    python3 -m pytest multi_asset/data/test_features_ma.py -v
"""
from __future__ import annotations

import os

import numpy as np
import pytest

from multi_asset.data.bar_loader import FEATURE_COLUMNS, DayPanel
from multi_asset.data.features_ma import build_features, compute_y600, valid_mask


# ---------------------------------------------------------------------------
# Synthetic panel fixture (no share mount needed)
# ---------------------------------------------------------------------------

def _make_synthetic_panel(T: int = 5000, seed: int = 0, leading_nan: int = 3) -> DayPanel:
    """A single-symbol synthetic panel with the real 57-column schema.

    mid is a gentle random walk; LOB/flow/depth columns are positive, finite,
    and weakly coupled to mid so features are non-degenerate. Leading rows NaN
    to mimic the real warmup behavior.
    """
    rng = np.random.default_rng(seed)
    cols = FEATURE_COLUMNS
    sym = "bnfbtc"
    arr = np.empty((T, len(cols)), dtype=np.float64)

    # base mid as a random walk around 50000
    steps = rng.normal(0, 0.5, size=T)
    mid = 50000.0 + np.cumsum(steps)

    half_spread = 0.5  # price units
    bid0 = mid - half_spread
    ask0 = mid + half_spread

    def put(name, vals):
        arr[:, cols.index(name)] = vals

    # prices: 5 levels each side, 1-tick apart
    put("mid", mid)
    put("open", mid)
    put("high", mid + 1.0)
    put("low", mid - 1.0)
    put("close", mid)
    put("twap", mid + rng.normal(0, 0.1, T))
    put("vwap", mid + rng.normal(0, 0.1, T))
    for lvl in range(5):
        bsuf = "bid" if lvl == 0 else f"bid_{lvl}"
        asuf = "ask" if lvl == 0 else f"ask_{lvl}"
        put(bsuf, bid0 - lvl)
        put(asuf, ask0 + lvl)
        # sizes: positive, level-decaying, slightly imbalanced by mid momentum
        szb = np.abs(rng.normal(10.0, 2.0, T)) * (0.8 ** lvl) + 1.0
        sza = np.abs(rng.normal(10.0, 2.0, T)) * (0.8 ** lvl) + 1.0
        bszuf = "bidsz" if lvl == 0 else f"bidsz_{lvl}"
        aszuf = "asksz" if lvl == 0 else f"asksz_{lvl}"
        put(bszuf, szb)
        put(aszuf, sza)

    # trade flow (positive)
    put("tdQtyBuy", np.abs(rng.normal(5.0, 2.0, T)))
    put("tdQtySell", np.abs(rng.normal(5.0, 2.0, T)))
    put("tdQtyPxBuy", np.abs(rng.normal(5.0, 2.0, T)) * mid)
    put("tdQtyPxSell", np.abs(rng.normal(5.0, 2.0, T)) * mid)
    put("tdCntBuy", np.abs(rng.normal(3.0, 1.0, T)))
    put("tdCntSell", np.abs(rng.normal(3.0, 1.0, T)))

    # book add/del
    put("bkAddBid", np.abs(rng.normal(4.0, 1.5, T)))
    put("bkAddAsk", np.abs(rng.normal(4.0, 1.5, T)))
    put("bkDelBid", np.abs(rng.normal(4.0, 1.5, T)))
    put("bkDelAsk", np.abs(rng.normal(4.0, 1.5, T)))

    # mid-change counters
    put("midChgUp", np.abs(rng.normal(2.0, 1.0, T)))
    put("midChgDn", np.abs(rng.normal(2.0, 1.0, T)))

    # cumulative depth buckets (monotone increasing with distance)
    deps = ["0.1", "0.3", "1.0", "3.0", "10.0", "30.0", "100.0", "300.0", "1000.0"]
    cumb = np.zeros(T)
    cuma = np.zeros(T)
    for i, dx in enumerate(deps):
        cumb = cumb + np.abs(rng.normal(8.0, 2.0, T)) * (1.0 + 0.3 * i)
        cuma = cuma + np.abs(rng.normal(8.0, 2.0, T)) * (1.0 + 0.3 * i)
        put(f"cumu_bidsz_dep_{dx}", cumb.copy())
        put(f"cumu_asksz_dep_{dx}", cuma.copy())

    # leading NaN warmup
    arr[:leading_nan, :] = np.nan

    return DayPanel(symbols=[sym], ts=np.arange(T, dtype=np.int64) * 1_000_000_000,
                    data={sym: arr}, cols=list(cols))


@pytest.fixture
def panel():
    return _make_synthetic_panel(T=5000, seed=7)


SYM = "bnfbtc"


# ---------------------------------------------------------------------------
# 1. Shape / names
# ---------------------------------------------------------------------------

def test_shape_and_names(panel):
    F, names = build_features(panel, SYM)
    T = panel.data[SYM].shape[0]
    assert F.shape[0] == T, "F rows must equal T"
    assert F.shape[1] == len(names), "names length must equal F cols"
    assert len(names) == len(set(names)), "feature names must be unique"
    assert 40 <= len(names) <= 70, f"expect 40-70 features, got {len(names)}"


# ---------------------------------------------------------------------------
# 2. CAUSALITY (critical) — perturb bar t=1000, rows < 1000 must be unchanged
# ---------------------------------------------------------------------------

def test_causality_no_lookahead(panel):
    """Mutate EVERY column at a single bar t0 and confirm no feature row < t0
    changes. Any look-ahead (future-shift, centered/forward rolling, reversed
    cumsum, y600 leaking into features) would break this."""
    t0 = 1000
    F0, names = build_features(panel, SYM)

    # build a perturbed copy: shock bar t0 across all columns
    arr = panel.data[SYM]
    arr2 = arr.copy()
    rng = np.random.default_rng(123)
    # multiplicative + additive shock that keeps values finite & valid-ish
    arr2[t0, :] = arr2[t0, :] * 1.5 + rng.normal(0, 3.0, arr2.shape[1])
    panel2 = DayPanel(symbols=panel.symbols, ts=panel.ts,
                      data={SYM: arr2}, cols=panel.cols)
    F1, _ = build_features(panel2, SYM)

    # rows strictly before t0 must be bit-identical (NaNs in same place)
    before0 = F0[:t0]
    before1 = F1[:t0]
    same = np.array_equal(np.nan_to_num(before0, nan=-9.99e9),
                          np.nan_to_num(before1, nan=-9.99e9))
    if not same:
        diff_rows = np.where(~np.all(
            np.nan_to_num(before0, nan=-9.99e9) == np.nan_to_num(before1, nan=-9.99e9),
            axis=1))[0]
        bad_cols = np.where(~np.all(
            np.nan_to_num(before0, nan=-9.99e9) == np.nan_to_num(before1, nan=-9.99e9),
            axis=0))[0]
        pytest.fail(
            f"LOOK-AHEAD LEAK: {diff_rows.size} rows < {t0} changed after perturbing "
            f"bar {t0}. First leaked rows={diff_rows[:5]}, "
            f"leaked features={[names[c] for c in bad_cols[:8]]}"
        )

    # and row t0 itself SHOULD change (sanity: the perturbation is observable)
    assert not np.array_equal(np.nan_to_num(F0[t0], nan=-9.99e9),
                              np.nan_to_num(F1[t0], nan=-9.99e9)), \
        "perturbation at t0 had no effect on its own row — features may ignore inputs"


# ---------------------------------------------------------------------------
# 3. No NaN/Inf after warmup
# ---------------------------------------------------------------------------

def test_finite_after_warmup(panel):
    F, names = build_features(panel, SYM)
    tail = F[300:]
    assert np.isfinite(tail).all(), (
        "rows >= 300 must be finite; offending cols: "
        f"{[names[c] for c in np.where(~np.isfinite(tail).all(axis=0))[0][:8]]}"
    )


# ---------------------------------------------------------------------------
# 4. y600 — forward-looking, last 600 NaN, ramp sign
# ---------------------------------------------------------------------------

def test_y600_forward_and_tail(panel):
    y = compute_y600(panel, SYM)
    T = panel.data[SYM].shape[0]
    assert y.shape == (T,)
    # last 600 rows NaN (no forward window)
    assert np.isnan(y[T - 600:]).all()
    # interior has finite values
    assert np.isfinite(y[1000:T - 600]).any()


def test_y600_ramp_sign():
    """A strictly rising mid => positive forward return; falling => negative."""
    T = 3000
    cols = FEATURE_COLUMNS
    arr = np.full((T, len(cols)), 1.0)  # keep all cols finite/nonzero
    mid_idx = cols.index("mid")
    bidsz_idx = cols.index("bidsz")
    asksz_idx = cols.index("asksz")
    arr[:, bidsz_idx] = 1.0
    arr[:, asksz_idx] = 1.0
    # rising ramp
    arr[:, mid_idx] = np.linspace(100.0, 200.0, T)
    panel = DayPanel(symbols=[SYM], ts=np.arange(T, dtype=np.int64),
                     data={SYM: arr}, cols=list(cols))
    y = compute_y600(panel, SYM)
    assert np.nanmean(y[:T - 600]) > 0, "rising mid must give positive y_600"

    # falling ramp
    arr[:, mid_idx] = np.linspace(200.0, 100.0, T)
    panel2 = DayPanel(symbols=[SYM], ts=np.arange(T, dtype=np.int64),
                      data={SYM: arr}, cols=list(cols))
    y2 = compute_y600(panel2, SYM)
    assert np.nanmean(y2[:T - 600]) < 0, "falling mid must give negative y_600"


def test_y600_exact_definition():
    """y[t] == log(mid[t+600]) - log(mid[t]) exactly."""
    T = 2000
    cols = FEATURE_COLUMNS
    rng = np.random.default_rng(1)
    arr = np.full((T, len(cols)), 1.0)
    mid_idx = cols.index("mid")
    mid = 100.0 + np.cumsum(np.abs(rng.normal(0, 0.1, T))) + 1.0
    arr[:, mid_idx] = mid
    panel = DayPanel(symbols=[SYM], ts=np.arange(T, dtype=np.int64),
                     data={SYM: arr}, cols=list(cols))
    y = compute_y600(panel, SYM)
    t = 500
    expected = np.log(mid[t + 600]) - np.log(mid[t])
    assert abs(y[t] - expected) < 1e-12


# ---------------------------------------------------------------------------
# 5. valid_mask — finite mid + nonzero size
# ---------------------------------------------------------------------------

def test_valid_mask(panel):
    m = valid_mask(panel, SYM)
    T = panel.data[SYM].shape[0]
    assert m.shape == (T,)
    assert m.dtype == bool
    # leading NaN warmup rows are invalid
    assert not m[0]
    # an interior healthy bar is valid
    assert m[2000]


# ---------------------------------------------------------------------------
# Optional: real-day smoke test (jpline only)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not os.environ.get("MA_FEAT_REAL_DAY"),
                    reason="set MA_FEAT_REAL_DAY=YYYYMMDD on jpline to run")
def test_real_day_smoke():
    from multi_asset.data.bar_loader import load_day_panel
    date = int(os.environ["MA_FEAT_REAL_DAY"])
    dp = load_day_panel(date, [SYM])
    F, names = build_features(dp, SYM)
    T = dp.data[SYM].shape[0]
    assert F.shape == (T, len(names))
    assert np.isfinite(F[300:]).all()
    y = compute_y600(dp, SYM)
    assert np.isnan(y[T - 600:]).all()
    print(f"\nreal-day {date}: T={T}, n_feat={len(names)}, "
          f"finite_after_warmup=OK, y600 tail-NaN=OK")
