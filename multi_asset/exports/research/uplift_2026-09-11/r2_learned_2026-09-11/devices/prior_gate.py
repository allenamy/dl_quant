"""PRIOR GATE (decision checklist: Ridge/LGBM before any DL), v4 caliber.
Targets, all cross-sectional per anchor over the pair-layout members:
  Rraw = rank(y4)                            (what the book already chases)
  Rtil = rank(y4 - beta_i * W_A0[i])         (the book's own realised error; beta_i = <y,W>/<W,W>)
Walk-forward EXACTLY as the in-service F10: folds YV in {2023..2026}, train = yrs<YV and i < first_te-60.
Features: v4-native dlw_fea82 (82 cols) ONLY. f8_fea89 is _ext lineage => FORBIDDEN.
"""
import numpy as np, json, time, os
t0=time.time()
def log(*a): print("[%7.1fs]"%(time.time()-t0),*a,flush=True)
R2="/workspace/uplift_2026-09-11/r2_learned"
TG=np.load("/workspace/dlw_v4raw/data/dlw_targets.npz",allow_pickle=True)
E_ts=TG["E_ts"].astype(np.int64); y4=TG["y4s"]; nA,NW=y4.shape; yrs=TG["yrs"].astype(int)
FE=np.load("/workspace/dlw_v4raw/data/dlw_fea82.npz",allow_pickle=True)
X=np.asarray(FE["X"]); pa=FE["pair_a"].astype(np.int64); ps=FE["pair_s"].astype(np.int64); names=FE["names"]
ST=np.searchsorted(pa,np.arange(nA+1))
A=np.load("/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz",allow_pickle=True)
lts=A["legs_ts"].astype(np.int64); OFF=int(np.searchsorted(E_ts,lts[0])); assert np.array_equal(E_ts[OFF:OFF+len(lts)],lts)
W=np.zeros((nA,NW),np.float32); W[OFF:OFF+len(lts)]=A["d30_n2_c42_W"]
log("loaded",X.shape,"nA",nA,"OFF",OFF)

def xrank(v):
    """TRUE cross-sectional rank in [-0.5,0.5]. NOT o[argsort(argsort)]=arange (that is the
    inverse permutation - the round-1 Track D defect, verified here to destroy rank corr 0.98->0.05)."""
    n=len(v)
    if n<2: return np.zeros(n,np.float64)
    return np.argsort(np.argsort(v)).astype(np.float64)/max(n-1,1)-0.5
_v=np.array([3.0,1.0,2.0]); assert np.allclose(xrank(_v),[0.5,-0.5,0.0]), xrank(_v)

nr=len(pa)
Rraw=np.full(nr,np.nan,np.float32); Rtil=np.full(nr,np.nan,np.float32)
Yraw=np.full(nr,np.nan,np.float32); Ytil=np.full(nr,np.nan,np.float32); Wrow=np.zeros(nr,np.float32)
beta=np.full(nA,np.nan,np.float64); okA=np.zeros(nA,bool)
for i in range(nA):
    a,b=int(ST[i]),int(ST[i+1])
    if b-a<50: continue
    cs=ps[a:b]; yv=y4[i,cs].astype(np.float64); wv=W[i,cs].astype(np.float64)
    ok=np.isfinite(yv)
    if ok.sum()<50: continue
    yo=yv[ok]; wo=wv[ok]; den=float((wo*wo).sum())
    bi=float((yo*wo).sum()/den) if den>1e-18 else 0.0
    beta[i]=bi; okA[i]=True
    yt=yo-bi*wo
    idx=np.nonzero(ok)[0]+a
    Yraw[idx]=yo; Ytil[idx]=yt; Wrow[a:b]=wv
    Rraw[idx]=xrank(yo); Rtil[idx]=xrank(yt)
m=np.isfinite(Rraw)&np.isfinite(Rtil)
log("targets built; anchors ok",int(okA.sum()),"rows",int(m.sum()),
    "median|beta|",float(np.nanmedian(np.abs(beta))),"corr(Rraw,Rtil)",float(np.corrcoef(Rraw[m],Rtil[m])[0,1]))
