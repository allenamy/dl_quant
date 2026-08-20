"""宽书止损参数网格(kcurve OOS king 臂): (depth -20/-25/-30)×(confirm 1/2)×(cool 21/42/84)。
判据冻结: 前沿 = maxDD 降幅最大 s.t. 净额代价≤10% 且逐年劣化≤1年。基线=无止损。"""
import numpy as np, json
exec(open('/mnt/storage/private/work_hsy/w3lane/kcurve/wide_stage2.py').read().split('def run(')[0])
def run(depth, need, cool):
    H=np.zeros(N); LR={'king':[],'rev24':[],'fund':[]}
    Pi=np.ones(N); sh=np.zeros(N); cb=np.zeros(N)
    cnt=np.zeros(N,int); su=np.full(N,-1); fires=0
    g=np.zeros(n); c=np.zeros(n); car=np.zeros(n); trn=np.zeros(n)
    for i in range(n):
        j=midx[i]
        if j<0: continue
        m=np.asarray(MEM[j],int); m=m[(m<N)]; m=m[elig[i][m]]
        if len(m)<SELMIN: continue
        q=qv4h[i,m]; sel=q>=QMIN
        if sel.sum()<SELMIN: continue
        if len(LR['king'])>=LOOK:
            r=np.stack([np.array(LR[l][-LOOK:]) for l in ('king','rev24','fund')])
            s_=np.maximum(r.mean(1)/(r.std(1)+1e-9),0.0); w3=s_/s_.sum() if s_.sum()>0 else np.array([1/3]*3)
        else: w3=np.array([1/3]*3)
        lz={'king':xz(pred[j][m]),'rev24':xz(-rev24[i,m]),'fund':xz(fe[i,m])}
        z=w3[0]*np.nan_to_num(lz['king'])+w3[1]*np.nan_to_num(lz['rev24'])+w3[2]*np.nan_to_num(lz['fund'])
        w=np.where(sel,z,0.0); w=w-w[sel].mean()
        gg=np.abs(w).sum()
        if gg<1e-9: continue
        w/=gg; cw=CAP/max(int(sel.sum()),1); w=np.clip(w,-cw,cw)
        g2=np.abs(w).sum()
        if g2>1e-9: w/=g2
        tgt=np.zeros(N); tgt[m]=w
        if depth is not None:
            bl=su>i
            if bl.any(): tgt[bl]=0.0
        sm=H+ALPHA*(tgt-H); tr=sm-H
        sm=np.where(np.abs(tr)<BAND,H,sm); tr=sm-H
        tiers=np.full(len(m),2,np.int8); tiers[q>=1e6]=1; tiers[q>=5e6]=0
        ta=np.abs(tr[m])
        cst=float(sum(ta[tiers==t].sum()*(fr*mk+(1-fr)*tk) for t,(mk,tk,fr) in enumerate(COST_B)))
        yv=np.nan_to_num(Y4[i],nan=0.0)
        g[i]=float((sm*yv).sum()*1e4); c[i]=cst
        car[i]=float((sm[m]*np.nan_to_num(fn[i,m],nan=0.0)*0.5).sum()*1e4)
        trn[i]=float(np.abs(tr).sum())
        for l in ('king','rev24','fund'):
            zz=np.nan_to_num(lz[l]); gl=np.abs(zz).sum()
            LR[l].append(float((zz/gl*yv[m]).sum()*1e4) if gl>1e-9 else 0.0)
        nsh=np.where(Pi>1e-12,sm/Pi,0.0)
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
        if depth is not None:
            cand=(np.abs(sh)>1e-12)&(dep<=depth)&(su<=i)
            cnt=np.where(cand,cnt+1,0); fr2=cnt>=need
            if fr2.any(): su[fr2]=i+cool; cnt[fr2]=0; fires+=int(fr2.sum())
        H=sm; Pi=Pi*(1.0+yv)
    ok=g!=0; net=(g-c+car)[ok]; yy=YR[ok]
    cum=np.cumsum(net); dd=cum-np.maximum.accumulate(cum)
    return {'net':round(float(net.mean()),3),'maxDD':round(float(-dd.min()),0),
            'ES5':round(float(np.sort(net)[:len(net)//20].mean()),1),
            'by_year':{int(y_):round(float(net[yy==y_].mean()),3) for y_ in sorted(set(yy.tolist()))},
            'fires':fires}
res={'S0':run(None,0,0)}
print('S0', json.dumps(res['S0'],ensure_ascii=False), flush=True)
for dp in (-0.20,-0.25,-0.30):
    for nd in (1,2):
        for cl in (21,42,84):
            k=f'd{int(-dp*100)}_n{nd}_c{cl}'
            res[k]=run(dp,nd,cl)
            print(k, json.dumps(res[k],ensure_ascii=False), flush=True)
S0=res['S0']
front=[]
for k,r in res.items():
    if k=='S0': continue
    cost=1-r['net']/S0['net']; cut=1-r['maxDD']/S0['maxDD']
    worse=sum(1 for y_ in r['by_year'] if r['by_year'][y_]<S0['by_year'][y_]-1e-9)
    if cost<=0.10 and worse<=1: front.append((k,round(cut,3),round(cost,3),worse))
front.sort(key=lambda x:-x[1])
print('FRONTIER(判据内, 按maxDD降幅):', json.dumps(front[:6],ensure_ascii=False), flush=True)
json.dump({'res':res,'frontier':front},open('/mnt/storage/private/work_hsy/w3lane/kcurve/wide_stop_grid.json','w'))
