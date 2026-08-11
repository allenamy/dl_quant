"""Engine C2: vol-gate position modulator.

BTC realized vol > threshold (tick-research ~18 bps/min) -> reduce participation / trend-neutral.
Parameterized (threshold / window / floor / curve). In replay mode logs every gate trigger.
Multiplies the calibrated magnitude by participation in [floor, 1].
"""
import numpy as np


class VolGate:
    def __init__(self, source, thresh_bps_min=18.0, window_h=24, floor=0.3,
                 curve="linear", full_at_ratio=1.0, floor_at_ratio=2.0):
        """participation=1 for rvol<=thresh*full_at_ratio; decays to `floor` by thresh*floor_at_ratio."""
        self.src = source; self.thresh = thresh_bps_min; self.window_h = window_h
        self.floor = floor; self.curve = curve
        self.full_at = thresh_bps_min * full_at_ratio; self.floor_at = thresh_bps_min * floor_at_ratio
        self.log = []

    def participation(self, t):
        rv = self.src.btc_rvol_bps_min(t, self.window_h)
        if not np.isfinite(rv):
            return 1.0
        if rv <= self.full_at:
            p = 1.0
        elif rv >= self.floor_at:
            p = self.floor
        else:
            frac = (rv - self.full_at) / max(self.floor_at - self.full_at, 1e-9)
            p = 1.0 - frac * (1.0 - self.floor)          # linear ramp
        if rv > self.thresh:
            self.log.append({"t": int(t), "rvol_bps_min": round(rv, 3), "participation": round(p, 3)})
        return float(p)

    def gate_log(self):
        return self.log
