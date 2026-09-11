"""R5/ND1: offset spectrum of rank-IC, k=-3..+3, plus a LOOKAHEAD POSITIVE CONTROL.
k = 0 is the tradeable read: signal built from bars closing <= E, y4 spans [E, E+4h).
k < 0 = BACKWARD (returns already realised before E).  k > 0 = further forward.
Positive control ADV1: the same column read from anchor i+1 (i.e. deliberately 4h of lookahead).
If the instrument cannot see that, it cannot see leakage either."""
import numpy as np, json
from scipy.stats import rankdata
R="/workspace/uplift_2026-09-11/r5_basis"
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
ts=PW["ts"].astype(np.int64); sym=[str(s) for s in PW["symbols"]]
FE1=np.asarray(PW["f_fund_ema_v1"],float); BM=np.isfinite(FE1)
FN=np.asarray(PW["f_fund_now"],float)
MT=np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz",allow_pickle=True)
E=MT["E_ts"].astype(np.int64); members=MT["members"]; y4=np.asarray(MT["y4"],float)
emap={int(t):i for i,t in enumerate(E)}
UM=np.load("/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz",allow_pickle=True)
umap={int(t):k for k,t in enumerate(UM["ts"].astype(np.int64))}; UMM=np.asarray(UM["mask"])
BP=np.load(R+"/basis_panel.npz",allow_pickle=True)
p_last=np.asarray(BP["p_last"],float); p_tw24=np.asarray(BP["p_tw24"],float)
p_sd8=np.asarray(BP["p_sd8"],float); p_tw_iv=np.asarray(BP["p_tw_iv"],float)
COL={"BLEVEL":p_last.copy(),"BGAPF":p_last-FN,"BGAPT":p_last-p_tw_iv,"BSLOPE":p_last-p_tw24,"BDISP":p_sd8,
     "CONTROL_FUND":FE1,"CONTROL_PLAST":p_last}
def sp(a,b):
    ok=np.isfinite(a)&np.isfinite(b)
    if ok.sum()<30: return np.nan
    x=rankdata(a[ok]); y=rankdata(b[ok])
    sx=x.std(); sy=y.std()
    if sx<1e-12 or sy<1e-12: return np.nan
    return float(((x-x.mean())*(y-y.mean())).mean()/(sx*sy))
OUT={}
for nm,M in COL.items():
    res={}
    for k in (-3,-2,-1,0,1,2,3):
        v=[]
        for i in range(len(ts)):
            j=emap.get(int(ts[i])+k*14400)
            if j is None: continue
            m=members[j]
            mk=UMM[umap[int(ts[i])+k*14400]] if int(ts[i])+k*14400 in umap else None
            if mk is not None: m=m[mk[m]]
            if len(m)<50: continue
            a=np.where(BM[i,m],M[i,m],np.nan); b=y4[j,m]
            r=sp(a,b)
            if np.isfinite(r): v.append(r)
        res["k=%+d"%k]={"n":len(v),"mean_IC":round(float(np.mean(v)),6),
                        "t":round(float(np.mean(v)/(np.std(v,ddof=1)/np.sqrt(len(v)))),2) if len(v)>10 else None}
    # positive control: read the column one anchor AHEAD (4h of deliberate lookahead)
    v=[]
    for i in range(len(ts)-1):
        j=emap.get(int(ts[i]))
        if j is None: continue
        m=members[j]
        mk=UMM[umap[int(ts[i])]] if int(ts[i]) in umap else None
        if mk is not None: m=m[mk[m]]
        if len(m)<50: continue
        r=sp(np.where(BM[i+1,m],M[i+1,m],np.nan),y4[j,m])
        if np.isfinite(r): v.append(r)
    res["ADV1_lookahead_control"]={"n":len(v),"mean_IC":round(float(np.mean(v)),6),
        "t":round(float(np.mean(v)/(np.std(v,ddof=1)/np.sqrt(len(v)))),2) if len(v)>10 else None}
    OUT[nm]=res; print(nm,json.dumps(res),flush=True)
json.dump(OUT,open(R+"/IC_SPECTRUM.json","w"),indent=1)
print("IC_DONE")
