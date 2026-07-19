"""Engine C6: cross-leg netting execution (0C crossleg_netting.md).

Slow legs' order timing aligned to king's 4h grid (<=4h delay, negligible for 8h/24h/daily signals);
compute the NET target position each 4h anchor and trade only the delta. Locks in the honest free
netting. NOT the daily-batch 75% hedge (that is king 4h-alpha signal loss disguised as savings --
0C flagged the trap; we never down-sample king).

Caliber note (0C 2026-07-15): this 4h-sync cadence-hold implementation IS the DEPLOYMENT spec
(11.9% hedge / 197.9 bps/yr on the shipped engine panel). It supersedes 0C's earlier proxy-panel
preview (86-179 bps/yr / 5-8%) which used a different, non-shipped funding/size construction.
Both are correct on their own panel; the engine number ships.

Leg rebalance cadences (0C): king 4h (dominant), funding 8h, s2 24h, size daily.

v1 fix: the net book each anchor is routed through chain.shape_position() (C3 isotonic calibrate +
tail cap + market-neutral) -- so C3 and the pos cap are on the live P&L path. The shaped book is
renormalized to the UN-shaped book gross (constant exposure -- matches vol-gate "exposure not
modulated"), so shaping enters only as within-anchor relative reweighting + tail trim (no global
scale blowup), the turnover scales stay consistent, and the no-shaping limit reproduces the blessed
baseline exactly. gross_turn is the pre-combination independent-trade counterfactual (unshaped);
net_turn is the shaped net book's actual turnover; hedge_rate = 1 - net/gross is the free netting.
"""
import numpy as np

LEG_CADENCE_H = {"king": 4, "s2": 24, "funding": 8, "size": 24}


class CrossLegNetting:
    def __init__(self, chain, weights, cadence=None, cost_bps=1.9):
        self.chain = chain; self.w = weights
        self.cad = dict(cadence or LEG_CADENCE_H); self.cost = cost_bps

    def run(self, anchors, ts, calib_by_year=None, year_of=None):
        """anchors: sorted king-4h anchor hour-indices. calib_by_year/year_of: optional walk-forward
        yearly C3 calibrators swapped in per year. Returns net positions + turnover stats."""
        chain = self.chain; N = chain.src.N
        if chain.funding_risk is not None:
            chain.funding_risk.n_gated = 0                # count only this run's dispersion gates
        held = {k: np.zeros(N) for k in self.w}
        prev_net = np.zeros(N)
        gross_turn = 0.0; net_turn = 0.0; net_positions = []
        cur_year = None
        for i, t in enumerate(anchors):
            ti = int(t)
            if calib_by_year is not None and year_of is not None:
                y = int(year_of[i])
                if y != cur_year:
                    chain.calibrator = calib_by_year.get(y); cur_year = y   # None -> identity
            legpos, m = chain.leg_positions(ti)                             # L1 sub-portfolios (len |m|)
            for k in self.w:
                if i == 0 or (ti % self.cad[k] == 0):                       # update leg only at its cadence
                    new = np.zeros(N); new[m] = legpos[k]
                    gross_turn += self.w[k] * np.abs(new - held[k]).sum()   # book-weighted independent trade
                    held[k] = new
            combo_full = sum(self.w[k] * held[k] for k in self.w)           # full-N combined held legs
            active = combo_full[m]
            base = active - active.mean()                                   # un-shaped book gross ref
            gref = np.abs(base).sum()
            shaped = chain.shape_position(active)                           # C3 + tail cap + market-neutral
            gsh = np.abs(shaped).sum()
            if gsh > 1e-12 and gref > 1e-12:
                shaped = shaped * (gref / gsh)                              # renorm to blessed book gross
            net = np.zeros(N); net[m] = shaped
            net_turn += np.abs(net - prev_net).sum()
            prev_net = net; net_positions.append((ti, m, net[m].copy()))
        yrs = (int(ts[anchors[-1]]) - int(ts[anchors[0]])) / (1000 * 3600 * 24 * 365.25)
        gross_ann = gross_turn / max(yrs, 1e-9); net_ann = net_turn / max(yrs, 1e-9)
        hedge = 1 - net_ann / gross_ann if gross_ann > 0 else 0.0
        return {"net_positions": net_positions, "gross_turn_ann": gross_ann, "net_turn_ann": net_ann,
                "hedge_rate": hedge, "savings_bps_yr": (gross_ann - net_ann) * self.cost, "years": yrs}
