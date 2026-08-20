"""腿权重臂(P3 §集中度轴, 预注册判据冻结): 对照=现行 msharpe(look900, 无帽);
A=cap50(w_fund≤0.5, 超额按比例归 king/rev) / B=look450 / C=cap50+look450 / D=等权1/3 / E=在役式固定(king.595/rev.202/fund.202)
判据(P3 冻结): 采纳需 全史夏普 ≥ 基线−0.05 且 最差月改善 ≥+0.5 bps/锚 且 2026-08切片 ≥ 基线−0.5。
附: 逐年 + 挤压锚(实盘<−50bps 同锚, 以 2026-08-20 各锚为例)切片。kcurve OOS king 臂。"""
import numpy as np, json
exec(open('/mnt/storage/private/work_hsy/w3lane/kcurve/wide_stage2.py').read().split('def run(')[0])
import datetime
MON=np.array([datetime.datetime.utcfromtimestamp(int(t)).strftime('%Y-%m') for t in pts])
def run(mode):
    H=np.zeros(N); LR={'king':[],'rev24':[],'fund':[]}
    g=np.zeros(n); c=np.zeros(n); car=np.zeros(n); W3=np.full((n,3),np.nan)
    look=450 if mode in ('B','C') else 900
    for i in range(n):
        j=midx[i]
        if j<0: continue
        m=np.asarray(MEM[j],int); m=m[(m<N)]; m=m[elig[i][m]]
        if len(m)<SELMIN: continue
        q=qv4h[i,m]; sel=q>=QMIN
        if sel.sum()<SELMIN: continue
        if mode=='D': w3=np.array([1/3]*3)
        elif mode=='E': w3=np.array([.595,.202,.202])
        elif len(LR['king'])>=look:
            r=np.stack([np.array(LR[l][-look:]) for l in ('king','rev24','fund')])
            s_=np.maximum(r.mean(1)/(r.std(1)+1e-9),0.0); w3=s_/s_.sum() if s_.sum()>0 else np.array([1/3]*3)
        else: w3=np.array([1/3]*3)
        if mode in ('A','C') and w3[2]>0.5:
            ex=w3[2]-0.5; base=w3[0]+w3[1]
            w3=np.array([w3[0]+ex*(w3[0]/base if base>0 else .5), w3[1]+ex*(w3[1]/base if base>0 else .5), 0.5])
        W3[i]=w3
        lz={'king':xz(pred[j][m]),'rev24':xz(-rev24[i,m]),'fund':xz(fe[i,m])}
        z=w3[0]*np.nan_to_num(lz['king'])+w3[1]*np.nan_to_num(lz['rev24'])+w3[2]*np.nan_to_num(lz['fund'])
        w=np.where(sel,z,0.0); w=w-w[sel].mean()
        gg=np.abs(w).sum()
        if gg<1e-9: continue
        w/=gg; cw=CAP/max(int(sel.sum()),1); w=np.clip(w,-cw,cw)
        g2=np.abs(w).sum()
        if g2>1e-9: w/=g2
        tgt=np.zeros(N); tgt[m]=w
        sm=H+ALPHA*(tgt-H); tr=sm-H
        sm=np.where(np.abs(tr)<BAND,H,sm); tr=sm-H
        tiers=np.full(len(m),2,np.int8); tiers[q>=1e6]=1; tiers[q>=5e6]=0
        ta=np.abs(tr[m])
        c[i]=float(sum(ta[tiers==t].sum()*(fr*mk+(1-fr)*tk) for t,(mk,tk,fr) in enumerate(COST_B)))
        yv=np.nan_to_num(Y4[i],nan=0.0)
        g[i]=float((sm*yv).sum()*1e4)
        car[i]=float((sm[m]*np.nan_to_num(fn[i,m],nan=0.0)*0.5).sum()*1e4)
        for l in ('king','rev24','fund'):
            zz=np.nan_to_num(lz[l]); gl=np.abs(zz).sum()
            LR[l].append(float((zz/gl*yv[m]).sum()*1e4) if gl>1e-9 else 0.0)
        H=sm
    ok=g!=0; net=(g-c+car)[ok]; yy=YR[ok]; mm=MON[ok]
    months={}
    for u in sorted(set(mm.tolist())):
        months[u]=float(net[mm==u].mean())
    worst_m=min(months.items(), key=lambda x:x[1])
    aug26=months.get('2026-08', float('nan'))
    cum=np.cumsum(net); dd=cum-np.maximum.accumulate(cum)
    w3m=np.nanmean(W3[ok],0)
    return {'net':round(float(net.mean()),3),'sharpe':round(float(net.mean()/net.std(ddof=1)*np.sqrt(6*365)),2),
            'by_year':{int(y_):round(float(net[yy==y_].mean()),3) for y_ in sorted(set(yy.tolist()))},
            'worst_month':[worst_m[0],round(worst_m[1],2)],'aug2026':round(aug26,2),
            'maxDD':round(float(-dd.min()),0),'ES5':round(float(np.sort(net)[:len(net)//20].mean()),1),
            'w3_mean':[round(float(x),3) for x in w3m]}
res={}
for mode in ('BASE','A','B','C','D','E'):
    res[mode]=run(mode); print(mode, json.dumps(res[mode],ensure_ascii=False), flush=True)
B=res['BASE']
for k in ('A','B','C','D','E'):
    r=res[k]
    res[k]['GATE']={'sharpe_ok':r['sharpe']>=B['sharpe']-0.05,'worst_month_gain':round(r['worst_month'][1]-B['worst_month'][1],2),
                    'aug_ok':r['aug2026']>=B['aug2026']-0.5,
                    'PASS':bool(r['sharpe']>=B['sharpe']-0.05 and (r['worst_month'][1]-B['worst_month'][1])>=0.5 and r['aug2026']>=B['aug2026']-0.5)}
    print(k,'GATE',json.dumps(res[k]['GATE'],ensure_ascii=False),flush=True)
json.dump(res,open('/mnt/storage/private/work_hsy/w3lane/kcurve/wide_legweight_arms.json','w'))
