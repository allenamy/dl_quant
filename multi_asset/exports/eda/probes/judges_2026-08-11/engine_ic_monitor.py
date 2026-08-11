"""Engine C4: IC monitor + retrain-trigger skeleton.

Rolling cross-sectional rank-IC over the (replayed) live signal, a decay alert threshold, and a
champion/challenger switch stub (OneNet-lite form). Retraining itself is NOT implemented — this is
the deployment hook a live system wires to promotion/retraining.
"""
import numpy as np
from collections import deque
from scipy.stats import rankdata


def xsec_rank_ic(pos, realized):
    pos = np.asarray(pos, float); realized = np.asarray(realized, float)
    ok = np.isfinite(pos) & np.isfinite(realized)
    if ok.sum() < 5:
        return np.nan
    rp, rr = rankdata(pos[ok]), rankdata(realized[ok])
    if rp.std() < 1e-12 or rr.std() < 1e-12:
        return np.nan
    return float(np.corrcoef(rp, rr)[0, 1])


class ICMonitor:
    def __init__(self, window=60, baseline_ic=None, decay_frac=0.5):
        self.window = window; self.baseline = baseline_ic; self.decay_frac = decay_frac
        self.ics = deque(maxlen=window); self.alerts = []; self.hist = []

    def update(self, t, pos, realized):
        ic = xsec_rank_ic(pos, realized)
        if np.isfinite(ic):
            self.ics.append(ic)
        roll = float(np.mean(self.ics)) if self.ics else float("nan")
        alert = (self.baseline is not None and len(self.ics) >= self.window
                 and roll < self.decay_frac * self.baseline)
        if alert:
            self.alerts.append({"t": int(t), "rolling_ic": round(roll, 4), "baseline": self.baseline})
        rec = {"t": int(t), "ic": ic, "rolling_ic": roll, "n": len(self.ics), "alert": bool(alert)}
        self.hist.append(rec)
        return rec

    def rolling_ic(self):
        return float(np.mean(self.ics)) if self.ics else float("nan")


class RetrainTrigger:
    """Champion/challenger switch stub. Signals a switch when the challenger's rolling IC beats the
    champion's by `margin` for `persist` consecutive steps; the caller promotes / triggers retrain."""
    def __init__(self, margin=0.003, persist=20):
        self.margin = margin; self.persist = persist; self.streak = 0; self.switches = []

    def step(self, t, champ_ic, chall_ic):
        if np.isfinite(champ_ic) and np.isfinite(chall_ic) and chall_ic > champ_ic + self.margin:
            self.streak += 1
        else:
            self.streak = 0
        if self.streak >= self.persist:
            self.switches.append({"t": int(t), "champ_ic": round(champ_ic, 4), "chall_ic": round(chall_ic, 4)})
            self.streak = 0
            return True
        return False
