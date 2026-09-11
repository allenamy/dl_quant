"""Offset spectrum: corr(signal rank at anchor i, y4 at anchor i+k) for k in [-4,+4], pooled cross-sectionally.
Signal layer (NOT the book layer). Rank-IC, not value-IC."""
import numpy as np, json, sys
D="/workspace/uplift_2026-09-11/dev_v4ev"; ES="/workspace/uplift_2026-09-11/event_state"
PW=np.load(f"{D}/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz",allow_pickle=True)
ts=PW["ts"].astype(np.int64); FE1=np.asarray(PW["f_fund_ema_v1"],float); BASE=np.isfinite(FE1)
MT=np.load(f"{D}/pod_backup_2026-08-21/wide_fea_hist_meta.npz",allow_pickle=True)
E=MT["E_ts"].astype(np.int64); y4=np.asarray(MT["y4"],float)
mrow={int(t):i for i,t in enumerate(E)}; mi=np.array([mrow[int(t)] for t in ts])
F=np.load(f"{ES}/feats_v4.npz",allow_pickle=True)
def rz(M):
    out=np.full(M.shape,np.nan)
    for i in range(M.shape[0]):
        v=M[i]; ok=np.isfinite(v); n=ok.sum()
        if n>=10: out[i,ok]=np.argsort(np.argsort(v[ok]))/max(n-1,1)-0.5
    return out
ZF=rz(np.where(BASE,FE1,np.nan))
def orth(M):
    Z=rz(M); R=np.full(Z.shape,np.nan)
    for i in range(Z.shape[0]):
        ok=np.isfinite(Z[i])&np.isfinite(ZF[i])
        if ok.sum()<10: continue
        x=ZF[i][ok]-ZF[i][ok].mean(); y=Z[i][ok]-Z[i][ok].mean(); vx=float((x*x).sum())
        b=float((x*y).sum()/vx) if vx>1e-12 else 0.0
        R[i][ok]=y-b*x
    return R
def spec(S):
    Zs=rz(S); res={}
    for k in range(-4,5):
        num=0.0; a=[]; b=[]
        for i in range(Zs.shape[0]):
            j=i+k
            if j<0 or j>=Zs.shape[0]: continue
            yy=y4[mi[j]]
            ok=np.isfinite(Zs[i])&np.isfinite(yy)
            if ok.sum()<20: continue
            v=yy[ok]; r=np.argsort(np.argsort(v))/max(ok.sum()-1,1)-0.5
            z=Zs[i][ok]
            a.append(float((z*r).sum())); b.append(float(np.sqrt((z*z).sum()*(r*r).sum())))
        res[str(k)]=round(sum(a)/sum(b),5) if b else None
    return res
out={}
for nm in ["SWDRIFT","SWRESID","SWRESID3","SWABS","CAPPIN","IVSWITCH","LISTEVT"]:
    M=np.where(BASE,np.asarray(F[nm],float),np.nan)
    out[nm]=spec(M); out["ORTH_"+nm]=spec(orth(M))
    print(nm,out[nm],flush=True); print("ORTH_"+nm,out["ORTH_"+nm],flush=True)
out["f_fund_ema_v1_reference"]=spec(np.where(BASE,FE1,np.nan))
print("REF",out["f_fund_ema_v1_reference"])
json.dump(out,open(f"{ES}/IC_SPECTRUM.json","w"),indent=1)
