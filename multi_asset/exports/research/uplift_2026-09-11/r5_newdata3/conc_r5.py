"""r5nd/conc_r5.py -- tail-concentration ruler, structure copied VERBATIM from
/workspace/uplift_2026-09-11/r3_gates/rs_conc.py (sha 3fd2f76496a593ba); only the ARMS dict differs
(the age signal and the AGE50 blend replace RESID_SHARPE). Control = the live fund leg (LIVE_FUND).
Reference readings from round 3: live fund leg 11.09% top-20 share / +6.71 ex-top-20 Sharpe;
RESID_SHARPE 130-189% / -2.40..-5.60 (died)."""
import numpy as np, calendar, json
from scipy.stats import rankdata
HC="/workspace/review_scratch/health_check"; B=HC+"/dev_v4/pod_backup_2026-08-21"
R5="/workspace/uplift_2026-09-11/r5nd"
MT=np.load(f"{B}/wide_fea_hist_meta.npz",allow_pickle=True)
E_ts=MT["E_ts"].astype(np.int64); members=MT["members"]; y4=np.asarray(MT["y4"],float); nA=len(E_ts)
PW=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True)
pts=PW["ts"].astype(np.int64); pw_row={int(t):j for j,t in enumerate(pts)}
WSYM=[str(s) for s in PW["symbols"]]; NW=len(WSYM); FE=np.asarray(PW["f_fund_ema_v1"],float)
UM=np.load(R5+"/masks/umask_R5_MONTHLY449.npz",allow_pickle=True)
umap={int(t):k for k,t in enumerate(UM["ts"].astype(np.int64))}; UMM=np.asarray(UM["mask"])
UROW={j:UMM[umap[int(t)]] for j,t in enumerate(pts) if int(t) in umap}
AG=np.load(R5+"/agemat.npz",allow_pickle=True); AGE=np.asarray(AG["age_days"],float)
def xz(v):
    ok=np.isfinite(v); out=np.full(len(v),np.nan)
    if ok.sum()>=10: out[ok]=rankdata(v[ok])/max(ok.sum()-1,1)-0.5
    return out
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
WIN={"pre2025":(T(2023,1,1),T(2025,1,1)),"2025on":(T(2025,1,1),T(2026,8,10,20)+1)}
ZFm=np.where(np.isfinite(FE),FE,np.nan)
def score_of(tag,j,m):
    if tag=="LIVE_FUND": return xz(FE[j,:])[m]
    if tag=="AGE_YOUNG": return xz(-AGE[j,:])[m]
    if tag=="SL_AGE50":
        b=np.isfinite(FE[j,:]); a=np.where(b,-AGE[j,:],np.nan)
        s=0.5*xz(np.where(b,FE[j,:],np.nan))+0.5*xz(a); return s[m]
    raise ValueError(tag)
out={}
for tag in ("LIVE_FUND","AGE_YOUNG","SL_AGE50"):
    recs={w:[] for w in WIN}
    for i in range(nA):
        j=pw_row.get(int(E_ts[i]))
        if j is None: continue
        t=int(E_ts[i]); w=[k for k,(lo,hi) in WIN.items() if lo<=t<hi]
        if not w: continue
        m=members[i]; mk=UROW.get(j)
        if mk is not None: m=m[mk[m]]
        if len(m)<50: continue
        sc=score_of(tag,j,m); yy=y4[i,m]; ok=np.isfinite(yy)
        if ok.sum()<50 or not np.isfinite(sc).any(): continue
        z=np.nan_to_num(sc); z=np.where(ok,z,0.0); z=z-z[ok].mean(); g=np.abs(z).sum()
        if g<=1e-9: continue
        c=(z/g)*np.nan_to_num(yy,nan=0.0)*1e4
        tot=float(c.sum()); o=np.argsort(-np.abs(c))
        recs[w[0]].append((tot,float(c[o[:5]].sum()),float(c[o[:20]].sum()),int(len(m))))
    out[tag]={}
    for w,v in recs.items():
        if len(v)<10: continue
        A=np.array(v); tot=A[:,0].mean()
        out[tag][w]={"n_anchors":len(v),"leg_ret_bps":round(float(tot),4),"mean_names":round(float(A[:,3].mean()),1),
            "top5_share_of_mean":round(float(A[:,1].mean()/tot),4),"top20_share_of_mean":round(float(A[:,2].mean()/tot),4),
            "ex_top5_bps":round(float((A[:,0]-A[:,1]).mean()),4),"ex_top20_bps":round(float((A[:,0]-A[:,2]).mean()),4),
            "ex_top20_sharpe":round(float((A[:,0]-A[:,2]).mean()/(A[:,0]-A[:,2]).std(ddof=1)*np.sqrt(2190)),3)}
        print(tag,w,json.dumps(out[tag][w]),flush=True)
json.dump(out,open(R5+"/conc_r5.json","w"),indent=1)
print("CONC_DONE")
