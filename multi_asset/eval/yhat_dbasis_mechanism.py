"""MECHANISM: why is empirical IC(yhat,spot)=0.0433 >> IC(yhat,perp)=0.0326 (ratio 1.33) when variance-dilution
predicts ~1.002? Hypothesis: yhat correlates with d_basis (=perp_ret - spot_ret over 600s), so the basis adjustment
partially OFFSETS the predicted move in perp -> perp IC drops more.
  perp_ret = spot_ret + d_basis.  IC(yhat,perp) = [cov(yhat,spot_ret)+cov(yhat,d_basis)] / (sig_yhat*sig_perp).
  If cov(yhat,d_basis) < 0 -> perp IC < spot IC (model's edge is eaten by basis). Measure corr(yhat,d_basis) + decompose.
Also: per-month ratio robustness; and DENSE vs per-day-CLEAN (the 1.33 was DENSE pred_q50_raw).
Run on SERVER: PYTHONPATH=. python multi_asset/eval/yhat_dbasis_mechanism.py
"""
from __future__ import annotations
import numpy as np, csv as _csv, gzip, os
from datetime import datetime, timezone
from scipy.stats import pearsonr
BOOK="/mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/dl-tardis/book_snapshot_25"; HZ=600*1_000_000
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
def grid(days,venue):
    TS=[];MID=[]
    for d in days:
        r=load_mid(d,venue)
        if r: TS.append(r[0]);MID.append(r[1])
    if not TS: return None
    TS=np.concatenate(TS);MID=np.concatenate(MID);o=np.argsort(TS);return TS[o],MID[o]
def at(g,TS,MID):
    idx=np.searchsorted(TS,g,side="right")-1; v=np.full(len(g),np.nan); m=idx>=0; v[m]=MID[idx[m]]; return v
def main():
    rows=list(_csv.DictReader(open("exports/final_l01/y600_l01_alwaysEMA_walkforward.csv")))
    ts=np.array([int(r["timestamp_us"]) for r in rows]); q=np.array([float(r["pred_q50_raw"]) for r in rows])
    mon=np.array([r["month"] for r in rows]); o=np.argsort(ts); ts,q,mon=ts[o],q[o],mon[o]
    days=sorted(set(datetime.fromtimestamp(t/1e6,tz=timezone.utc).strftime("%Y-%m-%d") for t in ts))
    sp=grid(days,"binance"); pp=grid(days,"binance-futures")
    sm0=at(ts,sp[0],sp[1]); smF=at(ts+HZ,sp[0],sp[1]); pm0=at(ts,pp[0],pp[1]); pmF=at(ts+HZ,pp[0],pp[1])
    spot_ret=np.log(smF/sm0); perp_ret=np.log(pmF/pm0); dbasis=perp_ret-spot_ret
    ok=~np.isnan(spot_ret)&~np.isnan(perp_ret)&~np.isnan(q)
    q,sr,pr,db,mn=q[ok],spot_ret[ok],perp_ret[ok],dbasis[ok],mon[ok]
    icS=pearsonr(q,sr)[0]; icP=pearsonr(q,pr)[0]; icB=pearsonr(q,db)[0]
    print(f"=== yhat vs spot/perp/d_basis (n={len(q)}) ===")
    print(f"  IC(yhat,SPOT)={icS:+.4f} IC(yhat,PERP)={icP:+.4f} ratio={icS/icP:.2f}")
    print(f"  IC(yhat,d_basis)={icB:+.4f}  (if NEGATIVE -> basis eats perp edge)")
    print(f"  sig_spot_ret={sr.std()*1e4:.2f}bps sig_perp={pr.std()*1e4:.2f} sig_dbasis={db.std()*1e4:.3f}bps")
    # decompose cov(yhat,perp)=cov(yhat,spot)+cov(yhat,dbasis)
    cYS=np.cov(q,sr)[0,1]; cYB=np.cov(q,db)[0,1]; cYP=np.cov(q,pr)[0,1]
    print(f"  cov(yhat,perp)={cYP:.3e} = cov(yhat,spot)={cYS:.3e} + cov(yhat,dbasis)={cYB:.3e}")
    print(f"  => basis offsets {(-cYB/cYS*100 if cYS!=0 else 0):+.1f}% of the spot covariance")
    print("  per-month ratio spot/perp:")
    for M in sorted(set(mn)):
        m=mn==M
        if m.sum()>50:
            s=pearsonr(q[m],sr[m])[0]; p=pearsonr(q[m],pr[m])[0]
            print(f"    {M}: IC_spot={s:+.4f} IC_perp={p:+.4f} ratio={s/p if p!=0 else float('nan'):.2f} corr(yhat,dbasis)={pearsonr(q[m],db[m])[0]:+.3f}")
    print("DONE_MECH.")
if __name__=="__main__": main()
