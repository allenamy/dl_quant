"""Engine C2 (revised per 0C tail_corisk.md): vol-gate = EXECUTION-TACTIC modulator, NOT exposure.

0C proved the book is a crisis BENEFICIARY (high-rvol Sharpe still +4.14; crisis-day leg corr -0.05;
worst-BTC-day combo mean +0.47) -> book-level de-leveraging LOSES money and forfeits the tail-hedge
property. But the tick-research execution degradation (crash-day markout -5.3) is real. So on high
BTC rvol this ONLY makes order placement more conservative (wider quotes / smaller slices / more
patient) while the TARGET POSITION is unchanged. Exposure modulation is disabled by design.
"""
import numpy as np


class VolGate:
    def __init__(self, source, thresh_bps_min=18.0, window_h=24, max_widen=2.0, min_slice=0.3):
        self.src = source; self.thresh = thresh_bps_min; self.window_h = window_h
        self.max_widen = max_widen; self.min_slice = min_slice; self.log = []

    def execution_tactic(self, t):
        """Order-placement tactic (NOT a position multiplier). exposure_mult is pinned to 1.0."""
        rv = self.src.btc_rvol_bps_min(t, self.window_h)
        base = {"quote_width_mult": 1.0, "slice_frac": 1.0, "patience": "normal",
                "rvol_bps_min": (round(rv, 3) if np.isfinite(rv) else None),
                "stress": False, "exposure_mult": 1.0}
        if not np.isfinite(rv) or rv <= self.thresh:
            return base
        over = min((rv - self.thresh) / self.thresh, 1.0)
        tac = {"quote_width_mult": 1.0 + over * (self.max_widen - 1.0),
               "slice_frac": 1.0 - over * (1.0 - self.min_slice),
               "patience": "patient", "rvol_bps_min": round(rv, 3),
               "stress": True, "exposure_mult": 1.0}       # EXPOSURE UNCHANGED (crisis beneficiary)
        self.log.append({"t": int(t), **tac})
        return tac

    def gate_log(self):
        return self.log
