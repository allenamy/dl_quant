"""条件止损书级验证。判据【冻结, 先于看数】: S4/S5 相对 S1 须 ①全期净额 ≥ S1 ②逐年≥4/5不劣
③p5尾部不劣 ④换手增量≤+5%。四条全过才算候选, 否则维持在役 S1。
S1 在役(全部名) / S4 仅空头且 fund≥+0.0002(挤压中) / S5 仅空头 / S6 全部但多头阈值放宽到-35%"""
import sys, json
import numpy as np, pandas as pd
MA="/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0,MA); sys.path.insert(0,MA+"/engine/live"); sys.path.insert(0,"/mnt/storage/private/work_hsy/quant_research_multi_asset")
PD="/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0,PD)
import legs as LG
import engine.replay_fullhist as RF
W={"king":.5952380952380952,"s2":.20238095238095238,"funding":.20238095238095238,"size":0.}
RB={"alpha":.5,"lambda":1.}; C1=4.137; BW=0.002; ANN=np.sqrt(6*365); COOL=42
src=RF.get_src(None,f"{PD}/king_pred_newgen.npz",f"{PD}/s2_pred_newgen.npz")
a,yr=RF._all_anchors(src); N=src.N; n=len(a)
FI,RVI=src.fund_idx,src.ch.index("rvol_24h"); SYMS=[str(s) for s in src.symbols]
TGT,MSK,RET,FND=[],[],[],[]
held={"k":np.full(N,np.nan),"s":np.full(N,np.nan),"f":np.full(N,np.nan)}
for i,t in enumerate(a):
    ti=int(t); m=np.asarray(src.tradeable(ti))
    if m.dtype==bool: m=np.where(m)[0]
    if i==0 or ti%8==0:
        v=np.full(N,np.nan); v[m]=src.king[ti,m]; held["k"]=v
    if i==0 or ti%24==0:
        v=np.full(N,np.nan); v[m]=src.s2[ti,m]; held["s"]=v
    if i==0 or ti%8==0:
        v=np.full(N,np.nan); v[m]=src.CH[ti,m,FI]; held["f"]=v
    r=LG.compose_book(held["k"][m],held["s"][m],held["f"][m],np.ones(len(m)),
                      weights=W,rvol=src.CH[ti,m,RVI].astype(float),risk_budget=RB)
    w=np.full(N,0.0); w[m]=np.asarray(r["target_w"],float)
    fv=np.full(N,np.nan); fv[m]=src.CH[ti,m,FI].astype(float)
    TGT.append(w); MSK.append(m); RET.append(src.Y4[ti,m].astype(float)); FND.append(fv)
def run(mode):
    state=None; prev=np.zeros(N); Pi=np.ones(N); sh=np.zeros(N); cb=np.zeros(N)
    cnt=np.zeros(N,int); su=np.full(N,-1); fires=0
    pnl=np.zeros(n); trn=np.zeros(n)
    for i in range(n):
        m=MSK[i]; syms=[SYMS[j] for j in m]
        out=LG.apply_harvest_ema(TGT[i][m],syms,state,0.05); state=out["state"]
        tgt=np.asarray(out["target_w"],float)
        if mode!='S0':
            bs=set(np.where(su>i)[0].tolist())
            if bs:
                for k2,j in enumerate(m):
                    if j in bs: tgt[k2]=0.0
        w=prev.copy(); w[[j for j in range(N) if j not in set(m)]]=0.0
        d=tgt-w[m]; T=np.abs(d)>BW
        wm=w[m].copy(); wm[T]=tgt[T]
        if T.any(): wm[T]-=wm.sum()/T.sum()
        w[m]=wm
        y=RET[i]; ok=np.isfinite(y); idx=m[ok]
        c=np.zeros(N); c[idx]=w[m][ok]*y[ok]*1e4
        pnl[i]=c.sum(); trn[i]=float(np.abs(w-prev).sum())
        nsh=np.where(Pi>1e-12,w/Pi,0.0)
        same=np.sign(nsh)==np.sign(sh); add=same&(np.abs(nsh)>np.abs(sh))
        red=same&(~add)&(np.abs(nsh)>1e-12); new=(~same)|(np.abs(sh)<1e-12)
        cb=np.where(add,cb+(nsh-sh)*Pi,cb)
        with np.errstate(all='ignore'):
            ratio=np.where(np.abs(sh)>1e-12,nsh/np.where(np.abs(sh)>1e-12,sh,1.0),0.0)
        cb=np.where(red,cb*ratio,cb); cb=np.where(new,nsh*Pi,cb); cb=np.where(np.abs(nsh)<1e-12,0.0,cb)
        sh=nsh
        with np.errstate(all='ignore'):
            avg=np.where(np.abs(sh)>1e-12,cb/sh,np.nan)
            dep=np.where(np.isfinite(avg)&(Pi>0),np.sign(sh)*(1.0-avg/Pi),0.0)
        if mode!='S0':
            fnd=np.nan_to_num(FND[i]); isshort=w<0
            thr=np.full(N,-0.25)
            if mode=='S6': thr=np.where(w>0,-0.35,-0.25)
            cand=(np.abs(sh)>1e-12)&(dep<=thr)&(su<=i)
            if mode=='S4': cand=cand&isshort&(fnd>=0.0002)
            elif mode=='S5': cand=cand&isshort
            cnt=np.where(cand,cnt+1,0)
            fire=cnt>=2
            if fire.any(): su[fire]=i+COOL; cnt[fire]=0; fires+=int(fire.sum())
        prev=w; upd=np.zeros(N); upd[idx]=y[ok]; Pi=Pi*(1.0+upd)
    net=pnl-trn*C1
    df=pd.DataFrame({'y':yr,'net':net})
    return {'net_all':round(float(net.mean()),4),'sharpe':round(float(net.mean()/net.std(ddof=1)*ANN),3),
            'by_year':{int(y_):round(float(g.net.mean()),3) for y_,g in df.groupby('y')},
            'p5':round(float(np.percentile(net,5)),2),'turnover':round(float(trn.mean()),5),'fires':fires}
res={}
for mode in ('S0','S1','S4','S5','S6'):
    res[mode]=run(mode); print(mode, json.dumps(res[mode],ensure_ascii=False), flush=True)
S1=res['S1']
for k in ('S4','S5','S6'):
    r=res[k]
    yrs_ok=sum(1 for y_ in r['by_year'] if r['by_year'][y_] >= S1['by_year'][y_]-1e-9)
    res[k]['GATE']={'net_ge_S1':r['net_all']>=S1['net_all'],'years_not_worse':f"{yrs_ok}/{len(r['by_year'])}",
                    'p5_not_worse':r['p5']>=S1['p5'],'turnover_ok':r['turnover']<=S1['turnover']*1.05,
                    'PASS':bool(r['net_all']>=S1['net_all'] and yrs_ok>=4 and r['p5']>=S1['p5'] and r['turnover']<=S1['turnover']*1.05)}
    print(k,'GATE',json.dumps(res[k]['GATE'],ensure_ascii=False), flush=True)
json.dump(res,open(f'{PD}/cond_stop_book.json','w'))
