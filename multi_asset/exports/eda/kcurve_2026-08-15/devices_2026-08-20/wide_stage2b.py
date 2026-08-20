"""忠实宽书 stage2: OOS king(kcurve, ts精确对齐) + 面板 rev24/fund + 重建 qv4h → 组书 → 风控四臂。
【自校验门, 不过不读风控数字】: sel≈216(±40) / gross_pos≈1.378(±0.15) / turnover≈0.0075(±0.004) / w3尾部≈[.21,.12,.68](±0.15)
【风控判据, 冻结先于看数】宽书是否需要止损层: S1 vs S0 须 ①maxDD 降幅≥10% ②净额代价≤5% ③逐年劣化年份≤1
"""
import numpy as np, json
from scipy.stats import rankdata
K='/mnt/storage/private/work_hsy/w3lane/kcurve'
P=np.load(f'{K}/data/wide_panel_4h_v1.npz', allow_pickle=True)
pts=np.asarray(P['ts']).astype('int64'); pts=pts//1000 if pts[0]>2e10 else pts
Y4=P['Y4']; elig=P['elig']; rev24=P['f_rev_24h']; fe=P['f_fund_ema']; fn=P['f_fund_now']
S1F=np.load(f'{K}/wide_faithful_stage1.npz', allow_pickle=True)
KSLOW=S1F['king']
qv4h=S1F['qv4h']
M=np.load(f'{K}/exports_train/kcurve_meta_K400_s2027.npz', allow_pickle=True)
ets=np.asarray(M['E_ts']).astype('int64'); ets=ets//1000 if ets[0]>2e10 else ets
yrs=M['yrs']; MEM=M['members']
pred=np.full((len(ets), Y4.shape[1]), np.nan, np.float32)
for y in (2023,2024,2025,2026):
    a=np.load(f'{K}/exports_train/kcurve_pred_K400_s2027_{y}.npy'); m=(yrs==y)
    pred[m]=a[m] if a.shape==pred.shape else a[:m.sum()]
pos={int(t):i for i,t in enumerate(ets)}
midx=np.array([pos.get(int(t),-1) for t in pts])
import datetime
YR=np.array([datetime.datetime.utcfromtimestamp(int(t)).year for t in pts])
n,N=Y4.shape
QMIN,CAP,ALPHA,BAND,LOOK,SELMIN=250000.,2.5,0.1,0.00025,900,80
COST_B=[(-0.25,5.0,0.85),(0.5,6.0,0.75),(2.0,8.0,0.55)]
DEPTH,COOL=-0.25,42
def xz(v):
    ok=np.isfinite(v); out=np.full(len(v),np.nan)
    if ok.sum()>=10: out[ok]=rankdata(v[ok])/max(ok.sum()-1,1)-0.5
    return out
