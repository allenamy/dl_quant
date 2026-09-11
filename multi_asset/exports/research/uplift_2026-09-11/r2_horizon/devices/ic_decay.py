"""SIGNAL LAYER (not the book layer). Forward rank-IC decay of 1h/4h features over the next 4h,
in 5-minute resolution, so the 1h-clock question can be priced. Also the k=0,-1,-2 offset spectrum."""
import numpy as np, sys, calendar, time
from scipy.stats import rankdata
sys.path.insert(0,"/workspace/uplift_2026-09-11/r2_horizon")
R="/workspace/uplift_2026-09-11/r2_horizon"
B="/workspace/review_scratch/health_check/dev_v4/pod_backup_2026-08-21"
PW=np.load(B+"/wide_panel_4h_hist_v2.npz",allow_pickle=True)
TS=PW["ts"].astype(np.int64)
F=np.load(R+"/feats_r2.npz",allow_pickle=True)
FE1=np.asarray(PW["f_fund_ema_v1"],np.float64); BASE=np.isfinite(FE1)
z=np.load("/workspace/data/dlnative_5m_wide829_f16_holefix2.npz",allow_pickle=True)
ts5=z["ts"].astype(np.int64); ch=[str(c) for c in z["ch"]]
pos={int(t):k for k,t in enumerate(ts5)}
K=np.array([pos[int(t)] for t in TS])
D=z["data"][:,:,ch.index("ret5")].astype(np.float32)
CS=np.vstack([np.zeros((1,D.shape[1])),np.cumsum(np.nan_to_num(D,nan=0.0).astype(np.float64),0)])
CN=np.vstack([np.zeros((1,D.shape[1])),np.cumsum(np.isfinite(D).astype(np.float64),0)])
def fwd(a,b):  # forward window [K+a, K+b)
    lo=np.minimum(K+a,len(D)); hi=np.minimum(K+b,len(D))
    n=CN[hi]-CN[lo]; s=CS[hi]-CS[lo]
    return np.where(n>=0.7*(b-a),s,np.nan)
def rz(M):
    o=np.full(M.shape,np.nan)
    for i in range(M.shape[0]):
        v=np.where(BASE[i],M[i],np.nan); ok=np.isfinite(v)
        if ok.sum()>=10: o[i,ok]=rankdata(v[ok])/(ok.sum()-1)-0.5
    return o
def ic(Zs,Y):
    r=[]
    for i in range(Zs.shape[0]):
        a=Zs[i]; b=Y[i]; m=np.isfinite(a)&np.isfinite(b)
        if m.sum()>50:
            br=rankdata(b[m]); ar=a[m]
            r.append(np.corrcoef(ar,br)[0,1])
    return float(np.mean(r)), float(np.std(r)/np.sqrt(len(r))), len(r)
g=lambda k: np.asarray(F[k],np.float64)
FEATS={"REV1H":-g("RET_SUM_12"),"VOL1H":g("RET_MSQ_12"),"TBF1H":g("TBF_MEAN_12"),
       "AMI1H":g("RET_MABS_12")/np.exp(g("LQV_MEAN_12")),"CPOS1H":g("CPOS_MEAN_12"),
       "QVS1H":g("LQV_MEAN_12")-g("LQV_MEAN_288"),
       "REV4H":-np.asarray(PW["f_rev_4h"],np.float64),"FUND":FE1,"AMI24H":np.asarray(PW["f_amihud_24h"],np.float64)}
SEG=[(0,12,"0-1h"),(12,24,"1-2h"),(24,36,"2-3h"),(36,48,"3-4h"),(48,96,"4-8h"),(96,144,"8-12h"),(144,288,"12-24h")]
Y={nm:fwd(a,b) for a,b,nm in SEG}
print("%-8s"%"feat"+"".join("%10s"%s[2] for s in SEG))
res={}
for fn,X in FEATS.items():
    Zs=rz(X); row=[]
    for a,b,nm in SEG:
        m,se,n=ic(Zs,Y[nm]); row.append(m)
    res[fn]=row
    print("%-8s"%fn+"".join("%+10.5f"%v for v in row))
np.save(R+"/ic_decay.npy",res,allow_pickle=True)
