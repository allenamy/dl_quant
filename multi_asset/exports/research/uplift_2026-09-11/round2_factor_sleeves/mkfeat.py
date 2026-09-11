"""Round-2 FACTOR/RESIDUAL feature builder. PREREG: K=36 (18 families x 2 signs) declared 2026-09-11
before any new arm was run.

CAUSALITY (VERIFIED): f_rev_4h[i] == Y4[i-1] exactly (max|diff| = 0.0 over the whole panel), i.e.
RET[i,:] = f_rev_4h[i,:] is the realised return of the bar (i-1, i], which is CLOSED at anchor i.
Y4[i] is the FORWARD return the book earns; it is never touched by any feature here.

WINDOW CONVENTION, pre-specified by mechanism (round-1 receipt: ending the Amihud window one anchor
before E turned CI-containing-zero into CI-excluding-zero):
  * reversal / momentum families  -> window ENDS AT BAR i (the (i-1,i] bar IS the signal)
  * state families (vol, beta, skew, liquidity quality/stability) -> window ENDS AT BAR i-1
  * cross-sectional residualisations of panel characteristics -> characteristic LAGGED one anchor
Panel: dev/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz = the file the DEVICE itself loads
(verified bitwise identical on all 21 2-D arrays to /workspace/data/wide_panel_4h_v2ext.npz).
Rank base: B = isfinite(f_fund_ema_v1) -- identical to the live fund leg's xz_in_base under UMASK_SCOPE=m1.
"""
import numpy as np, os, json, hashlib
PAN="/workspace/uplift_2026-09-11/r2_factor/dev/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz"
P=np.load(PAN,allow_pickle=True)
ts=P["ts"].astype(np.int64); sym=[str(x) for x in P["symbols"]]
NA,NS=len(ts),len(sym)
def c(k): return np.asarray(P[k],np.float64)
FE1=c("f_fund_ema_v1"); B=np.isfinite(FE1)
RET=c("f_rev_4h")                      # realised return of bar (i-1, i]; closed at anchor i
AM=c("f_amihud_24h"); ASZ=c("f_asz_24h"); VOL=c("f_vol_7d"); RNG=c("f_range_24h")
VQ=c("f_volq_ratio"); TBF=c("f_tbf_24h"); CPOS=c("f_cpos_24h")
IV=c("f_fund_iv"); IVf=np.where(np.isfinite(IV)&(IV>0),IV,8.0); RN8=c("f_fund_now")*(8.0/IVf)

# ---------- market factor: cross-sectional mean return over the rank base ----------
Rm=np.where(B&np.isfinite(RET),RET,np.nan)
with np.errstate(all="ignore"):
    MKT=np.nanmean(Rm,axis=1)
MKT=np.where(np.isfinite(MKT),MKT,0.0)
print("MKT std %.5f"%MKT.std(),flush=True)

# ---------- rolling helpers ----------
def rs(X,W,off):
    """sum over rows [i-off-W+1, i-off] inclusive; NaN treated as 0. Returns (sum, count)."""
    F=np.isfinite(X); Z=np.where(F,X,0.0)
    cz=np.concatenate([np.zeros((1,)+X.shape[1:]),np.cumsum(Z,axis=0)])
    cf=np.concatenate([np.zeros((1,)+X.shape[1:]),np.cumsum(F.astype(np.float64),axis=0)])
    i=np.arange(X.shape[0]); hi=np.clip(i-off+1,0,X.shape[0]); lo=np.clip(i-off-W+1,0,X.shape[0])
    return cz[hi]-cz[lo], cf[hi]-cf[lo]
def rs1(x,W,off):
    x=np.asarray(x,np.float64)
    cz=np.concatenate([[0.0],np.cumsum(x)])
    i=np.arange(len(x)); hi=np.clip(i-off+1,0,len(x)); lo=np.clip(i-off-W+1,0,len(x))
    return cz[hi]-cz[lo]

