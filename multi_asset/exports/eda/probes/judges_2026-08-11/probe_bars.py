import time, numpy as np
from multi_asset.data.bar_loader import load_day_panel
SYM = ["bnfbtc", "bnfeth", "bnfsol", "bnfbnb", "bnfxrp", "bnfdog", "bnfada",
       "bnflink", "bnfbch", "bnftrx", "bnfltc", "bnfdot", "bnffil", "bnfetc"]
day = 20250310
t0 = time.time()
dp = load_day_panel(day, SYM)
print(f"load {day} 14sym: {time.time()-t0:.1f}s | T={len(dp.ts)} ncols={len(dp.cols)}")
have = [c for c in ["mid","bid","ask","bidsz","asksz","tdQtyBuy","tdQtySell","tdQtyPxBuy","tdQtyPxSell","bkDelBid"] if c in dp.cols]
print("cols present:", have)


def c(s, n):
    return dp.data[s][:, dp.cols.index(n)].astype(np.float64)


print(f"\n{'sym':>6} {'hrNotl_$M':>10} {'spr_bps':>8} {'L1notl_$':>10} {'oppNotl/s_$':>11}")
for s in SYM:
    mid = c(s, "mid"); bid = c(s, "bid"); ask = c(s, "ask")
    good = np.isfinite(mid) & (mid > 0)
    spr = np.nanmedian(((ask - bid) / mid * 1e4)[good])
    # notional per second = tdQtyPx (already qty*px in quote units? check magnitude)
    buyN = c(s, "tdQtyPxBuy"); sellN = c(s, "tdQtyPxSell")
    hr_notl = np.nanmean(buyN + sellN) * 3600.0    # per-sec notional * 3600
    l1_notl = np.nanmedian((c(s, "bidsz") * mid)[good])
    opp_s = np.nanmedian((sellN)[sellN > 0]) if (sellN > 0).any() else np.nan
    print(f"{s[3:]:>6} {hr_notl/1e6:>10.2f} {spr:>8.3f} {l1_notl:>10.0f} {opp_s:>11.0f}")
