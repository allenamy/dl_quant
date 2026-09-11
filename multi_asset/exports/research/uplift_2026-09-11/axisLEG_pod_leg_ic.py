"""Monthly cross-sectional rank-IC per book leg + funding regime stats.
Inputs (pod2): /workspace/data/wide_fea_v2ext_meta.npz (E_ts, members, y4, qvk)
               /workspace/data/wide_panel_4h_v2ext.npz (ts, f_rev_24h, f_fund_ema_v1, f_fund_now, f_fund_iv, elig)
               /workspace/uplift_2026-09-11/slow_pred_pinned.npy  (sha 158cd4ac..., = in-service shadow_bundle v3_2026-09)
Leg definitions read from shadow_loop_v3.py L471 and pod_export_bundle_v3.py L104-109 (same formula).
y4 caliber = SUM of 5m simple returns (E-0904-F); NOT the money caliber prod(1+r)-1.
"""
import numpy as np, json, time, sys
from scipy.stats import rankdata, spearmanr
M=np.load('/workspace/data/wide_fea_v2ext_meta.npz',allow_pickle=True)
E=M['E_ts'].astype(np.int64); members=M['members']; y4=M['y4']
P=np.load('/workspace/data/wide_panel_4h_v2ext.npz',allow_pickle=True)
pts=P['ts'].astype(np.int64); prow={int(t):j for j,t in enumerate(pts)}
R24=P['f_rev_24h']; FE=P['f_fund_ema_v1']; FN=P['f_fund_now']; IV=P['f_fund_iv']
PRED=np.load('/workspace/uplift_2026-09-11/slow_pred_pinned.npy')
nA=len(E)
def sp(a,b):
    ok=np.isfinite(a)&np.isfinite(b)
    if ok.sum()<30: return np.nan
    r=spearmanr(a[ok],b[ok])
    return float(r.correlation if hasattr(r,'correlation') else r[0])
def xz(v):
    ok=np.isfinite(v); out=np.full(len(v),np.nan); n=ok.sum()
    if n>=10: out[ok]=rankdata(v[ok])/max(n-1,1)-0.5
    return out
legs=('king','rev24','fund')
IC={l:np.full(nA,np.nan) for l in legs}
LR={l:np.full(nA,np.nan) for l in legs}
ICL={l:{k:np.full(nA,np.nan) for k in range(0,13)} for l in ('fund','king')}
REG={k:np.full(nA,np.nan) for k in ('fn_mean','fn_sd','fn_p10','fn_p90','fn_fracneg','fn_absmean','n','fe_sd','fe_mean','y_sd')}
for i in range(nA):
    j=prow.get(int(E[i]))
    if j is None: continue
    m=members[i]
    y=y4[i,m]; ok=np.isfinite(y)
    if ok.sum()<50: continue
    sc={'king':PRED[i,m].astype(np.float64),'rev24':-R24[j,m].astype(np.float64),'fund':FE[j,m].astype(np.float64)}
    for l in legs:
        IC[l][i]=sp(sc[l],y)
        z=np.nan_to_num(xz(sc[l])); z=np.where(ok,z,0.0)
        z=z-(z[ok].mean() if ok.sum() else 0); g=np.abs(z).sum()
        LR[l][i]=float((z/g*np.nan_to_num(y,nan=0.0)).sum()*1e4) if g>1e-9 else 0.0
    for l in ('fund','king'):
        sf=np.full(829,np.nan); sf[m]=sc[l]
        for k in range(0,13):
            if i+k>=nA: continue
            ICL[l][k][i]=sp(sf,y4[i+k].astype(np.float64))
    fn=FN[j,m].astype(np.float64); iv=IV[j,m].astype(np.float64)
    iv=np.where(np.isfinite(iv)&(iv>0),iv,8.0)
    fn4=fn*(4.0/iv)*1e4   # bps per 4h
    f=fn4[np.isfinite(fn4)]
    if len(f)>=30:
        REG['fn_mean'][i]=f.mean(); REG['fn_sd'][i]=f.std(); REG['fn_p10'][i]=np.percentile(f,10)
        REG['fn_p90'][i]=np.percentile(f,90); REG['fn_fracneg'][i]=(f<0).mean(); REG['fn_absmean'][i]=np.abs(f).mean()
        REG['n'][i]=len(f)
    fe=FE[j,m].astype(np.float64); fe=fe[np.isfinite(fe)]
    if len(fe)>=30: REG['fe_sd'][i]=fe.std(); REG['fe_mean'][i]=fe.mean()
    REG['y_sd'][i]=np.nanstd(y)*1e4
out={'E_ts':E.tolist(),'IC':{k:v.tolist() for k,v in IC.items()},'LR':{k:v.tolist() for k,v in LR.items()},
     'ICL':{l:{str(k):v.tolist() for k,v in d.items()} for l,d in ICL.items()},
     'REG':{k:v.tolist() for k,v in REG.items()}}
json.dump(out,open('/workspace/uplift_2026-09-11/leg_ic_out.json','w'))
print('DONE', nA, 'anchors; finite IC fund', int(np.isfinite(IC['fund']).sum()), 'king', int(np.isfinite(IC['king']).sum()))
