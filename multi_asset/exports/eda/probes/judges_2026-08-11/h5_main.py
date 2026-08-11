import pandas as pd, numpy as np
from scipy import stats

pd.set_option('display.width', 200)

# ---------- load backtest dataset ----------
df = pd.read_csv('/Users/haosiyu/Desktop/quant_research/exports/final_l01/y600_backtest_dataset.csv')
df = df.sort_values('timestamp_ms').reset_index(drop=True)
df['ts'] = pd.to_datetime(df['timestamp_ms'], unit='ms', utc=True)
df['date'] = df['ts'].dt.date

# ---------- non-overlap subsample (greedy >=600s apart) ----------
ts = df['timestamp_ms'].values
keep = np.zeros(len(ts), bool); last = -10**18
for i, t in enumerate(ts):
    if t - last >= 600_000:
        keep[i] = True; last = t
no = df[keep].copy()
print(f"rows total={len(df)} non-overlap={len(no)}  days={no['date'].nunique()}")

# ---------- per-day-CLEAN IC (both raw and demeaned calibers) ----------
def daily_ic(g):
    if len(g) < 30: return pd.Series({'n': len(g), 'ic_raw': np.nan, 'ic_dm': np.nan})
    return pd.Series({'n': len(g),
                      'ic_raw': np.corrcoef(g['y_pred_raw'], g['y_true_ret_bps'])[0,1],
                      'ic_dm':  np.corrcoef(g['y_pred_demeaned'], g['y_true_demeaned_bps'])[0,1]})
dic = no.groupby('date').apply(daily_ic, include_groups=False).reset_index()
dic = dic.dropna(subset=['ic_raw'])
print(f"per-day-CLEAN pooled: mean ic_raw={dic['ic_raw'].mean():.4f}  mean ic_dm={dic['ic_dm'].mean():.4f}  n_days={len(dic)}")

# choose caliber matching the reported 0.0387
IC = 'ic_raw' if abs(dic['ic_raw'].mean()-0.0387) < abs(dic['ic_dm'].mean()-0.0387) else 'ic_dm'
print(f"using caliber: {IC}")

# ---------- conditioning variables (strictly PRIOR) ----------
# funding: prior 8h print at/before day start (00:00 print is fixed at 00:00, known before first row 00:10)
f = pd.read_csv('/Users/haosiyu/Desktop/quant_research/data/funding/btcusdt_funding.csv')
f['ft'] = pd.to_datetime(f['fundingTime_ms'], unit='ms', utc=True)
f = f.sort_values('ft')

days = pd.to_datetime(pd.Series(sorted(dic['date'].unique()))).dt.tz_localize('UTC')
day_start_ms = days.dt.as_unit('ms').astype('int64').values
fms = f['fundingTime_ms'].values; frate = f['fundingRate'].values
# last print known at day start (+60s tol: 00:00:00.00x prints are known before first row at 00:10)
idx = np.searchsorted(fms, day_start_ms + 60_000, side='right') - 1
assert (idx >= 0).all()
cond = pd.DataFrame({'date': [d.date() for d in days], 'funding_prior': frate[idx]})
cond['abs_funding_prior'] = cond['funding_prior'].abs()

# OI / positioning: prior-DAY aggregates from 5m metrics
m = pd.read_csv('/Users/haosiyu/Desktop/quant_research/data/funding/btcusdt_metrics_5m.csv',
                usecols=['create_time','sum_open_interest','sum_toptrader_long_short_ratio'])
m['t'] = pd.to_datetime(m['create_time'], utc=True)
m['date'] = m['t'].dt.date
md = m.groupby('date').agg(oi_last=('sum_open_interest','last'),
                           tt_ls_mean=('sum_toptrader_long_short_ratio','mean')).sort_index()
md['oi_pct_chg'] = md['oi_last'].pct_change()          # change over that day (close-to-close)
md_shift = md.shift(1)                                 # value AS OF prior day
cond = cond.merge(md_shift[['oi_pct_chg','tt_ls_mean']].rename(
        columns={'oi_pct_chg':'oi_chg_prior_day','tt_ls_mean':'ttls_prior_day'}),
        left_on='date', right_index=True, how='left')

# premium-index vol: prior-day std of 5m pidx_close
p = pd.read_csv('/Users/haosiyu/Desktop/quant_research/data/funding/btcusdt_premium_index_5m.csv',
                usecols=['openTime_ms','pidx_close'])
p['t'] = pd.to_datetime(p['openTime_ms'], unit='ms', utc=True)
p['date'] = p['t'].dt.date
pv = p.groupby('date')['pidx_close'].std().rename('pidx_vol').to_frame().sort_index().shift(1)
cond = cond.merge(pv.rename(columns={'pidx_vol':'pidxvol_prior_day'}),
                  left_on='date', right_index=True, how='left')

D = dic.merge(cond, on='date', how='left')
print(f"days with all conditioners: {D.dropna().shape[0]} / {len(D)}")

# ---------- tercile IC tables ----------
def tercile_table(D, var, ic_col=IC):
    d = D.dropna(subset=[var, ic_col]).copy()
    d['ter'] = pd.qcut(d[var].rank(method='first'), 3, labels=['T1(low)','T2(mid)','T3(high)'])
    g = d.groupby('ter', observed=True).agg(
        n_days=(ic_col,'size'), mean_ic=(ic_col,'mean'), med_ic=(ic_col,'median'),
        std_ic=(ic_col,'std'), lo=(var,'min'), hi=(var,'max'))
    lo_ic = d[d['ter']=='T1(low)'][ic_col]; hi_ic = d[d['ter']=='T3(high)'][ic_col]
    t, pv_ = stats.ttest_ind(hi_ic, lo_ic, equal_var=False)
    print(f"\n=== IC by tercile of {var} ===")
    print(g.round(4))
    print(f"T3-T1 diff={hi_ic.mean()-lo_ic.mean():+.4f}  Welch t={t:.2f} p={pv_:.3f}")
    return d

D.to_csv('/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad/daily_ic_cond.csv', index=False)

for var in ['funding_prior','abs_funding_prior','oi_chg_prior_day','ttls_prior_day','pidxvol_prior_day']:
    tercile_table(D, var)

D.to_csv('/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad/daily_ic_cond.csv', index=False)
no.to_csv('/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad/nonoverlap_rows.csv', index=False)
