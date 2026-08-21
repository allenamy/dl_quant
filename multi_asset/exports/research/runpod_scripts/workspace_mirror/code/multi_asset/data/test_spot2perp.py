"""TDD for build_spot2perp.py (LIGHT retarget — proven SPOT inputs + PERP target).

Builds 2025-02-10 via the builder as a subprocess on the training server, then
verifies against the source caches:
  * X / X_raw / regime_prior / timestamps are the SPOT inputs (preserved verbatim).
  * y_600 / y_mask_600 are the PERP target (position-joined), i.e. y_600 EQUALS
    the perp cache y_600 and DIFFERS from the spot cache y_600 (target swapped).
  * shapes are mutually consistent.

Runs on jpline (paths absolute to the server repo); mirrors test_dual_npz.py.
"""
import numpy as np
import subprocess

_PY = "/root/miniconda3/envs/hsy_v5push/bin/python"
_REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
_DAY = "2025-02-10"


def _load(npz_dir):
    return np.load("%s/data/%s/%s.npz" % (_REPO, npz_dir, _DAY),
                   allow_pickle=True)


def test_spot2perp_retarget():
    # build the day fresh (--force so the assertion runs even if cached)
    subprocess.run(
        [_PY, "multi_asset/data/build_spot2perp.py", "--days", _DAY, "--force"],
        check=True, cwd=_REPO)

    out = _load("npz_spot2perp")
    spot = _load("npz_spot")
    perp = _load("npz_perp")

    # --- SPOT inputs preserved verbatim ---
    assert np.array_equal(out["X"], spot["X"]), "X must equal SPOT X"
    assert np.array_equal(out["X_raw"], spot["X_raw"]), "X_raw must equal SPOT X_raw"
    assert np.array_equal(out["regime_prior"], spot["regime_prior"]), \
        "regime_prior must equal SPOT regime_prior"
    assert np.array_equal(out["timestamps"].astype(np.int64),
                          spot["timestamps"].astype(np.int64)), \
        "timestamps must come from SPOT"
    assert out["X"].shape[-1] == 64

    # --- target swapped to PERP (position-aligned) ---
    yo = np.nan_to_num(out["y_600"])
    yp = np.nan_to_num(perp["y_600"])
    ys = np.nan_to_num(spot["y_600"])
    assert np.array_equal(yo, yp), "y_600 must equal PERP y_600 (position-joined)"
    assert not np.array_equal(yo, ys), \
        "y_600 must NOT equal SPOT y_600 (target actually swapped to perp)"
    assert np.array_equal(out["y_mask_600"].astype(np.uint8),
                          perp["y_mask_600"].astype(np.uint8)), \
        "y_mask_600 must equal PERP y_mask_600"

    # --- shapes mutually consistent ---
    N = out["X"].shape[0]
    assert out["X_raw"].shape[0] == N
    assert out["regime_prior"].shape[0] == N
    assert out["timestamps"].shape[0] == N
    assert out["y_600"].shape[0] == N
    assert out["y_mask_600"].shape[0] == N

    # timestamps strictly increasing, microsecond epoch
    ts = out["timestamps"].astype(np.int64)
    assert (np.diff(ts) > 0).all() and ts.max() > 2e12