def run(mode, diag=False):
    H=np.zeros(N); LR={'king':[],'rev24':[],'fund':[]}
    Pi=np.ones(N); sh=np.zeros(N); cb=np.zeros(N)
    cnt=np.zeros(N,int); su=np.full(N,-1); fires=0
    g=np.zeros(n); c=np.zeros(n); car=np.zeros(n); trn=np.zeros(n); sels=[]; gps=[]; w3l=None
    for i in range(n):
        j=midx[i]
        if j<0: continue
        m=np.asarray(MEM[j],int); m=m[(m<N)]
        m=m[elig[i][m]]
        if len(m)<SELMIN: continue
        q=qv4h[i,m]; sel=q>=QMIN
        if sel.sum()<SELMIN: continue
        if len(LR['king'])>=LOOK:
            r=np.stack([np.array(LR[l][-LOOK:]) for l in ('king','rev24','fund')])
            s_=np.maximum(r.mean(1)/(r.std(1)+1e-9),0.0); w3=s_/s_.sum() if s_.sum()>0 else np.array([1/3]*3)
        else: w3=np.array([1/3]*3)
        w3l=w3
        lz={'king':xz(KSLOW[i][m]),'rev24':xz(-rev24[i,m]),'fund':xz(fe[i,m])}
        z=w3[0]*np.nan_to_num(lz['king'])+w3[1]*np.nan_to_num(lz['rev24'])+w3[2]*np.nan_to_num(lz['fund'])
        w=np.where(sel,z,0.0); w=w-w[sel].mean()
        gg=np.abs(w).sum()
        if gg<1e-9: continue
        w/=gg; cw=CAP/max(int(sel.sum()),1); w=np.clip(w,-cw,cw)
        g2=np.abs(w).sum()
        if g2>1e-9: w/=g2
        tgt=np.zeros(N); tgt[m]=w
        if mode!='S0':
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
        trn[i]=float(np.abs(tr).sum()); sels.append(int(sel.sum())); gps.append(float(np.abs(sm).sum()))
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
        if mode!='S0':
            need=2 if mode!='S2' else 1
            cand=(np.abs(sh)>1e-12)&(dep<=DEPTH)&(su<=i)
            if mode=='S4':
                fnd=np.nan_to_num(fn[i]); cand=cand&(sm<0)&(fnd>=0.0002)
            cnt=np.where(cand,cnt+1,0); fr2=cnt>=need
            if fr2.any(): su[fr2]=i+COOL; cnt[fr2]=0; fires+=int(fr2.sum())
        H=sm; Pi=Pi*(1.0+yv)
    ok=g!=0; net=(g-c+car)[ok]; yy=YR[ok]
    cum=np.cumsum(net); dd=cum-np.maximum.accumulate(cum)
    s5=np.sort(net)[:max(1,len(net)//20)]
    out={'n':int(ok.sum()),'net':round(float(net.mean()),3),'sharpe':round(float(net.mean()/net.std(ddof=1)*np.sqrt(6*365)),2),
         'by_year':{int(y_):round(float(net[yy==y_].mean()),3) for y_ in sorted(set(yy.tolist()))},
         'ES5':round(float(s5.mean()),1),'maxDD':round(float(-dd.min()),0),'turnover':round(float(trn[ok].mean()),5),'fires':fires}
    if diag: out['selftest']={'sel':round(float(np.mean(sels[-500:])),0),'gross_pos':round(float(np.mean(gps[-500:])),4),'w3_last':[round(float(x),3) for x in (w3l if w3l is not None else [0,0,0])]}
    return out
res={}
r0=run('S0',diag=True); res['S0']=r0
st=r0['selftest']
print('自校验: sel',st['sel'],'(需216±40) gross_pos',st['gross_pos'],'(需1.378±0.15) turnover',r0['turnover'],'(需0.0075±0.004) w3',st['w3_last'],'(需≈[.21,.12,.68])', flush=True)
PASS=(abs(st['sel']-216)<=40) and (abs(st['gross_pos']-1.378)<=0.15) and (abs(r0['turnover']-0.0075)<=0.004)
print('SELFTEST_PASS =', PASS, flush=True)
print('S0', json.dumps(r0,ensure_ascii=False), flush=True)
for mode in ('S1','S2','S4'):
    res[mode]=run(mode); print(mode, json.dumps(res[mode],ensure_ascii=False), flush=True)
if PASS:
    S0,S1=res['S0'],res['S1']
    worse=sum(1 for y_ in S1['by_year'] if S1['by_year'][y_]<S0['by_year'][y_])
    res['GATE']={'maxDD_cut':round(1-S1['maxDD']/max(S0['maxDD'],1e-9),3),'net_cost':round(1-S1['net']/max(S0['net'],1e-9),3),
                 'years_worse':worse,'NEED_STOP':bool((1-S1['maxDD']/S0['maxDD'])>=0.10 and (1-S1['net']/S0['net'])<=0.05 and worse<=1)}
    print('GATE', json.dumps(res['GATE'],ensure_ascii=False), flush=True)
res['selftest_pass']=bool(PASS)
json.dump(res,open(f'{K}/wide_stage2_slowking.json','w'))
