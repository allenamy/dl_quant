"""S7 offset spectrum for the ORTHOGONALISED signals (same construction as drive_sleeves3.py)."""
import numpy as np, json
from scipy.stats import rankdata
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
ts=PW["ts"].astype(np.int64); FE1=np.asarray(PW["f_fund_ema_v1"],float); BASE=np.isfinite(FE1)
IV=np.asarray(PW["f_fund_iv"],float); IVf=np.where(np.isfinite(IV)&(IV>0),IV,8.0)
RN8=np.asarray(PW["f_fund_now"],float)*(8.0/IVf)
MT=np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz",allow_pickle=True)
E=MT["E_ts"].astype(np.int64); mem=MT["members"]; y4=MT["y4"]
prow={int(t):j for j,t in enumerate(ts)}
def rz(M):
    out=np.full(M.shape,np.nan)
    for i in range(M.shape[0]):
        v=M[i]; ok=np.isfinite(v); n=ok.sum()
        if n>=10: out[i,ok]=np.argsort(np.argsort(v[ok]))/max(n-1,1)-0.5
    return out
ZF=rz(np.where(BASE,FE1,np.nan))
def col(c):
    if c=="D_SURP": return RN8-FE1
    return np.asarray(PW[c],float)
def xz(v):
    ok=np.isfinite(v); out=np.full(len(v),np.nan); n=ok.sum()
    if n>=10: out[ok]=rankdata(v[ok])/max(n-1,1)-0.5
    return out
out={}
for name,sgn in (("f_amihud_24h",1.0),("f_asz_24h",-1.0),("D_SURP",-1.0)):
    Z=rz(np.where(BASE,col(name),np.nan)); R=np.full(Z.shape,np.nan)
    for i in range(Z.shape[0]):
        ok=np.isfinite(Z[i])&np.isfinite(ZF[i])
        if ok.sum()<10: continue
        x=ZF[i][ok]; y=Z[i][ok]; vx=float((x*x).sum())
        b=float((x*y).sum()/vx) if vx>1e-12 else 0.0
        R[i][ok]=y-b*x
    S=sgn*R
    acc={k:[] for k in range(-4,5)}
    for i in range(200,len(E)-8):
        j=prow.get(int(E[i]))
        if j is None: continue
        m=mem[i]; z=xz(S[j,m])
        if not np.isfinite(z).any(): continue
        for k in acc:
            yy=y4[i+k,m]; ok=np.isfinite(z)&np.isfinite(yy)
            if ok.sum()<30: continue
            r=np.corrcoef(rankdata(z[ok]),rankdata(yy[ok]))[0,1]
            if np.isfinite(r): acc[k].append(r)
    tag=f"ORTH_{name}_{'p' if sgn>0 else 'm'}"
    out[tag]={str(k):round(float(np.mean(v)),5) for k,v in acc.items()}
    out[tag]["n"]=len(acc[0]); print(tag, json.dumps(out[tag]), flush=True)
json.dump(out,open("/workspace/uplift_2026-09-11/trackD_v4/LEAK_offsets_orth.json","w"),indent=1)
