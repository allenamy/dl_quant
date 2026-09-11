"""S5 offset spectrum: corr(signal rank @ anchor i, y4 @ anchor i+k), k=-3..+4. SIGNAL LAYER."""
import numpy as np, sys
sys.path.insert(0,"/workspace/uplift_2026-09-11/r2_horizon")
from common import *
from scipy.stats import rankdata
MT=np.load(HC+"/dev_v4/pod_backup_2026-08-21/wide_fea_hist_meta.npz",allow_pickle=True)
E=MT["E_ts"].astype(np.int64); Y=np.asarray(MT["y4"],np.float64)
rmap={int(t):k for k,t in enumerate(E)}
ridx=np.array([rmap.get(int(t),-1) for t in TS])
ok=ridx>=0; print("panel rows mapped to meta y4:",ok.mean())
F=np.load(R+"/feats_r2.npz",allow_pickle=True); g=lambda k: np.asarray(F[k],np.float64)
AMI3D=g("RET_MABS_864")/np.exp(g("LQV_MEAN_864")); TBF3D=g("TBF_MEAN_864")
REV1H=-g("RET_SUM_12")
SIG={"ORTH_AMI3D":orth(AMI3D),"ORTH_TBF3D":orth(TBF3D),"ORTH_REV1H":orth(REV1H),"FUND(deployed)":ZF}
KS=[-3,-2,-1,0,1,2,3,4]
print("%-16s"%"signal"+"".join("%10s"%("k=%+d"%k) for k in KS))
for nm,S in SIG.items():
    Zs=ZR(S) if nm!="FUND(deployed)" else S
    row=[]
    for k in KS:
        cs=[]
        for i in range(len(TS)):
            ii=i+k
            if ii<0 or ii>=len(TS) or not ok[ii]: continue
            a=Zs[i]; b=Y[ridx[ii]]
            m=np.isfinite(a)&np.isfinite(b)
            if m.sum()>50: cs.append(np.corrcoef(rankdata(a[m]),rankdata(b[m]))[0,1])
        row.append(float(np.mean(cs)))
    print("%-16s"%nm+"".join("%+10.5f"%v for v in row),flush=True)
