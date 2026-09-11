import numpy as np, time
B="/workspace/review_scratch/health_check/dev_v4/pod_backup_2026-08-21"
PW=np.load(B+"/wide_panel_4h_hist_v2.npz",allow_pickle=True)
pts=PW["ts"].astype(np.int64); Y4=np.asarray(PW["Y4"],np.float64); RV4=np.asarray(PW["f_rev_4h"],np.float64)
RV24=np.asarray(PW["f_rev_24h"],np.float64)
z=np.load("/workspace/data/dlnative_5m_wide829_f16_holefix2.npz",allow_pickle=True)
ts5=z["ts"].astype(np.int64); ch=[str(c) for c in z["ch"]]
ir=ch.index("ret5")
D=z["data"][:,:,ir].astype(np.float32)
print("loaded ret5",D.shape, "finite",np.isfinite(D).mean())
pos={int(t):k for k,t in enumerate(ts5)}
CS=np.vstack([np.zeros((1,D.shape[1]),np.float64),np.nancumsum(np.nan_to_num(D,nan=0.0).astype(np.float64),0)])
# test on a slice of anchors
J=np.arange(2000,9000,37)
K=np.array([pos[int(pts[j])] for j in J])
def w(a,b):  # sum over 5m rows [a,b)
    return CS[b]-CS[a]
def cc(A,Bm):
    a=A.ravel(); b=Bm.ravel(); m=np.isfinite(a)&np.isfinite(b)&(np.abs(a)>0)&(np.abs(b)>0)
    return np.corrcoef(a[m],b[m])[0,1], m.sum()
print("Y4[j]   vs sum ret5 [k, k+48) :", cc(Y4[J],w(K,K+48)))
print("Y4[j]   vs sum ret5 [k+1,k+49):", cc(Y4[J],w(K+1,K+49)))
print("rev4[j] vs sum ret5 [k-48,k)  :", cc(RV4[J],w(K-48,K)))
print("rev4[j] vs sum ret5 [k-47,k+1):", cc(RV4[J],w(K-47,K+1)))
print("rev24[j]vs sum ret5 [k-288,k) :", cc(RV24[J],w(K-288,K)))
