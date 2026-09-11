"""Mechanism evidence: what are the LOB features actually proxying? Per-anchor Spearman of each LOB
feature rank against the deployed fund score, the 8h-equivalent funding rate, realised vol, amihud, and
the past 4h return. Signal layer, LOBFULL-eligible anchors only."""
import numpy as np, json, calendar
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
ts=PW["ts"].astype(np.int64); FE1=np.asarray(PW["f_fund_ema_v1"],float); BASE=np.isfinite(FE1)
IV=np.asarray(PW["f_fund_iv"],float); IVf=np.where(np.isfinite(IV)&(IV>0),IV,8.0)
RN8=np.asarray(PW["f_fund_now"],float)*(8.0/IVf)
REF={"fund_ema_v1":FE1,"fund_rn8":RN8,"vol_7d":np.asarray(PW["f_vol_7d"],float),
     "amihud_24h":np.asarray(PW["f_amihud_24h"],float),"rev_4h":np.asarray(PW["f_rev_4h"],float),
     "range_24h":np.asarray(PW["f_range_24h"],float),"asz_24h":np.asarray(PW["f_asz_24h"],float)}
def rz(M):
    out=np.full(M.shape,np.nan)
    for i in range(M.shape[0]):
        v=M[i]; ok=np.isfinite(v); n=ok.sum()
        if n>=10: out[i,ok]=np.argsort(np.argsort(v[ok]))/max(n-1,1)-0.5
    return out
def xcorr(A,B):
    vals=[]
    for i in range(A.shape[0]):
        a=A[i]; b=B[i]; ok=np.isfinite(a)&np.isfinite(b)
        if ok.sum()<20: continue
        x=a[ok]-a[ok].mean(); y=b[ok]-b[ok].mean()
        d=np.sqrt((x*x).sum()*(y*y).sum())
        if d>0: vals.append(float((x*y).sum()/d))
    v=np.array(vals); return (float(v.mean()),float(v.std(ddof=1)/np.sqrt(len(v))),len(v))
RZ={k:rz(np.where(BASE,v,np.nan)) for k,v in REF.items()}
LOB="/workspace/uplift_2026-09-11/r2/lob2"
out={}
for nm in ["LDVOL","LIVOL","LSLASY","LDTREND","LCONVX","LDINNOV","LIMBINN","LDVOLR","_R1MEAN"]:
    z=np.load("%s/%s.npz"%(LOB,nm),allow_pickle=True)
    Z=rz(np.where(BASE,np.asarray(z["mat"],np.float64),np.nan))
    e={k:[round(x,4) for x in xcorr(Z,RZ[k])[:2]] for k in RZ}
    out[nm]=e; print("%-9s %s"%(nm,json.dumps(e)),flush=True)
json.dump(out,open("/workspace/uplift_2026-09-11/r2/MECH_r2.json","w"),indent=1)
