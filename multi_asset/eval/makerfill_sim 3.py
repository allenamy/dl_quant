"""Maker-fill effective-cost simulator (APPROVED 2026-07-11, highest-value workstream).

For M0's ACTUAL rebalance orders (fullhist preds -> rank weights -> per-asset direction), simulate
working the order PASSIVELY at the touch for k seconds, from our 1s book+flow columns, and compute
the data-supported EFFECTIVE cost per side vs the naive taker 1.7 bps.

Per order (asset s, rebalance ts t, direction dir):
  - post at touch (buy@bid0 / sell@ask0); queue-ahead ~= same-side L1 size (JOIN-AT-BACK approx).
  - queue depletes each second by opposite-side taker volume + same-side cancels (bkDel). fill when
    cumulative depletion >= queue-ahead, within k.
  - filled: markout(D) = signed mid move from fill to fill+D (adverse if against us). half_spread
    captured. effective_cost = -markout - half_spread - rebate  (bps, +=cost).
  - unfilled within k: taker-complete -> taker_cost = half_spread + taker_fee.
  effective = p_fill*(-markout - half_spread - rebate) + (1-p_fill)*taker_cost.

APPROXIMATIONS (labeled, per spec):
  - queue-join-at-back (we see aggregate L1, not our rank) -> CONSERVATIVE (overstates queue-ahead
    -> understates fill rate -> if anything overstates cost).
  - 1s aggregation (no sub-second sequencing; a second's trades vs cancels are unordered) -> OPTIMISTIC
    (ignores within-second adverse ordering). Net: the two biases partly offset; treat as order-of-mag.

Run: PYTHONPATH=. python multi_asset/eval/makerfill_sim.py [--days_per_year N] [--k 60] [--markout 60]
"""
from __future__ import annotations
import argparse
import glob
import os.path as p
import numpy as np
from multi_asset.data.bar_loader import load_day_panel

EXPORT = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train"
SYMBOLS = ["bnfbtc", "bnfeth", "bnfsol", "bnfbnb", "bnfxrp", "bnfdog", "bnfada",
           "bnflink", "bnfbch", "bnftrx", "bnfltc", "bnfdot", "bnffil", "bnfetc"]
TAKER_FEE = 1.5           # bps taker fee (+ half-spread added) — Binance USDT-perp taker floor-ish
REBATE = 0.0             # bps maker rebate (conservative: 0)


def rank_weights(scores):
    r = scores.argsort().argsort().astype(np.float64)
    r = r - r.mean(); sden = np.abs(r).sum()
    return r / sden * 2.0 if sden > 0 else r


def load_m0(tag):
    d = p.join(EXPORT, tag)
    ref = np.load(p.join(d, "panel_ref.npz"), allow_pickle=True)
    ts, day, CL = ref["ts"].astype(np.int64), ref["day"], ref["CL"]
    T, S = CL.shape
    pred = np.full((T, S), np.nan, np.float32)
    for f in sorted(glob.glob(p.join(d, "fold_*_preds.npz"))):
        z = np.load(f, allow_pickle=True); rows = z["te_rows"]; pred[rows] = z["pred"][rows]
    return ts, day, CL, pred


