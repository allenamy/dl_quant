"""Forward vs backward cross-sectional rank-IC at k=-3..+3 for the price-space book features.
Y4 on the panel is the FORWARD 4h return (verified: corr(d4h book price, f_rev_4h)=0.886, corr with Y4=-0.006).
IC_k = mean over anchors of xsec Spearman( S_i , Y4_{i+k} ). k>=0 forward, k<0 backward.
Also: rho of the feature to f_amihud_24h and to the depth level round 2 measured (LOBDEPTH/_R1MEAN)."""
import numpy as np, json, calendar
from scipy.stats import rankdata
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
P=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
ts=P["ts"].astype(np.int64); Y=np.asarray(P["Y4"],float)
BASE=np.isfinite(np.asarray(P["f_fund_ema_v1"],float))
AMI=np.asarray(P["f_amihud_24h"],float)
R1=np.asarray(np.load("/workspace/uplift_2026-09-11/r2/lob2/_R1MEAN.npz",allow_pickle=True)["mat"],float)
LSL=np.asarray(np.load("/workspace/uplift_2026-09-11/r2/lob2/LSLASY.npz",allow_pickle=True)["mat"],float)
LCX=np.asarray(np.load("/workspace/uplift_2026-09-11/r2/lob2/LCONVX.npz",allow_pickle=True)["mat"],float)
LIM=np.asarray(np.load("/workspace/uplift_2026-09-11/lob/LOBIMB1.npz",allow_pickle=True)["mat"],float)
END=T(2026,8,10,20)+1
def rz(v):
    ok=np.isfinite(v); o=np.full(len(v),np.nan)
    if ok.sum()>=20: o[ok]=rankdata(v[ok])/max(ok.sum()-1,1)-0.5
    return o
out={}
for nm in ["BTILT","PSKEW","PCURVA","BLEAD"]:
    S=np.where(BASE,np.asarray(np.load("/workspace/uplift_2026-09-11/r5_lob/feat/%s.npz"%nm,allow_pickle=True)["mat"],float),np.nan)
    rec={"coverage":round(float(np.isfinite(S).mean()),4),
         "median_names":float(np.median(np.isfinite(S).sum(1)[np.isfinite(S).sum(1)>0]))}
    Z=np.array([rz(S[i]) for i in range(len(ts))])
    for k in range(-3,4):
        ics=[]
        for i in range(len(ts)):
            j=i+k
            if j<0 or j>=len(ts) or ts[i]>=END: continue
            a=Z[i]; b=Y[j]; ok=np.isfinite(a)&np.isfinite(b)
            if ok.sum()<50: continue
            ics.append(np.corrcoef(a[ok],rankdata(b[ok]))[0,1])
        rec["ic_k%+d"%k]=[round(float(np.mean(ics)),5),round(float(np.std(ics,ddof=1)/np.sqrt(len(ics))),5),len(ics)]
    # cross-sectional rho of the feature RANK to the things it must not be
    for onm,O in [("f_amihud_24h",AMI),("LOB_depth_level_R1MEAN",R1),("LSLASY",LSL),("LCONVX",LCX),("LOBIMB1",LIM)]:
        rr=[]
        for i in range(0,len(ts),7):
            a=Z[i]; b=rz(O[i]); ok=np.isfinite(a)&np.isfinite(b)
            if ok.sum()<50: continue
            rr.append(np.corrcoef(a[ok],b[ok])[0,1])
        rec["xsec_rho_to_"+onm]=round(float(np.mean(rr)),4) if rr else None
    out[nm]=rec; print(nm,json.dumps(rec),flush=True)
json.dump(out,open("/workspace/uplift_2026-09-11/r5_lob/IC_r5.json","w"),indent=1)
