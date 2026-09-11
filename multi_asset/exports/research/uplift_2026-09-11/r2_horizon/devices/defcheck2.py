import numpy as np
from scipy.stats import spearmanr
B="/workspace/review_scratch/health_check/dev_v4/pod_backup_2026-08-21"
PW=np.load(B+"/wide_panel_4h_hist_v2.npz",allow_pickle=True)
pts=PW["ts"].astype(np.int64)
z=np.load("/workspace/data/dlnative_5m_wide829_f16_holefix2.npz",allow_pickle=True)
ts5=z["ts"].astype(np.int64); ch=[str(c) for c in z["ch"]]
pos={int(t):k for k,t in enumerate(ts5)}
K=np.array([pos[int(t)] for t in pts]); D=z["data"]
J=np.arange(3000,9000,29); KJ=K[J]
ir=ch.index("ret5"); iq=ch.index("log_qv")
R=np.stack([D[k-288:k,:,ir].astype(np.float64) for k in KJ])
Q=np.stack([D[k-288:k,:,iq].astype(np.float64) for k in KJ])
qv=np.exp(Q)
AMP=np.asarray(PW["f_amihud_24h"],np.float64)[J]
def sp(A,Bm):
    r=[]
    for i in range(A.shape[0]):
        a=A[i];b=Bm[i];m=np.isfinite(a)&np.isfinite(b)
        if m.sum()>50: r.append(spearmanr(a[m],b[m]).statistic)
    return float(np.nanmean(r))
with np.errstate(all="ignore"):
    # 4h-bar aggregation: 6 bars of 48
    R4=R.reshape(len(J),6,48,829).sum(2); Q4=qv.reshape(len(J),6,48,829).sum(2)
    print("4h-bar mean(|r4|/qv4)       :",sp(AMP,np.nanmean(np.abs(R4)/np.maximum(Q4,1e-9),1)))
    print("4h-bar sum|r4|/sumqv4       :",sp(AMP,np.nansum(np.abs(R4),1)/np.nansum(Q4,1)))
    print("5m  mean|r|/mean qv  x1e6   :",sp(AMP,np.nanmean(np.abs(R),1)/np.nanmean(qv,1)))
    print("5m  sqrt mean r^2 / mean qv :",sp(AMP,np.sqrt(np.nanmean(R**2,1))/np.nanmean(qv,1)))
    print("5m  mean|r| / exp(mean logqv):",sp(AMP,np.nanmean(np.abs(R),1)/np.exp(np.nanmean(Q,1))))
    print("1/qv alone (-mean logqv)    :",sp(AMP,-np.nanmean(Q,1)))
    print("vol alone sqrt(mean r^2)    :",sp(AMP,np.sqrt(np.nanmean(R**2,1))))
    print("log form: log mean|r| - mean logqv:",sp(AMP,np.log(np.maximum(np.nanmean(np.abs(R),1),1e-12))-np.nanmean(Q,1)))
