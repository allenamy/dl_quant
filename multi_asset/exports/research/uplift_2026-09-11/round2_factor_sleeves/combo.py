"""Upper bound on what this family can deliver. Using the FULL-CYCLE (n=9918) correlation matrix and
the IN-SAMPLE Sharpes of all 36 round-2 arms, compute the maximum attainable combined Sharpe with
optimal (unconstrained, in-sample) weights: SR_opt = sqrt(mu' Sigma^-1 mu) scaled to annual.
This is an OPTIMISTIC UPPER BOUND: weights are fitted on the same data they are scored on."""
import numpy as np, sys, os, glob, json
sys.path.insert(0,"/workspace/uplift_2026-09-11/r2_factor")
import lib2 as L
R="/workspace/uplift_2026-09-11/r2_factor"
A0p="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz"
G={}; A=L.load(A0p); ts0,g0=L.gser(A); G["A0"]=g0
for p in sorted(glob.glob(R+"/out/SL2_ORTH_*.npz")):
    Rr=L.load(p); ts,g=L.gser(Rr); assert np.array_equal(ts,ts0)
    G[os.path.basename(p)[9:-4]]=g
m=L.msk(ts0,*L.W["full22"])
names=[k for k in G]
M=np.array([G[k][m] for k in names]); ok=np.isfinite(M).all(axis=0); M=M[:,ok]
ANN=np.sqrt(2190.0); n=M.shape[1]
mu=M.mean(axis=1); S=np.cov(M)
def sr_opt(idx):
    mm=mu[idx]; SS=S[np.ix_(idx,idx)]
    SS=SS+np.eye(len(idx))*1e-12*np.trace(SS)/len(idx)
    w=np.linalg.solve(SS,mm)
    return float(np.sqrt(max(mm@w,0.0))*ANN), w
iA0=names.index("A0")
sleeves=[i for i in range(len(names)) if i!=iA0]
print("individual annualised Sharpe, full cycle n=%d:"%n)
for i in np.argsort(-mu/np.sqrt(np.diag(S))):
    print("  %-22s SR %+6.3f"%(names[i], mu[i]/np.sqrt(S[i,i])*ANN))
srA0=mu[iA0]/np.sqrt(S[iA0,iA0])*ANN
print("\nA0 alone (in-sample) SR = %+.3f"%srA0)
s_all,_=sr_opt(list(range(len(names))))
print("IN-SAMPLE OPTIMAL over A0 + ALL 36 round-2 sleeves  SR = %+.3f   (upper bound, weights fitted in sample)"%s_all)
s_sl,_=sr_opt(sleeves)
print("IN-SAMPLE OPTIMAL over the 36 sleeves WITHOUT A0     SR = %+.3f"%s_sl)
# honest out-of-sample version: fit weights on 2022-01-31..2024-12-31, score 2025-01-01..2026-08-10
import datetime as dt
f=lambda s:int(dt.datetime.strptime(s,"%Y-%m-%d").replace(tzinfo=dt.timezone.utc).timestamp())
tsm=ts0[m]
tr=tsm<f("2025-01-01"); te=~tr
mu_tr=M[:,tr].mean(axis=1); S_tr=np.cov(M[:,tr])
S_tr=S_tr+np.eye(len(names))*1e-10*np.trace(S_tr)/len(names)
w=np.linalg.solve(S_tr,mu_tr)
r_te=w@M[:,te]
print("\nWALK-FORWARD: weights fitted 2022-01-31..2024-12-31 (n=%d), scored 2025-01-01..2026-08-10 (n=%d)"%(tr.sum(),te.sum()))
print("  OOS combined SR = %+.3f   (A0 alone on the same OOS span = %+.3f)"%(
   r_te.mean()/r_te.std(ddof=1)*ANN, M[iA0,te].mean()/M[iA0,te].std(ddof=1)*ANN))
