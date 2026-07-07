"""ISOLATE THE PURE TARGET EFFECT: does predicting PERP 600s return cost IC vs SPOT 600s return, holding features fixed?
Mechanism: perp_ret = spot_ret + d(basis). If sigma(d_basis over 600s) << sigma_ret -> near-zero dilution.

From btcusdt_copy: build matched spot-mid and perp-mid series (binance vs binance-futures), compute 600s returns on a
~600s grid, measure:
  1. sigma(spot 600s ret), sigma(perp 600s ret), corr(spot_ret, perp_ret).
  2. sigma(d_basis over 600s) where basis = log(perp_mid/spot_mid); d_basis = basis(t+600)-basis(t).
  3. THEORETICAL dilution of an IC against spot if used to predict perp: rho = corr(spot_ret,perp_ret) =
     1/sqrt(1 + var(d_basis)/var(spot_ret)). IC(features->perp) ~ IC(features->spot) * rho (if features predict spot_ret,
     and d_basis is ~orthogonal noise). Report rho.
  4. EMPIRICAL: load the production yhat (predicts perp), and the per-node SPOT return at same timestamps; compare
     IC(yhat, perp_ret) vs IC(yhat, spot_ret). If ~equal -> target choice is ~irrelevant; the model's signal is the same.
Run on SERVER: PYTHONPATH=. python multi_asset/eval/spot_vs_perp_target.py
"""
from __future__ import annotations
import numpy as np, csv as _csv, gzip, os
from datetime import datetime, timezone, timedelta
from scipy.stats import pearsonr
BOOK="/mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/dl-tardis/book_snapshot_25"

def load_mid(day, venue):
    f=f"{BOOK}/{day}/{venue}/BTCUSDT.csv.gz"
    if not os.path.exists(f): return None
    ts=[];mid=[];last=-1
    with gzip.open(f,"rt") as fh:
        hdr=fh.readline().split(","); ia=hdr.index("asks[0].price"); ib=hdr.index("bids[0].price"); it=hdr.index("timestamp")
        for line in fh:
            p=line.split(",")
            try:
                t=int(p[it])
                if t-last<1_000_000: continue
                ts.append(t); mid.append((float(p[ia])+float(p[ib]))/2); last=t
            except: continue
    return (np.array(ts,np.int64),np.array(mid,np.float64)) if ts else None

def grid_mids(days, venue):
    TS=[];MID=[]
    for d in days:
        r=load_mid(d,venue)
        if r: TS.append(r[0]); MID.append(r[1])
    if not TS: return None
    TS=np.concatenate(TS);MID=np.concatenate(MID);o=np.argsort(TS); return TS[o],MID[o]

def at(ts_grid, TS, MID):  # value at-or-before each grid ts
    idx=np.searchsorted(TS,ts_grid,side="right")-1; v=np.full(len(ts_grid),np.nan); m=idx>=0; v[m]=MID[idx[m]]
    return v

