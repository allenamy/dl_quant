"""(A) 静态杠杆前沿 vs 回撤阶梯: 若阶梯点落在静态前沿之上 ⇒ 有增量; 否则=降杠杆的换皮.
(B) 混合的尾部检验: 两书最坏5%锚的共现、尾部相关、最坏30天窗里混合 vs 单书, 以及"压力时相关=0.6"的悲观混合."""
import sys, json, time, numpy as np
PD="/mnt/storage/private/work_hsy/probe_artifacts"
live=np.load(f"{PD}/net_S1_ts.npy"); lts=live[:,0].astype(int); lpg=live[:,1]/0.987
wide=np.load(f"{PD}/nets_histv2_-30_2_42_pergross.npy"); wts=wide[:,0].astype(int); wpg=wide[:,1]
lm={int(t):i for i,t in enumerate(lts)}; common=[(lm[int(t)],j) for j,t in enumerate(wts) if int(t) in lm]
li=np.array([c[0] for c in common]); wi=np.array([c[1] for c in common]); L=lpg[li]; W=wpg[wi]; B=0.5*L+0.5*W
def sim(x, gross, shr=1.0, ladder=None, seed=11):
    x=x-x.mean()*(1-shr); rng=np.random.RandomState(seed); L_=180; nb=len(x)//L_; NY=2190; nbk=NY//L_+1
    hit=0; ann=[]
    for _ in range(2000):
        idx=rng.randint(0,nb,nbk); path=np.concatenate([x[i*L_:(i+1)*L_] for i in idx])[:NY]/1e4
        nav=1.0; peak=1.0; mult=1.0; h=False
        for r in path:
            if ladder:
                dd=nav/peak-1
                mult=1.0
                for th,mu in ladder:
                    if dd<=th: mult=mu
            nav*=1+gross*mult*r; peak=max(peak,nav)
            if nav/peak-1<=-0.25: h=True
        hit+=h; ann.append(nav-1)
    return round(hit/2000,3), round(float(np.median(ann)),3)
LAD_STD=[(-0.10,0.7),(-0.15,0.5),(-0.20,0.3)]
LAD_SOFT=[(-0.15,0.7),(-0.20,0.5)]
LAD_HARD=[(-0.08,0.6),(-0.12,0.4),(-0.16,0.2)]
out={"A_frontier":{}, "B_tail":{}}
for nm,x in (("在役",L),("宽书",W),("混合",B)):
    fr={}
    for g in (1.0,1.25,1.5,1.75,2.0,2.5):
        fr[f"static@{g}"]=sim(x,g)
    for g in (2.0,2.5):
        fr[f"ladSTD@{g}"]=sim(x,g,ladder=LAD_STD); fr[f"ladSOFT@{g}"]=sim(x,g,ladder=LAD_SOFT); fr[f"ladHARD@{g}"]=sim(x,g,ladder=LAD_HARD)
    out["A_frontier"][nm]=fr; print("A", nm, json.dumps(fr,ensure_ascii=False), flush=True)
# (B) 尾部
q5L=np.percentile(L,5); q5W=np.percentile(W,5)
both=np.mean((L<=q5L)&(W<=q5W)); indep=0.05*0.05
tail_corr=np.corrcoef(L[(L<=q5L)|(W<=q5W)], W[(L<=q5L)|(W<=q5W)])[0,1]
def worst_windows(x, k=180, n=5):
    s=np.array([x[i:i+k].sum() for i in range(0,len(x)-k,6)]); idx=np.argsort(s)[:n]; return idx*6, s[idx]
wl,sl=worst_windows(L); ww,sw=worst_windows(W)
tb={"P(两书同在最坏5%)":round(float(both),4),"独立假设":round(indep,4),"尾部相关(任一在最坏5%时)":round(float(tail_corr),3),
    "在役最坏5个30天窗(bps/单位gross)":[round(float(v),0) for v in sl],"同窗宽书":[round(float(W[i:i+180].sum()),0) for i in wl],"同窗混合":[round(float(B[i:i+180].sum()),0) for i in wl],
    "宽书最坏5个30天窗":[round(float(v),0) for v in sw],"同窗在役":[round(float(L[i:i+180].sum()),0) for i in ww],"同窗混合":[round(float(B[i:i+180].sum()),0) for i in ww]}
# 悲观混合: 压力锚(任一书 ≤ 其 5% 分位)把另一书替换为与之相关 0.6 的合成值
rng=np.random.RandomState(3); Wp=W.copy(); stress=(L<=q5L); z=(L-L.mean())/L.std()
Wp[stress]=W.mean()+W.std()*(0.6*z[stress]+np.sqrt(1-0.36)*rng.randn(stress.sum()))
Bp=0.5*L+0.5*Wp
tb["悲观混合(压力时相关0.6)@2.0"]=sim(Bp,2.0); tb["悲观混合@2.0 折让"]=sim(Bp,2.0,0.55); tb["原混合@2.0"]=sim(B,2.0); tb["在役@2.0"]=sim(L,2.0)
out["B_tail"]=tb; print("B", json.dumps(tb,ensure_ascii=False), flush=True)
json.dump(out,open(f"{PD}/killline_frontier_tail.json","w"),indent=1,ensure_ascii=False)