def beta_ivol(W,off,minn=None):
    """per-name OLS of RET on MKT over the W bars ending at row i-off."""
    if minn is None: minn=max(20,W//3)
    M2=np.broadcast_to(MKT[:,None],RET.shape)
    F=np.isfinite(RET)&B
    Sy,n=rs(np.where(F,RET,np.nan),W,off)
    Sx,_=rs(np.where(F,M2,np.nan),W,off)
    Sxy,_=rs(np.where(F,RET*M2,np.nan),W,off)
    Sxx,_=rs(np.where(F,M2*M2,np.nan),W,off)
    Syy,_=rs(np.where(F,RET*RET,np.nan),W,off)
    with np.errstate(all="ignore"):
        den=n*Sxx-Sx*Sx
        beta=np.where(np.abs(den)>1e-18,(n*Sxy-Sx*Sy)/den,np.nan)
        alpha=(Sy-beta*Sx)/np.maximum(n,1)
        ssy=Syy-Sy*Sy/np.maximum(n,1)
        ssres=ssy-beta*(Sxy-Sx*Sy/np.maximum(n,1))
        ivol=np.sqrt(np.maximum(ssres,0.0)/np.maximum(n-2,1))
        r2=np.where(ssy>1e-18,1.0-np.maximum(ssres,0.0)/ssy,np.nan)
    bad=(n<minn)
    for A in (beta,alpha,ivol,r2): A[bad]=np.nan
    return beta,ivol,r2,alpha,n

print("beta/ivol ...",flush=True)
BET42,IVOL42,R2_42,AL42,N42 = beta_ivol(42,1)        # 7d state, ends at bar i-1
def resid_sum(k):
    b,_,_,a,_=beta_ivol(180,1+k)                     # beta window ends BEFORE the reversal window
    Sy,n=rs(np.where(np.isfinite(RET)&B,RET,np.nan),k,0)
    Sx=rs1(MKT,k,0)
    return Sy - b*Sx - a*n
print("residual sums ...",flush=True)
E1=resid_sum(1); E6=resid_sum(6); E18=resid_sum(18); E42=resid_sum(42)

def res_moments(W,off):
    b,_,_,a,_=beta_ivol(W,off)
    R = RET - b*np.broadcast_to(MKT[:,None],RET.shape) - a
    R = np.where(np.isfinite(RET)&B,R,np.nan)
    S1,n=rs(R,W,off); S2,_=rs(R*R,W,off); S3,_=rs(R*R*R,W,off)
    with np.errstate(all="ignore"):
        mu=S1/np.maximum(n,1); v=S2/np.maximum(n,1)-mu*mu
        sd=np.sqrt(np.maximum(v,0.0))
        sk=np.where(sd>1e-12,(S3/np.maximum(n,1)-3*mu*v-mu**3)/np.maximum(sd**3,1e-30),np.nan)
    sk[n<W//3]=np.nan
    return sk
print("residual skew ...",flush=True)
RSKEW=res_moments(180,1)

def rollmax(X,W,off):
    out=np.full(X.shape,np.nan)
    Xf=np.where(np.isfinite(X),X,-np.inf)
    for i in range(X.shape[0]):
        hi=i-off+1; lo=max(0,i-off-W+1)
        if hi-lo<W//3: continue
        out[i]=Xf[lo:hi].max(axis=0)
    return np.where(np.isfinite(out),out,np.nan)
b180,_,_,a180,_=beta_ivol(180,1)
RESID_ALL=np.where(np.isfinite(RET)&B, RET-b180*np.broadcast_to(MKT[:,None],RET.shape)-a180, np.nan)
print("rolling max ...",flush=True)
RMAX=rollmax(RESID_ALL,42,1)

def semibeta(W,off,down=True):
    sel=(MKT<0) if down else (MKT>=0)
    M2=np.broadcast_to((MKT*sel)[:,None],RET.shape); S2=np.broadcast_to(sel[:,None].astype(float),RET.shape)
    F=np.isfinite(RET)&B&(S2>0)
    Sy,n=rs(np.where(F,RET,np.nan),W,off); Sx,_=rs(np.where(F,M2,np.nan),W,off)
    Sxy,_=rs(np.where(F,RET*M2,np.nan),W,off); Sxx,_=rs(np.where(F,M2*M2,np.nan),W,off)
    with np.errstate(all="ignore"):
        den=n*Sxx-Sx*Sx
        b=np.where(np.abs(den)>1e-18,(n*Sxy-Sx*Sy)/den,np.nan)
    b[n<W//6]=np.nan
    return b
print("semibetas ...",flush=True)
BD=semibeta(180,1,True); BU=semibeta(180,1,False)

S6,_=rs(np.where(np.isfinite(RET)&B,RET,np.nan),6,0)
def varr(X,W,off):
    S1,n=rs(X,W,off); S2,_=rs(X*X,W,off)
    with np.errstate(all="ignore"):
        v=S2/np.maximum(n,1)-(S1/np.maximum(n,1))**2
    v[n<W//3]=np.nan; return v
v1=varr(np.where(np.isfinite(RET)&B,RET,np.nan),180,1)
v6=varr(np.where(np.isfinite(S6)&B,S6,np.nan),180,1)
with np.errstate(all="ignore"): VARRATIO=v6/np.maximum(6.0*v1,1e-30)
VARRATIO=np.where(np.isfinite(v1)&np.isfinite(v6),VARRATIO,np.nan)

def trail_mean_std(X,W,off):
    S1,n=rs(X,W,off); S2,_=rs(X*X,W,off)
    mu=S1/np.maximum(n,1)
    with np.errstate(all="ignore"): sd=np.sqrt(np.maximum(S2/np.maximum(n,1)-mu*mu,0.0))
    mu[n<W//3]=np.nan; sd[n<W//3]=np.nan
    return mu,sd
AMm,AMs=trail_mean_std(np.where(B,AM,np.nan),42,1)
ASZm,ASZs=trail_mean_std(np.where(B,ASZ,np.nan),42,1)
AM_L1=np.full_like(AM,np.nan); AM_L1[1:]=AM[:-1]
with np.errstate(all="ignore"):
    LIQTREND=AM_L1-AMm
    LIQSTAB=AMs/np.maximum(np.abs(AMm),1e-12)
    ASZSTAB=ASZs/np.maximum(np.abs(ASZm),1e-12)

def rz(M):
    out=np.full(M.shape,np.nan)
    for i in range(M.shape[0]):
        v=M[i]; ok=np.isfinite(v); n=ok.sum()
        if n>=10: out[i,ok]=np.argsort(np.argsort(v[ok]))/max(n-1,1)-0.5
    return out
ZFUND=rz(np.where(B,FE1,np.nan))
wF=np.where(np.isfinite(ZFUND), -np.sign(ZFUND)*(np.abs(ZFUND)>1/6.0), 0.0)
num=np.nansum(np.where(np.isfinite(RET),wF*RET,0.0),axis=1); den=np.nansum(np.abs(wF),axis=1)
FFAC=np.where(den>0,num/np.maximum(den,1e-12),0.0)
def beta_to(fac,W,off):
    M2=np.broadcast_to(np.asarray(fac,np.float64)[:,None],RET.shape)
    F=np.isfinite(RET)&B
    Sy,n=rs(np.where(F,RET,np.nan),W,off); Sx,_=rs(np.where(F,M2,np.nan),W,off)
    Sxy,_=rs(np.where(F,RET*M2,np.nan),W,off); Sxx,_=rs(np.where(F,M2*M2,np.nan),W,off)
    with np.errstate(all="ignore"):
        dn=n*Sxx-Sx*Sx; b=np.where(np.abs(dn)>1e-18,(n*Sxy-Sx*Sy)/dn,np.nan)
    b[n<W//3]=np.nan; return b
print("funding beta ...",flush=True)
BETAFUND=beta_to(FFAC,180,1)

def lag1(M):
    o=np.full_like(M,np.nan); o[1:]=M[:-1]; return o
def xsec_resid(Y,Xs):
    ZY=rz(np.where(B,Y,np.nan)); ZX=[rz(np.where(B,x,np.nan)) for x in Xs]
    R=np.full(ZY.shape,np.nan)
    for i in range(ZY.shape[0]):
        ok=np.isfinite(ZY[i]).copy()
        for zx in ZX: ok&=np.isfinite(zx[i])
        if ok.sum()<30: continue
        A=np.column_stack([np.ones(ok.sum())]+[zx[i][ok] for zx in ZX])
        y=ZY[i][ok]
        try: b,*_=np.linalg.lstsq(A,y,rcond=None)
        except Exception: continue
        R[i,ok]=y-A@b
    return R
print("xsec residualisations ...",flush=True)
AMIRESID  = xsec_resid(lag1(AM), [lag1(VOL), lag1(RNG)])
FUNDRESID = xsec_resid(FE1,      [lag1(AM),  lag1(ASZ), lag1(VOL)])
TURNRESID = xsec_resid(lag1(VQ), [lag1(AM)])

FEATS={
 "RESREV_1":  -E1,          "RESREV_6":  -E6,          "RESREV_18": -E18,
 "RESMOM_42":  E42,         "IVOL_42":   IVOL42,       "IVOLRAT":   1.0-R2_42,
 "BETA_42":    BET42,       "DBETA":     BD-BU,        "RESMAX":    RMAX,
 "RESSKEW":    RSKEW,       "VARRATIO":  VARRATIO,     "LIQTREND":  LIQTREND,
 "LIQSTAB":    LIQSTAB,     "ASZSTAB":   ASZSTAB,      "FUNDRESID": FUNDRESID,
 "AMIRESID":   AMIRESID,    "TURNRESID": TURNRESID,    "BETAFUND":  BETAFUND,
}
assert len(FEATS)==18, len(FEATS)
OUT="/workspace/uplift_2026-09-11/r2_factor/feat"
os.makedirs(OUT,exist_ok=True)
man={}
for k,M in FEATS.items():
    M=np.where(B,np.asarray(M,np.float64),np.nan)
    f=OUT+"/"+k+".npy"; np.save(f,M.astype(np.float32))
    man[k]={"finite":float(np.isfinite(M).mean()),"finite_in_base":float(np.isfinite(M)[B].mean()),
            "sha16":hashlib.sha256(open(f,"rb").read()).hexdigest()[:16]}
    print("%-11s finite_all %.3f  finite_in_base %.3f"%(k,man[k]["finite"],man[k]["finite_in_base"]),flush=True)
np.save(OUT+"/_ZFUND.npy",ZFUND.astype(np.float32))
np.save(OUT+"/_MKT.npy",MKT); np.save(OUT+"/_RET.npy",RET.astype(np.float32)); np.save(OUT+"/_B.npy",B)
json.dump({"panel":PAN,"K_declared":36,"families":list(FEATS),"manifest":man},
          open("/workspace/uplift_2026-09-11/r2_factor/feat_manifest.json","w"),indent=1)
print("DONE")
