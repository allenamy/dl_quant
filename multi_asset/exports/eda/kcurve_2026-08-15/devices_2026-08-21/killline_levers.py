"""触线概率的杠杆矩阵(在役 S1 / 宽书 d30 / 50-50 混合; 每单位 gross 序列 × 恒定 gross):
① 基线(峰值回撤 −25%) ② 回撤阶梯(峰值回撤 −10%→gross×0.7, −15%→×0.5, −20%→×0.3; 回到 −8% 内恢复) ③ 停机线按年初基线(非峰值)
块 180 锚 × 2000 路径; 回放原值 与 折让×0.55 各一。"""
import sys, json, time, numpy as np
PD="/mnt/storage/private/work_hsy/probe_artifacts"
live=np.load(f"{PD}/net_S1_ts.npy"); lts=live[:,0].astype(int); lnet=live[:,1]
# 在役 gross ≈0.987 恒定 ⇒ 每单位 gross ≈ net/0.987
lpg=lnet/0.987
wide=np.load(f"{PD}/nets_histv2_-30_2_42_pergross.npy"); wts=wide[:,0].astype(int); wpg=wide[:,1]
# 对齐交集(同 4h 锚 ts)
lm={int(t):i for i,t in enumerate(lts)}; common=[(lm[int(t)],j) for j,t in enumerate(wts) if int(t) in lm]
li=np.array([c[0] for c in common]); wi=np.array([c[1] for c in common])
print("对齐锚数", len(common), time.strftime('%Y-%m-%d',time.gmtime(int(lts[li[0]]))), time.strftime('%Y-%m-%d',time.gmtime(int(lts[li[-1]]))), flush=True)
L_al=lpg[li]; W_al=wpg[wi]
c=np.corrcoef(L_al,W_al)[0,1]; print("两书每锚相关", round(float(c),3), flush=True)
blend=0.5*L_al+0.5*W_al
def sim(x, gross, shr=1.0, ladder=False, baseline=False, seed=11):
    x=x-x.mean()*(1-shr); rng=np.random.RandomState(seed); L_=180; nb=len(x)//L_; NY=2190; nbk=NY//L_+1
    hit=0; ann=[]
    for _ in range(2000):
        idx=rng.randint(0,nb,nbk); path=np.concatenate([x[i*L_:(i+1)*L_] for i in idx])[:NY]/1e4
        nav=1.0; peak=1.0; mult=1.0; minnav=1.0; h=False
        for r in path:
            dd=nav/peak-1
            if ladder:
                if dd<=-0.20: mult=0.3
                elif dd<=-0.15: mult=0.5
                elif dd<=-0.10: mult=0.7
                elif dd>=-0.08: mult=1.0
            nav*=1+gross*mult*r; peak=max(peak,nav); minnav=min(minnav,nav)
            trig = (nav<=0.75) if baseline else (nav/peak-1<=-0.25)
            if trig: h=True
        hit+=h; ann.append(nav-1)
    return round(hit/2000,3), round(float(np.median(ann)),3), round(float(np.percentile(ann,5)),3)
res={}
for nm,x in (("在役S1",L_al),("宽书d30",W_al),("50-50混合",blend)):
    for gross in (2.0,2.5,3.0):
        row={}
        for shr in (1.0,0.55):
            row[f"基线_shr{shr}"]=sim(x,gross,shr)
            row[f"阶梯_shr{shr}"]=sim(x,gross,shr,ladder=True)
            row[f"年初基线线_shr{shr}"]=sim(x,gross,shr,baseline=True)
        res[f"{nm}@{gross}"]=row; print(nm, gross, json.dumps(row,ensure_ascii=False), flush=True)
json.dump(res,open(f"{PD}/killline_levers.json","w"),indent=1,ensure_ascii=False)
