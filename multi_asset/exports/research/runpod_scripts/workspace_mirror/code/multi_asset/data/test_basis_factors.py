"""TDD tests for the REAL basis factors (Stage C real-basis).

Run on the jpline server (needs the read-only Tardis books + lastts_cache):

    /root/miniconda3/envs/hsy_v5push/bin/python -m pytest \
        multi_asset/data/test_basis_factors.py -q

Or as a plain script (no pytest dep):

    /root/miniconda3/envs/hsy_v5push/bin/python multi_asset/data/test_basis_factors.py

What is asserted (on 2 real days):
  1. mids are ABSOLUTE BTC prices (~tens of thousands), not mid-relative.
  2. basis_bps is finite and PLAUSIBLE (a few bps, |median| < 25, not thousands).
  3. basis_z is standardized (median ~0, robust scale O(1), not O(100)).
  4. basis_ema_dev / basis_mom are STRICTLY CAUSAL: corrupting mids strictly
     AFTER a cut second leaves every prediction-second <= cut byte-identical
     (a real leak would change them).
"""
from __future__ import annotations

import os.path as p
import sys

import numpy as np

sys.path.insert(0, p.dirname(p.dirname(p.dirname(p.abspath(__file__)))))  # repo root
from multi_asset.data import build_mid_cache as bmc          # noqa: E402
from multi_asset.data import build_basis_factors as bbf       # noqa: E402

# two real days that exist in both books + lastts (one strong, one choppy)
DAYS = ["2025-02-10", "2026-03-10"]


# ---------------------------------------------------------------------------
def _mids_for_day(day):
    spot_sec, spot_mid = bmc._mid_1s(day, bmc.SPOT_VENUE)
    perp_sec, perp_mid = bmc._mid_1s(day, bmc.PERP_VENUE)
    common = np.intersect1d(spot_sec, perp_sec)
    s = spot_mid[np.searchsorted(spot_sec, common)]
    pm = perp_mid[np.searchsorted(perp_sec, common)]
    return common, s, pm


def test_mids_are_absolute_prices():
    for day in DAYS:
        sec, spot, perp = _mids_for_day(day)
        assert sec.size > 1000, "%s: too few seconds (%d)" % (day, sec.size)
        for name, m in (("spot", spot), ("perp", perp)):
            assert np.all(np.isfinite(m)), "%s %s: non-finite mid" % (day, name)
            med = float(np.median(m))
            assert 1_000.0 < med < 1_000_000.0, (
                "%s %s mid median=%.2f not an absolute BTC price (tens of "
                "thousands expected)" % (day, name, med))
        print("[ok] %s mids absolute: spot~%.0f perp~%.0f"
              % (day, np.median(spot), np.median(perp)))


def test_basis_bps_plausible():
    for day in DAYS:
        sec, spot, perp = _mids_for_day(day)
        parts = bbf.per_second_factors(sec, spot, perp)
        bps = parts["basis_bps"]
        assert np.all(np.isfinite(bps)), "%s: basis_bps has non-finite" % day
        assert np.all(np.abs(bps) <= bbf.CLIP_BPS + 1e-9), (
            "%s: basis_bps exceeds clip" % day)
        med = float(np.median(bps))
        p95 = float(np.percentile(np.abs(bps), 95))
        assert abs(med) < 25.0, (
            "%s: |median basis|=%.2f bps implausibly large (a few bps expected; "
            "thousands -> mids did NOT cancel-free / wrong venue)" % (day, med))
        assert p95 < bbf.CLIP_BPS, "%s: basis 95pct at clip ceiling" % day
        print("[ok] %s basis_bps median=%.2f p95|.|=%.2f bps (plausible)"
              % (day, med, p95))


def test_basis_z_standardized():
    for day in DAYS:
        sec, spot, perp = _mids_for_day(day)
        parts = bbf.per_second_factors(sec, spot, perp)
        z = parts["basis_z"]
        z = z[np.isfinite(z)]
        assert z.size > 100, "%s: too few finite basis_z" % day
        med = float(np.median(z))
        mad = float(np.median(np.abs(z - med)) * 1.4826)
        assert abs(med) < 1.0, "%s: basis_z median=%.3f not ~0" % (day, med)
        assert 0.1 < mad < 10.0, (
            "%s: basis_z robust scale=%.3f not O(1) (not standardized)"
            % (day, mad))
        print("[ok] %s basis_z median=%.3f mad-sigma=%.3f (standardized)"
              % (day, med, mad))


