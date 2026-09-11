"""Per-arm signal-layer diagnostics for round-2 sleeves (methodology (e) of the brief).
For each pred matrix: forward/backward per-anchor rank-IC at k=-2..+2 against y4, sigma_pred/sigma_y,
per-year IC sign, and rank-correlation to the deployed fund score and to the round-1 Amihud feature.
NOTE these are SIGNAL-LAYER numbers. A signal-layer instrument is not the book layer."""
import numpy as np, json, sys, os, calendar, datetime as dt
R2="/workspace/uplift_2026-09-11/r2_learned"
TG=np.load("/workspace/dlw_v4raw/data/dlw_targets.npz",allow_pickle=True)
E_ts=TG["E_ts"].astype(np.int64); y4=TG["y4s"]; nA,NW=y4.shape; yrs=TG["yrs"].astype(int)
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
pts=PW["ts"].astype(np.int64); OFF=int(np.searchsorted(E_ts,pts[0]))
FUND=np.full((nA,NW),np.nan,np.float32); FUND[OFF:OFF+len(pts)]=np.asarray(PW["f_fund_ema_v1"],np.float32)
AMI =np.full((nA,NW),np.nan,np.float32); AMI [OFF:OFF+len(pts)]=np.asarray(PW["f_amihud_24h"],np.float32)
def xrank(v):
    n=len(v)
    if n<2: return np.zeros(n)
    return np.argsort(np.argsort(v)).astype(np.float64)/max(n-1,1)-0.5
def ic_k(M,k,rows=None):
    """per-anchor Spearman(score_i , y4_{i+k}) averaged; k>0 = forward beyond the held bar."""
    out=[]
    rng=range(nA) if rows is None else rows
    for i in rng:
        j=i+k
        if j<0 or j>=nA: continue
        s=M[i]; t=y4[j]
        m=np.isfinite(s)&np.isfinite(t)
        if m.sum()<50: continue
        a=xrank(s[m]); b=xrank(t[m])
        if a.std()>0 and b.std()>0: out.append(((a-a.mean())*(b-b.mean())).mean()/(a.std()*b.std()))
    return (float(np.mean(out)), int(len(out))) if out else (None,0)
def xcorr(M,N,rows):
    out=[]
    for i in rows:
        s=M[i]; t=N[i]; m=np.isfinite(s)&np.isfinite(t)
        if m.sum()<50: continue
        a=xrank(s[m]); b=xrank(t[m])
        if a.std()>0 and b.std()>0: out.append(((a-a.mean())*(b-b.mean())).mean()/(a.std()*b.std()))
    return float(np.mean(out)) if out else None
if __name__=="__main__":
    res={}
    for name in sys.argv[1:]:
        p=R2+"/preds/%s.npy"%name
        if not os.path.exists(p): print("skip",name); continue
        M=np.load(p)
        rows=[i for i in range(nA) if np.isfinite(M[i]).sum()>=50]
        sub=rows[::3]
        e={"n_anchors_with_score":len(rows)}
        e["offset_spectrum"]={str(k):(lambda r:(round(r[0],5) if r[0] is not None else None))(ic_k(M,k,sub)) for k in (-2,-1,0,1,2)}
        # sigma_pred / sigma_y  (score standardised per anchor -> compare dispersion of the IMPLIED
        # return forecast is not available for a pure score, so report the raw score dispersion ratio
        sp=[];sy=[]
        for i in sub:
            s=M[i]; t=y4[i]; m=np.isfinite(s)&np.isfinite(t)
            if m.sum()<50: continue
            sp.append(float(np.std(s[m]))); sy.append(float(np.std(t[m])))
        e["sigma_pred_over_sigma_y_raw"]=round(float(np.mean(sp)/np.mean(sy)),4) if sp else None
        e["ic_by_year"]={}
        for y in (2023,2024,2025,2026):
            r=[i for i in rows if yrs[i]==y]
            v,_=ic_k(M,0,r[::3])
            e["ic_by_year"][str(y)]=round(v,5) if v is not None else None
        e["xcorr_to_deployed_fund_score"]=round(xcorr(M,FUND,sub),4) if xcorr(M,FUND,sub) is not None else None
        e["xcorr_to_round1_amihud"]=round(xcorr(M,AMI,sub),4) if xcorr(M,AMI,sub) is not None else None
        res[name]=e
        print(name,json.dumps(e),flush=True)
    old={}
    fp=R2+"/DIAG_r2.json"
    if os.path.exists(fp): old=json.load(open(fp))
    old.update(res); json.dump(old,open(fp,"w"),indent=1)