def sim_order(dir_buy, bi, dp, s, k, D):
    """One order at bar bi. Return (filled, markout_bps, half_spread_bps, spread_bps) or None."""
    def c(n):
        return dp.data[s][:, dp.cols.index(n)].astype(np.float64)
    mid = c("mid"); bid = c("bid"); ask = c("ask")
    Tn = mid.shape[0]
    if bi + k + D >= Tn or not (np.isfinite(mid[bi]) and mid[bi] > 0):
        return None
    spr = (ask[bi] - bid[bi]) / mid[bi] * 1e4
    if not np.isfinite(spr) or spr < 0:
        return None
    half = spr / 2.0
    # Queue depletes via OPPOSITE-side taker VOLUME consuming the orders ahead (join-at-back).
    # Trade-driven only: bkDel is per-second cancel volume stored NEGATIVE and can't be cleanly
    # attributed to ahead-of-us vs behind-us, so we EXCLUDE it -> CONSERVATIVE (cancels-ahead would
    # only raise fills / lower cost). Standard queue-reactive fill.
    if dir_buy:
        queue = c("bidsz")[bi]
        deplete = c("tdQtySell")                     # sell takers consume our bid queue
    else:
        queue = c("asksz")[bi]
        deplete = c("tdQtyBuy")
    if not np.isfinite(queue) or queue <= 0:
        return None
    cum = np.nancumsum(deplete[bi + 1:bi + 1 + k])
    hit = np.where(cum >= queue)[0]
    if hit.size == 0:
        return False, np.nan, half, spr             # unfilled within k
    fill_i = bi + 1 + int(hit[0])
    # markout D seconds after fill; signed so + = favourable (mid moves our way)
    mv = (mid[fill_i + D] - mid[fill_i]) / mid[fill_i] * 1e4
    markout = mv if dir_buy else -mv
    return True, float(markout), half, spr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days_per_year", type=int, default=8)
    ap.add_argument("--k", type=int, default=60)
    ap.add_argument("--markout", type=int, default=60)
    ap.add_argument("--tag", default="m0_fullhist_wf")
    args = ap.parse_args()
    ts, day, CL, pred = load_m0(args.tag)

    # sample days per year that have clean rebalances
    cl_days = np.unique(day[CL.any(1)])
    by_year = {}
    for d in cl_days:
        by_year.setdefault(int(d) // 10000, []).append(int(d))
    sample = []
    for y, ds in by_year.items():
        ds = sorted(ds); step = max(1, len(ds) // args.days_per_year)
        sample += ds[::step][:args.days_per_year]
    print(f"[sim] tag={args.tag} k={args.k}s markout={args.markout}s | sampling {len(sample)} days "
          f"across {sorted(by_year)} | taker={TAKER_FEE}+half bps", flush=True)

    # accumulators: per (sym, year) -> lists
    acc = {}
    for d in sample:
        yr = d // 10000
        try:
            dp = load_day_panel(d, SYMBOLS)
        except Exception as e:
            print(f"  day {d} load fail {e!r}"); continue
        drows = np.where((day == d) & CL.any(1))[0]
        for t in drows:
            v = CL[t] & np.isfinite(pred[t])
            if v.sum() < 5:
                continue
            w = np.zeros(len(SYMBOLS)); idx = np.where(v)[0]
            w[idx] = rank_weights(pred[t, idx])
            bi = int(np.searchsorted(dp.ts, ts[t]))
            if bi <= 0 or bi >= dp.ts.shape[0]:
                continue
            for si in idx:
                if abs(w[si]) < 1e-9:
                    continue
                res = sim_order(w[si] > 0, bi, dp, SYMBOLS[si], args.k, args.markout)
                if res is None:
                    continue
                filled, mk, half, spr = res
                key = (SYMBOLS[si][3:], yr)
                a = acc.setdefault(key, {"n": 0, "fill": 0, "mk": [], "half": [], "eff": []})
                a["n"] += 1
                taker = half + TAKER_FEE
                if filled:
                    a["fill"] += 1; a["mk"].append(mk)
                    eff = (-mk - half - REBATE)
                else:
                    eff = taker
                a["half"].append(half); a["eff"].append(eff)
    # report
    print(f"\n{'sym':>6} {'yr':>5} {'n':>6} {'fill%':>6} {'half_bps':>8} "
          f"{'mk_mean':>8} {'mk_p10':>7} {'mk_p90':>7} {'eff_bps':>8}  (taker ref ~1.7)")
    yr_eff = {}
    for (sym, yr) in sorted(acc):
        a = acc[(sym, yr)]
        fillr = a["fill"] / max(a["n"], 1)
        mka = np.array(a["mk"]) if a["mk"] else np.array([np.nan])
        mk = np.nanmean(mka)
        mk10 = np.nanpercentile(mka, 10) if a["mk"] else np.nan     # adverse tail = silent bleed
        mk90 = np.nanpercentile(mka, 90) if a["mk"] else np.nan
        half = np.nanmean(a["half"]); eff = np.nanmean(a["eff"])
        print(f"{sym:>6} {yr:>5} {a['n']:>6} {fillr:>6.2f} {half:>8.3f} "
              f"{mk:>+8.3f} {mk10:>+7.2f} {mk90:>+7.2f} {eff:>+8.3f}")
        yr_eff.setdefault(yr, []).append(eff)
    print("\n=== per-YEAR mean effective cost bps/side (avg over assets) ===")
    for yr in sorted(yr_eff):
        print(f"  {yr}: {np.nanmean(yr_eff[yr]):+.3f} bps/side  (vs taker ~1.7)")


if __name__ == "__main__":
    main()
