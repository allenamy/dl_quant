"""E family: holding-horizon variants of the DEPLOYED fund score + the bitwise parity receipt."""
import numpy as np, sys
sys.path.insert(0,"/workspace/uplift_2026-09-11/r2_horizon")
from common import *
J=[]
# --- parity receipt: inject f_fund_ema_v1 itself into the A0 configuration -> must be BITWISE A0
J.append(("E0_PARITY",FE1,IBCOM,None,True))
# --- reference: the deployed fund score as a standalone 4h sleeve
J.append(("E_BASE",FE1,SLCOM,None,True))
# --- MA-N: causal trailing mean of the fund RANK over N anchors (12h/24h/3d hold)
def ma(N):
    Z=ZF.copy(); out=np.full(Z.shape,np.nan)
    for i in range(Z.shape[0]):
        lo=max(0,i-N+1); blk=Z[lo:i+1]
        with np.errstate(all="ignore"): out[i]=np.nanmean(blk,0)
    return fill(out)[0]
# --- STEP-N: fund rank refreshed only every N anchors (phase 0), held in between
def step(N):
    out=np.full(ZF.shape,np.nan)
    for i in range(ZF.shape[0]): out[i]=ZF[i-(i%N)]
    return fill(out)[0]
for N,h in [(3,"12h"),(6,"24h"),(18,"3d")]:
    J.append(("E_MA%d"%N,ma(N),SLCOM,None,False))
    J.append(("E_STEP%d"%N,step(N),SLCOM,None,False))
if __name__=="__main__":
    for tag,M,com,ex,kw in J: run(tag,M,com,ex,keepW=kw)
    print("DONE")