def test_ema_dev_and_mom_strictly_causal():
    """Corrupt mids strictly AFTER a cut second; every prediction-second <= cut
    must yield byte-identical basis_ema_dev and basis_mom (and basis_z)."""
    for day in DAYS:
        sec, spot, perp = _mids_for_day(day)
        T = sec.size
        cut_pos = T // 2
        cut_sec = int(sec[cut_pos])
        # prediction seconds = a strided sample of the grid (proxy for windows)
        pred_secs = sec[::180]

        base = bbf.sample_at_pred_secs(sec, bbf.per_second_factors(sec, spot, perp),
                                       pred_secs)

        # corrupt EVERY second strictly after cut_sec (both mids), huge offset+noise
        rng = np.random.default_rng(0)
        fut = sec > cut_sec
        spot_c = spot.copy(); perp_c = perp.copy()
        scale = float(np.std(spot)) or 1.0
        spot_c[fut] = spot[fut] + rng.standard_normal(fut.sum()) * scale + 5e4
        perp_c[fut] = perp[fut] + rng.standard_normal(fut.sum()) * scale + 5e4
        corr = bbf.sample_at_pred_secs(
            sec, bbf.per_second_factors(sec, spot_c, perp_c), pred_secs)

        keep = pred_secs <= cut_sec
        assert keep.sum() > 10, "%s: too few <=cut windows" % day
        for name in ("basis_bps", "basis_z", "basis_mom", "basis_ema_dev"):
            a = base[name][keep]
            b = corr[name][keep]
            same = np.array_equal(np.nan_to_num(a, nan=0.0),
                                  np.nan_to_num(b, nan=0.0))
            assert same, ("%s: %s changed for <=cut windows after future "
                          "corruption -> LEAK" % (day, name))
        # and confirm the corruption DID move > cut windows (test is not a no-op)
        fut_keep = pred_secs > cut_sec
        if fut_keep.sum() > 0:
            moved = not np.array_equal(
                np.nan_to_num(base["basis_bps"][fut_keep], nan=0.0),
                np.nan_to_num(corr["basis_bps"][fut_keep], nan=0.0))
            assert moved, "%s: future corruption was a no-op (test invalid)" % day
        print("[ok] %s ema_dev/mom/z strictly causal (%d <=cut windows unchanged)"
              % (day, int(keep.sum())))


def test_end_to_end_day_build():
    """build_factors_for_day returns aligned (timestamps, F) matching lastts."""
    import os
    for day in DAYS:
        lastf = p.join(bbf.LASTTS_DIR, "%s.npz" % day)
        assert os.path.exists(lastf), "lastts missing for %s" % day
        ts, F, parts = bbf.build_factors_for_day(day)
        with np.load(lastf) as zl:
            lts = zl["timestamps"].astype(np.int64)
        assert ts.shape == lts.shape and np.array_equal(ts, lts), (
            "%s: basis timestamps != lastts timestamps" % day)
        assert F.shape == (ts.size, 4), "%s: F shape %s" % (day, F.shape)
        fin = float(np.isfinite(F).all(axis=1).mean())
        assert fin > 0.9, "%s: only %.3f rows fully finite" % (day, fin)
        print("[ok] %s end-to-end: N=%d aligned, finite_frac=%.4f"
              % (day, ts.size, fin))


def _main():
    tests = [test_mids_are_absolute_prices, test_basis_bps_plausible,
             test_basis_z_standardized, test_ema_dev_and_mom_strictly_causal,
             test_end_to_end_day_build]
    fails = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            fails += 1
            print("[FAIL] %s: %s" % (t.__name__, e))
        except Exception as e:
            fails += 1
            print("[ERROR] %s: %s: %s" % (t.__name__, type(e).__name__, e))
    print("\n%s: %d/%d passed"
          % ("PASS" if fails == 0 else "FAIL", len(tests) - fails, len(tests)))
    return fails


if __name__ == "__main__":
    sys.exit(1 if _main() else 0)
