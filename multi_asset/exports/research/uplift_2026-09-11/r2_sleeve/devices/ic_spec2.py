import numpy as np, calendar
from scipy.stats import rankdata
R="/workspace/uplift_2026-09-11/r2_sleeve"
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
ts=PW["ts"].astype(np.int64); FE1=np.asarray(PW["f_fund_ema_v1"],float); B=np.isfinite(FE1)
Y4=np.asarray(PW["Y4"],float)
def rz(M):
    out=np.full(M.shape,np.nan)
    for i in range(M.shape[0]):
        v=M[i]; ok=np.isfinite(v); n=ok.sum()
        if n>=10: out[i,ok]=(rankdata(v[ok])-1.0)/max(n-1,1)-0.5
    return out
ZF=rz(np.where(B,FE1,np.nan))
def orth(Z):
    Rr=np.full(Z.shape,np.nan)
    for i in range(Z.shape[0]):
        ok=np.isfinite(Z[i])&np.isfinite(ZF[i])
        if ok.sum()<10: continue
        x=ZF[i][ok]; y=Z[i][ok]; vx=float((x*x).sum())
        b=float((x*y).sum()/vx) if vx>1e-12 else 0.0
        Rr[i][ok]=y-b*x
    return Rr
def lagn(Z,n):
    L=np.full_like(Z,np.nan); L[n:]=Z[:-n]; return np.where(B,L,np.nan)
def ema(M,hl):
    a=1.0-0.5**(1.0/hl); O=np.full(M.shape,np.nan); s=np.full(M.shape[1],np.nan)
    for i in range(M.shape[0]):
        v=M[i]; ok=np.isfinite(v)
        s=np.where(np.isfinite(s)&ok, s+a*(v-s), np.where(ok,v,s)); O[i]=s
    return O
YR=rz(Y4)
def spec(S,mask=None,ks=(-3,-2,-1,0,1,2)):
    out={}
    for k in ks:
        num=0.0;n=0
        for i in range(S.shape[0]):
            if mask is not None and not mask[i]: continue
            j=i+k
            if j<0 or j>=S.shape[0]: continue
            ok=np.isfinite(S[i])&np.isfinite(YR[j])
            if ok.sum()<30: continue
            a=S[i][ok]-S[i][ok].mean(); b=YR[j][ok]-YR[j][ok].mean()
            d=np.sqrt((a*a).sum()*(b*b).sum())
            if d>0: num+=float((a*b).sum()/d); n+=1
        out[k]=num/max(n,1)
    return out
TBF=np.where(B,np.asarray(PW["f_tbf_24h"],float),np.nan)
S=orth(lagn(rz(ema(TBF,8)),1))
A=orth(lagn(rz(np.where(B,np.asarray(PW["f_amihud_24h"],float),np.nan)),1))
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
early=(ts<T(2025,1,1)); late=(ts>=T(2025,1,1))
for nm,Sx in [("TBF_ema08",S),("PC_amihud_lag",A),("DEPLOYED_fund",ZF)]:
    s=spec(Sx); print("%-16s ALL   "%nm+"  ".join("k=%+d %+0.4f"%(k,s[k]) for k in sorted(s)))
    se=spec(Sx,early); sl=spec(Sx,late)
    print("%-16s <2025 "%""+"  ".join("k=%+d %+0.4f"%(k,se[k]) for k in sorted(se)))
    print("%-16s >=2025"%""+"  ".join("k=%+d %+0.4f"%(k,sl[k]) for k in sorted(sl)))
