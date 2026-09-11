"""S7 gate: offset spectrum ic(k) = mean_i Spearman(orth_signal@i, Y4@i+k) across names.
GATE A receipt fixes the meaning: Y4@i is the FORWARD 4h return traded from anchor i, so
k=0 is forward predictive power and k=-1 is the bar that just closed."""
import numpy as np, json
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
def lag1(Z):
    L=np.full_like(Z,np.nan); L[1:]=Z[:-1]; return np.where(B,L,np.nan)
YR=rz(Y4)   # rank of the traded forward return, per anchor
def spec(S,ks=(-3,-2,-1,0,1,2,3)):
    out={}
    for k in ks:
        num=0.0; n=0
        for i in range(S.shape[0]):
            j=i+k
            if j<0 or j>=S.shape[0]: continue
            ok=np.isfinite(S[i])&np.isfinite(YR[j])
            if ok.sum()<30: continue
            a=S[i][ok]-S[i][ok].mean(); b=YR[j][ok]-YR[j][ok].mean()
            d=np.sqrt((a*a).sum()*(b*b).sum())
            if d>0: num+=float((a*b).sum()/d); n+=1
        out[k]=num/max(n,1)
    return out
NEW=np.load(R+"/feat/r2_new_feats.npz",allow_pickle=True)
CAND={}
for k in ["f_tbf_24h","f_rev_24h","f_vol_7d","f_range_24h","f_cpos_24h","f_volq_ratio","f_mom_30d","f_fund_iv"]:
    CAND["L_"+k]=orth(lag1(rz(np.where(B,np.asarray(PW[k],float),np.nan))))
for k in ["ROLL","VR","RSKEW","JUMP","DSEMI","ILLQTR","QVTR","CNTSZ"]:
    CAND["N_"+k]=orth(rz(np.where(B,np.asarray(NEW[k],float),np.nan)))
CAND["PC_amihud_lag"]=orth(lag1(rz(np.where(B,np.asarray(PW["f_amihud_24h"],float),np.nan))))
CAND["RAW_tbf_unlagged"]=orth(rz(np.where(B,np.asarray(PW["f_tbf_24h"],float),np.nan)))
CAND["RAW_amihud_unlagged"]=orth(rz(np.where(B,np.asarray(PW["f_amihud_24h"],float),np.nan)))
CAND["DEPLOYED_fund_score"]=ZF
res={}
print("%-22s %8s %8s %8s %8s %8s %8s %8s   %s"%("arm","k=-3","k=-2","k=-1","k=0","k=+1","k=+2","k=+3","S7 |ic(-1)|<=2*ic(0) & ic(0)>0"))
for nm,S in CAND.items():
    s=spec(S); res[nm]=s
    ok = (s[0]>0) and (abs(s[-1])<=2*s[0])
    print("%-22s %+8.4f %+8.4f %+8.4f %+8.4f %+8.4f %+8.4f %+8.4f   %s"%(nm,s[-3],s[-2],s[-1],s[0],s[1],s[2],s[3],"PASS" if ok else "FAIL"))
json.dump({k:{str(a):b for a,b in v.items()} for k,v in res.items()},open(R+"/RESULT_r2_icspec.json","w"),indent=1)
