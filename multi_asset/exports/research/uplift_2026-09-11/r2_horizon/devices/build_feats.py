"""Round-2 horizon feature builder. All windows RIGHT-OPEN at the anchor: [k-W, k).
Writes /workspace/uplift_2026-09-11/r2_horizon/feats_r2.npz on the 4h panel grid (10039 x 829)."""
import numpy as np, time, gc, json, hashlib, sys
R="/workspace/uplift_2026-09-11/r2_horizon"
B="/workspace/review_scratch/health_check/dev_v4/pod_backup_2026-08-21"
PW=np.load(B+"/wide_panel_4h_hist_v2.npz",allow_pickle=True)
pts=PW["ts"].astype(np.int64); NA=len(pts); NW=829
z=np.load("/workspace/data/dlnative_5m_wide829_f16_holefix2.npz",allow_pickle=True)
ts5=z["ts"].astype(np.int64); ch=[str(c) for c in z["ch"]]
pos={int(t):k for k,t in enumerate(ts5)}
K=np.array([pos[int(t)] for t in pts]); assert (K>=0).all()
print("anchors",NA,"min K",K.min(),"max K",K.max(),flush=True)
OUT={}
def winstats(ci,Ws,name,do_abs=False,do_sq=False,do_sum=True,do_mean=True):
    t=time.time()
    X=z["data"][:,:,ci].astype(np.float32)
    fin=np.isfinite(X)
    Xf=np.where(fin,X,0.0).astype(np.float64)
    CN=np.vstack([np.zeros((1,NW)),np.cumsum(fin.astype(np.float64),0)])
    CS=np.vstack([np.zeros((1,NW)),np.cumsum(Xf,0)])
    CA=np.vstack([np.zeros((1,NW)),np.cumsum(np.abs(Xf),0)]) if do_abs else None
    CQ=np.vstack([np.zeros((1,NW)),np.cumsum(Xf*Xf,0)]) if do_sq else None
    for W in Ws:
        lo=np.maximum(K-W,0); hi=K
        n=CN[hi]-CN[lo]
        ok=n>=0.7*W
        s=CS[hi]-CS[lo]
        if do_sum: OUT["%s_SUM_%d"%(name,W)]=np.where(ok,s,np.nan).astype(np.float32)
        if do_mean: OUT["%s_MEAN_%d"%(name,W)]=np.where(ok,s/np.maximum(n,1),np.nan).astype(np.float32)
        if do_abs:
            a=CA[hi]-CA[lo]; OUT["%s_MABS_%d"%(name,W)]=np.where(ok,a/np.maximum(n,1),np.nan).astype(np.float32)
        if do_sq:
            q=CQ[hi]-CQ[lo]; OUT["%s_MSQ_%d"%(name,W)]=np.where(ok,q/np.maximum(n,1),np.nan).astype(np.float32)
    del X,fin,Xf,CN,CS,CA,CQ; gc.collect()
    print("%-10s done %.1fs"%(name,time.time()-t),flush=True)
winstats(ch.index("ret5"),[12,144,864],"RET",do_abs=True,do_sq=True)
winstats(ch.index("ret5"),[288],"RET",do_abs=True,do_sq=False,do_sum=False,do_mean=False)
winstats(ch.index("log_qv"),[12,144,288,864,8640],"LQV",do_sum=False)
winstats(ch.index("tbf"),[12,144,864],"TBF",do_sum=False)
winstats(ch.index("cpos"),[12],"CPOS",do_sum=False)
np.savez_compressed(R+"/feats_r2.npz",ts=pts,symbols=PW["symbols"],**OUT)
print("saved",len(OUT),"keys",flush=True)
print(json.dumps(sorted(OUT.keys())))
