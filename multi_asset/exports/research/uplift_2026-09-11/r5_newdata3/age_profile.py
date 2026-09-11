"""r5nd/age_profile.py -- DESCRIPTIVE (not an admission test): what listing age does to the fund leg.
Grid = the device's own evaluation grid (meta E_ts, members, y4, qvk from the v4 meta the gate-P recipe
links as wide_fea_hist_meta.npz), member set narrowed by the A0 mask exactly as rs_conc.py does.
Caliber: y4 is the pod 5m lineage sum-of-simple-5m-returns (E-0904-F); rank-IC is invariant to that choice.
Outputs r5nd/age_profile.json"""
import numpy as np, json, time, calendar
from scipy.stats import rankdata
R="/workspace/uplift_2026-09-11/r5nd"; HC="/workspace/review_scratch/health_check"
B=HC+"/dev_v4/pod_backup_2026-08-21"
MT=np.load(f"{B}/wide_fea_hist_meta.npz",allow_pickle=True)
E_ts=MT["E_ts"].astype(np.int64); members=MT["members"]; y4=np.asarray(MT["y4"],float); qvk=np.asarray(MT["qvk"],float)
nA=len(E_ts)
PW=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True)
pts=PW["ts"].astype(np.int64); pw_row={int(t):j for j,t in enumerate(pts)}
WSYM=[str(s) for s in PW["symbols"]]; NW=len(WSYM)
FE=np.asarray(PW["f_fund_ema_v1"],float); FN=np.asarray(PW["f_fund_now"],float)
IV=np.asarray(PW["f_fund_iv"],float) if "f_fund_iv" in PW else np.full_like(FN,8.0)
RN8=FN*(8.0/np.where(np.isfinite(IV)&(IV>0),IV,8.0))
UM=np.load(R+"/masks/umask_R5_MONTHLY449.npz",allow_pickle=True)
assert [str(s) for s in UM["symbols"]]==WSYM
umap={int(t):k for k,t in enumerate(UM["ts"].astype(np.int64))}; UMM=np.asarray(UM["mask"])
AG=np.load(R+"/agemat.npz",allow_pickle=True); AGE=np.asarray(AG["age_days"],float)
assert np.array_equal(AG["ts"].astype(np.int64),pts)
def xz(v):
    ok=np.isfinite(v); out=np.full(len(v),np.nan)
    if ok.sum()>=10: out[ok]=rankdata(v[ok])/max(ok.sum()-1,1)-0.5
    return out
BUCK=[(0,90,"<90d"),(90,180,"90-180d"),(180,365,"180-365d"),(365,730,"1-2y"),(730,1e9,">2y")]
YRS=sorted(set(time.gmtime(int(t)).tm_year for t in E_ts))
acc={}   # (year,bucket) -> lists
ic_rows={}   # (year,bucket) -> per-anchor ic of fund score vs y4 within the bucket
qv4h_all=np.expm1(np.clip(np.nan_to_num(qvk,nan=0.0),0,30))*48
for i in range(nA):
    t=int(E_ts[i]); j=pw_row.get(t)
    if j is None: continue
    y=time.gmtime(t).tm_year
    m=members[i]; mk=UMM[umap[t]] if t in umap else None
    if mk is not None: m=m[mk[m]]
    if len(m)<50: continue
    a=AGE[j,m]; yy=y4[i,m]; rn=RN8[j,m]; fe=FE[j,m]; qv=qv4h_all[i,m]
    liq=(qv>=2.5e5)
    for lo,hi,nm in BUCK:
        sel=(a>=lo)&(a<hi)&liq
        if sel.sum()<3: continue
        k=(y,nm); d=acc.setdefault(k,{"n":[],"y4":[],"rn8":[],"deepneg":[],"qv4h":[]})
        d["n"].append(int(sel.sum())); d["y4"].append(float(np.nanmean(yy[sel])))
        d["rn8"].append(float(np.nanmean(rn[sel]))); d["deepneg"].append(float(np.nanmean(rn[sel]<=-0.0010)))
        d["qv4h"].append(float(np.nanmedian(qv[sel])))
        okf=sel&np.isfinite(fe)&np.isfinite(yy)
        if okf.sum()>=10:
            r1=rankdata(fe[okf]); r2=rankdata(yy[okf])
            ic=float(np.corrcoef(r1,r2)[0,1])
            ic_rows.setdefault(k,[]).append(ic)
out={"buckets":{}}
for y in YRS:
    for lo,hi,nm in BUCK:
        k=(y,nm)
        if k not in acc: continue
        d=acc[k]; ics=ic_rows.get(k,[])
        out["buckets"]["%d|%s"%(y,nm)]={
            "anchors":len(d["n"]),"names_mean":round(float(np.mean(d["n"])),1),
            "y4_mean_bps":round(float(np.mean(d["y4"]))*1e4,3),
            "rn8_mean_bps":round(float(np.mean(d["rn8"]))*1e4,3),
            "deepneg_share":round(float(np.mean(d["deepneg"])),4),
            "qv4h_median_usd":round(float(np.median(d["qv4h"])),0),
            "fund_rankIC":round(float(np.mean(ics)),4) if ics else None,
            "fund_rankIC_n":len(ics)}
# ---- forward vs backward rank-IC spectrum of the AGE signal, k = -3..+3 ----
spec={}
for tag,MAT,sgn in (("AGE_young",AGE,-1.0),("FUND_EMA",FE,1.0)):
    row={}
    for kk in range(-3,4):
        vals=[]
        for i in range(nA):
            t=int(E_ts[i]); j=pw_row.get(t)
            if j is None: continue
            i2=i+kk
            if i2<0 or i2>=nA: continue
            if int(E_ts[i2])-t != kk*14400: continue
            m=members[i]; mk=UMM[umap[t]] if t in umap else None
            if mk is not None: m=m[mk[m]]
            if len(m)<50: continue
            s=sgn*MAT[j,m]; yy=y4[i2,m]
            ok=np.isfinite(s)&np.isfinite(yy)
            if ok.sum()<50: continue
            vals.append(float(np.corrcoef(rankdata(s[ok]),rankdata(yy[ok]))[0,1]))
        row[str(kk)]={"rankIC":round(float(np.mean(vals)),5),"n":len(vals)} if vals else None
    spec[tag]=row
out["ic_spectrum_k_minus3_to_plus3"]=spec
out["caliber"]={"grid":"meta E_ts / members, A0 mask MONTHLY449, liq qv4h>=2.5e5",
                "y4":"pod 5m lineage, sum of 5m simple returns (E-0904-F)","ic":"Spearman via rankdata"}
json.dump(out,open(R+"/age_profile.json","w"),indent=1)
for k,v in out["buckets"].items(): print(k,json.dumps(v),flush=True)
print("SPECTRUM",json.dumps(spec),flush=True)
print("AGE_PROFILE_DONE")
