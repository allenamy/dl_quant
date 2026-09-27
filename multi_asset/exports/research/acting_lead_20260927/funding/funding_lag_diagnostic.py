#!/usr/bin/env python3
"""Frozen predicate in funding_lag_prereg.md. Read-only remote CPU, stdout only."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[k]='1'
import hashlib,json,time,resource
import numpy as np
from scipy.stats import rankdata

T0=time.time()
EXPECTED={'42':'b80a64b21978c032b1669587a2b91c747586956209a9878a498f6d16f64f85bf','2027':'173c535bbacc9460e7125a8220ab1f7189346d6158eff4ed26d18f182f576ff3'}
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def rr(v):return rankdata(v,method='average')/len(v)
def residual(C,x):return x-C@np.linalg.lstsq(C,x,rcond=None)[0]
def cor(x,y):
    d=np.linalg.norm(x)*np.linalg.norm(y)
    return float(x@y/d) if d>1e-20 else np.nan
def summ(a,days):
    ds,inv=np.unique(days,return_inverse=True)
    vals=np.bincount(inv,weights=a)/np.bincount(inv)
    # Circular blocks span calendar time including missing population days.
    ax=np.arange(ds.min(),ds.max()+1); x=np.full(len(ax),np.nan);x[ds-ax[0]]=vals
    rng=np.random.default_rng(20260927); b=[]
    for _ in range(2000):
        starts=rng.integers(0,len(ax),int(np.ceil(len(ax)/30)))
        idx=((starts[:,None]+np.arange(30))%len(ax)).ravel()[:len(ax)]
        b.append(float(np.nanmean(x[idx])))
    b=np.array(b);se=float(np.std(b,ddof=1))
    return {'mean':float(vals.mean()),'ci95':np.quantile(b,[.025,.975]).tolist(),'bootstrap_se':se,'MDE_80pct_approx':2.8*se,'active_days':len(ds),'calendar_days':len(ax),'anchors':len(a)}

out={'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'repository_head':'3b4a2815ad4b8d45ee09ed8b69222e04b5885301','prereg_sha256':'c554c0cf57990df2b9c954caf4725adb58ac21c54207986b153d6f1a7b7475b1','statistic':'Within-anchor partial Pearson / partial rank Pearson (Spearman); equal anchor within UTC day then equal day; 30 calendar day circular blocks','per_seed':{},'limitations':['Conditional diagnostic, not EMA intervention or deployable PnL','Both seed populations share market outcomes','Population W24H is inherited, not independently regenerated here','No September outcomes; final population at 2026-08-30 20Z','Planted controls have exact conditional correlation by construction: instrument calibration, not a real-data power guarantee']}
for seed,exp in EXPECTED.items():
    p=f'/workspace/uplift_r3_2026-09-13/L2/out/L2N_data_s{seed}.npz'
    h=sha(p);assert h==exp,(seed,'SHA mismatch',h)
    z=np.load(p,allow_pickle=False)
    E=z['E'];day=z['day'];year=z['year'];F=z['F'];K=z['KZ'];Y=z['rA'];ii=z['i'];names=z['n'];SA=z['SA'];h0=int(np.flatnonzero(z['shiftA']==0)[0])
    assert np.array_equal(Y,SA[:,h0],equal_nan=True),'target absolute h0 alignment'
    assert np.all(E%14400==0) and np.all(day==E//86400),'anchor grid'
    assert np.all(F[:,7]<0),'population must have fund z < 0'
    assert np.all(np.diff(E)>=0),'rows not ordered'
    assert len(np.unique(np.column_stack([E,names]),axis=0))==len(E),'duplicate name anchor'
    vals=[];drops={};rng=np.random.default_rng(20260927)
    bounds=np.r_[0,np.flatnonzero(np.diff(E))+1,len(E)]
    for l,u in zip(bounds[:-1],bounds[1:]):
        ok=np.isfinite(Y[l:u])&np.isfinite(F[l:u][:,[4,7,8]]).all(1)&np.isfinite(K[l:u])
        f=F[l:u][ok];y=Y[l:u][ok];k=K[l:u][ok]
        if len(y)<20:drops['n_lt20']=drops.get('n_lt20',0)+1;continue
        assert len(set(ii[l:u]))==1,'one E must map to one label index'
        ef=rr(f[:,7]);C=np.column_stack([np.ones(len(y)),ef,rr(k),rr(f[:,4])]);g=rr(f[:,8])-ef;x=residual(C,g)
        yp=residual(C,y);ys=residual(C,rr(y))
        if np.linalg.norm(x)<1e-10 or np.linalg.norm(yp)<1e-10 or np.linalg.norm(ys)<1e-10:
            drops['degenerate']=drops.get('degenerate',0)+1;continue
        # Independent randomized nuisance; orthogonalization pins exact 0 and .015.
        xu=x/np.linalg.norm(x);noise=residual(C,rng.permutation(yp));noise-=xu*(xu@noise);noise/=np.linalg.norm(noise)
        planted=.015*xu+np.sqrt(1-.015**2)*noise
        vals.append([int(E[l]),int(day[l]),int(year[l]),len(y),cor(x,yp),cor(x,ys),cor(x,planted),cor(x,noise)])
    v=np.array(vals);groups={}
    for lab,m in [('pre2026',v[:,2]<2026),('2026',v[:,2]==2026)]+[(str(q),v[:,2]==q) for q in sorted(set(v[:,2].astype(int))) if q!=2026]:
        d={'rows':int(v[m,3].sum())}
        for name,j in [('pearson',4),('spearman',5),('positive_control',6),('negative_control',7)]:d[name]=summ(v[m,j],v[m,1].astype(int))
        # Floating-point controls need absolute tolerance around exact 0 / planted .015.
        d['controls_pass']=d['positive_control']['ci95'][0]>0 and abs(d['negative_control']['mean'])<1e-12 and max(abs(np.array(d['negative_control']['ci95'])))<1e-12
        groups[lab]=d
    years=[str(q) for q in sorted(set(v[:,2].astype(int)))]
    support=all(groups[g][m]['ci95'][0]>0 for g in ('pre2026','2026') for m in ('pearson','spearman')) and all(groups[g][m]['mean']>0 for g in years for m in ('pearson','spearman'))
    refuted=any(groups[g][m]['ci95'][1]<0 for g in ('pre2026','2026') for m in ('pearson','spearman'))
    out['per_seed'][seed]={'path':p,'sha256':h,'bytes':os.path.getsize(p),'input_rows':len(E),'h0_absolute_alignment':True,'first_anchor':int(v[:,0].min()),'last_anchor':int(v[:,0].max()),'dropped_anchors':drops,'groups':groups,'predicate':'SUPPORT' if support else 'DIRECTION_REFUTED_IN_AT_LEAST_ONE_ERA' if refuted else 'NOT_ESTABLISHED'}
    del z,F,K,Y,SA
out['wall_seconds']=time.time()-T0;out['rss_max_kb']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
out['overall']='SUPPORT' if all(r['predicate']=='SUPPORT' for r in out['per_seed'].values()) else 'NOT_ESTABLISHED'
print(json.dumps(out,indent=2,allow_nan=False,default=lambda x:x.item() if isinstance(x,np.generic) else str(x)))
