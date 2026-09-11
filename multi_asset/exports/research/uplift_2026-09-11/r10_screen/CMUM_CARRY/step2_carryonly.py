"""CMUM_CARRY: carry-only book series (basis P&L NOT yet included -> this is an UPPER BOUND on Sharpe).
Arms frozen before inspection: A=last-settlement sign, B=EMA(k) sign, C=hysteresis band, D=static short-CM."""
import os,json,datetime as dt,numpy as np
ENV_WHITELIST={"LC_CTYPE","LANG","PATH","PWD","SHLVL","_","__CF_USER_TEXT_ENCODING","HOME","TMPDIR","CPATH","LIBRARY_PATH","MANPATH","SDKROOT"}
assert set(os.environ)<=ENV_WHITELIST, sorted(set(os.environ)-ENV_WHITELIST)
W=os.path.dirname(os.path.abspath(__file__))
Z=np.load(W+"/book_inputs.npz",allow_pickle=True)
TS=Z["TS"];D=Z["D"];R=Z["R"];H=Z["H"];A0g=Z["A0g"];A0turn=Z["A0turn"]
CM_END=int(dt.datetime(2026,6,30,20,tzinfo=dt.timezone.utc).timestamp())
cov=(TS<=CM_END)&(H.sum(1)>=10)
print("coverage anchors %d / %d  (%s .. %s)"%(cov.sum(),len(TS),dt.datetime.utcfromtimestamp(TS[cov][0]),dt.datetime.utcfromtimestamp(TS[cov][-1])))
N,n=D.shape
def series(sig):
    """sig (N,n) desired position sign on the pair (+1 = long CM / short UM). returns carry_bps, turnover, nnames"""
    w=np.where(H,sig,0.0)
    cnt=np.abs(w).sum(1)
    wl=np.where(cnt[:,None]>0, w/np.where(cnt[:,None]==0,1,cnt[:,None])/2.0, 0.0)  # per-leg weight, sum|w| over 2 legs =1
    carry=1e4*2.0*(wl*np.nan_to_num(R)).sum(1)*(-1.0)   # sigma=+1 (long CM/short UM) earns -(f_UM-f_CM)= -R
    dw=np.abs(wl-np.vstack([wl[:1]*0,wl[:-1]])).sum(1)*2.0   # both legs move identically -> x2
    return carry,dw,cnt
res={}
def rep(tag,carry,dw,cnt,mask):
    c=carry[mask];t=dw[mask]
    res[tag]=dict(n=int(mask.sum()),carry_bps=float(c.mean()),carry_sd=float(c.std(ddof=1)),
      sharpe_carryonly=float(c.mean()/c.std(ddof=1)*np.sqrt(2190)),turnover=float(t.mean()),
      names=float(cnt[mask].mean()),flip_frac=float(t.mean()/2.0))
    print(f"{tag:18s} n={res[tag]['n']:5d} carry={c.mean():+8.4f} sd={c.std(ddof=1):7.4f} SR_carryonly={res[tag]['sharpe_carryonly']:+7.3f} turn={t.mean():7.4f} names={cnt[mask].mean():5.1f}")
# A: last settlement sign. we want to RECEIVE: earn -(f_UM-f_CM)*sigma -> choose sigma=-sign(D)
sA=-np.sign(np.nan_to_num(D))
cA,tA,nA=series(sA); rep("A_last",cA,tA,nA,cov)
# B: EMA of D
for k in (3,6,12,30,90):
    a=2.0/(k+1); E=np.zeros_like(D); prev=np.zeros(n)
    Df=np.where(H,np.nan_to_num(D),np.nan)
    for i in range(N):
        x=np.where(np.isfinite(Df[i]),Df[i],prev); prev=(1-a)*prev+a*x; E[i]=prev
    cB,tB,nB=series(-np.sign(E)); rep("B_ema%d"%k,cB,tB,nB,cov)
# C: hysteresis on last-settlement D with band b (bps/hour)
for b in (0.02,0.05,0.10,0.25):
    th=b/1e4; s=np.zeros((N,n)); prev=np.zeros(n)
    Dn=np.nan_to_num(D)
    for i in range(N):
        cur=prev.copy()
        cur=np.where(Dn[i]>th,-1.0,np.where(Dn[i]<-th,1.0,cur))
        s[i]=cur; prev=cur
    cC,tC,nC=series(s); rep("C_hyst%.2f"%b,cC,tC,nC,cov)
# D: static short-CM/long-UM  (sigma=-1 everywhere)
cD,tD,nD=series(-np.ones((N,n))); rep("D_static_shortCM",cD,tD,nD,cov)
cD2,tD2,nD2=series(np.ones((N,n))); rep("D_static_longCM",cD2,tD2,nD2,cov)
np.savez_compressed(W+"/carryonly_series.npz",TS=TS,cov=cov,
   A=cA,A_t=tA,B=cB,B_t=tB,C=cC,C_t=tC,Dm=cD,Dm_t=tD)
json.dump(res,open(W+"/STEP2_carryonly.json","w"),indent=1)
