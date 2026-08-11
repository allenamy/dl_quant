import numpy as np
import pandas as pd
from scipy import stats

CSV = '/Users/haosiyu/Desktop/quant_research/exports/final_l01/y600_backtest_dataset.csv'
df = pd.read_csv(CSV)
df = df.sort_values('timestamp_ms').reset_index(drop=True)
df['dt'] = pd.to_datetime(df['timestamp_ms'], unit='ms', utc=True)
df['day'] = df['dt'].dt.strftime('%Y-%m-%d')

# ---------- non-overlap subsample: greedy >=600s apart (stride 180 -> 720s spacing) ----------
ts = df['timestamp_ms'].values
keep = np.zeros(len(df), bool)
last = -np.inf
for i, t in enumerate(ts):
    if t - last >= 600_000:
        keep[i] = True
        last = t
no = df[keep].reset_index(drop=True)
print(f'non-overlap rows: {len(no)} of {len(df)}  (spacing mode: {pd.Series(np.diff(no.timestamp_ms)).mode()[0]/1000:.0f}s)')

def ar1(x):
    x = np.asarray(x, float)
    if len(x) < 8: return np.nan
    return np.corrcoef(x[:-1], x[1:])[0, 1]

def vr(x, q):
    """Variance ratio: Var(sum of q consecutive non-overlap 600s returns)/(q*Var(single)). >1 trending, <1 mean-reverting."""
    x = np.asarray(x, float)
    if len(x) < q * 4: return np.nan
    n = len(x) // q * q
    agg = x[:n].reshape(-1, q).sum(axis=1)
    v1 = np.var(x, ddof=1)
    if v1 <= 0: return np.nan
    return np.var(agg, ddof=1) / (q * v1)

def ic(sub, pred='y_pred_raw', true='y_true_ret_bps'):
    if len(sub) < 8: return np.nan
    return np.corrcoef(sub[pred], sub[true])[0, 1]

def clean_ic(sub, pred='y_pred_raw', true='y_true_ret_bps'):
    """per-day-CLEAN: corr within each UTC day (non-overlap rows), averaged across days"""
    vals = [ic(g, pred, true) for _, g in sub.groupby('day')]
    vals = [v for v in vals if not np.isnan(v)]
    return (np.mean(vals), len(vals)) if vals else (np.nan, 0)

# =============== (a) per-month AR1 / VR vs monthly IC ===============
print('\n=== (a) per-month state vs IC (non-overlap 720s rows) ===')
rows = []
for m, g in no.groupby('month'):
    y = g['y_true_ret_bps'].values
    # AR1 only across contiguous 720s pairs
    gap = np.diff(g['timestamp_ms'].values)
    ok = np.abs(gap - 720_000) < 5_000
    a1 = np.corrcoef(y[:-1][ok], y[1:][ok])[0, 1]
    cic, nd = clean_ic(g)
    rows.append(dict(month=m, n=len(g), AR1=a1, VR3=vr(y, 3), VR5=vr(y, 5),
                     IC_pool=ic(g), IC_clean=cic, ndays=nd))
A = pd.DataFrame(rows)
print(A.to_string(index=False, float_format=lambda v: f'{v: .4f}'))
for state in ['AR1', 'VR3', 'VR5']:
    for icc in ['IC_pool', 'IC_clean']:
        r, p = stats.spearmanr(A[state], A[icc])
        rp, pp = stats.pearsonr(A[state], A[icc])
        print(f'rank-corr({state}, {icc}) = {r:+.3f} (p={p:.3f}) | pearson {rp:+.3f} (p={pp:.3f})  n=10')

# =============== per-day state table (for b,c) ===============
day_rows = []
for d, g in no.groupby('day'):
    y = g['y_true_ret_bps'].values
    day_rows.append(dict(day=d, month=g['month'].iloc[0], n=len(g),
                         VR3=vr(y, 3), AR1=ar1(y), day_ic=ic(g)))
