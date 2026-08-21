import numpy as np, datetime as dt, sys, json
from scipy.stats import rankdata

VAR = sys.argv[1] if len(sys.argv)>1 else "primary"
# variants: primary | dropmisspanel | dropnanleg | nanwin_strict

meta=np.load("/workspace/data/wide_fea_v1_meta.npz",allow_pickle=True)
E=meta["E_ts"].astype(np.int64); mem=meta["members"]; Y4M=meta["y4"].astype(np.float64); QVK=meta["qvk"].astype(np.float64)
pan=np.load("/workspace/data/wide_panel_4h_v1.npz",allow_pickle=True)
PTS=pan["ts"].astype(np.int64); REV=pan["f_rev_24h"].astype(np.float64); FEMA=pan["f_fund_ema"].astype(np.float64); FNOW=pan["f_fund_now"].astype(np.float64)
PRED=np.load("/workspace/exports_train/slow_lgbm_pred.npy").astype(np.float64)
nA=len(E); nS=829
pmap={int(t):i for i,t in enumerate(PTS)}
prow=np.array([pmap.get(int(t),-1) for t in E])

# ---------- delayed 4h return from 5m cache ----------
import os
CACHE="/workspace/cleanroom/y4_delayed_%s.npy"%("49" if VAR=="bars49" else "48")
if os.path.exists(CACHE):
    Y4D=np.load(CACHE)
else:
    z5=np.load("/workspace/data/dlnative_5m_wide829_f16.npz",allow_pickle=True)
    dts=z5["ts"].astype(np.int64)
    X=z5["data"][:,:,0]; del z5
    Xf=X.astype(np.float32); del X
    e_idx=np.searchsorted(dts,E); assert np.all(dts[e_idx]==E), "anchor not on 5m grid"
    Y4D=np.full((nA,nS),np.nan,np.float64)
    for i,e in enumerate(e_idx):
        blk=Xf[e+1:e+50] if VAR=="bars49" else Xf[e+1:e+49]
        ok=np.isfinite(blk); cnt=ok.sum(0)
        s=np.where(ok,blk,0.0).astype(np.float64).sum(0)
        Y4D[i]=np.where(cnt>=46,s,np.nan)
    del Xf
    np.save(CACHE,Y4D)

# ---------- leg rank standardisation ----------
def rankz(v):
    out=np.full(v.shape,np.nan)
    ok=np.isfinite(v); n=int(ok.sum())
    if n>=2:
        r=rankdata(v[ok],method='average')-(0.0 if VAR=="rank1based" else 1.0)
        out[ok]=r/(n-1)-0.5
    elif n==1:
        out[ok]=0.0
    return out

MEM=[np.asarray(m,dtype=np.int64) for m in mem]
ZL=[np.full((nA,nS),np.nan) for _ in range(3)]
for i in range(nA):
    mm=MEM[i]; j=prow[i]
    raw=[PRED[i,mm],
         -REV[j,mm] if j>=0 else np.full(len(mm),np.nan),
         FEMA[j,mm] if j>=0 else np.full(len(mm),np.nan)]
    for L in range(3):
        ZL[L][i,mm]=rankz(raw[L])

# ---------- single-leg book returns (walk-forward input) ----------
R=np.full((nA,3),np.nan)
for i in range(nA):
    mm=MEM[i]; yy=Y4M[i,mm]
    for L in range(3):
        z=ZL[L][i,mm]; s=np.nansum(np.abs(z))
        if s>0:
            w=np.where(np.isfinite(z),z,0.0)/s
            R[i,L]=np.nansum(w*np.where(np.isfinite(yy),yy,0.0))*1e4

