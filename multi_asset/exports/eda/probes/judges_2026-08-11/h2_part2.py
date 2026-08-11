import pandas as pd, numpy as np
from scipy import stats
SP='/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad'
V = pd.read_csv(f'{SP}/h2_daily_table.csv',index_col=0,parse_dates=True)
lag_cols=[c for c in V.columns if c.startswith('L_')]

print('==== BETWEEN-MONTH vs WITHIN-MONTH decomposition ====')
mo_mean = V.groupby('month')[['ic']+lag_cols].mean()
for c in ['L_mabs','L_rv','L_pidx_std','L_trend']:
    rb,pb = stats.spearmanr(mo_mean[c],mo_mean['ic'])
    # within: demean by month, pooled
    v = V[[c,'ic','month']].dropna().copy()
    v['cd']=v[c]-v.groupby('month')[c].transform('mean')
    v['icd']=v['ic']-v.groupby('month')['ic'].transform('mean')
    rw,pw = stats.spearmanr(v['cd'],v['icd'])
    print(f'{c:12s} between-month(n=10) rho={rb:+.3f} p={pb:.3f} | within-month(demeaned,n={len(v)}) rho={rw:+.3f} p={pw:.3f}')

print('\n==== TERCILE SPLIT (pooled, full-sample terciles — descriptive) ====')
for c in ['L_mabs','L_rv','L_pidx_std','L_trend','L_oi_chg','L_ic']:
    v=V[[c,'ic']].dropna()
    q=v[c].rank(pct=True)
    lo=v.ic[q<=1/3].mean(); mid=v.ic[(q>1/3)&(q<=2/3)].mean(); hi=v.ic[q>2/3].mean()
    nlo=(q<=1/3).sum(); nhi=(q>2/3).sum()
    t,pv=stats.ttest_ind(v.ic[q>2/3],v.ic[q<=1/3])
    print(f'{c:12s} lo={lo:+.4f} mid={mid:+.4f} hi={hi:+.4f}  hi-lo={hi-lo:+.4f} (t={t:+.2f} p={pv:.3f}, n={nlo}/{nhi})')

print('\n==== HONEST CAUSAL GATING (expanding-quantile thresholds, burn-in 40 days) ====')
V=V.sort_index()
def gate_sim(col, mode, q, burn=40):
    """mode: 'above' keep day if L_col > expanding q-quantile of PAST L_col values"""
    x=V[col].values; ic=V['ic'].values; months=V['month'].values
    keepmask=np.zeros(len(V),bool); active=np.zeros(len(V),bool)
    for i in range(len(V)):
        if i<burn or np.isnan(x[i]): continue
        past=x[:i]; past=past[~np.isnan(past)]
        if len(past)<burn: continue
        thr=np.quantile(past,q); active[i]=True
        keepmask[i] = (x[i]>thr) if mode=='above' else (x[i]<thr)
    return keepmask,active

def report(name,keepmask,active):
    ic=V['ic'].values; months=V['month'].values
    a_ic=ic[active]; g_ic=ic[keepmask]
    print(f'\n-- {name}: kept {keepmask.sum()}/{active.sum()} active days --')
    print(f'   ungated(active-days) pooled dailyIC={np.nanmean(a_ic):+.4f} | gated pooled dailyIC={np.nanmean(g_ic):+.4f}  lift={np.nanmean(g_ic)-np.nanmean(a_ic):+.4f}')
    rows=[]
    for mo in sorted(set(months)):
        am=(months==mo)&active; km=(months==mo)&keepmask
        if am.sum()==0: continue
        rows.append((mo,am.sum(),km.sum(),np.nanmean(ic[am]),np.nanmean(ic[km]) if km.sum()>0 else np.nan))
    for mo,na,nk,ia,ik in rows:
        print(f'   {mo}: days {nk:2d}/{na:2d}  IC ungated={ia:+.4f}  gated={ik:+.4f}' if not np.isnan(ik) else f'   {mo}: days 0/{na:2d}  IC ungated={ia:+.4f}  gated=NO DAYS TRADED')
    floors_u=min(r[3] for r in rows); vals=[r[4] for r in rows if not np.isnan(r[4])]
    floors_g=min(vals) if vals else np.nan
    print(f'   monthly floor: ungated={floors_u:+.4f} -> gated={floors_g:+.4f}')

for col,mode,q in [('L_mabs','above',0.5),('L_rv','above',0.5),('L_pidx_std','above',0.5),('L_mabs','above',1/3)]:
    k,a=gate_sim(col,mode,q); report(f'{col} {mode} expanding-q{q:.2f}',k,a)

# 2-descriptor AND gate: L_mabs above median AND L_pidx_std above median
k1,a1=gate_sim('L_mabs','above',0.5); k2,a2=gate_sim('L_pidx_std','above',0.5)
report('L_mabs>med AND L_pidx_std>med', k1&k2, a1&a2)

# weighting variant: weight = expanding pct-rank of L_mabs
print('\n==== WEIGHTING variant (weight day by expanding pct-rank of L_mabs) ====')
x=V['L_mabs'].values; ic=V['ic'].values; months=V['month'].values
w=np.full(len(V),np.nan)
for i in range(len(V)):
    if i<40 or np.isnan(x[i]): continue
    past=x[:i]; past=past[~np.isnan(past)]
    if len(past)<40: continue
    w[i]=(past<x[i]).mean()
act=~np.isnan(w)
print(f'active days={act.sum()}  unweighted IC={np.nanmean(ic[act]):+.4f}  rank-weighted IC={np.nansum(ic[act]*w[act])/np.nansum(w[act]):+.4f}')
for mo in sorted(set(months)):
    m=(months==mo)&act
    if m.sum()==0: continue
    print(f'   {mo}: unw={np.nanmean(ic[m]):+.4f}  wgt={np.nansum(ic[m]*w[m])/np.nansum(w[m]):+.4f}  ndays={m.sum()}')
