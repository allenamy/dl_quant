"""TDD for build_perp_y_clean.py — leak-free re-anchored perp y_600 target.

Builds 2 days via the builder as a subprocess on the training server, then
verifies the re-anchored target against the source caches:

  * SPOT inputs (X / X_raw / regime_prior / timestamps) preserved verbatim.
  * y_600 is FINITE on valid rows and has a plausible ~bps magnitude.
  * CAUSALITY / OFFSET-0: re-derive y from mid_cache independently using
    s = floor(spot_ts/1e6) and s+600 (stitching the next day), and assert it
    matches the builder's y_600 bit-for-bit on valid rows -> proves the target
    window starts EXACTLY at s (offset 0) and uses only s and s+600.
  * corr(y_600_clean, spot_y_600) > 0.95 (same ~600s forward move, perp vs spot).
  * the OLD leaked offset is NOT what we used: confirm the new target differs
    from the spot target (it is the perp leg) yet tracks it (>0.95).

Runs on jpline (paths absolute to the server repo); mirrors test_spot2perp.py.
"""
import datetime as dt
import os.path as p
import subprocess

import numpy as np

_PY = "/root/miniconda3/envs/hsy_v5push/bin/python"
_REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
_DAYS = ["2025-02-10", "2025-02-11"]

US_PER_SEC = 1_000_000
HORIZON = 600


def _load(npz_dir, day):
    return np.load("%s/data/%s/%s.npz" % (_REPO, npz_dir, day), allow_pickle=True)


def _mid_grid(day):
    """today's (sec, perp_mid) with next day stitched on (mirrors the builder)."""
    z0 = np.load("%s/data/mid_cache/%s.npz" % (_REPO, day))
    sec0 = z0["sec"].astype(np.int64)
    mid0 = z0["perp_mid"].astype(np.float64)
    nxt = (dt.date.fromisoformat(day) + dt.timedelta(days=1)).isoformat()
    fn = "%s/data/mid_cache/%s.npz" % (_REPO, nxt)
    if p.exists(fn):
        z1 = np.load(fn)
        sec1 = z1["sec"].astype(np.int64)
        mid1 = z1["perp_mid"].astype(np.float64)
        keep = sec1 > sec0[-1]
        if keep.any():
            sec0 = np.concatenate([sec0, sec1[keep]])
            mid0 = np.concatenate([mid0, mid1[keep]])
    return sec0, mid0


def _independent_reanchor(spot_ts_us, sec, perp_mid):
    """Reference re-anchor via a dict lookup (independent of the builder's impl)
    so a shared bug can't hide. y at s = log(mid[s+600]/mid[s])."""
    s2mid = {int(k): float(v) for k, v in zip(sec, perp_mid)}
    s = (spot_ts_us // US_PER_SEC).astype(np.int64)
    y = np.full(s.shape, np.nan, dtype=np.float64)
    for i in range(s.size):
        a = s2mid.get(int(s[i]))
        b = s2mid.get(int(s[i]) + HORIZON)
        if a is not None and b is not None and a > 0 and b > 0:
            y[i] = np.log(b / a)
    return y


def test_perp_y_clean_reanchor():
    subprocess.run(
        [_PY, "multi_asset/data/build_perp_y_clean.py", "--days", *_DAYS, "--force"],
        check=True, cwd=_REPO)

    for day in _DAYS:
        out = _load("npz_spot2perp_clean", day)
        spot = _load("npz_spot", day)

        # --- SPOT inputs preserved verbatim ---
        assert np.array_equal(out["X"], spot["X"]), "X must equal SPOT X"
        assert np.array_equal(out["X_raw"], spot["X_raw"]), "X_raw must equal SPOT"
        assert np.array_equal(out["regime_prior"], spot["regime_prior"]), \
            "regime_prior must equal SPOT"
        assert np.array_equal(out["timestamps"].astype(np.int64),
                              spot["timestamps"].astype(np.int64)), \
            "timestamps must come from SPOT"
        assert out["X"].shape[-1] == 64

        ts = out["timestamps"].astype(np.int64)
        y = out["y_600"].astype(np.float64)
        mask = out["y_mask_600"].astype(bool)
        N = ts.shape[0]
        assert y.shape[0] == N and mask.shape[0] == N

        # --- shapes & a real number of valid rows ---
        assert mask.sum() > 0.9 * N, "too many invalid rows: %d/%d" % (mask.sum(), N)

        # --- FINITE + plausible bps magnitude on valid rows ---
        yv = y[mask]
        assert np.all(np.isfinite(yv)), "y_600 must be finite on valid rows"
        std_bps = float(np.std(yv) * 1e4)
        # 10-min BTC perp log-return std is ~5..40 bps; bound generously.
        assert 1.0 < std_bps < 200.0, "implausible y std %.2f bps" % std_bps
        assert float(np.max(np.abs(yv))) < 0.5, "single-window |y| too large"

        # --- CAUSALITY / OFFSET-0: independent re-derivation must match ---
        sec, perp_mid = _mid_grid(day)
        y_ref = _independent_reanchor(ts, sec, perp_mid)
        ref_valid = np.isfinite(y_ref)
        # every builder-valid row must be ref-valid and bit-equal (float32 cast)
        assert np.all(ref_valid[mask]), \
            "builder marked rows valid that the independent re-anchor cannot derive"
        np.testing.assert_allclose(
            y[mask], y_ref[mask].astype(np.float32).astype(np.float64),
            rtol=0, atol=0,
            err_msg="y_600 != independent log(mid[s+600]/mid[s]) -> offset/leak bug")

        # --- explicit offset-0 check: y at row i uses mid at EXACTLY s and s+600 ---
        s = (ts // US_PER_SEC).astype(np.int64)
        s2mid = {int(k): float(v) for k, v in zip(sec, perp_mid)}
        idx = np.where(mask)[0]
        for i in idx[:: max(1, idx.size // 50)]:           # sample ~50 rows
            a = s2mid[int(s[i])]
            b = s2mid[int(s[i]) + HORIZON]
            assert abs(float(y[i]) - np.float32(np.log(b / a))) < 1e-7, \
                "offset-0 violated at row %d" % i

        # --- corr with spot's OWN (leak-free) y_600 > 0.95 ---
        spot_y = spot["y_600"].astype(np.float64)
        both = mask & np.isfinite(spot_y)
        c = float(np.corrcoef(y[both], spot_y[both])[0, 1])
        assert c > 0.95, "corr(y_clean, spot_y_600)=%.4f <= 0.95" % c
        # and it must NOT be byte-identical to spot (it's the perp leg)
        assert not np.array_equal(y[both], spot_y[both]), \
            "clean perp target must differ from spot target"

        print("[%s] N=%d valid=%d y_std=%.2fbps corr_spot=%.4f OK"
              % (day, N, int(mask.sum()), std_bps, c))
