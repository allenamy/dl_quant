"""Maker-fill feasibility grounding (2026-07-11, user execution challenge). Computes the
order-of-magnitude quantities a fill-probability model needs, from our 1s bar columns, to
answer: is a passive/maker execution economically different from the naive taker 1.7 bps/side?

Per sample day/asset:
  - median spread (bps)                        <- the maker's spread-capture edge (half-spread)
  - L1 queue-depletion time = bidsz0 / sell-rate (s)  <- can a resting order fill in 30-180s?
  - cancel rate bkDelBid vs L1                 <- queue also depletes via cancels (helps fill)
  - ADVERSE-SELECTION markout: after a sell-heavy second (a maker BUY would fill), the forward
    mid move over {30,60}s (bps). Negative = mid drifts against the fill = adverse cost.
The effective maker cost ~ adverse_markout - half_spread - rebate; sign decides if fast signals
come alive. Queue position is APPROXIMATE (L1 aggregate size, our order assumed at the back).

Run: PYTHONPATH=. python multi_asset/eval/makerfill_feasibility.py
"""
from __future__ import annotations
import numpy as np
from multi_asset.data.bar_loader import load_day_panel

SY = ["bnfbtc", "bnfeth", "bnfsol", "bnffil"]     # mega / mega / mid / small-cap
DAYS = [20240603, 20240917, 20250310, 20250715]   # spread across the window


def col(dp, s, n):
    return dp.data[s][:, dp.cols.index(n)].astype(np.float64)


def main():
    print(f"{'day':>9} {'sym':>7} {'spr_bps':>8} {'L1sz':>10} {'sell/s':>9} "
          f"{'depl_s':>7} {'cxl/L1':>7} {'mk30_bps':>9} {'mk60_bps':>9} {'p_fill60':>8}")
    for day in DAYS:
        try:
            dp = load_day_panel(day, SY)
        except Exception as e:
            print(f"{day} load fail {e!r}"); continue
        for s in SY:
            mid = col(dp, s, "mid"); bid = col(dp, s, "bid"); ask = col(dp, s, "ask")
            bidsz = col(dp, s, "bidsz"); tdSell = col(dp, s, "tdQtySell")
            bkDel = col(dp, s, "bkDelBid")
            good = np.isfinite(mid) & (mid > 0) & np.isfinite(bidsz) & (bidsz > 0)
            spr = np.nanmedian(((ask - bid) / mid * 1e4)[good])
            L1 = np.nanmedian(bidsz[good])
            snz = tdSell[tdSell > 0]
            sellrate = np.nanmedian(snz) if snz.size else np.nan     # median non-zero sell qty/s
            depl = L1 / sellrate if sellrate and sellrate > 0 else np.nan
            cxl = np.nanmedian(bkDel[good]) / L1 if L1 > 0 else np.nan
            # fill event proxy: a second with sell volume >= the L1 queue (order at back clears)
            # cheap proxy for "a maker buy at bid would have filled this second"
            fill_ev = tdSell >= L1
            def markout(D):
                mk = (mid[D:] - mid[:-D]) / mid[:-D] * 1e4
                fe = fill_ev[:-D] & good[:-D] & np.isfinite(mk)
                return float(np.nanmean(mk[fe])) if fe.sum() > 50 else np.nan
            mk30, mk60 = markout(30), markout(60)
            # crude P(fill within 60s): fraction of starts where cumulative 60s sell vol >= L1
            csum = np.convolve(np.nan_to_num(tdSell), np.ones(60), "valid")
            pfill = float((csum >= L1).mean()) if csum.size else np.nan
            print(f"{day:>9} {s[3:]:>7} {spr:>8.3f} {L1:>10.1f} {sellrate:>9.2f} "
                  f"{depl:>7.1f} {cxl:>7.3f} {mk30:>9.4f} {mk60:>9.4f} {pfill:>8.3f}")


if __name__ == "__main__":
    main()
