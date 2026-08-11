"""TDD test for multi_asset/eda/perpY_basis_regime_gate.py causal regime indicators.

THE GUARANTEE UNDER TEST
------------------------
The whole point of the regime-conditioned basis salvage is that the regime
indicator used to flip the basis sign must be STRICTLY CAUSAL (<= t). If the
indicator peeked at the future, any "recovered" basis edge would be a leak, not
a tradeable signal. So we test exactly that, plus finiteness:

1. ``causal_vol``, ``causal_ER``, ``causal_absret`` computed on the per-second
   spot mid up to second t are byte-identical when the mids strictly AFTER a cut
   second are corrupted (future-corruption leaves <=t values unchanged). This is
   the same shuffle-future contract the basis builder passes.

2. The indicators are finite on a realistic (warmup-respecting) sample and have
   non-degenerate variance (a constant indicator can't gate anything).

3. The per-second -> prediction-second sampling is itself <= t (re-uses the
   tested ``sample_at_pred_secs`` from build_basis_factors).

All deterministic. Pure-numpy synthetic mids; no data files touched.
"""
from __future__ import annotations

import os.path as _p
import sys

import numpy as np

_REPO = _p.dirname(_p.dirname(_p.dirname(_p.abspath(__file__))))  # repo root
sys.path.insert(0, _REPO)

from multi_asset.eda import perpY_basis_regime_gate as g  # noqa: E402


# ----------------------------------------------------------------------------
# synthetic per-second spot mid: a contiguous 1s grid with a random-walk mid
# ----------------------------------------------------------------------------
T = 8000          # ~2.2h of seconds, enough to fill the 1h trailing windows
CUT = 5000        # corrupt strictly after this second index


def _spot_series(seed=0):
    rng = np.random.default_rng(seed)
    sec = np.arange(T, dtype=np.int64) + 1_700_000_000  # plausible unix secs
    # geometric-ish random walk so log-returns are well defined and non-zero
    steps = rng.standard_normal(T) * 0.0008
    logp = np.cumsum(steps)
    spot_mid = 50_000.0 * np.exp(logp)
    return sec, spot_mid


def _corrupt_after(spot_mid, cut_idx, seed=1):
    """Replace every second strictly after cut_idx with large seeded noise."""
    rng = np.random.default_rng(seed)
    out = spot_mid.copy()
    fut = np.arange(spot_mid.size) > cut_idx
    scale = float(np.nanstd(spot_mid)) or 1.0
    out[fut] = rng.standard_normal(int(fut.sum())) * scale * 50.0 + scale * 1000.0
    return out


# ----------------------------------------------------------------------------
# 1. STRICT CAUSALITY of every per-second indicator
# ----------------------------------------------------------------------------
def test_indicators_strictly_causal_per_second():
    sec, spot = _spot_series(seed=0)
    spot_c = _corrupt_after(spot, CUT, seed=1)

    parts0 = g.causal_regime_per_second(sec, spot)
    parts1 = g.causal_regime_per_second(sec, spot_c)

    assert set(parts0.keys()) == set(g.REGIME_NAMES), parts0.keys()
    keep = sec <= sec[CUT]  # seconds at or before the cut second
    for nm in g.REGIME_NAMES:
        a0 = parts0[nm][keep]
        a1 = parts1[nm][keep]
        # NaNs (warmup) must match position-for-position; finite values identical
        both_nan = np.isnan(a0) & np.isnan(a1)
        same = both_nan | (a0 == a1)
        assert same.all(), (
            "%s changed at <=cut seconds after future corruption -> NOT causal "
            "(n_changed=%d)" % (nm, int((~same).sum())))


# ----------------------------------------------------------------------------
# 2. CAUSALITY end-to-end via the prediction-second sampler (the real path)
# ----------------------------------------------------------------------------
def test_indicators_strictly_causal_sampled():
    sec, spot = _spot_series(seed=2)
    spot_c = _corrupt_after(spot, CUT, seed=3)
    # prediction seconds scattered across the grid (some <=cut, some >cut)
    pred_secs = sec[200::137]

    R0 = g.causal_regime_at_pred_secs(sec, spot, pred_secs)
    R1 = g.causal_regime_at_pred_secs(sec, spot_c, pred_secs)

    keep = pred_secs <= sec[CUT]
    assert keep.sum() > 5, "test needs several <=cut prediction seconds"
    for nm in g.REGIME_NAMES:
        a0 = R0[nm][keep]
        a1 = R1[nm][keep]
        both_nan = np.isnan(a0) & np.isnan(a1)
        same = both_nan | (a0 == a1)
        assert same.all(), (
            "%s sampled value changed at a <=cut prediction-second -> leak" % nm)


# ----------------------------------------------------------------------------
# 3. FINITE + NON-DEGENERATE on a warmup-respecting sample
# ----------------------------------------------------------------------------
def test_indicators_finite_and_nondegenerate():
    sec, spot = _spot_series(seed=4)
    parts = g.causal_regime_per_second(sec, spot)
    # past the longest warmup (1h), values must be finite and varying
    tail = slice(g.VOL_WIN_SEC + 10, None)
    for nm in g.REGIME_NAMES:
        v = parts[nm][tail]
        assert np.isfinite(v).all(), "%s has non-finite values past warmup" % nm
        assert np.nanstd(v) > 0, "%s is constant -> cannot gate a regime" % nm


# ----------------------------------------------------------------------------
# 4. WARMUP is NaN (no peeking at an incomplete window as if it were complete):
#    the first second has no past, so every trailing indicator is NaN there.
# ----------------------------------------------------------------------------
def test_indicators_warmup_is_nan():
    sec, spot = _spot_series(seed=5)
    parts = g.causal_regime_per_second(sec, spot)
    for nm in g.REGIME_NAMES:
        assert np.isnan(parts[nm][0]), "%s must be NaN at the first second" % nm


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print("PASS", fn.__name__)
        except AssertionError as e:
            failed += 1
            print("FAIL", fn.__name__, "->", e)
        except Exception as e:  # noqa
            failed += 1
            print("ERROR", fn.__name__, "->", type(e).__name__, e)
    print("\n%d/%d passed" % (len(fns) - failed, len(fns)))
    sys.exit(1 if failed else 0)
