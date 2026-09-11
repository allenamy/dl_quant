"""R5/ND1: tail-concentration ruler. VERBATIM the construction of r3_gates/rs_conc.py (sha 3fd2f749...),
only the score matrix is mine.  Control = the live fund leg (reads 11.09% / +6.71 in the round-3 receipt)."""
import numpy as np, calendar, json, glob, os, sys
from scipy.stats import rankdata
HC="/workspace/review_scratch/health_check"; B=HC+"/dev_v4/pod_backup_2026-08-21"
R="/workspace/uplift_2026-09-11/r5_basis"
MT=np.load(f"{B}/wide_fea_hist_meta.npz",allow_pickle=True)
E_ts=MT["E_ts"].astype(np.int64); members=MT["members"]; y4=np.asarray(MT["y4"],float); nA=len(E_ts)
PW=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True)
pts=PW["ts"].astype(np.int64); pw_row={int(t):j for j,t in enumerate(pts)}
WSYM=[str(s) for s in PW["symbols"]]; NW=len(WSYM); FE=np.asarray(PW["f_fund_ema_v1"],float)
UM=np.load(HC+"/masks/umask_UPIT_CRYPTO.npz",allow_pickle=True)
umap={int(t):k for k,t in enumerate(UM["ts"].astype(np.int64))}; UMM=np.asarray(UM["mask"])
UROW={j:UMM[umap[int(t)]] for j,t in enumerate(pts) if int(t) in umap}
def xz(v):
    ok=np.isfinite(v); out=np.full(len(v),np.nan)
    if ok.sum()>=10: out[ok]=rankdata(v[ok])/max(ok.sum()-1,1)-0.5
    return out
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
WIN={"fullcycle":(T(2022,1,1),T(2026,8,10,20)+1),"pre2025":(T(2023,1,1),T(2025,1,1)),"2025on":(T(2025,1,1),T(2026,8,10,20)+1)}
ARMS={"LIVE_FUND":None}
for p in sorted(glob.glob(R+"/dev/sig/R5_*.npz")):
    ARMS[os.path.basename(p)[:-4]]=p
out={}
for tag,path in ARMS.items():
    S=None
    if path:
        Z=np.load(path,allow_pickle=True); assert np.array_equal(Z["ts"].astype(np.int64),pts)
        SM=np.asarray(Z["mat"],float); S={int(t):SM[k] for k,t in enumerate(pts)}
    recs={w:[] for w in WIN}
    for i in range(nA):
        j=pw_row.get(int(E_ts[i]))
        if j is None: continue
        t=int(E_ts[i]); w=[k for k,(lo,hi) in WIN.items() if lo<=t<hi]
        if not w: continue
        m=members[i]; mk=UROW.get(j)
        if mk is not None: m=m[mk[m]]
        if len(m)<50: continue
        sc=xz(FE[j,:])[m] if S is None else xz(S[t])[m]
        yy=y4[i,m]; ok=np.isfinite(yy)
        if ok.sum()<50 or not np.isfinite(sc).any(): continue
        z=np.nan_to_num(sc); z=np.where(ok,z,0.0); z=z-z[ok].mean(); g=np.abs(z).sum()
        if g<=1e-9: continue
        c=(z/g)*np.nan_to_num(yy,nan=0.0)*1e4
        tot=float(c.sum()); o=np.argsort(-np.abs(c))
        for ww in w: recs[ww].append((tot,float(c[o[:5]].sum()),float(c[o[:20]].sum()),int(len(m))))
    out[tag]={}
    for w,v in recs.items():
        if len(v)<10: continue
        A=np.array(v); tot=A[:,0].mean()
        out[tag][w]={"n_anchors":len(v),"leg_ret_bps":round(float(tot),4),"mean_names":round(float(A[:,3].mean()),1),
          "top5_share_of_mean":round(float(A[:,1].mean()/tot),4),"top20_share_of_mean":round(float(A[:,2].mean()/tot),4),
          "ex_top20_bps":round(float((A[:,0]-A[:,2]).mean()),4),
          "ex_top20_sharpe":round(float((A[:,0]-A[:,2]).mean()/(A[:,0]-A[:,2]).std(ddof=1)*np.sqrt(2190)),3)}
    print(tag,json.dumps(out[tag]),flush=True)
json.dump(out,open(R+"/CONCENTRATION.json","w"),indent=1)
print("CONC_DONE")
