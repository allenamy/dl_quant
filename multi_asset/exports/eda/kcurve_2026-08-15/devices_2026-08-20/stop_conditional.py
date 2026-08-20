"""缺口 I(多头尾部) + D(funding 补偿): 在真书 S0 路径上, 记录每个"本会触发"的深亏事件,
量其后续42锚(7天)的该名贡献(=不止损的代价/收益), 按 多空 × funding 档 × 流动性 分层。
判据: 若某层"持有"系统性为正 ⇒ 该层应豁免止损; 逐年同号方可采纳(≥4/5)。"""
import sys, json
import numpy as np, pandas as pd
MA="/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0,MA); sys.path.insert(0,MA+"/engine/live"); sys.path.insert(0,"/mnt/storage/private/work_hsy/quant_research_multi_asset")
PD="/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0,PD)
import legs as LG
import engine.replay_fullhist as RF
W={"king":.5952380952380952,"s2":.20238095238095238,"funding":.20238095238095238,"size":0.}
RB={"alpha":.5,"lambda":1.}; C1=4.137; BW=0.002; DEPTH=-0.25; FWD=42
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
state=None; prev=np.zeros(N); Pi=np.ones(N); sh=np.zeros(N); cb=np.zeros(N)
CTR=np.zeros((n,N),np.float32); WT=np.zeros((n,N),np.float32); ret_own=np.zeros((n,N),np.float32)
cnt=np.zeros(N,int); events=[]
for i in range(n):
    m=MSK[i]; syms=[SYMS[j] for j in m]
    out=LG.apply_harvest_ema(TGT[i][m],syms,state,0.05); state=out["state"]
    tgt=np.asarray(out["target_w"],float)
    w=prev.copy(); w[[j for j in range(N) if j not in set(m)]]=0.0
    d=tgt-w[m]; T=np.abs(d)>BW
    wm=w[m].copy(); wm[T]=tgt[T]
    if T.any(): wm[T]-=wm.sum()/T.sum()
    w[m]=wm
    y=RET[i]; ok=np.isfinite(y); idx=m[ok]
    c=np.zeros(N); c[idx]=w[m][ok]*y[ok]*1e4
    CTR[i]=c; WT[i]=w
    rr=np.zeros(N); rr[idx]=y[ok]; ret_own[i]=rr
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
    hit=(np.abs(sh)>1e-12)&(dep<=DEPTH)
    cnt=np.where(hit,cnt+1,0)
    fire=cnt>=2
    for j in np.where(fire)[0]:
        events.append({'i':i,'j':int(j),'yr':int(yr[i]),'side':1 if w[j]>0 else -1,
                       'fund':float(FND[i][j]) if np.isfinite(FND[i][j]) else 0.0,
                       'w':float(abs(w[j])),'dep':float(dep[j])})
    cnt=np.where(fire,0,cnt)
    prev=w; upd=np.zeros(N); upd[idx]=y[ok]; Pi=Pi*(1.0+upd)
print('触发事件数', len(events))
for e in events:
    i,j=e['i'],e['j']
    hi=min(i+1+FWD,n)
    e['hold_bps']=float(CTR[i+1:hi,j].sum())          # 继续持有该名的后续贡献(书 bps)
    e['ret_fwd']=float(np.nansum(ret_own[i+1:hi,j]))
E=pd.DataFrame(events)
res={'n':len(E),'mean_hold_bps':round(float(E.hold_bps.mean()),4)}
def grp(df,key):
    o={}
    for k,g in df.groupby(key):
        if len(g)>=25: o[str(k)]={'n':len(g),'hold_bps':round(float(g.hold_bps.mean()),4),
                                  'pos_rate':round(float((g.hold_bps>0).mean()),3)}
    return o
res['by_side']=grp(E,'side')
E['fbin']=pd.cut(E.fund,[-9,-0.0005,-0.0001,0.0001,0.0005,9],labels=['ff_neg','neg','flat','pos','ff_pos'])
res['by_fund']=grp(E,'fbin')
res['by_year']=grp(E,'yr')
E['sy']=E.side.astype(str)+'_'+E.fbin.astype(str)
res['side_x_fund']=grp(E,'sy')
# 逐年同号检验(多头/空头分别)
for s_ in (1,-1):
    sub=E[E.side==s_]
    res[f'side{s_}_by_year']={int(k):[len(g),round(float(g.hold_bps.mean()),4)] for k,g in sub.groupby('yr') if len(g)>=15}
print(json.dumps(res,ensure_ascii=False,indent=1))
json.dump(res,open(f'{PD}/stop_conditional.json','w'))