D = pd.DataFrame(day_rows).sort_values('day').reset_index(drop=True)
D['prior_VR3'] = D['VR3'].shift(1)
D['prior_AR1'] = D['AR1'].shift(1)
# require prior day is actually the calendar prior day
pd_day = pd.to_datetime(D['day'])
D.loc[(pd_day - pd_day.shift(1)).dt.days != 1, ['prior_VR3', 'prior_AR1']] = np.nan
print(f'\ndays total={len(D)}, with valid prior-day state={D.prior_VR3.notna().sum()}')
print('prior_VR3 dist:', D['prior_VR3'].describe()[['mean','25%','50%','75%']].round(3).to_dict())

# =============== (b) causal daily class: trending if prior-day VR3 >= 1 ===============
print('\n=== (b) prior-day VR3 >= 1 -> trending class ===')
no2 = no.merge(D[['day', 'prior_VR3', 'prior_AR1']], on='day')
no2['cls'] = np.where(no2['prior_VR3'] >= 1.0, 'TREND', 'CHOP')
no2.loc[no2['prior_VR3'].isna(), 'cls'] = 'NA'
out = []
for m, g in no2[no2.cls != 'NA'].groupby('month'):
    r = dict(month=m)
    for c in ['TREND', 'CHOP']:
        s = g[g.cls == c]
        cic, nd = clean_ic(s)
        r[f'{c}_ICpool'] = ic(s); r[f'{c}_ICclean'] = cic; r[f'{c}_ndays'] = nd
    out.append(r)
B = pd.DataFrame(out)
print(B.to_string(index=False, float_format=lambda v: f'{v: .4f}'))
for c in ['TREND', 'CHOP']:
    s = no2[no2.cls == c]
    cic, nd = clean_ic(s)
    dic = D.merge(s[['day']].drop_duplicates(), on='day')['day_ic'].dropna()
    t, p = stats.ttest_1samp(dic, 0)
    print(f'POOLED {c}: ICpool={ic(s):+.4f} ICclean={cic:+.4f} ndays={nd} rows={len(s)} '
          f'day-IC mean={dic.mean():+.4f} t={t:+.2f} p={p:.4f} frac_days={nd/D.prior_VR3.notna().sum():.2%}')
# TREND-CHOP difference significance (two-sample t on per-day ICs)
di_t = D[D.day.isin(no2[no2.cls=='TREND'].day.unique())]['day_ic'].dropna()
di_c = D[D.day.isin(no2[no2.cls=='CHOP'].day.unique())]['day_ic'].dropna()
t, p = stats.ttest_ind(di_t, di_c, equal_var=False)
print(f'TREND vs CHOP per-day IC diff: {di_t.mean()-di_c.mean():+.4f} t={t:+.2f} p={p:.4f}')

# alt state: prior-day AR1 >= 0
print('\n--- alt gate: prior-day AR1 >= 0 ---')
no2['cls2'] = np.where(no2['prior_AR1'] >= 0, 'TREND', 'CHOP')
no2.loc[no2['prior_AR1'].isna(), 'cls2'] = 'NA'
for c in ['TREND', 'CHOP']:
    s = no2[no2.cls2 == c]
    cic, nd = clean_ic(s)
    print(f'POOLED {c}: ICpool={ic(s):+.4f} ICclean={cic:+.4f} ndays={nd} rows={len(s)}')

# =============== (c) flipped signal on choppy days ===============
print('\n=== (c) choppy-class days: flipped signal (-y_pred) ===')
s = no2[no2.cls == 'CHOP'].copy()
s['neg_pred'] = -s['y_pred_raw']
cic_f, nd = clean_ic(s, pred='neg_pred')
per_day_ic = np.array([ic(g) for _, g in s.groupby('day') if len(g) >= 8])
t, p = stats.ttest_1samp(per_day_ic, 0)
print(f'CHOP flipped: ICpool={ic(s, pred="neg_pred"):+.4f} ICclean={cic_f:+.4f} ndays={nd}')
print(f'CHOP original per-day IC: mean={per_day_ic.mean():+.4f} median={np.median(per_day_ic):+.4f} '
      f'std={per_day_ic.std():.4f} t={t:+.2f} p={p:.4f} | frac days IC<0: {(per_day_ic<0).mean():.2%}')
# by month for choppy flipped
for m, g in s.groupby('month'):
    cic, nd = clean_ic(g, pred='neg_pred')
    print(f'  {m}: flipped ICpool={ic(g, pred="neg_pred"):+.4f} ICclean={cic:+.4f} ndays={nd}')
