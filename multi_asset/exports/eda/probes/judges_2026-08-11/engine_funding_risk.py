"""Engine C5: funding-leg risk control (0C tail_corisk.md).

The book's only real left tail = 2022-11-09 funding -18sigma (FTX) — funding crowding-reversion
gap risk on a mega-entity collapse. This acts ONLY on the funding leg (the other 3 legs are crash
BENEFICIARIES and are left untouched): (i) per-name funding-z winsorize, (ii) single-name L1
concentration cap, (iii) funding cross-sectional dispersion gate (shrink the whole funding leg when
funding dispersion explodes). Trims the -18 tail without harming the crash-beneficiary property.
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

    def apply(self, funding_raw):
        """funding_raw: per-member raw funding factor -> risk-controlled funding-z (same length)."""
        f = np.asarray(funding_raw, float); m = np.isfinite(f)
        z = np.zeros_like(f)
        if m.sum() >= 3:
            mu, sd = f[m].mean(), f[m].std()
            if sd > 1e-12:
                z[m] = (f[m] - mu) / sd
        z = np.clip(z, -self.winsor_z, self.winsor_z)                     # (i) winsorize
        disp = self._disp(funding_raw); shrink = 1.0                       # (iii) dispersion gate
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
