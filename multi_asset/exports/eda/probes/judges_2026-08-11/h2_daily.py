import pandas as pd, numpy as np
from scipy import stats

ROOT='/Users/haosiyu/Desktop/quant_research'
df = pd.read_csv(f'{ROOT}/exports/final_l01/y600_backtest_dataset.csv')
df['dt'] = pd.to_datetime(df['datetime_utc'])
df['date'] = df['dt'].dt.date
df = df.sort_values('timestamp_ms').reset_index(drop=True)

# ---- non-overlap subsample (>=600s apart), greedy within each UTC day ----
keep=np.zeros(len(df),bool); last={}
ts_arr=df['timestamp_ms'].values; dates=df['date'].values
for i in range(len(df)):
    d=dates[i]; lt=last.get(d,-1e18)
    if ts_arr[i]-lt>=600000: keep[i]=True; last[d]=ts_arr[i]
no = df[keep]
print('non-overlap rows:',len(no),'days:',no["date"].nunique())

# ---- per-day descriptors + daily CLEAN IC ----
rows=[]
for d,g in no.groupby('date'):
    y=g['y_true_ret_bps'].values; p=g['y_pred_raw'].values
    n=len(y)
    if n<30: continue
    ic = np.corrcoef(p,y)[0,1]
    ic_s = stats.spearmanr(p,y)[0]
    rv = y.std(ddof=1)
    trend = abs(y.sum())/np.abs(y).sum()
    ar1 = np.corrcoef(y[:-1],y[1:])[0,1]
    mabs = np.abs(y).mean()
    rows.append(dict(date=d,n=n,ic=ic,ic_s=ic_s,rv=rv,trend=trend,ar1=ar1,mabs=mabs,
                     month=g['month'].iloc[0]))
D = pd.DataFrame(rows).set_index('date'); D.index=pd.to_datetime(D.index)
print('days with IC:',len(D),' mean n/day:',D.n.mean().round(1))
print('pooled per-day-CLEAN IC (mean of daily):',D.ic.mean().round(4),' daily IC std:',D.ic.std().round(4))
print('daily IC AR1:', np.corrcoef(D.ic.values[:-1],D.ic.values[1:])[0,1].round(3))

# ---- external daily aggregates ----
f = pd.read_csv(f'{ROOT}/data/funding/btcusdt_funding.csv')
f['dt']=pd.to_datetime(f['datetime_utc']); f['date']=f['dt'].dt.normalize()
F = f.groupby('date')['fundingRate'].agg(fund_mean='mean',fund_std='std')

px = pd.read_csv(f'{ROOT}/data/funding/btcusdt_premium_index_5m.csv')
px['dt']=pd.to_datetime(px['datetime_utc']); px['date']=px['dt'].dt.normalize()
P = px.groupby('date')['pidx_close'].agg(pidx_mean='mean',pidx_std='std')

m = pd.read_csv(f'{ROOT}/data/funding/btcusdt_metrics_5m.csv')
m['dt']=pd.to_datetime(m['create_time']); m['date']=m['dt'].dt.normalize()
M = m.groupby('date').agg(oi_last=('sum_open_interest','last'),
                          toptrader_mean=('sum_toptrader_long_short_ratio','mean'),
                          takerls_mean=('sum_taker_long_short_vol_ratio','mean'))
M['oi_chg'] = M['oi_last'].pct_change()
M = M.drop(columns='oi_last')

X = D.join(F,how='left').join(P,how='left').join(M,how='left')

# ---- causal lag-1: prior-day descriptor -> today IC ----
desc_cols=['rv','trend','ar1','mabs','fund_mean','fund_std','pidx_mean','pidx_std','oi_chg','toptrader_mean','takerls_mean']
for c in desc_cols+['ic']:
    X[f'L_{c}'] = X[c].shift(1)   # calendar-consecutive? index is dates; shift by row. check gaps
# gap check: only use rows where prior row is exactly 1 day before
gap_ok = (X.index.to_series().diff().dt.days==1)
X['gap_ok']=gap_ok
print('rows with 1-day-prior available:',int(gap_ok.sum()),'/',len(X))

V = X[X.gap_ok].copy()
lag_cols=[f'L_{c}' for c in desc_cols]+['L_ic']

print('\n==== POOLED Spearman rank-corr: prior-day descriptor vs next-day CLEAN IC ====')
res=[]
for c in lag_cols:
    v=V[[c,'ic']].dropna()
    r,pv=stats.spearmanr(v[c],v['ic'])
    res.append((c,len(v),r,pv))
res.sort(key=lambda t:-abs(t[2]))
for c,n,r,pv in res: print(f'{c:18s} n={n:3d}  rho={r:+.3f}  p={pv:.3f}')

print('\n==== WITHIN-MONTH Spearman (sign consistency) ====')
months=sorted(V.month.unique())
for c,_,r,_ in res:
    per=[]
    for mo in months:
        v=V[V.month==mo][[c,'ic']].dropna()
        if len(v)>=8: per.append((mo,stats.spearmanr(v[c],v['ic'])[0]))
    signs=[np.sign(x[1]) for x in per]
    agree=sum(1 for s in signs if s==np.sign(r))
    detail=' '.join(f'{mo[-2:]}:{rr:+.2f}' for mo,rr in per)
    print(f'{c:18s} pooled={r:+.3f}  same-sign {agree}/{len(per)}  | {detail}')

V.to_csv('/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad/h2_daily_table.csv')
