"""R8 aux2: (a) G5 offset spectrum with nan-robust aggregation (aux.py used plain mean and a handful of
all-zero pre-coverage rows poisoned it); (b) concentration on the EXACT rs_conc.py member set + windows,
so the live-fund control reproduces the pinned 0.1109 / +6.709 before my arms are read on the same ruler."""
import numpy as np, json, calendar, time
from scipy.stats import rankdata
R="/workspace/uplift_2026-09-11/r8_inbook"; HC="/workspace/review_scratch/health_check"
B=HC+"/dev_v4/pod_backup_2026-08-21"
MT=np.load(B+"/wide_fea_hist_meta.npz",allow_pickle=True)
E_ts=MT["E_ts"].astype(np.int64); members=MT["members"]; y4=np.asarray(MT["y4"],float); nA=len(E_ts)
PW=np.load(B+"/wide_panel_4h_hist_v2.npz",allow_pickle=True)
pts=PW["ts"].astype(np.int64); pw_row={int(t):j for j,t in enumerate(pts)}
FE=np.asarray(PW["f_fund_ema_v1"],float)
UM=np.load(HC+"/masks/umask_UPIT_CRYPTO.npz",allow_pickle=True)
umap={int(t):k for k,t in enumerate(UM["ts"].astype(np.int64))}; UMM=np.asarray(UM["mask"])
UROW={j:UMM[umap[int(t)]] for j,t in enumerate(pts) if int(t) in umap}
P=np.load(R+"/parts.npz",allow_pickle=True)
ZF=np.asarray(P["ZF"],float); ORTHF=np.asarray(P["ORTHF"],float); BM=np.asarray(P["BM"],bool)
ZB=np.asarray(P["ZB"],float)
def xz(v):
    ok=np.isfinite(v); out=np.full(len(v),np.nan)
    if ok.sum()>=10: out[ok]=rankdata(v[ok])/max(ok.sum()-1,1)-0.5
    return out
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
OUT={"read_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
# ---- (a) offset spectrum, nan-robust ----
COLS={"CONTROL_FUND":np.where(BM,FE,np.nan),"RAW_ZB(basis, declared sign)":np.where(BM,ZB,np.nan),
      "TILT_ORTHF(flipped, traded sign)":np.where(BM,ORTHF,np.nan)}
spec={}
for nm,M in COLS.items():
    row={}
    for k in range(-3,4):
        ic=[]
        for i in range(len(pts)):
            j=i+k
            if j<0 or j>=len(pts): continue
            tj=int(pts[j]); e=np.searchsorted(E_ts,tj)
            if e>=nA or E_ts[e]!=tj: continue
            m=np.asarray(members[e],np.int64); mk=UROW.get(pw_row[tj])
            if mk is not None: m=m[mk[m]]
            if len(m)<50: continue
            v=M[i,m]; yy=y4[e,m]; ok=np.isfinite(v)&np.isfinite(yy)
            if ok.sum()<50: continue
            vv=v[ok]
            if np.nanstd(vv)<=0: continue
            ic.append(float(np.corrcoef(rankdata(vv),rankdata(yy[ok]))[0,1]))
        ic=np.array(ic); ic=ic[np.isfinite(ic)]
        row["k%+d"%k]={"ic":round(float(ic.mean()),5),"t":round(float(ic.mean()/ic.std(ddof=1)*np.sqrt(len(ic))),2),"n":int(len(ic))}
    spec[nm]=row; print("SPEC",nm,json.dumps(row),flush=True)
OUT["offset_spectrum"]=spec
# ---- (b) concentration, rs_conc.py member set + windows (calibration vs pinned control) ----
WIN={"pre2025":(T(2023,1,1),T(2025,1,1)),"2025on":(T(2025,1,1),T(2026,8,10,20)+1),
     "GIVEBACK":(T(2026,8,19),T(2026,8,21,20)+1)}
SIG={"LIVE_FUND":None,"TILT_ONLY":"T","R8A_BLEND_010":R+"/dev/sig/R8A_BLEND_010.npz",
     "R8A_BLEND_050":R+"/dev/sig/R8A_BLEND_050.npz","R8C_GT_025":R+"/dev/sig/R8C_GT_025.npz"}
conc={}
for tag,path in SIG.items():
    M=ZF if path is None else (np.where(BM,ORTHF,np.nan) if path=="T" else np.asarray(np.load(path)["mat"],float))
    recs={w:[] for w in WIN}
    for i in range(len(pts)):
        t=int(pts[i]); ws=[k for k,(lo,hi) in WIN.items() if lo<=t<hi]
        if not ws: continue
        e=np.searchsorted(E_ts,t)
        if e>=nA or E_ts[e]!=t: continue
        m=np.asarray(members[e],np.int64); mk=UROW.get(i)
        if mk is not None: m=m[mk[m]]
        if len(m)<50: continue
        sc=xz(M[i,:])[m]; yy=y4[e,m]; ok=np.isfinite(yy)
        if ok.sum()<50 or not np.isfinite(sc).any(): continue
        z=np.nan_to_num(sc); z=np.where(ok,z,0.0); z=z-z[ok].mean(); g=np.abs(z).sum()
        if g<=1e-9: continue
        c=(z/g)*np.nan_to_num(yy,nan=0.0)*1e4
        tot=float(c.sum()); o=np.argsort(-np.abs(c))
        for w in ws: recs[w].append((tot,float(c[o[:5]].sum()),float(c[o[:20]].sum()),len(m)))
    conc[tag]={}
    for w,v in recs.items():
        if len(v)<5: continue
        A=np.array(v); tot=A[:,0].mean()
        conc[tag][w]={"n":len(v),"leg_ret_bps":round(float(tot),4),"mean_names":round(float(A[:,3].mean()),1),
          "top5_share":round(float(A[:,1].mean()/tot),4),"top20_share":round(float(A[:,2].mean()/tot),4),
          "ex_top20_bps":round(float((A[:,0]-A[:,2]).mean()),4),
          "ex_top20_sharpe":round(float((A[:,0]-A[:,2]).mean()/(A[:,0]-A[:,2]).std(ddof=1)*np.sqrt(2190)),3)}
        print("CONC",tag,w,json.dumps(conc[tag][w]),flush=True)
OUT["concentration_rsconc_member_set"]=conc
json.dump(OUT,open(R+"/AUX2.json","w"),indent=1)
print("AUX2_DONE")
