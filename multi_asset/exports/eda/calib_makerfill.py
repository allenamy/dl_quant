"""0C Track-1 — maker-fill CONSERVATIVE calibration on 14 mega-cap bar_1s (READ-ONLY).
Per coin: liquidity (hourly notional), spread, adverse-selection markout, and fill-rate as a function
of (order/hourly-notional f, working-window k). CONSERVATIVE choices: join-at-back (queue-ahead = full
L1 notional), trade-driven depletion ONLY (exclude cancels bkDel -> only raises real fills), our full
order O must clear on top of the L1 queue. Writes exports/eda/makerfill_calib_raw.json.
"""
import sys, json, time, numpy as np
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
from multi_asset.data.bar_loader import load_day_panel

EDA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/eda/"
SYM = ["bnfbtc", "bnfeth", "bnfsol", "bnfbnb", "bnfxrp", "bnfdog", "bnfada",
       "bnflink", "bnfbch", "bnftrx", "bnfltc", "bnfdot", "bnffil", "bnfetc"]
DAYS = [20220315, 20220615, 20221017, 20230315, 20230615, 20231016, 20240315, 20240617,
        20241015, 20250317, 20250616, 20250915]   # 3/yr across 2022-2025 regimes
KS = [60, 300, 900]
FGRID = [0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1]  # order as fraction of HOURLY notional
ANCHOR_STEP = 1800   # sample a working-order every 30 min, both directions
MARKOUT_D = 60


def col(dp, s, n):
    return dp.data[s][:, dp.cols.index(n)].astype(np.float64)


if __name__ == "__main__":
    # accumulators per coin
    acc = {s: dict(hrN=[], spr=[], half=[], mk=[],
                   fill={k: {f: [0, 0] for f in FGRID} for k in KS}) for s in SYM}
    for day in DAYS:
        t0 = time.time()
        try:
            dp = load_day_panel(day, SYM)
        except Exception as e:
            print(f"day {day} load fail {e!r}", flush=True); continue
        T = len(dp.ts)
        anchors = np.arange(3600, T - 1000, ANCHOR_STEP)   # skip first hour, leave tail for markout+k
        for s in SYM:
            mid = col(dp, s, "mid"); bid = col(dp, s, "bid"); ask = col(dp, s, "ask")
            bidszN = col(dp, s, "bidsz") * mid; askszN = col(dp, s, "asksz") * mid
            sellN = np.nan_to_num(col(dp, s, "tdQtyPxSell")); buyN = np.nan_to_num(col(dp, s, "tdQtyPxBuy"))
            good = np.isfinite(mid) & (mid > 0)
            hrN = float(np.nanmean((buyN + sellN)[good]) * 3600.0)
            spr = float(np.nanmedian(((ask - bid) / mid * 1e4)[good]))
            acc[s]["hrN"].append(hrN); acc[s]["spr"].append(spr); acc[s]["half"].append(spr / 2.0)
            csum_sell = np.concatenate([[0.0], np.cumsum(sellN)])   # prefix sums for O(1) windows
            csum_buy = np.concatenate([[0.0], np.cumsum(buyN)])
            for bi in anchors:
                if bi + 1000 >= T or not good[bi]:
                    continue
                for dir_buy in (True, False):
                    q0 = bidszN[bi] if dir_buy else askszN[bi]      # L1 queue-ahead notional (join-at-back)
                    if not np.isfinite(q0) or q0 <= 0:
                        continue
                    csum = csum_sell if dir_buy else csum_buy
                    for k in KS:
                        cumk = csum[bi + 1 + k] - csum[bi + 1]      # opposite-taker notional over k s
                        for f in FGRID:
                            O = f * hrN
                            acc[s]["fill"][k][f][1] += 1
                            if cumk >= q0 + O:
                                acc[s]["fill"][k][f][0] += 1
                    # markout at join-at-back fill (first sec cum_opp >= q0), D forward, signed favourable
                    need = q0
                    # find first t in [bi+1, bi+900] where running cum >= need
                    win = (csum[bi + 1: bi + 1 + 900] - csum[bi + 1])
                    hit = np.where(win >= need)[0]
                    if hit.size:
                        fi = bi + 1 + int(hit[0])
                        if fi + MARKOUT_D < T and good[fi]:
                            mv = (mid[fi + MARKOUT_D] - mid[fi]) / mid[fi] * 1e4
                            acc[s]["mk"].append(mv if dir_buy else -mv)
        print(f"day {day} done {time.time()-t0:.0f}s", flush=True)

    out = {}
    for s in SYM:
        a = acc[s]
        mk = np.array(a["mk"]) if a["mk"] else np.array([np.nan])
        fr = {str(k): {str(f): (a["fill"][k][f][0] / a["fill"][k][f][1] if a["fill"][k][f][1] else np.nan)
                       for f in FGRID} for k in KS}
        out[s[3:]] = dict(hourly_notl_usd=round(float(np.median(a["hrN"])), 0),
                          spread_bps=round(float(np.median(a["spr"])), 4),
                          half_spread_bps=round(float(np.median(a["half"])), 4),
                          markout_mean_bps=round(float(np.nanmean(mk)), 4),
                          markout_p25_bps=round(float(np.nanpercentile(mk, 25)), 4),
                          markout_median_bps=round(float(np.nanmedian(mk)), 4),
                          n_markout=int(np.isfinite(mk).sum()),
                          fill_rate=fr)
        print(f"{s[3:]:>5} hrN ${out[s[3:]]['hourly_notl_usd']/1e6:.1f}M spr {out[s[3:]]['spread_bps']:.2f} "
              f"mk {out[s[3:]]['markout_mean_bps']:+.3f} fill(f=1%,k=300) {fr['300']['0.01']:.2f}", flush=True)
    json.dump(dict(days=DAYS, ks=KS, fgrid=FGRID, markout_d=MARKOUT_D, per_coin=out),
              open(EDA + "makerfill_calib_raw.json", "w"), indent=2, default=str)
    print("SAVED " + EDA + "makerfill_calib_raw.json", flush=True)
