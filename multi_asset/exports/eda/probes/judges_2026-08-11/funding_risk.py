"""Engine C5: funding-leg risk control (0C tail_corisk.md).

The book's only real left tail = 2022-11-09 funding crowding-reversion gap risk (FTX). This acts
ONLY on the funding leg (the other 3 legs are crash BENEFICIARIES and are left untouched):
(i) per-name funding winsorize, (ii) single-name L1 concentration cap, (iii) funding cross-sectional
dispersion gate (shrink the whole funding leg when funding dispersion explodes).

v1 note: `apply` now takes the ALREADY-WEIGHTED funding leg (z OR rank) and the raw funding factor
separately -- the raw is used ONLY for the dispersion gate (iii). Under bounded RANK weighting the
winsor (i) and name-cap (ii) are near-no-ops (rank is already bounded), so C5 demotes from
"necessary hygiene" to "insurance"; under unbounded Z weighting they are load-bearing (0C measured
single-name L1 up to 0.49 without them). See engine/exp_funding_weighting.py for the 2x2.
"""
import numpy as np


class FundingLegRiskControl:
    def __init__(self, winsor_z=4.0, name_cap=0.15, disp_gate_z=4.0, disp_shrink=0.3, disp_ref=None):
        self.winsor_z = winsor_z; self.name_cap = name_cap
        self.disp_gate_z = disp_gate_z; self.disp_shrink = disp_shrink
        self.disp_ref = disp_ref            # (mean, std) of trailing funding-dispersion; None -> gate off
        self.n_gated = 0

    def _disp(self, funding_raw):
        f = np.asarray(funding_raw, float); m = np.isfinite(f)
        return float(np.std(f[m])) if m.sum() >= 3 else np.nan

    def apply(self, signal, funding_raw=None):
        """signal: pre-weighted funding leg (z or rank scale, UNsigned). funding_raw: raw funding
        factor, used ONLY for the dispersion gate. Returns risk-controlled leg (same length)."""
        z = np.asarray(signal, float).copy()
        z = np.clip(z, -self.winsor_z, self.winsor_z)                     # (i) winsorize (no-op for rank)
        disp = self._disp(funding_raw if funding_raw is not None else signal)   # (iii) dispersion gate
        shrink = 1.0
        if self.disp_ref is not None and np.isfinite(disp):
            dz = (disp - self.disp_ref[0]) / (self.disp_ref[1] + 1e-12)
            if dz > self.disp_gate_z:
                shrink = self.disp_shrink; self.n_gated += 1
        z = z * shrink
        gross = np.abs(z).sum()                                            # (ii) name concentration cap
        if gross > 1e-9:
            w = np.clip(z / gross, -self.name_cap, self.name_cap)
            z = w * gross
        return z, {"dispersion": disp, "shrink": shrink}

    @staticmethod
    def calibrate_dispersion(source, anchors):
        """trailing funding-dispersion (mean,std) over a set of anchors -> disp_ref for the gate."""
        ds = []
        frc = FundingLegRiskControl()
        for t in anchors:
            legs, _ = source.legs_raw(int(t))
            d = frc._disp(legs["funding"])
            if np.isfinite(d):
                ds.append(d)
        ds = np.array(ds)
        return (float(ds.mean()), float(ds.std())) if len(ds) else (0.0, 1.0)
