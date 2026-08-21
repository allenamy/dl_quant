import sys, json, time, numpy as np
PD="/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0,PD)
MA="/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0,MA); sys.path.insert(0,MA+"/engine/live"); sys.path.insert(0,"/mnt/storage/private/work_hsy/quant_research_multi_asset")
import legs as LG, engine.replay_fullhist as RF
W={"king":.5952380952380952,"s2":.20238095238095238,"funding":.20238095238095238,"size":0.}; RB={"alpha":.5,"lambda":1.}; BW=0.002
src=RF.get_src(None,f"{PD}/king_pred_newgen.npz",f"{PD}/s2_pred_newgen.npz"); a,yr=RF._all_anchors(src); N=src.N; n=len(a)
FI,RVI=src.fund_idx,src.ch.index("rvol_24h"); SYMS=[str(s) for s in src.symbols]
held={"k":np.full(N,np.nan),"s":np.full(N,np.nan),"f":np.full(N,np.nan)}; state=None; prev=np.zeros(N); G=np.zeros(n)
for i,t in enumerate(a):
    ti=int(t); m=np.asarray(src.tradeable(ti)); m=np.where(m)[0] if m.dtype==bool else m
    if i==0 or ti%8==0: v=np.full(N,np.nan); v[m]=src.king[ti,m]; held["k"]=v
    if i==0 or ti%24==0: v=np.full(N,np.nan); v[m]=src.s2[ti,m]; held["s"]=v
    if i==0 or ti%8==0: v=np.full(N,np.nan); v[m]=src.CH[ti,m,FI]; held["f"]=v
    r=LG.compose_book(held["k"][m],held["s"][m],held["f"][m],np.ones(len(m)),weights=W,rvol=src.CH[ti,m,RVI].astype(float),risk_budget=RB)
    tgt0=np.full(N,0.0); tgt0[m]=np.asarray(r["target_w"],float)
    out=LG.apply_harvest_ema(tgt0[m],[SYMS[j] for j in m],state,0.05); state=out["state"]; tgt=np.asarray(out["target_w"],float)
    w=prev.copy(); w[[j for j in range(N) if j not in set(m)]]=0.0
    d=tgt-w[m]; T=np.abs(d)>BW; wm=w[m].copy(); wm[T]=tgt[T]
    if T.any(): wm[T]-=wm.sum()/T.sum()
    w[m]=wm; G[i]=float(np.abs(w).sum()); prev=w
net=np.load(f"{PD}/net_S1.npy"); assert len(net)==n
print("在役 gross 逐锚: 均", round(float(G.mean()),3), "中位", round(float(np.median(G)),3), "p5/p95", round(float(np.percentile(G,5)),3), round(float(np.percentile(G,95)),3), flush=True)
res={}
for y0 in (2022, 2024):
    m=(yr>=y0)&(G>0.2); pu=net[m]/G[m]
    for shr in (1.0,0.55):
        x=pu-pu.mean()*(1-shr); rng=np.random.RandomState(11); L_=180; nb=len(x)//L_; NY=2190; nbk=NY//L_+1
        out={"n":int(m.sum()),"mean_per_gross":round(float(pu.mean()),3),"sd_per_gross":round(float(pu.std()),2)}
        for Gt in (2.0,3.0,3.5):
            hit=0; ann=[]
            for _ in range(2000):
                idx=rng.randint(0,nb,nbk); path=np.concatenate([x[i*L_:(i+1)*L_] for i in idx])[:NY]*Gt/1e4
                cum=np.cumprod(1+path); dd=cum/np.maximum.accumulate(cum)-1; hit+=dd.min()<=-0.25; ann.append(cum[-1]-1)
            out[f"gross{Gt}"]={"P_hit_-25%":round(hit/2000,3),"ann_median":round(float(np.median(ann)),3),"ann_p5":round(float(np.percentile(ann,5)),3)}
        res[f"y{y0}_shr{shr}"]=out; print(f"live_constgross y{y0} shr{shr}", json.dumps(out), flush=True)
json.dump(res, open(f"{PD}/lev_live_constgross.json","w"), indent=1)
