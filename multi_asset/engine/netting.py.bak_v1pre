"""Engine C6: cross-leg netting execution (0C crossleg_netting.md).

Slow legs' order timing aligned to king's 4h grid (<=4h delay, negligible for 8h/24h/daily signals);
compute the NET target position each 4h anchor and trade only the delta. Locks in the honest free
netting (86-179 bps/yr @ book weights). NOT the daily-batch 75% hedge (that is king 4h-alpha signal
loss disguised as savings -- 0C flagged the trap; we never down-sample king).

Leg rebalance cadences (0C): king 4h (dominant), funding 8h, s2 24h, size daily.
"""
import numpy as np

LEG_CADENCE_H = {"king": 4, "s2": 24, "funding": 8, "size": 24}


def _l1(x):
    g = np.abs(x).sum(); return x / g if g > 1e-9 else x


class CrossLegNetting:
    def __init__(self, chain, weights, cadence=None, cost_bps=1.9):
        self.chain = chain; self.w = weights
        self.cad = dict(cadence or LEG_CADENCE_H); self.cost = cost_bps

    def run(self, anchors, ts):
        """anchors: sorted king-4h anchor hour-indices. Returns net positions + turnover stats."""
        N = self.chain.src.N
        held = {k: np.zeros(N) for k in self.w}
        prev_net = np.zeros(N)
        gross_turn = 0.0; net_turn = 0.0; net_positions = []
        for i, t in enumerate(anchors):
            legs, m = self.chain.leg_signals(int(t))
            for k in self.w:
                if i == 0 or (int(t) % self.cad[k] == 0):          # update leg only at its cadence
                    new = np.zeros(N); new[m] = _l1(legs[k])
                    gross_turn += self.w[k] * np.abs(new - held[k]).sum()   # book-weighted independent trade
                    held[k] = new
            net = sum(self.w[k] * held[k] for k in self.w)
            net = net - net.mean()                                  # market neutral
            net_turn += np.abs(net - prev_net).sum()
            prev_net = net; net_positions.append((int(t), m, net[m].copy()))
        yrs = (int(ts[anchors[-1]]) - int(ts[anchors[0]])) / (1000 * 3600 * 24 * 365.25)
        gross_ann = gross_turn / max(yrs, 1e-9); net_ann = net_turn / max(yrs, 1e-9)
        hedge = 1 - net_ann / gross_ann if gross_ann > 0 else 0.0
        return {"net_positions": net_positions, "gross_turn_ann": gross_ann, "net_turn_ann": net_ann,
                "hedge_rate": hedge, "savings_bps_yr": (gross_ann - net_ann) * self.cost, "years": yrs}
