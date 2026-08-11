"""Engine C1 (revised): signal production chain.

Exposes per-leg cross-sectional SIGNED signals (funding leg risk-controlled via C5) for the
cross-leg netting layer; combines with book weights -> isotonic-calibrated (tail-capped) E[bps]
-> market-neutral target positions. vol-gate is EXECUTION-TACTIC metadata only (exposure is NOT
modulated -- 0C: the book is a crisis beneficiary).
"""
import numpy as np

DEFAULT_WEIGHTS = {"king": 0.30, "s2": 0.10, "funding": 0.30, "size": 0.30}   # 0C 4-leg book weights
DEFAULT_SIGNS = {"king": +1, "s2": +1, "funding": -1, "size": +1}             # funding = crowding-reversion


def _z(x):
    x = np.asarray(x, float); m = np.isfinite(x); out = np.zeros_like(x)
    if m.sum() >= 3:
        mu, sd = x[m].mean(), x[m].std()
        if sd > 1e-12:
            out[m] = (x[m] - mu) / sd
    return out


class SignalChain:
    def __init__(self, source, weights=None, signs=None, calibrator=None, vol_gate=None,
                 funding_risk=None, pos_cap_pct=99.0):
        self.src = source; self.w = dict(weights or DEFAULT_WEIGHTS); self.sign = dict(signs or DEFAULT_SIGNS)
        self.calibrator = calibrator; self.vol_gate = vol_gate; self.funding_risk = funding_risk
        self.pos_cap_pct = pos_cap_pct

    def leg_signals(self, t):
        """per-member xsec-standardized SIGNED leg signals (funding risk-controlled). For netting."""
        legs, m = self.src.legs_raw(t)
        out = {}
        for k in self.w:
            if k == "funding" and self.funding_risk is not None:
                z, _ = self.funding_risk.apply(legs["funding"]); out[k] = self.sign[k] * z
            else:
                out[k] = self.sign[k] * _z(legs[k])
        return out, m

    def combined_signal(self, t):
        legs, m = self.leg_signals(t)
        return sum(self.w[k] * legs[k] for k in self.w), m

    def fit_calibrator(self, val_ym, calibrator):
        S, Y = [], []
        for t in self.src.month_anchors(val_ym):
            c, m = self.combined_signal(int(t)); S.append(c); Y.append(self.src.realized_fwd_bps(int(t)))
        calibrator.fit(np.concatenate(S), np.concatenate(Y)); self.calibrator = calibrator; return self

    def target_position(self, t):
        combo, m = self.combined_signal(t)
        mag = self.calibrator.transform(combo) if (self.calibrator and self.calibrator.fitted()) else combo
        mag = np.nan_to_num(mag)
        if self.pos_cap_pct and np.isfinite(mag).any() and len(mag) >= 10:           # tail cap
            lo, hi = np.nanpercentile(mag, 100 - self.pos_cap_pct), np.nanpercentile(mag, self.pos_cap_pct)
            mag = np.clip(mag, lo, hi)
        pos = mag - mag.mean()                                                        # market-neutral; exposure NOT vol-modulated
        tac = self.vol_gate.execution_tactic(t) if self.vol_gate else None
        return {"t": int(t), "asset_idx": m, "position": pos, "combined": combo, "exec_tactic": tac}
