"""TRADEABILITY check of the 0.169 (pt_vwap_return_1s.last reversion) -- bounce artifact or real?

Coordinator hypothesis: pt_vwap_return_1s is TRADE-VWAP (bounces bid<->ask); y_600 is BOOK-MID. A vwap up-tick
(trade at ask) -> next mid mechanically lower -> -corr you can't capture without crossing the spread. Tests:

A. MID vs TRADE 1s return reversion (2025-10, CLEAN univariate Pearson with y_600):
   - pt_vwap_return_1s.last (trade-VWAP)  [the suspect]
   - mid 1s return from x_mid_ratio_log sequence diff (book-mid based, relative perp-spot)
   - any spot-64 mid-return channel we can identify
   If trade-VWAP reverts strongly but mid-return does NOT -> BID-ASK BOUNCE (non-tradeable).
   If mid-return ALSO reverts -> real reversion.

B. NET-OF-COST: the reversion strategy = short when vwap_return_1s.last>0. Edge per window in bps =
   |corr| * sigma(y_600) (the IC * target vol = the realizable per-unit-signal return). Compare to cost tiers
   (BTC perp ~1-3 bps/side round-trip 2-6 bps). Also report sigma(y_600) in bps and the implied gross edge of
   the TOP-decile reversion signal (mean |y_600| when |vwap_ret| is extreme) vs cost.

C. SPREAD context: x_spread_ratio_log magnitude (proxy) -- is the reversion smaller than the spread?
Run on SERVER: PYTHONPATH=. python multi_asset/data/tradeability_169.py
"""
from __future__ import annotations
import numpy as np, glob, os, warnings
warnings.filterwarnings("ignore"); warnings.simplefilter("ignore")
from scipy.stats import pearsonr

CACHE="data/npz_v2arch"
VWAP_RET_CH=64+7   # pt_vwap_return_1s
MIDRATIO_CH=80     # x_mid_ratio_log (log perp_mid/spot_mid)
def dd(p): return os.path.basename(p)[:-4]

def load_2510():
    fs=sorted(glob.glob(f"{CACHE}/*.npz")); days=[f for f in fs if dd(f)[:7]=="2025-10"]
    vw=[]; midret=[]; y=[]; ts=[]; ysig_raw=[]
    for f in days:
        d=np.load(f,allow_pickle=True); m=d["y_mask_600"].astype(bool)
        if m.sum()==0: continue
        X=d["X"][m]
        vw.append(X[:,-1,VWAP_RET_CH].astype(np.float32))          # trade-vwap 1s ret (last step)
        midret.append((X[:,-1,MIDRATIO_CH]-X[:,-2,MIDRATIO_CH]).astype(np.float32))  # 1s mid-ratio diff (book-based)
        y.append(d["y_600"][m].astype(np.float32))
        ts.append(d["timestamps"][m].astype(np.int64))
    return (np.nan_to_num(np.concatenate(vw)), np.nan_to_num(np.concatenate(midret)),
            np.concatenate(y), np.concatenate(ts))

def clean_idx(ts, off=0):
    o=np.argsort(ts); keep=[]; last=-1e18
    for i in range(off,len(o)):
        if ts[o[i]]-last>=600*1_000_000: keep.append(o[i]); last=ts[o[i]]
    return np.array(keep)

vw, midret, y, ts = load_2510()
k=clean_idx(ts,0)
print(f"=== TRADEABILITY of 2025-10 0.169 ===  N_clean={len(k)}")

# A. mid vs trade reversion
def cp(a,b): r=pearsonr(a,b)[0]; return r if np.isfinite(r) else np.nan
print("\n[A] 1s-return reversion vs y_600 (CLEAN univariate Pearson):")
print(f"  pt_vwap_return_1s.last (TRADE-vwap)  : {cp(vw[k],y[k]):+.4f}   <- the 0.169 driver")
print(f"  x_mid_ratio_log 1s-diff (BOOK-mid)   : {cp(midret[k],y[k]):+.4f}   <- if ~0 => bid-ask bounce")
# correlation between the two 1s returns (do they even measure the same move?)
print(f"  corr(trade-vwap-ret, mid-ratio-diff) : {cp(vw[k],midret[k]):+.4f}")

# B. net-of-cost
ysig_bps = y.std()*1e4   # y_600 is a return; sigma in bps
print(f"\n[B] NET-OF-COST:")
print(f"  sigma(y_600) = {ysig_bps:.2f} bps")
ic=abs(cp(vw[k],y[k]))
print(f"  IC*sigma (per-unit-signal realizable return) = {ic*ysig_bps:.3f} bps")
# decile edge: mean y_600 in the extreme-|vwap| decile (the actual tradeable edge of fading it)
vk=vw[k]; yk=y[k]; thr=np.quantile(np.abs(vk),0.9)
ext=np.abs(vk)>=thr
# fade: position = -sign(vwap); realized = position*y
fade_ret = (-np.sign(vk[ext])*yk[ext]).mean()*1e4
print(f"  TOP-decile |vwap_ret| fade edge = {fade_ret:+.3f} bps/window (gross, before cost)")
print(f"  cost floor: BTC perp ~1.0 bps/side -> ~2.0 bps round-trip (taker). maker ~0.")
print(f"  => net (taker) = {fade_ret-2.0:+.3f} bps ; net (maker~0.4 rt) = {fade_ret-0.4:+.3f} bps")

# C. spread context
spr=np.load(sorted(glob.glob(f'{CACHE}/2025-10*.npz'))[0],allow_pickle=True)
print(f"\n[C] VERDICT:")
mid_rev=abs(cp(midret[k],y[k])); trade_rev=abs(cp(vw[k],y[k]))
if mid_rev < 0.3*trade_rev:
    print(f"  MID reversion ({mid_rev:.3f}) << TRADE reversion ({trade_rev:.3f}) -> BID-ASK BOUNCE artifact (NON-tradeable)")
else:
    print(f"  MID reversion ({mid_rev:.3f}) survives vs TRADE ({trade_rev:.3f}) -> real reversion")
print(f"  net-of-cost top-decile fade: taker {fade_ret-2.0:+.2f} bps -> {'TRADEABLE' if fade_ret-2.0>0 else 'NON-tradeable (inside cost)'}")
print("DONE_TRADE.")
