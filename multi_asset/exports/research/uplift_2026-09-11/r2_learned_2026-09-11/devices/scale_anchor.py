"""Scale anchor + offset spectrum for the prior gate. Measures the SAME per-anchor Spearman metric on
the IN-SERVICE predictors, so 'IC 0.07' can be read against something instead of in a vacuum."""
import numpy as np, json
R2="/workspace/uplift_2026-09-11/r2_learned"
TG=np.load("/workspace/dlw_v4raw/data/dlw_targets.npz",allow_pickle=True)
E_ts=TG["E_ts"].astype(np.int64); y4=TG["y4s"]; nA,NW=y4.shape; yrs=TG["yrs"].astype(int)
FE=np.load("/workspace/dlw_v4raw/data/dlw_fea82.npz",allow_pickle=True)
pa=FE["pair_a"].astype(np.int64); ps=FE["pair_s"].astype(np.int64); names=list(FE["names"])
ST=np.searchsorted(pa,np.arange(nA+1))
T=np.load(R2+"/targets_resid.npz"); Rraw=T["Rraw"]; Rtil=T["Rtil"]; OFF=int(T["OFF"])
PG=np.load(R2+"/prior_gate_preds.npz")
A=np.load("/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz",allow_pickle=True)
lts=A["legs_ts"].astype(np.int64)
def xrank(v):
    n=len(v)
    if n<2: return np.zeros(n)
    return np.argsort(np.argsort(v)).astype(np.float64)/max(n-1,1)-0.5
OK=np.array([ST[i+1]-ST[i]>=50 for i in range(nA)])
TEST=np.array([i for i in range(nA) if OK[i] and yrs[i]>=2023])
def ic_rows(pred_rows, targ_rows, idxs):
    o=[]
    for i in idxs:
        a,b=int(ST[i]),int(ST[i+1]); p=pred_rows[a:b]; t=targ_rows[a:b]
        k=np.isfinite(p)&np.isfinite(t)
        if k.sum()<50: continue
        pr=xrank(p[k]); tr=xrank(t[k])
        if pr.std()>0 and tr.std()>0: o.append(((pr-pr.mean())*(tr-tr.mean())).mean()/(pr.std()*tr.std()))
    return np.array(o)
def mat_to_rows(M, shift=0):
    out=np.full(len(pa),np.nan,np.float32)
    for i in range(nA):
        j=i+shift
        if j<0 or j>=M.shape[0]: continue
        a,b=int(ST[i]),int(ST[i+1])
        if b-a<1: continue
        out[a:b]=M[j,ps[a:b]]
    return out
res={}
# in-service predictors, same metric, same test anchors
F10=np.load("/workspace/review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_A0_s42.npy")
SL3=np.load("/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy")   # king, axis 10182
M4=np.load("/workspace/data/wide_fea_v4_meta.npz",allow_pickle=True); E4=M4["E_ts"].astype(np.int64)
KG=np.full((nA,NW),np.nan,np.float32); r={int(t):k for k,t in enumerate(E4)}
for i,t in enumerate(E_ts):
    k=r.get(int(t))
    if k is not None: KG[i]=SL3[k]
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
FUND=np.full((nA,NW),np.nan,np.float32); FUND[OFF:OFF+len(lts)]=np.asarray(PW["f_fund_ema_v1"],np.float32)
AMI=np.full((nA,NW),np.nan,np.float32); AMI[OFF:OFF+len(lts)]=np.asarray(PW["f_amihud_24h"],np.float32)
for nm,M in (("INSERVICE_f10_A0",F10),("INSERVICE_king_SLOWv3",KG),("DEPLOYED_fund_ema_v1",FUND),("ROUND1_amihud_24h",AMI)):
    rows=mat_to_rows(M)
    res[nm]={"IC_vs_raw":float(np.mean(ic_rows(rows,Rraw,TEST))),"IC_vs_til":float(np.mean(ic_rows(rows,Rtil,TEST))),"n":int(len(ic_rows(rows,Rraw,TEST)))}
for nm in PG.files:
    v=ic_rows(PG[nm],Rraw,TEST); res["PG_"+nm]={"IC_vs_raw":float(v.mean()),"t":float(v.mean()/v.std(ddof=1)*np.sqrt(len(v))),"n":int(len(v))}
# offset spectrum for ridge_raw and the in-service f10, k = -3..+3 (shift the TARGET)
def spec(pred_rows):
    out={}
    for k in range(-3,4):
        tr=np.full(len(pa),np.nan,np.float32)
        for i in range(nA):
            j=i+k
            if j<0 or j>=nA: continue
            a,b=int(ST[i]),int(ST[i+1]); aj,bj=int(ST[j]),int(ST[j+1])
            if b-a<50 or bj-aj<50: continue
            mm={int(s):q for q,s in enumerate(ps[aj:bj])}
            tgt=np.full(b-a,np.nan,np.float32)
            for q,s in enumerate(ps[a:b]):
                z=mm.get(int(s))
                if z is not None: tgt[q]=Rraw[aj+z]
            tr[a:b]=tgt
        v=ic_rows(pred_rows,tr,TEST[::5])
        out[str(k)]=round(float(v.mean()),5)
    return out
res["offset_spectrum_ridge_raw"]=spec(PG["ridge_raw"])
res["offset_spectrum_inservice_f10"]=spec(mat_to_rows(F10))
res["feature_names"]=names
json.dump(res,open(R2+"/scale_anchor.json","w"),indent=1)
print(json.dumps({k:v for k,v in res.items() if k!="feature_names"},indent=1))
