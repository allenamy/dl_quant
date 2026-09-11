import numpy as np, calendar, time, json, hashlib, os
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
HCP="/workspace/review_scratch/health_check/dev_v4/probe_artifacts"
R2="/workspace/uplift_2026-09-11/r2_horizon"
def peek(p,key="d30_n2_c42_rec"):
    Z=np.load(p,allow_pickle=True); cc=[str(c) for c in Z["cols"]]
    A=np.asarray(Z[key] if key in Z else Z["rec"],float)
    ts=np.round(A[:,cc.index("ts")]).astype(np.int64)
    return cc,A,ts
cc,A,ts=peek(HCP+"/w10_ablation_series_V4_A0_dyn_s42.npz")
print("A0 cols",cc)
print("A0 n",len(ts),"first",time.strftime("%Y-%m-%d %HZ",time.gmtime(ts[0])),"last",time.strftime("%Y-%m-%d %HZ",time.gmtime(ts[-1])))
CUT=T(2026,8,30,20)
for W in (900,):
    t2=ts[W:]; m=t2<=CUT
    print("warm",W,"-> n",len(t2),"after cut",int(m.sum()),"first",time.strftime("%Y-%m-%d %HZ",time.gmtime(t2[0])),"last",time.strftime("%Y-%m-%d %HZ",time.gmtime(t2[m][-1])))
cc2,A2,ts2=peek(R2+"/out/C_TBF3D__p.npz")
print("arm cols equal:",cc2==cc)
print("arm n",len(ts2),"first",time.strftime("%Y-%m-%d %HZ",time.gmtime(ts2[0])),"last",time.strftime("%Y-%m-%d %HZ",time.gmtime(ts2[-1])))
print("ts identical to A0?",np.array_equal(ts2,ts))
inter=np.intersect1d(ts2,ts); print("intersect",len(inter))
t2=ts2[900:]; m=t2<=CUT; print("arm warm900 cut n",int(m.sum()))
