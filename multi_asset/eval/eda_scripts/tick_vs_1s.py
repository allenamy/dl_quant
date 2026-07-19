"""0C Track-1 deepdive Part-1 — TICK-LEVEL validation of the 1s-bar maker-fill approximation.
TICK sim on Tardis µs book_snapshot_25 + trades (true price-level FIFO queue) vs my 1s-bar sim, same
BTC-perp days/anchors/order-grid. Isolates the 1s-aggregation bias + measures cancel-exclusion
conservatism + characterizes markout regime dependence (crash days). CPU-only READ-ONLY.
Writes exports/eda/tick_vs_1s_raw.json.
"""
import sys, time, json, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
from multi_asset.data.bar_loader import load_day_panel

TARDIS = "/mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/dl-tardis"
EDA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/eda/"
DAYS = ["2023-06-15", "2023-08-17", "2023-10-10", "2024-03-15", "2024-04-13", "2024-05-20",
        "2024-08-05", "2025-02-03", "2025-03-17", "2025-07-14", "2025-09-15", "2025-11-15"]
KS = [60, 300, 900]
FGRID = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05]
ANCHOR_STEP = 1800
MK_D = 60


def load_tardis(day):
    b = f"{TARDIS}/book_snapshot_25/{day}/binance-futures/BTCUSDT.csv.gz"
    t = f"{TARDIS}/trades/{day}/binance-futures/BTCUSDT.csv.gz"
    bk = pd.read_csv(b, usecols=["timestamp", "asks[0].price", "asks[0].amount", "bids[0].price", "bids[0].amount"])
    tr = pd.read_csv(t, usecols=["timestamp", "side", "price", "amount"])
    return (bk["timestamp"].to_numpy(np.int64),
            bk["bids[0].price"].to_numpy(float), bk["bids[0].amount"].to_numpy(float),
            bk["asks[0].price"].to_numpy(float), bk["asks[0].amount"].to_numpy(float),
            tr["timestamp"].to_numpy(np.int64), (tr["side"].to_numpy() == "sell"),
            tr["price"].to_numpy(float), tr["amount"].to_numpy(float))


def tick_day(day):
    bts, bbp, bba, bap, baa, tts, tsell, tpx, tam = load_tardis(day)
    mid = (bbp + bap) / 2.0
    hrN = float((tpx * tam).sum() / ((tts[-1] - tts[0]) / 1e6 / 3600))
    day0 = bts[0] - (bts[0] % (86400 * 1_000_000))
    anchors_us = day0 + (np.arange(3600, 86400 - 1000, ANCHOR_STEP)) * 1_000_000
    res = {str(k): {f: [0, 0] for f in FGRID} for k in KS}
    mks = []; cancel_clear = [0, 0]
    for au in anchors_us:
        bi = int(np.searchsorted(bts, au)) - 1
        if bi < 0 or bi + 5 >= len(bts):
            continue
        ti0 = int(np.searchsorted(tts, au)); ti1 = int(np.searchsorted(tts, au + 900 * 1_000_000))
        if ti1 <= ti0:
            continue
        wpx = tpx[ti0:ti1]; wam = tam[ti0:ti1]; wsell = tsell[ti0:ti1]; wts = tts[ti0:ti1]
        for dir_buy in (True, False):
            p0 = bbp[bi] if dir_buy else bap[bi]
            q0 = bba[bi] if dir_buy else baa[bi]
            if not (p0 > 0 and q0 > 0):
                continue
            consume = (wsell & (wpx <= p0)) if dir_buy else ((~wsell) & (wpx >= p0))
            ccum = np.cumsum(np.where(consume, wam, 0.0))
            for k in KS:
                kx = int(np.searchsorted(wts, au + k * 1_000_000))
                cumk = ccum[kx - 1] if kx > 0 else 0.0
                for f in FGRID:
                    Obtc = f * hrN / p0
                    res[str(k)][f][1] += 1
                    if cumk >= q0 + Obtc:
                        res[str(k)][f][0] += 1
            hit = np.where(ccum >= q0)[0]
            if hit.size:
                tf = wts[hit[0]]
                fj = int(np.searchsorted(bts, tf + MK_D * 1_000_000)) - 1
                bj = int(np.searchsorted(bts, tf)) - 1
                if 0 <= bj < fj < len(bts):
                    mv = (mid[fj] - mid[bj]) / mid[bj] * 1e4
                    mks.append(mv if dir_buy else -mv)
            if dir_buy:
                bwin = slice(bi, min(bi + 6000, len(bts)))
                same = bbp[bwin] == p0; ba_w = bba[bwin]; bts_w = bts[bwin]
                kx300 = int(np.searchsorted(wts, au + 300 * 1_000_000))
                trades300 = ccum[kx300 - 1] if kx300 > 0 else 0.0
                cidx = np.where(same & (ba_w < 0.2 * q0) & (bts_w <= au + 300 * 1_000_000))[0]
                if cidx.size:
                    cancel_clear[0] += 1 if trades300 < q0 else 0
                    cancel_clear[1] += 1
    fr = {str(k): {str(f): (res[str(k)][f][0] / res[str(k)][f][1] if res[str(k)][f][1] else np.nan)
                   for f in FGRID} for k in KS}
    grid = np.arange(bts[0], bts[-1], 60 * 1_000_000); gi = np.searchsorted(bts, grid) - 1; gi = gi[gi >= 0]
    gm = mid[gi]; rets = np.diff(np.log(gm[gm > 0])); rvol = float(np.std(rets) * 1e4)
    return dict(hourly_notl=hrN, spread_bps=float(np.median((bap - bbp) / mid * 1e4)), rvol_bps_min=rvol,
                fill_rate=fr, markout_mean=float(np.nanmean(mks)), markout_p25=float(np.nanpercentile(mks, 25)),
                markout_median=float(np.nanmedian(mks)), n_mk=len(mks),
                cancel_clear_frac=(cancel_clear[0] / cancel_clear[1] if cancel_clear[1] else np.nan))


