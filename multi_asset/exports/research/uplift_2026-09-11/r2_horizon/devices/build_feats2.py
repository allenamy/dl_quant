import numpy as np, time, gc
R="/workspace/uplift_2026-09-11/r2_horizon"
B="/workspace/review_scratch/health_check/dev_v4/pod_backup_2026-08-21"
PW=np.load(B+"/wide_panel_4h_hist_v2.npz",allow_pickle=True); pts=PW["ts"].astype(np.int64); NW=829
z=np.load("/workspace/data/dlnative_5m_wide829_f16_holefix2.npz",allow_pickle=True)
ts5=z["ts"].astype(np.int64); ch=[str(c) for c in z["ch"]]
pos={int(t):k for k,t in enumerate(ts5)}; K=np.array([pos[int(t)] for t in pts])
OUT={}
def ws(ci,Ws,name,do_abs=False):
    X=z["data"][:,:,ci].astype(np.float32); fin=np.isfinite(X); Xf=np.where(fin,X,0.0).astype(np.float64)
    CN=np.vstack([np.zeros((1,NW)),np.cumsum(fin.astype(np.float64),0)])
    CS=np.vstack([np.zeros((1,NW)),np.cumsum(Xf,0)])
    CA=np.vstack([np.zeros((1,NW)),np.cumsum(np.abs(Xf),0)]) if do_abs else None
    for W in Ws:
        lo=np.maximum(K-W,0); hi=K; n=CN[hi]-CN[lo]; ok=n>=0.7*W; s=CS[hi]-CS[lo]
        OUT["%s_MEAN_%d"%(name,W)]=np.where(ok,s/np.maximum(n,1),np.nan).astype(np.float32)
        if do_abs:
            a=CA[hi]-CA[lo]; OUT["%s_MABS_%d"%(name,W)]=np.where(ok,a/np.maximum(n,1),np.nan).astype(np.float32)
    del X,fin,Xf,CN,CS,CA; gc.collect(); print(name,"done",flush=True)
ws(ch.index("tbf"),[2016,4032,8640],"TBF")
ws(ch.index("ret5"),[2016],"RET",do_abs=True)
ws(ch.index("log_qv"),[2016],"LQV")
np.savez_compressed(R+"/feats_r2b.npz",ts=pts,symbols=PW["symbols"],**OUT)
print("saved",sorted(OUT.keys()))
