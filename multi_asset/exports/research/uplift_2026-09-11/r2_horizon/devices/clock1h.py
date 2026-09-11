"""SIGNAL LAYER paper book (NOT the device, NOT the book layer). Purpose: price a 1h-clock sleeve,
and reconcile the signal-layer IC of REV1H with its zero book-layer gross P&L.
Calibration arm: the same instrument at the 4h clock for FUND and AMI3D must line up with the
device pnl_ex/gross_total, or the instrument is not trusted."""
import numpy as np, sys
from scipy.stats import rankdata
R="/workspace/uplift_2026-09-11/r2_horizon"; HC="/workspace/review_scratch/health_check"
PB=HC+"/dev_v4/pod_backup_2026-08-21"
PW=np.load(PB+"/wide_panel_4h_hist_v2.npz",allow_pickle=True)
TS=PW["ts"].astype(np.int64); FE1=np.asarray(PW["f_fund_ema_v1"],np.float64); BASE=np.isfinite(FE1)
UZ=np.load(HC+"/masks/umask_UPIT_CRYPTO.npz",allow_pickle=True)
umap={int(t):k for k,t in enumerate(UZ["ts"].astype(np.int64))}; UM=np.asarray(UZ["mask"])
UROW=np.zeros((len(TS),829),bool)
for j,t in enumerate(TS):
    k=umap.get(int(t))
    if k is not None: UROW[j]=UM[k]
z=np.load("/workspace/data/dlnative_5m_wide829_f16_holefix2.npz",allow_pickle=True)
ts5=z["ts"].astype(np.int64); ch=[str(c) for c in z["ch"]]
pos={int(t):k for k,t in enumerate(ts5)}; K4=np.array([pos[int(t)] for t in TS])
D=z["data"][:,:,ch.index("ret5")].astype(np.float32); N5=len(D)
def cums(X,ab=False):
    Xf=np.where(np.isfinite(X),X,0.0).astype(np.float64)
    if ab: Xf=np.abs(Xf)
    return (np.vstack([np.zeros((1,829)),np.cumsum(Xf,0)]),
            np.vstack([np.zeros((1,829)),np.cumsum(np.isfinite(X).astype(np.float64),0)]))
CS,CN=cums(D); CA,_=cums(D,ab=True)
del z
def WIN(Cc,Cn,a,b,mean=False,frac=0.7):
    lo=np.clip(a,0,N5); hi=np.clip(b,0,N5); n=Cn[hi]-Cn[lo]; s=Cc[hi]-Cc[lo]
    need=frac*(hi-lo)[:,None]
    v=s/np.maximum(n,1) if mean else s
    return np.where(n>=need,v,np.nan)
def czr(M,msk):
    o=np.full(M.shape,np.nan)
    for i in range(M.shape[0]):
        v=np.where(msk[i],M[i],np.nan); ok=np.isfinite(v)
        if ok.sum()>=10: o[i,ok]=rankdata(v[ok])/(ok.sum()-1)-0.5
    return o
def orth_to(Z,Zf):
    Rr=np.full(Z.shape,np.nan)
    for i in range(Z.shape[0]):
        ok=np.isfinite(Z[i])&np.isfinite(Zf[i])
        if ok.sum()<10: continue
        x=Zf[i][ok];y=Z[i][ok];vx=float((x*x).sum());b=float((x*y).sum()/vx) if vx>1e-12 else 0.0
        r=y-b*x; Rr[i][ok]=r-r.mean()
    return Rr
def gross1(Zs):
    Wt=np.where(np.isfinite(Zs),Zs,0.0)
    g=np.abs(Wt).sum(1,keepdims=True)
    return np.where(g>1e-12,Wt/np.maximum(g,1e-12),0.0)
MSK4=BASE&UROW
FZ4=czr(FE1,MSK4)
FF=np.load(R+"/feats_r2.npz")
AMI3D=np.asarray(FF["RET_MABS_864"],np.float64)/np.exp(np.asarray(FF["LQV_MEAN_864"],np.float64))
REV1H4=-WIN(CS,CN,K4-12,K4)
print("=== SIGNAL-LAYER paper book, 4h clock (bps per anchor per unit gross) ===",flush=True)
print("%-7s %8s %8s %8s %8s %9s %9s"%("sig","0-1h","1-2h","2-3h","3-4h","0-4h","turn"))
out={}
for nm,X,do in [("FUND",FE1,False),("AMI3D",AMI3D,True),("REV1H",REV1H4,True)]:
    Z=czr(X,MSK4)
    if do: Z=orth_to(Z,FZ4)
    Wt=gross1(Z); row=[]
    for a,b in [(0,12),(12,24),(24,36),(36,48)]:
        r=np.nan_to_num(WIN(CS,CN,K4+a,K4+b),nan=0.0); row.append(float((Wt*r).sum(1).mean()*1e4))
    tot=float((Wt*np.nan_to_num(WIN(CS,CN,K4,K4+48),nan=0.0)).sum(1).mean()*1e4)
    to=float(np.abs(np.diff(Wt,axis=0)).sum(1).mean())
    out[nm]=dict(segs=row,tot=tot,turn=to)
    print("%-7s %+8.3f %+8.3f %+8.3f %+8.3f %+9.3f %9.4f"%(nm,row[0],row[1],row[2],row[3],tot,to),flush=True)
# ---------- 1h clock ----------
H=np.arange(K4[0],K4[-1]+1,12)                      # hourly grid on the 5m axis
j4=np.searchsorted(K4,H,side="right")-1             # last 4h panel row at or before each hour (causal)
MSKH=MSK4[j4]; FZH=FZ4[j4]
REV1HH=-WIN(CS,CN,H-12,H)
AMIH=WIN(CA,CN,H-864,H,mean=True)                   # |ret| part only; qv part is slow, reuse 4h row
print("=== SIGNAL-LAYER paper book, 1h clock, n=%d hourly anchors ==="%len(H),flush=True)
print("%-7s %10s %10s %10s %10s"%("sig","gross/1h","turn/1h","net@2.2bp","net@3.52bp"))
res1h={}
for nm,X in [("REV1H",REV1HH),("FUND",FE1[j4]),("AMI3D_r",AMIH)]:
    Z=czr(X,MSKH)
    if nm!="FUND": Z=orth_to(Z,FZH)
    Wt=gross1(Z)
    r=np.nan_to_num(WIN(CS,CN,H,H+12),nan=0.0)
    gr=float((Wt*r).sum(1).mean()*1e4)
    to=float(np.abs(np.diff(Wt,axis=0)).sum(1).mean())
    res1h[nm]=dict(gross=gr,turn=to,net22=gr-to*2.2,net352=gr-to*3.52)
    print("%-7s %+10.4f %10.4f %+10.4f %+10.4f"%(nm,gr,to,gr-to*2.2,gr-to*3.52),flush=True)
np.save(R+"/clock_res.npy",dict(clock4h=out,clock1h=res1h),allow_pickle=True)
print("DONE")
