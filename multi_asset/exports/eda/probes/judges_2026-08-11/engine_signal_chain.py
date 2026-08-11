"""Engine C1: signal production chain.

panel@t -> 4-leg cross-sectional signals (king/S2 = OOS DL preds [checkpoint-inference in live
mode]; funding/SIZE = factor formulas) -> weighted combine -> isotonic-calibrated E[bps] magnitude
-> vol-gate participation -> market-neutral target positions. Replay mode over existing anchors;
live-mode swaps PanelSource for a live feed and the OOS pred reads for checkpoint inference.
"""
import numpy as np

# final book weights + leg signs are CONFIG (0C sets the shipped values); these are v0 placeholders.
DEFAULT_WEIGHTS = {"king": 0.35, "s2": 0.25, "funding": 0.20, "size": 0.20}
DEFAULT_SIGNS = {"king": +1, "s2": +1, "funding": -1, "size": +1}   # funding = crowding-reversion


def _z(x):
    x = np.asarray(x, float); m = np.isfinite(x); out = np.zeros_like(x)
    if m.sum() >= 3:
        mu, sd = x[m].mean(), x[m].std()
        if sd > 1e-12:
            out[m] = (x[m] - mu) / sd
    return out


class SignalChain:
    def __init__(self, source, weights=None, signs=None, calibrator=None, vol_gate=None):
        self.src = source
        self.w = dict(weights or DEFAULT_WEIGHTS); self.sign = dict(signs or DEFAULT_SIGNS)
        self.calibrator = calibrator; self.vol_gate = vol_gate

    def combined_signal(self, t):
        legs, m = self.src.legs_raw(t)
        combo = np.zeros(len(m))
        for k in self.w:
            combo += self.w[k] * self.sign[k] * _z(legs[k])
        return combo, m

    def fit_calibrator(self, val_ym, calibrator):
        S, Y = [], []
        for t in self.src.month_anchors(val_ym):
            combo, m = self.combined_signal(int(t))
            S.append(combo); Y.append(self.src.realized_fwd_bps(int(t)))
        calibrator.fit(np.concatenate(S), np.concatenate(Y))
        self.calibrator = calibrator
        return self

    def target_position(self, t):
        combo, m = self.combined_signal(t)
        mag = self.calibrator.transform(combo) if (self.calibrator and self.calibrator.fitted()) else combo
        mag = np.nan_to_num(mag)
        p = self.vol_gate.participation(t) if self.vol_gate else 1.0
        mag = mag * p
        pos = mag - mag.mean()                       # market-neutral (dollar-neutral)
        return {"t": int(t), "asset_idx": m, "position": pos, "combined": combo, "participation": p}

    def replay(self, ym):
        return [self.target_position(int(t)) for t in self.src.month_anchors(ym)]
