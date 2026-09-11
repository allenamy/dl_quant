"""S7 offset spectrum: rank-IC of a signal at anchor i against y4 at anchor i+k, k in [-4,+4].
A causal signal peaks at k=0 and has no larger |value| at k<0. usage: leakcheck.py NAME_p NAME_m ..."""
import numpy as np, sys, json
from scipy.stats import rankdata
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
ts=PW["ts"].astype(np.int64)
FE1=np.asarray(PW["f_fund_ema_v1"],float); BASE=np.isfinite(FE1)
IV=np.asarray(PW["f_fund_iv"],float); IVf=np.where(np.isfinite(IV)&(IV>0),IV,8.0)
RN8=np.asarray(PW["f_fund_now"],float)*(8.0/IVf)
MT=np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz",allow_pickle=True)
E=MT["E_ts"].astype(np.int64); mem=MT["members"]; y4=MT["y4"]
prow={int(t):j for j,t in enumerate(ts)}
def col(c):
    if c=="f_fund_rn8": return RN8
    if c=="D_SURP": return RN8-FE1
    if c=="D_MOMSPREAD": return np.asarray(PW["f_mom_30d"],float)-np.asarray(PW["f_mom_7d"],float)
    if c=="D_VOLADJMOM": return np.asarray(PW["f_mom_7d"],float)/(np.abs(np.asarray(PW["f_vol_7d"],float))+1e-6)
    return np.asarray(PW[c],float)
def xz(v):
    ok=np.isfinite(v); out=np.full(len(v),np.nan); n=ok.sum()
    if n>=10: out[ok]=rankdata(v[ok])/max(n-1,1)-0.5
    return out
out={}
KS=range(-4,5)
for spec in sys.argv[1:]:
    name,sgn=(spec[:-2],1.0) if spec.endswith("_p") else (spec[:-2],-1.0)
    S=np.where(BASE,sgn*col(name),np.nan)
    acc={k:[] for k in KS}
    for i in range(200,len(E)-8):
        j=prow.get(int(E[i]))
        if j is None: continue
        m=mem[i]; z=xz(S[j,m])
        if not np.isfinite(z).any(): continue
        for k in KS:
            yy=y4[i+k,m]
            ok=np.isfinite(z)&np.isfinite(yy)
            if ok.sum()<30: continue
            r=np.corrcoef(rankdata(z[ok]),rankdata(yy[ok]))[0,1]
            if np.isfinite(r): acc[k].append(r)
    out[spec]={str(k):(float(np.mean(v)) if v else None) for k,v in acc.items()}
    out[spec]["n"]=len(acc[0])
    print(spec, json.dumps({k:(round(v,5) if isinstance(v,float) else v) for k,v in out[spec].items()}), flush=True)
json.dump(out,open("/workspace/uplift_2026-09-11/trackD_v4/LEAK_offsets.json","w"),indent=1)
