"""0C Track-1 deepdive Part-2/3 — regime-stratified bar_1s sweep (14 mega-caps, ~28 days incl 2022
LUNA/FTX + 2024-08-05 crash). Per-day per-coin fill-rate(f,k) + spread + hourly-notl + daily BTC rvol
(regime descriptor). Answers: is the fill curve still liquidity-invariant on crash days? do spreads
widen? (markout comes from TICK, not this — 1s markout proven unreliable). CPU-only READ-ONLY.
Writes exports/eda/bar_regime_raw.json.
"""
import sys, time, json, numpy as np
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
from multi_asset.data.bar_loader import load_day_panel

EDA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/eda/"
SYM = ["bnfbtc", "bnfeth", "bnfsol", "bnfbnb", "bnfxrp", "bnfdog", "bnfada",
       "bnflink", "bnfbch", "bnftrx", "bnfltc", "bnfdot", "bnffil", "bnfetc"]
# regime-spanning days across 2022-2025; STRESS = LUNA 2022-05-12, FTX 2022-11-09, others
DAYS = [20220315, 20220512, 20220615, 20221109, 20221215, 20230317, 20230615, 20230817,
        20231016, 20240117, 20240315, 20240413, 20240617, 20240805, 20241015, 20241211,
        20250203, 20250317, 20250616, 20250714, 20250915, 20251015]
KS = [60, 300, 900]
FGRID = [0.002, 0.005, 0.01, 0.02, 0.05]
STEP = 1800


def col(dp, s, n):
    return dp.data[s][:, dp.cols.index(n)].astype(np.float64)


if __name__ == "__main__":
    out = {}
    for day in DAYS:
        t0 = time.time()
        try:
            dp = load_day_panel(day, SYM)
        except Exception as e:
            print(f"{day} fail {e!r}", flush=True); continue
        T = len(dp.ts); anchors = np.arange(3600, T - 1000, STEP)
        # BTC rvol (regime): std of 60s mid logret
        bmid = col(dp, "bnfbtc", "mid"); gm = bmid[::60]; gm = gm[np.isfinite(gm) & (gm > 0)]
        rvol = float(np.std(np.diff(np.log(gm))) * 1e4)
        per_coin = {}
        for s in SYM:
            mid = col(dp, s, "mid"); bid = col(dp, s, "bid"); ask = col(dp, s, "ask")
            bidszN = col(dp, s, "bidsz"); askszN = col(dp, s, "asksz")
            sellA = np.nan_to_num(col(dp, s, "tdQtySell")); buyA = np.nan_to_num(col(dp, s, "tdQtyBuy"))
            px = np.nan_to_num(col(dp, s, "tdQtyPxSell")) + np.nan_to_num(col(dp, s, "tdQtyPxBuy"))
            good = np.isfinite(mid) & (mid > 0)
            hrN = float(np.nanmean(px[good]) * 3600.0)
            spr = float(np.nanmedian(((ask - bid) / mid * 1e4)[good]))
            csS = np.concatenate([[0.0], np.cumsum(sellA)]); csB = np.concatenate([[0.0], np.cumsum(buyA)])
            res = {str(k): {f: [0, 0] for f in FGRID} for k in KS}
            for bi in anchors:
                if bi + 1000 >= T or not good[bi]:
                    continue
                for dir_buy in (True, False):
                    p0 = bid[bi] if dir_buy else ask[bi]; q0 = bidszN[bi] if dir_buy else askszN[bi]
                    if not (p0 > 0 and q0 > 0):
                        continue
                    cs = csS if dir_buy else csB
                    for k in KS:
                        cumk = cs[bi + 1 + k] - cs[bi + 1]
                        for f in FGRID:
                            res[str(k)][f][1] += 1
                            if cumk >= q0 + f * hrN / p0:
                                res[str(k)][f][0] += 1
            fr = {str(k): {str(f): (res[str(k)][f][0] / res[str(k)][f][1] if res[str(k)][f][1] else np.nan)
                           for f in FGRID} for k in KS}
            per_coin[s[3:]] = dict(hourly_notl=round(hrN, 0), spread_bps=round(spr, 3), fill_rate=fr)
        out[str(day)] = dict(btc_rvol_bps_min=round(rvol, 2), per_coin=per_coin)
        print(f"{day} ({time.time()-t0:.0f}s) rvol {rvol:.1f} | btc spr {per_coin['btc']['spread_bps']:.3f} "
              f"fill(1%k300) btc {per_coin['btc']['fill_rate']['300']['0.01']:.2f} "
              f"fil {per_coin['fil']['fill_rate']['300']['0.01']:.2f}", flush=True)
    json.dump(dict(days=DAYS, ks=KS, fgrid=FGRID, per_day=out), open(EDA + "bar_regime_raw.json", "w"), indent=2, default=str)
    print("SAVED " + EDA + "bar_regime_raw.json", flush=True)
