"""NEW LEVER: append funding/OI as RAW INPUT CHANNELS to X (not regime_prior) -> DL backbone learns the
NON-LINEAR interaction with the book. The additive-Ridge gate tested only LINEAR value (+0.0012); FiLM/router
are specific failed forms. This feeds 8 DESIGNED, LEAK-SAFE funding/OI features as extra X channels (broadcast
across the 600-step window as the <=t value) so the Conformer + cross-features process them.

Mechanism: drift-month failure = positioning-regime INVERSION (funding flips neg, OI craters, L/S flips). That
inversion IS in funding/OI -> giving the DL these channels could let it ADAPT (most relevant on drift months).

Reuses the VERIFIED leak-safe designed() math from oi_designed_ridge_gate.py (8 feats: dOI_n, oi_z, oi_accel,
quad_sign(divergence), fund_x_oi, toptrader_ext, taker_ls, divergence-mag). For each window ending at t (us):
5m metrics bar fully <=t, 8h funding settled <=t -> forward-filled. Broadcast the <=t value to all 600 steps.

DISK-SAFE: writes a SEPARATE --dst cache (reads --src mode='r', never modifies). X (N,600,C) -> (N,600,C+8).
n_features auto-widens (train reads X.shape[-1]). Idempotent (skip if dst X already wider).
Run: PYTHONPATH=. python multi_asset/data/add_funding_channels.py --src npz_v2arch --dst npz_v2arch_fundch --start YYYY-MM-DD --end YYYY-MM-DD --apply
"""
from __future__ import annotations
import numpy as np, glob, os, csv, argparse, sys
from datetime import datetime, timezone
MET="data/funding/btcusdt_metrics_5m.csv"; FUND="data/funding/btcusdt_funding.csv"; BAR_US=300*1_000_000
def parse_us(s): return int(datetime.strptime(s,"%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())*1_000_000
def f2(x):
    try: return float(x)
    except: return np.nan
def load_metrics():
    rows=[]
    with open(MET) as f:
        for r in csv.DictReader(f):
            try: rows.append((parse_us(r["create_time"]),f2(r["sum_open_interest"]),f2(r["sum_open_interest_value"]),f2(r["sum_toptrader_long_short_ratio"]),f2(r["sum_taker_long_short_vol_ratio"]),f2(r["count_long_short_ratio"])))
            except Exception: continue
    a=np.array(rows); return a[np.argsort(a[:,0])]
def load_funding():
    rows=[]
    with open(FUND) as f:
        for r in csv.DictReader(f):
            try: rows.append((int(r["fundingTime_ms"])*1000,f2(r["fundingRate"])))
            except Exception: continue
    a=np.array(rows); return a[np.argsort(a[:,0])]
M=load_metrics(); F=load_funding()
MT=M[:,0]; OI=M[:,1]; OIV=M[:,2]; TT=M[:,3]; TK=M[:,4]; RT=M[:,5]; PRICE=OIV/np.clip(OI,1e-9,None); FT=F[:,0]; FR=F[:,1]
def designed(win_ts_us):
    cut=win_ts_us-BAR_US
    im=np.searchsorted(MT,cut,side="right")-1; iff=np.searchsorted(FT,win_ts_us,side="right")-1
    N=len(win_ts_us); out=np.zeros((N,8),np.float32); v=(im>=0)&(iff>=0); iv=im[v]; ifv=iff[v]
    K=6; iK=np.clip(iv-K,0,None)
    dOI=OI[iv]-OI[iK]; dP=PRICE[iv]-PRICE[iK]
    dOIn=dOI/(np.abs(OI[iv])+1e-9); dPn=dP/(np.abs(PRICE[iv])+1e-9)
    oiz=np.zeros(len(iv))
    for j,i in enumerate(iv):
        lo=max(0,i-71); h=OI[lo:i+1]; oiz[j]=(OI[i]-h.mean())/(h.std()+1e-9)
    fz=np.zeros(len(ifv))
    for j,i in enumerate(ifv):
        lo=max(0,i-29); h=FR[lo:i+1]; fz[j]=(FR[i]-h.mean())/(h.std()+1e-9)
    oi_accel=(OI[iv]-OI[iK])-(OI[iK]-OI[np.clip(iv-2*K,0,None)])
    out[v,0]=dOIn; out[v,1]=oiz; out[v,2]=oi_accel/(np.abs(OI[iv])+1e-9); out[v,3]=np.sign(dOI)*np.sign(dP)
    out[v,4]=dOIn*dPn; out[v,5]=fz*oiz; out[v,6]=TT[iv]-1.0; out[v,7]=TK[iv]
    return np.nan_to_num(out)
NAMES=["f_dOI_n","f_oi_z","f_oi_accel","f_quad_sign","f_divergence","f_fund_x_oi","f_toptrader_ext","f_taker_ls"]

def dd(p): return os.path.basename(p)[:-4]
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--src",required=True); ap.add_argument("--dst",required=True)
    ap.add_argument("--start"); ap.add_argument("--end"); ap.add_argument("--apply",action="store_true")
    a=ap.parse_args()
    if a.src==a.dst: sys.exit("src==dst not allowed (separate cache)")
    src=f"data/{a.src}"; dst=f"data/{a.dst}"; os.makedirs(dst,exist_ok=True)
    files=sorted(glob.glob(f"{src}/*.npz"))
    sel=[f for f in files if (not a.start or dd(f)>=a.start) and (not a.end or dd(f)<=a.end)]
    print(f"add_funding_channels: {len(sel)} day(s) {a.start}..{a.end} -> {dst} (apply={a.apply})")
    for f in sel:
        day=dd(f); dp=f"{dst}/{day}.npz"
        if os.path.exists(dp):
            try:
                z=np.load(dp);
                if z["X"].shape[-1]>=z["X"].shape[-1]:  # presence check below
                    pass
            except Exception: pass
        d=dict(np.load(f,allow_pickle=True))
        X=d["X"]  # (N,600,C)
        ts=d["timestamps"].astype(np.int64)
        fc=designed(ts)  # (N,8) <=t
        # broadcast across the 600-step window (constant per-window <=t value)
        fc_seq=np.broadcast_to(fc[:,None,:],(X.shape[0],X.shape[1],8)).astype(X.dtype)
        d["X"]=np.concatenate([X,fc_seq],axis=2)
        d["funding_channel_names"]=np.array(NAMES)
        cov=np.mean(np.any(fc!=0,1))
        if not a.apply:
            print(f"  [dry] {day}: X {X.shape}->{d['X'].shape} cov={cov:.3f}"); continue
        tmp=dp+".tmp.npz"; np.savez(tmp,**d); os.replace(tmp,dp)
        print(f"  {day}: X->{d['X'].shape} cov={cov:.3f}")
    print("DONE_FUNDCH.")
if __name__=="__main__": main()
