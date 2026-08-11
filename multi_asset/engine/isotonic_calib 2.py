"""Engine C3: isotonic calibration layer.

Monotone map rank-signal -> E[bps] fit on a val window. Isotonic (monotone) => rank-order
preserved => cross-sectional rank-IC INVARIANT (IC is alpha, magnitude is the calibrated by-product).
Output = calibrated expected-bps magnitude for downstream Kelly/net-cost sizing.
"""
import numpy as np
from scipy.stats import rankdata
from sklearn.isotonic import IsotonicRegression


class IsotonicCalibrator:
    def __init__(self, increasing=True):
        self.iso = None; self.increasing = increasing

    def fit(self, signal, realized_bps):
        s = np.asarray(signal, float).ravel(); y = np.asarray(realized_bps, float).ravel()
        ok = np.isfinite(s) & np.isfinite(y)
        assert ok.sum() >= 50, "need >=50 finite (signal, bps) pairs to calibrate"
        self.iso = IsotonicRegression(out_of_bounds="clip", increasing=self.increasing).fit(s[ok], y[ok])
        return self

    def transform(self, signal):
        s = np.asarray(signal, float)
        if self.iso is None:
            return s.copy()
        out = np.full(s.shape, np.nan); ok = np.isfinite(s)
        out[ok] = self.iso.transform(s[ok].ravel())
        return out

    def fitted(self):
        return self.iso is not None


def rank_ic(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 5:
        return np.nan
    ra, rb = rankdata(a[ok]), rankdata(b[ok])
    if ra.std() < 1e-12 or rb.std() < 1e-12:
        return np.nan
    return float(np.corrcoef(ra, rb)[0, 1])


def ic_invariance_check(signal, realized_bps, calibrator, tol=0.005):
    """Confirm the monotone calibration preserves rank-IC. Isotonic is *weakly* monotone, so it
    creates ties (flat E[bps] regions) that cause a tiny rank-reshuffle => IC preserved up to
    tie-flattening (not bit-exact). `invariant` = |ic_raw - ic_cal| < tol."""
    cal = calibrator.transform(signal)
    ic_raw = rank_ic(np.asarray(signal, float), np.asarray(realized_bps, float))
    ic_cal = rank_ic(cal, np.asarray(realized_bps, float))
    delta = abs(ic_raw - ic_cal) if (np.isfinite(ic_raw) and np.isfinite(ic_cal)) else np.nan
    return {"ic_raw": ic_raw, "ic_calibrated": ic_cal, "delta": float(delta),
            "invariant": bool(np.isfinite(delta) and delta < tol)}
