"""Round-2 sleeve features. GATE A receipt: rows [idx(E), idx(E)+48) reconstruct panel Y4 exactly
(median|d|=0, corr 0.999998) => 5m row idx(E) is the FIRST TRADED bar. Causal-at-E rows are index < idx(E).
LAG-1 convention (the round-1 Amihud fix): every window ENDS at idx(E)-48, i.e. one 4h anchor earlier,
so the i-1 -> i bar is EXCLUDED."""
import numpy as np, time, os
F="/workspace/uplift_2026-09-11/r2_sleeve/feat"
P=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
pts=P["ts"].astype(np.int64)
ts5=np.load("/workspace/data/dlnative_5m_wide829_f16_holefix2.npz",allow_pickle=True)["ts"].astype(np.int64)
pos=np.searchsorted(ts5,pts); assert (ts5[pos]==pts).all()
NT=len(ts5); NS=829; W24=288; W7=2016; LAG=48
t0=time.time()
def csum(X):
    C=np.zeros((NT+1,NS),np.float64); np.cumsum(X,axis=0,out=C[1:]); return C
def win(C,e,w):
    a=e-w; b=e; out=np.full((len(e),NS),np.nan)
    ok=a>=0
    out[ok]=C[b[ok]]-C[a[ok]]; return out
E=pos-LAG                      # window end row (exclusive) = one anchor before E
acc={}
r5=np.load(F+"/ret5.npy").astype(np.float64)
val=np.isfinite(r5); r5z=np.where(val,r5,0.0)
Cn=csum(val.astype(np.float64)); C1=csum(r5z); C2=csum(r5z**2); C3=csum(r5z**3); C4=csum(r5z**4)
Ca=csum(np.abs(r5z)); Cd=csum(np.where(r5z<0,r5z**2,0.0))
lag=np.zeros_like(r5z); lag[1:]=r5z[:-1]*r5z[1:]; Cl=csum(lag)
print("r5 cumsums",round(time.time()-t0,1),flush=True)
n24=win(Cn,E,W24); n7=win(Cn,E,W7)
s1=win(C1,E,W24); s2=win(C2,E,W24); s3=win(C3,E,W24); s4=win(C4,E,W24)
sa=win(Ca,E,W24); sd=win(Cd,E,W24); sl=win(Cl,E,W24)
s2_7=win(C2,E,W7); s1_7=win(C1,E,W7); sa_7=win(Ca,E,W7); n_ok=(n24>=200)
with np.errstate(all="ignore"):
    mu=s1/n24; var=s2/n24-mu**2
    acc["ROLL"]=2.0*np.sqrt(np.maximum(0.0,-(sl/n24-mu**2)))
    acc["RSKEW"]=(s3/n24-3*mu*(s2/n24)+2*mu**3)/np.maximum(var,1e-18)**1.5
    acc["JUMP"]=n24*s4/np.maximum(s2,1e-18)**2
    acc["DSEMI"]=sd/np.maximum(s2,1e-18)
    # variance ratio over 7d: var of non-overlapping 4h blocks vs 48*var(5m)
del C1,C2,C3,C4,Ca,Cd,Cl,lag
# VR needs 4h block returns: aggregate r5 into the 48-bar blocks aligned to anchors
B=np.add.reduceat(r5z,np.arange(0,NT-NT%48,48),axis=0)   # 4h blocks on the 5m grid
Bv=np.add.reduceat(val.astype(np.float64),np.arange(0,NT-NT%48,48),axis=0)
CB2=csum_b=np.zeros((B.shape[0]+1,NS)); np.cumsum(B**2,axis=0,out=csum_b[1:])
CB1=np.zeros((B.shape[0]+1,NS)); np.cumsum(B,axis=0,out=CB1[1:])
CBn=np.zeros((B.shape[0]+1,NS)); np.cumsum((Bv>=40).astype(np.float64),axis=0,out=CBn[1:])
Eb=E//48; ab=Eb-42
okb=ab>=0
b2=np.full((len(E),NS),np.nan); b1=np.full((len(E),NS),np.nan); bn=np.full((len(E),NS),np.nan)
b2[okb]=csum_b[Eb[okb]]-csum_b[ab[okb]]; b1[okb]=CB1[Eb[okb]]-CB1[ab[okb]]; bn[okb]=CBn[Eb[okb]]-CBn[ab[okb]]
with np.errstate(all="ignore"):
    vb=b2/bn-(b1/bn)**2
    v5=s2_7/n7-(s1_7/n7)**2
    acc["VR"]=vb/np.maximum(48.0*v5,1e-20)
del B,Bv,csum_b,CB1,CBn,r5,r5z,val
print("r5 feats",round(time.time()-t0,1),flush=True)
# volume channels
lqv=np.load(F+"/log_qv.npy").astype(np.float64); v=np.isfinite(lqv)
Cq=csum(np.where(v,lqv,0.0)); Cqn=csum(v.astype(np.float64))
q24=win(Cq,E,W24)/np.maximum(win(Cqn,E,W24),1); q7=win(Cq,E,W7)/np.maximum(win(Cqn,E,W7),1)
acc["QVTR"]=q24-q7
qv=np.exp(np.clip(np.where(v,lqv,np.nan),0,30)); Cqv=csum(np.nan_to_num(qv))
il24=sa/np.maximum(win(Cqv,E,W24),1e-9); il7=sa_7/np.maximum(win(Cqv,E,W7),1e-9)
with np.errstate(all="ignore"):
    acc["ILLQTR"]=np.log(np.maximum(il24,1e-30))-np.log(np.maximum(il7,1e-30))
del lqv,qv,Cq,Cqn,Cqv
lc=np.load(F+"/log_cnt.npy").astype(np.float64); la=np.load(F+"/log_avgsz.npy").astype(np.float64)
vv=np.isfinite(lc)&np.isfinite(la)
Cc=csum(np.where(vv,lc,0.0)); Cs=csum(np.where(vv,la,0.0)); Cvn=csum(vv.astype(np.float64))
nn=np.maximum(win(Cvn,E,W24),1)
acc["CNTSZ"]=win(Cc,E,W24)/nn-win(Cs,E,W24)/nn
del lc,la,Cc,Cs,Cvn
print("vol feats",round(time.time()-t0,1),flush=True)
for k in acc:
    A=acc[k]; A[~n_ok]=np.nan; acc[k]=A.astype(np.float32)
    print("%-8s finite %.3f  med %.4g"%(k,np.isfinite(A).mean(),np.nanmedian(A)),flush=True)
np.savez_compressed("/workspace/uplift_2026-09-11/r2_sleeve/feat/r2_new_feats.npz",ts=pts,symbols=P["symbols"],**acc)
print("DONE",round(time.time()-t0,1),flush=True)