def bar1s_day(day_int):
    dp = load_day_panel(day_int, ["bnfbtc"]); s = "bnfbtc"

    def c(n):
        return dp.data[s][:, dp.cols.index(n)].astype(np.float64)
    mid = c("mid"); bid = c("bid"); ask = c("ask"); bidszN = c("bidsz"); askszN = c("asksz")
    sellA = np.nan_to_num(c("tdQtySell")); buyA = np.nan_to_num(c("tdQtyBuy"))
    px = np.nan_to_num(c("tdQtyPxSell")) + np.nan_to_num(c("tdQtyPxBuy"))
    good = np.isfinite(mid) & (mid > 0); hrN = float(np.nanmean(px[good]) * 3600.0); T = len(mid)
    anchors = np.arange(3600, T - 1000, ANCHOR_STEP)
    csS = np.concatenate([[0.0], np.cumsum(sellA)]); csB = np.concatenate([[0.0], np.cumsum(buyA)])
    res = {str(k): {f: [0, 0] for f in FGRID} for k in KS}; mks = []
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
                    Obase = f * hrN / p0
                    res[str(k)][f][1] += 1
                    if cumk >= q0 + Obase:
                        res[str(k)][f][0] += 1
            win = cs[bi + 1: bi + 1 + 900] - cs[bi + 1]; hit = np.where(win >= q0)[0]
            if hit.size:
                fi = bi + 1 + int(hit[0])
                if fi + MK_D < T and good[fi]:
                    mv = (mid[fi + MK_D] - mid[fi]) / mid[fi] * 1e4
                    mks.append(mv if dir_buy else -mv)
    fr = {str(k): {str(f): (res[str(k)][f][0] / res[str(k)][f][1] if res[str(k)][f][1] else np.nan)
                   for f in FGRID} for k in KS}
    return dict(hourly_notl=hrN, spread_bps=float(np.nanmedian(((ask - bid) / mid * 1e4)[good])),
                fill_rate=fr, markout_mean=float(np.nanmean(mks)), markout_p25=float(np.nanpercentile(mks, 25)),
                n_mk=len(mks))


if __name__ == "__main__":
    out = {}
    for day in DAYS:
        t0 = time.time(); di = int(day.replace("-", ""))
        try:
            tick = tick_day(day)
        except Exception as e:
            print(f"{day} tick fail {e!r}", flush=True); tick = None
        try:
            bar = bar1s_day(di)
        except Exception as e:
            print(f"{day} bar fail {e!r}", flush=True); bar = None
        out[day] = dict(tick=tick, bar1s=bar)
        if tick and bar:
            print(f"{day} ({time.time()-t0:.0f}s) rvol {tick['rvol_bps_min']:.1f}bps/min | "
                  f"fill(1%,k300) T {tick['fill_rate']['300']['0.01']:.2f} B {bar['fill_rate']['300']['0.01']:.2f} | "
                  f"mk T {tick['markout_mean']:+.2f} (p25 {tick['markout_p25']:+.1f}) B {bar['markout_mean']:+.2f} | "
                  f"cxl-clear {tick['cancel_clear_frac']:.2f}", flush=True)
    json.dump(dict(days=DAYS, ks=KS, fgrid=FGRID, per_day=out), open(EDA + "tick_vs_1s_raw.json", "w"), indent=2, default=str)
    print("SAVED " + EDA + "tick_vs_1s_raw.json", flush=True)
