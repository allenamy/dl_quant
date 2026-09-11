"""R8/BUILD-1 auxiliary gates: G5 offset spectrum, G4 concentration (score-layer ruler, verbatim math from
r3_gates/rs_conc.py sha 3fd2f76496a593ba), giveback anchor-level bootstrap, regime-conditional rho."""
import numpy as np, json, calendar, time, sys
from scipy.stats import rankdata
sys.path.insert(0,"/workspace/uplift_2026-09-11/r8_inbook")
R="/workspace/uplift_2026-09-11/r8_inbook"; HC="/workspace/review_scratch/health_check"
B=HC+"/dev_v4/pod_backup_2026-08-21"
MT=np.load(B+"/wide_fea_hist_meta.npz",allow_pickle=True)
E_ts=MT["E_ts"].astype(np.int64); members=MT["members"]; y4=np.asarray(MT["y4"],float); qvk=MT["qvk"]; nA=len(E_ts)
PW=np.load(B+"/wide_panel_4h_hist_v2.npz",allow_pickle=True)
pts=PW["ts"].astype(np.int64); pw_row={int(t):j for j,t in enumerate(pts)}
WSYM=[str(s) for s in PW["symbols"]]; NW=len(WSYM); FE=np.asarray(PW["f_fund_ema_v1"],float)
UM=np.load(HC+"/masks/umask_UPIT_CRYPTO.npz",allow_pickle=True)
umap={int(t):k for k,t in enumerate(UM["ts"].astype(np.int64))}; UMM=np.asarray(UM["mask"])
UROW={j:UMM[umap[int(t)]] for j,t in enumerate(pts) if int(t) in umap}
P=np.load(R+"/parts.npz",allow_pickle=True)
assert np.array_equal(P["ts"].astype(np.int64),pts)
ZF=np.asarray(P["ZF"],float); ORTHF=np.asarray(P["ORTHF"],float); BM=np.asarray(P["BM"],bool)
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FULL_HI=T(2026,8,10,20)
def xz(v):
    ok=np.isfinite(v); out=np.full(len(v),np.nan)
    if ok.sum()>=10: out[ok]=rankdata(v[ok])/max(ok.sum()-1,1)-0.5
    return out
# ---------- m1 member set, exactly as the device builds it ----------
MEM=np.empty(nA,dtype=object)
for i in range(nA):
    q=np.nan_to_num(qvk[i],nan=-1.0); o=np.argsort(-q); o=o[q[o]>-0.5]
    MEM[i]=np.sort(o[:829]).astype(np.int64)
OUT={"read_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
# ---------- G5 offset spectrum on the panel axis ----------
COLS={"CONTROL_FUND":np.where(BM,FE,np.nan),"TILT_ORTHF":np.where(BM,ORTHF,np.nan)}
spec={}
for nm,M in COLS.items():
    row={}
    for k in range(-3,4):
        ic=[]
        for i in range(len(pts)):
            j=i+k
            if j<0 or j>=len(pts): continue
            t=int(pts[i]); r=pw_row.get(t)
            e=np.searchsorted(E_ts,int(pts[j]))
            if e>=nA or E_ts[e]!=int(pts[j]): continue
            m=MEM[e]; mk=UROW.get(pw_row[int(pts[j])]) if int(pts[j]) in pw_row else None
            if mk is not None: m=m[mk[m]]
            v=M[i,m]; yy=y4[e,m]
            ok=np.isfinite(v)&np.isfinite(yy)
            if ok.sum()<50: continue
            a=rankdata(v[ok]); b=rankdata(yy[ok])
            ic.append(float(np.corrcoef(a,b)[0,1]))
        ic=np.array(ic); row["k%+d"%k]={"ic":round(float(ic.mean()),5),"t":round(float(ic.mean()/ic.std(ddof=1)*np.sqrt(len(ic))),2),"n":len(ic)}
    spec[nm]=row
    print("SPEC",nm,json.dumps(row),flush=True)
OUT["offset_spectrum"]=spec
# ---------- G4 concentration, score-layer, ruler math verbatim from rs_conc.py ----------
SIG={"LIVE_FUND":None,"R8A_BLEND_010":R+"/dev/sig/R8A_BLEND_010.npz","R8A_BLEND_050":R+"/dev/sig/R8A_BLEND_050.npz",
     "R8B_OVL_100":R+"/dev/sig/R8B_OVL_100.npz","R8C_GT_025":R+"/dev/sig/R8C_GT_025.npz","TILT_ONLY":None}
WIN={"FULLCYCLE":(int(pts[900]),FULL_HI+1),"GIVEBACK":(T(2026,8,19),T(2026,8,21,20)+1)}
conc={}
for tag,path in SIG.items():
    M=ZF if tag=="LIVE_FUND" else (np.where(BM,ORTHF,np.nan) if tag=="TILT_ONLY" else np.asarray(np.load(path)["mat"],float))
    recs={w:[] for w in WIN}
    for i in range(len(pts)):
        t=int(pts[i]); w=[k for k,(lo,hi) in WIN.items() if lo<=t<hi]
        if not w: continue
        e=np.searchsorted(E_ts,t)
        if e>=nA or E_ts[e]!=t: continue
        m=MEM[e]; mk=UROW.get(i)
        if mk is not None: m=m[mk[m]]
        if len(m)<50: continue
        sc=xz(M[i,:])[m]; yy=y4[e,m]; ok=np.isfinite(yy)
        if ok.sum()<50 or not np.isfinite(sc).any(): continue
        z=np.nan_to_num(sc); z=np.where(ok,z,0.0); z=z-z[ok].mean(); g=np.abs(z).sum()
        if g<=1e-9: continue
        c=(z/g)*np.nan_to_num(yy,nan=0.0)*1e4
        tot=float(c.sum()); o=np.argsort(-np.abs(c))
        for ww in w: recs[ww].append((tot,float(c[o[:5]].sum()),float(c[o[:20]].sum()),len(m)))
    conc[tag]={}
    for w,v in recs.items():
        if len(v)<5: continue
        A=np.array(v); tot=A[:,0].mean()
        conc[tag][w]={"n":len(v),"leg_ret_bps":round(float(tot),4),
          "top5_share":round(float(A[:,1].mean()/tot),4),"top20_share":round(float(A[:,2].mean()/tot),4),
          "ex_top20_bps":round(float((A[:,0]-A[:,2]).mean()),4),
          "ex_top20_sharpe":round(float((A[:,0]-A[:,2]).mean()/(A[:,0]-A[:,2]).std(ddof=1)*np.sqrt(2190)),3)}
        print("CONC",tag,w,json.dumps(conc[tag][w]),flush=True)
OUT["concentration"]=conc
json.dump(OUT,open(R+"/AUX.json","w"),indent=1)
print("AUX_DONE")