np.savez(R2+"/targets_resid.npz",Rraw=Rraw,Rtil=Rtil,Yraw=Yraw,Ytil=Ytil,Wrow=Wrow,beta=beta,okA=okA,OFF=OFF)

def ic_by_anchor(pred, targ, idxs):
    out=[]
    for i in idxs:
        a,b=int(ST[i]),int(ST[i+1])
        p=pred[a:b]; t=targ[a:b]; k=np.isfinite(p)&np.isfinite(t)
        if k.sum()<50: continue
        pr=xrank(p[k]); tr=xrank(t[k])
        sp=pr.std(); st=tr.std()
        if sp>0 and st>0: out.append(float(((pr-pr.mean())*(tr-tr.mean())).mean()/(sp*st)))
    return np.array(out)

Xf=np.nan_to_num(X.astype(np.float32),nan=0.0)
rep={"device":"prior_gate.py","features":"dlw_fea82 (82, v4 native)","folds":{}}
PRED={"ridge_raw":np.full(nr,np.nan,np.float32),"ridge_til":np.full(nr,np.nan,np.float32),
      "lgbm_raw":np.full(nr,np.nan,np.float32),"lgbm_til":np.full(nr,np.nan,np.float32)}
import lightgbm as lgb
for YV in (2023,2024,2025,2026):
    te=np.where(yrs==YV)[0]
    if te.size==0: continue
    first_te=int(te[0])
    tr=np.array([i for i in range(first_te-60) if yrs[i]<YV and okA[i]])
    ter=np.array([i for i in te if okA[i]])
    rtr=np.concatenate([np.arange(ST[i],ST[i+1]) for i in tr])
    rte=np.concatenate([np.arange(ST[i],ST[i+1]) for i in ter])
    Xtr=Xf[rtr]; mu=Xtr.mean(0); sd=Xtr.std(0)+1e-6
    Ztr=np.clip((Xtr-mu)/sd,-5,5); Zte=np.clip((Xf[rte]-mu)/sd,-5,5)
    fold={"n_train_rows":int(len(rtr)),"n_test_rows":int(len(rte)),"n_train_anchors":int(len(tr))}
    for tname,T in (("raw",Rraw),("til",Rtil)):
        ytr=T[rtr]; k=np.isfinite(ytr)
        Zk=Ztr[k]; yk=ytr[k].astype(np.float64)
        G=Zk.T.astype(np.float64)@Zk.astype(np.float64)+1e3*np.eye(Zk.shape[1]); c=Zk.T.astype(np.float64)@yk
        w=np.linalg.solve(G,c)
        PRED["ridge_"+tname][rte]=(Zte@w).astype(np.float32)
        ss=np.arange(0,len(Zk),3)
        g=lgb.train({"objective":"regression","learning_rate":0.05,"num_leaves":31,"min_data_in_leaf":500,
                     "feature_fraction":0.7,"bagging_fraction":0.7,"bagging_freq":1,"verbose":-1,"seed":42,
                     "num_threads":8},
                    lgb.Dataset(Zk[ss],label=yk[ss]),num_boost_round=300)
        PRED["lgbm_"+tname][rte]=g.predict(Zte).astype(np.float32)
        fold["ridge_"+tname+"_w_norm"]=float(np.linalg.norm(w))
    for mn in PRED:
        for tn,T in (("raw",Rraw),("til",Rtil)):
            v=ic_by_anchor(PRED[mn],T,ter)
            if len(v): fold["IC_"+mn+"_vs_"+tn]=[round(float(v.mean()),5),round(float(v.mean()/v.std(ddof=1)*np.sqrt(len(v))),2)]
    rep["folds"][str(YV)]=fold
    log(YV,json.dumps({k:v for k,v in fold.items() if k.startswith("IC_")}))
np.savez(R2+"/prior_gate_preds.npz",**PRED)
json.dump(rep,open(R2+"/prior_gate_report.json","w"),indent=1)
log("PRIOR_GATE_DONE")