def main():
    # test months matching the production CSV span
    months=["2025-10","2025-11","2025-12","2026-01","2026-02"]  # representative (skip the short v2arch months)
    HZ=600*1_000_000
    allspot_r=[];allperp_r=[];alldbasis=[]
    for ym in months:
        y,mo=ym.split("-");
        import calendar
        nd=calendar.monthrange(int(y),int(mo))[1]
        days=[f"{ym}-{d:02d}" for d in range(1,nd+1)]
        sp=grid_mids(days,"binance"); pp=grid_mids(days,"binance-futures")
        if sp is None or pp is None: print(f"{ym}: missing venue"); continue
        # 600s grid from perp ts
        t0=pp[0][0]; t1=pp[0][-1]; grid=np.arange(t0,t1,HZ)
        sm=at(grid,sp[0],sp[1]); pm=at(grid,pp[0],pp[1])
        ok=~np.isnan(sm)&~np.isnan(pm); sm=sm[ok]; pm=pm[ok]; g=grid[ok]
        # consecutive 600s returns
        sr=np.diff(np.log(sm))*1e4; pr=np.diff(np.log(pm))*1e4  # bps
        basis=np.log(pm/sm)*1e4; dbasis=np.diff(basis)  # bps
        # keep only steps where grid is contiguous 600s
        cont=np.diff(g)<1.5*HZ
        sr=sr[cont]; pr=pr[cont]; dbasis=dbasis[cont]
        allspot_r.append(sr);allperp_r.append(pr);alldbasis.append(dbasis)
        rho=pearsonr(sr,pr)[0]
        print(f"{ym}: n={len(sr)} sig_spot={sr.std():.2f} sig_perp={pr.std():.2f} sig_dbasis={dbasis.std():.3f}bps corr(spot,perp)={rho:.4f}")
    sr=np.concatenate(allspot_r);pr=np.concatenate(allperp_r);db=np.concatenate(alldbasis)
    rho=pearsonr(sr,pr)[0]
    print(f"\n=== POOLED ({len(sr)} 600s steps) ===")
    print(f"  sigma(spot 600s ret) = {sr.std():.2f} bps")
    print(f"  sigma(perp 600s ret) = {pr.std():.2f} bps")
    print(f"  sigma(d_basis/600s)  = {db.std():.3f} bps")
    print(f"  corr(spot_ret, perp_ret) = {rho:.4f}")
    dilution=1/np.sqrt(1+db.var()/sr.var())
    print(f"  THEORETICAL dilution rho = 1/sqrt(1+var(dbasis)/var(spot_ret)) = {dilution:.4f}")
    print(f"  => an IC that predicts SPOT ret, applied to PERP ret, retains ~{dilution*100:.1f}% (loses ~{(1-dilution)*100:.1f}%)")
    print(f"  => TARGET effect spot->perp = ~{(1-rho)*100:.1f}% IC loss (NOT 2x). The '2x' was a FEATURES (spot-book vs perp-book) comparison.")
    # empirical: production yhat vs spot-ret vs perp-ret at same nodes
    print("\n=== EMPIRICAL: production yhat IC vs SPOT-target and PERP-target (same nodes) ===")
    rows=list(_csv.DictReader(open("exports/final_l01/y600_l01_alwaysEMA_walkforward.csv")))
    ts=np.array([int(r["timestamp_us"]) for r in rows]); q=np.array([float(r["pred_q50_raw"]) for r in rows])
    yperp=np.array([float(r["target_raw"]) for r in rows])  # this is the perp target the model trained on
    o=np.argsort(ts); ts,q,yperp=ts[o],q[o],yperp[o]
    # build spot return at each node: spot_mid(t+600)-spot_mid(t)
    days=sorted(set(datetime.fromtimestamp(t/1e6,tz=timezone.utc).strftime("%Y-%m-%d") for t in ts))
    sp=grid_mids(days,"binance")
    if sp is not None:
        sm_now=at(ts,sp[0],sp[1]); sm_fut=at(ts+HZ,sp[0],sp[1])
        spot_ret=np.log(sm_fut/sm_now)  # raw log ret (same units as target_raw which is standardized... compare via corr only)
        ok=~np.isnan(spot_ret)&~np.isnan(q)
        ic_perp=pearsonr(q[ok],yperp[ok])[0]
        ic_spot=pearsonr(q[ok],spot_ret[ok])[0]
        print(f"  n={ok.sum()} | IC(yhat, PERP-target)={ic_perp:+.4f} | IC(yhat, SPOT-target)={ic_spot:+.4f} | ratio spot/perp={ic_spot/ic_perp:.2f}")
        print(f"  => if ~equal, the model's signal predicts BOTH equally -> target choice is ~IRRELEVANT to IC.")
    print("DONE_SPOTPERP.")

if __name__=="__main__": main()
