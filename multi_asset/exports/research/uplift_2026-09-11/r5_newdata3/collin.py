"""r5nd/collin.py -- is the listing-age sleeve NEW INFORMATION, or the round-4 Amihud sleeve restated?
(a) cross-sectional rank correlation of the young rank ZY against the Amihud rank ZA and log_qv, per year,
    on the A0 member set;  (b) g-series correlation of my SL_AGE50 arm to the round-4 XIB arm;
(c) the age signal's forward/backward rank-IC spectrum at k=-3..+3 (nanmean; anchors where the member ages
    are all tied produce an undefined IC and are excluded, with the count reported)."""
import numpy as np, json, time
from scipy.stats import rankdata
R="/workspace/uplift_2026-09-11/r5nd"; HC="/workspace/review_scratch/health_check"
B=HC+"/dev_v4/pod_backup_2026-08-21"
MT=np.load(f"{B}/wide_fea_hist_meta.npz",allow_pickle=True)
E_ts=MT["E_ts"].astype(np.int64); members=MT["members"]; y4=np.asarray(MT["y4"],float); nA=len(E_ts)
PW=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True)
pts=PW["ts"].astype(np.int64); pw_row={int(t):j for j,t in enumerate(pts)}
WSYM=[str(s) for s in PW["symbols"]]
AM=np.asarray(PW["f_amihud_24h"],float); FE=np.asarray(PW["f_fund_ema_v1"],float)
AG=np.load(R+"/agemat.npz",allow_pickle=True); AGE=np.asarray(AG["age_days"],float)
UM=np.load(R+"/masks/umask_R5_MONTHLY449.npz",allow_pickle=True)
umap={int(t):k for k,t in enumerate(UM["ts"].astype(np.int64))}; UMM=np.asarray(UM["mask"])
def rk(v):
    ok=np.isfinite(v); out=np.full(len(v),np.nan)
    if ok.sum()>=10: out[ok]=rankdata(v[ok])/max(ok.sum()-1,1)-0.5
    return out
def sp(a,b):
    ok=np.isfinite(a)&np.isfinite(b)
    if ok.sum()<20: return np.nan
    x,y=rankdata(a[ok]),rankdata(b[ok])
    if x.std()==0 or y.std()==0: return np.nan
    return float(np.corrcoef(x,y)[0,1])
yrs=np.array([time.gmtime(int(t)).tm_year for t in E_ts])
acc={}
for i in range(nA):
    t=int(E_ts[i]); j=pw_row.get(t)
    if j is None: continue
    m=members[i]; mk=UMM[umap[t]] if t in umap else None
    if mk is not None: m=m[mk[m]]
    if len(m)<50: continue
    y=yrs[i]; d=acc.setdefault(y,{"age_vs_amihud":[],"age_vs_fund":[],"amihud_vs_fund":[],"tied_age":0,"n":0})
    a=-AGE[j,m]
    d["age_vs_amihud"].append(sp(a,AM[j,m])); d["age_vs_fund"].append(sp(a,FE[j,m]))
    d["amihud_vs_fund"].append(sp(AM[j,m],FE[j,m])); d["n"]+=1
    if np.nanstd(a)==0: d["tied_age"]+=1
out={"cross_sectional_rank_corr_on_A0_members":{}}
for y in sorted(acc):
    d=acc[y]
    out["cross_sectional_rank_corr_on_A0_members"][str(y)]={
        "anchors":d["n"],
        "rho_young_vs_amihud":round(float(np.nanmean(d["age_vs_amihud"])),4),
        "rho_young_vs_fundEMA":round(float(np.nanmean(d["age_vs_fund"])),4),
        "rho_amihud_vs_fundEMA":round(float(np.nanmean(d["amihud_vs_fund"])),4),
        "anchors_with_all_ages_tied":d["tied_age"]}
# (c) IC spectrum for the young signal, nanmean
spec={}
for tag,MAT,sgn in (("AGE_young",AGE,-1.0),("AMIHUD",AM,1.0),("FUND_EMA",FE,1.0)):
    row={}
    for kk in range(-3,4):
        vals=[]
        for i in range(nA):
            t=int(E_ts[i]); j=pw_row.get(t)
            if j is None: continue
            i2=i+kk
            if i2<0 or i2>=nA or int(E_ts[i2])-t!=kk*14400: continue
            m=members[i]; mk=UMM[umap[t]] if t in umap else None
            if mk is not None: m=m[mk[m]]
            if len(m)<50: continue
            v=sp(sgn*MAT[j,m],y4[i2,m])
            if np.isfinite(v): vals.append(v)
        row[str(kk)]={"rankIC":round(float(np.mean(vals)),5),"n_anchors_defined":len(vals)}
    spec[tag]=row
out["ic_spectrum_k_minus3_to_plus3"]=spec
# (b) g-series correlation vs the round-4 arms
def gser(p):
    Z=np.load(p,allow_pickle=True); Rr=np.asarray(Z["rec"],float); ix={str(c):i for i,c in enumerate(Z["cols"])}
    ts=Rr[:,ix["ts"]].astype(np.int64)
    g=np.where(Rr[:,ix["gross_total"]]>0,Rr[:,ix["net_ex"]]/np.maximum(Rr[:,ix["gross_total"]],1e-12),np.nan)
    m=np.isfinite(g); m[:900]=False; return ts[m],g[m]
pairs={}
for seat in ("dyn","fix"):
  for sd in ("42","2027"):
    a=gser(R+"/arms/R5S_SL_AGE50_%s_s%s.npz"%(seat,sd))
    for nm,p in (("A0",R+"/arms/R5U_A0M_%s_s%s.npz"%(seat,sd)),
                 ("XIB_r4","/workspace/uplift_2026-09-11/r4_p1/arms/R4B1_XIB_%s_s%s.npz"%(seat,sd))):
        b=gser(p); ts=np.intersect1d(a[0],b[0])
        x=a[1][np.searchsorted(a[0],ts)]; y=b[1][np.searchsorted(b[0],ts)]
        pairs["SL_AGE50|%s|%s|s%s"%(nm,seat,sd)]={"n":int(len(ts)),"rho":round(float(np.corrcoef(x,y)[0,1]),4)}
out["g_series_corr"]=pairs
json.dump(out,open(R+"/collin_r5.json","w"),indent=1)
print(json.dumps(out,indent=1))