# ---------- main replay ----------
TIER=[(5e6,0.85*(-0.25)+0.15*5.0),(1e6,0.75*0.5+0.25*6.0),(-1.0,0.55*2.0+0.45*8.0)]
H=np.zeros(nS)
net=np.full(nA,np.nan); wlog=np.full((nA,3),np.nan); skipped=[]
DEC=np.full((nA,4),np.nan)
for i in range(nA):
    mm=MEM[i]; j=prow[i]
    # walk-forward leg weights
    if i<900:
        w=np.array([1/3,1/3,1/3])
    else:
        win=R[i-900:i]; sh=np.zeros(3)
        for L in range(3):
            c=win[:,L]; c=c[np.isfinite(c)]
            if VAR=="nanwin_strict":
                c2=win[:,L]
                sh[L]=(c2.mean()/c2.std()) if np.all(np.isfinite(c2)) and c2.std()>0 else 0.0
            else:
                sh[L]=(c.mean()/c.std()) if (len(c)>=2 and c.std()>0) else 0.0
        sh=np.maximum(sh,0.0)
        w=sh/sh.sum() if sh.sum()>0 else np.array([1/3,1/3,1/3])
    wlog[i]=w
    if VAR=="dropmisspanel" and j<0:
        skipped.append(i); continue
    # composite
    zc=np.zeros(len(mm)); anyfin=np.zeros(len(mm),bool)
    for L in range(3):
        z=ZL[L][i,mm]; f=np.isfinite(z)
        zc+=w[L]*np.where(f,z,0.0); anyfin|=f
    vol=np.expm1(QVK[i,mm])*48.0
    keep=np.isfinite(Y4M[i,mm])&(vol>=250000.0)
    if VAR=="dropnanleg":
        keep&= np.isfinite(ZL[0][i,mm])&np.isfinite(ZL[1][i,mm])&np.isfinite(ZL[2][i,mm])
    else:
        keep&=anyfin
    n_eff=int(keep.sum())
    if n_eff<80: skipped.append(i); continue
    cols=mm[keep]; zz=zc[keep]
    zz=zz-zz.mean()
    s=np.abs(zz).sum()
    if s<=0: skipped.append(i); continue
    ww=zz/s
    cap=2.5/n_eff
    ww=np.clip(ww,-cap,cap)
    s2=np.abs(ww).sum()
    if s2<=0: skipped.append(i); continue
    ww=ww/s2
    tgt=np.zeros(nS); tgt[cols]=ww
    sm=H+0.1*(tgt-H)
    d=sm-H
    sm=np.where(np.abs((tgt-H) if VAR=="deadband_tgt" else d)<2.5e-4,H,sm)
    trade=sm-H
    volA=np.expm1(QVK[i])*48.0
    rate=np.where(volA>=5e6,TIER[0][1],np.where(volA>=1e6,TIER[1][1],TIER[2][1]))
    cost=float(np.sum(np.abs(trade)*rate))
    yd=Y4D[i]; gross=float(np.nansum(sm*np.where(np.isfinite(yd),yd,0.0))*1e4)
    fnd=0.0 if j<0 else float(np.nansum(sm*np.where(np.isfinite(FNOW[j]),FNOW[j],0.0)/2.0)*1e4)
    net[i]=gross-fnd-cost
    DEC[i]=[gross,fnd,cost,float(np.abs(trade).sum())]
    H=sm

yrs=np.array([dt.datetime.fromtimestamp(int(t),dt.UTC).year for t in E])
sel=(yrs>=2024)&np.isfinite(net)
v=net[sel]; ANN=np.sqrt(6*365)
def sh(x): return float(x.mean()/x.std()*ANN) if len(x)>1 and x.std()>0 else float('nan')
out=dict(variant=VAR,n=int(sel.sum()),sharpe=round(sh(v),4),mean_bps=round(float(v.mean()),4),
         std=round(float(v.std()),4),
         by_year={int(Y):[int((sel&(yrs==Y)).sum()),round(sh(net[sel&(yrs==Y)]),4),round(float(net[sel&(yrs==Y)].mean()),4)] for Y in (2024,2025,2026)},
         first5=[round(float(x),3) for x in v[:5]], last5=[round(float(x),3) for x in v[-5:]],
         first5_ts=[dt.datetime.fromtimestamp(int(t),dt.UTC).isoformat() for t in E[sel][:5]],
         last5_ts=[dt.datetime.fromtimestamp(int(t),dt.UTC).isoformat() for t in E[sel][-5:]],
         skipped_ge2024=int(sum(1 for i in skipped if yrs[i]>=2024)),
         w_mean_2024plus=[round(float(x),4) for x in np.nanmean(wlog[yrs>=2024],axis=0)],
         decomp_gross_fund_cost_turn=[round(float(x),4) for x in np.nanmean(DEC[sel],axis=0)],
         sharpe_se=round(float(np.sqrt((1+0.5*(v.mean()/v.std())**2)/len(v))*ANN),4))
print(json.dumps(out,indent=1))
open("/workspace/cleanroom/res_%s.json"%VAR,"w").write(json.dumps(out))
