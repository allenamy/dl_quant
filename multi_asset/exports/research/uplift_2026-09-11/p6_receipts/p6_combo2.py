"""P6 step 4b: PAIRED bootstrap of the Sharpe DIFFERENCE SR(combo) - SR(A0), same UTC-day blocks resampled
for both series (the level CI in P6_COMBO.json is not the right statistic for a paired gain)."""
import numpy as np, json, calendar
APY=2190; WARM=900
P6="/workspace/uplift_2026-09-11/p6/arms"; R3K="/workspace/uplift_2026-09-11/r3k/arms"
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FULL_HI=T(2026,8,10,20)+1; FROZ_LO=T(2025,3,1)
def load(p):
    Z=np.load(p,allow_pickle=True); cols=[str(c) for c in Z["cols"]]; ix={c:i for i,c in enumerate(cols)}
    Rr=np.asarray(Z["rec" if "rec" in Z.files else "d30_n2_c42_rec"],float)[WARM:]
    ts=np.round(Rr[:,ix["ts"]]).astype(np.int64); m=ts<FULL_HI
    return ts[m],(Rr[:,ix["net_ex"]]/Rr[:,ix["gross_total"]])[m]
def sr(x): return float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(APY))
def paired(A,S,days,a,k,B=2000):
    rng=np.random.default_rng([20260905,k]); ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    order=np.argsort(inv,kind="stable"); Ao=A[order]; So=S[order]; io=inv[order]
    st=np.searchsorted(io,np.arange(nd)); en=np.append(st[1:],len(io))
    idx=rng.integers(0,nd,size=(B,nd)); out=np.empty(B); outg=np.empty(B)
    for b in range(B):
        sl=idx[b]; av=np.concatenate([Ao[st[j]:en[j]] for j in sl]); sv=np.concatenate([So[st[j]:en[j]] for j in sl])
        cv=(1-a)*av+a*sv
        out[b]=sr(cv)-sr(av); outg[b]=cv.mean()-av.mean()
    return ([float(np.percentile(out,2.5)),float(np.percentile(out,97.5))],float((out>0).mean()),
            [float(np.percentile(outg,2.5)),float(np.percentile(outg,97.5))],float((outg>0).mean()))
OUT={}
for seed in ("42","2027"):
    ta,A=load("%s/A0_PWR230k_s%s.npz"%(R3K,seed)); tb,S=load("%s/w10_ablation_series_P6_AMQ64_PWR_s%s.npz"%(P6,seed))
    com,ia,ib=np.intersect1d(ta,tb,return_indices=True); A=A[ia]; S=S[ib]; days=com//86400; fz=com>=FROZ_LO
    D={}
    for a in (0.20,0.30,0.40,0.50):
        r={}
        for k in (0,9):
            ci,p,cig,pg=paired(A,S,days,a,k)
            r["k%d"%k]={"dSR_ci95":ci,"P_dSR>0":p,"dg_ci95":cig,"P_dg>0":pg}
        r["dSR_point"]=sr((1-a)*A+a*S)-sr(A)
        r["dg_point"]=float((((1-a)*A+a*S)-A).mean())
        # frozen window, same statistic
        ciF,pF,_,_=paired(A[fz],S[fz],days[fz],a,0)
        r["frozen_dSR_ci95_k0"]=ciF; r["frozen_P_dSR>0"]=pF
        r["frozen_dSR_point"]=sr((1-a)*A[fz]+a*S[fz])-sr(A[fz])
        D["%.2f"%a]=r
        print(seed,a,json.dumps(r),flush=True)
    OUT["s"+seed]=D
json.dump(OUT,open("/workspace/uplift_2026-09-11/p6/P6_COMBO_PAIRED.json","w"),indent=1)
print("PAIRED_DONE")
