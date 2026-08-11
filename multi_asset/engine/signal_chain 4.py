"""Engine C1 (v1): signal production chain.

Per-leg cross-sectional SIGNED signals -> L1-normalized sub-portfolios (unit gross each, book
weights control capital share) -> combine -> C3 isotonic calibrate (fit on a val window) -> tail
cap -> market-neutral target position. The netting layer (C6) holds the same leg sub-portfolios at
their cadence and routes the combined signal through the SAME shape_position() tail, so C3 + the
tail cap are on the live P&L path (v1 fix: previously netting.run bypassed target_position).

vol-gate is EXECUTION-TACTIC metadata only (exposure is NOT modulated -- 0C: the book is a crisis
beneficiary). funding leg weighting is z (default legacy) or rank (bounded; see funding_mode).
"""
import numpy as np
from scipy.stats import rankdata

DEFAULT_WEIGHTS = {"king": 0.30, "s2": 0.10, "funding": 0.30, "size": 0.30}   # 0C 4-leg book weights
DEFAULT_SIGNS = {"king": +1, "s2": +1, "funding": -1, "size": +1}             # funding = crowding-reversion


def _z(x):
    x = np.asarray(x, float); m = np.isfinite(x); out = np.zeros_like(x)
    if m.sum() >= 3:
        mu, sd = x[m].mean(), x[m].std()
        if sd > 1e-12:
            out[m] = (x[m] - mu) / sd
    return out


def _rank_centered(x):
    """cross-sectional rank mapped to [-1, 1] (zero-mean, naturally bounded). NaN -> 0."""
    x = np.asarray(x, float); m = np.isfinite(x); out = np.zeros_like(x)
    if m.sum() >= 3:
        r = rankdata(x[m]); k = len(r)
        out[m] = (2.0 * (r - 1) / (k - 1) - 1.0) if k > 1 else 0.0
    return out


def _l1(x):
    g = np.abs(x).sum(); return x / g if g > 1e-9 else x


class SignalChain:
    def __init__(self, source, weights=None, signs=None, calibrator=None, vol_gate=None,
                 funding_risk=None, pos_cap_pct=99.0, funding_mode="z"):
        self.src = source; self.w = dict(weights or DEFAULT_WEIGHTS); self.sign = dict(signs or DEFAULT_SIGNS)
        self.calibrator = calibrator; self.vol_gate = vol_gate; self.funding_risk = funding_risk
        self.pos_cap_pct = pos_cap_pct; self.funding_mode = funding_mode

    def _funding_base(self, funding_raw):
        return _rank_centered(funding_raw) if self.funding_mode == "rank" else _z(funding_raw)

    def leg_signals(self, t):
        """per-member SIGNED leg signals (funding risk-controlled), unnormalized (z/rank scale)."""
        legs, m = self.src.legs_raw(t)
        out = {}
        for k in self.w:
            if k == "funding":
                base = self._funding_base(legs["funding"])
                if self.funding_risk is not None:
                    base, _ = self.funding_risk.apply(base, funding_raw=legs["funding"])
                out[k] = self.sign[k] * base
            else:
                out[k] = self.sign[k] * _z(legs[k])
        return out, m

    def leg_positions(self, t):
        """per-leg L1-normalized sub-portfolios (unit gross each). The netting layer holds these."""
        legs, m = self.leg_signals(t)
        return {k: _l1(legs[k]) for k in legs}, m

    def combined_signal(self, t):
        legs, m = self.leg_positions(t)
        return sum(self.w[k] * legs[k] for k in self.w), m

    def shape_position(self, combo):
        """C3 isotonic calibrate (if fitted) -> tail cap -> market-neutral demean. The shared tail
        used by BOTH target_position() and the netting P&L path."""
        mag = self.calibrator.transform(combo) if (self.calibrator and self.calibrator.fitted()) else np.asarray(combo, float)
        mag = np.nan_to_num(mag)
        if self.pos_cap_pct and mag.size >= 10 and np.isfinite(mag).any():
            lo, hi = np.nanpercentile(mag, 100 - self.pos_cap_pct), np.nanpercentile(mag, self.pos_cap_pct)
            mag = np.clip(mag, lo, hi)
        return mag - mag.mean()

    def target_position(self, t):
        combo, m = self.combined_signal(t)
        pos = self.shape_position(combo)
        tac = self.vol_gate.execution_tactic(t) if self.vol_gate else None
        return {"t": int(t), "asset_idx": m, "position": pos, "combined": combo, "exec_tactic": tac}

    def fit_calibrator_on(self, anchors, calibrator):
        """fit C3 on (combined_signal, realized_bps) pairs over an explicit anchor set (walk-forward)."""
        S, Y = [], []
        for t in anchors:
            c, _ = self.combined_signal(int(t)); r = self.src.realized_fwd_bps(int(t))
            ok = np.isfinite(c) & np.isfinite(r)
            if ok.any():
                S.append(c[ok]); Y.append(r[ok])
        calibrator.fit(np.concatenate(S), np.concatenate(Y)); return calibrator

    def fit_calibrator(self, val_ym, calibrator):
        self.calibrator = self.fit_calibrator_on(self.src.month_anchors(val_ym), calibrator); return self
