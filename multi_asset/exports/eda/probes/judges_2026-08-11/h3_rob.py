import numpy as np
import pandas as pd
from scipy import stats

CSV = '/Users/haosiyu/Desktop/quant_research/exports/final_l01/y600_backtest_dataset.csv'
df = pd.read_csv(CSV).sort_values('timestamp_ms').reset_index(drop=True)
df['day'] = pd.to_datetime(df['timestamp_ms'], unit='ms', utc=True).dt.strftime('%Y-%m-%d')
ts = df['timestamp_ms'].values
keep = np.zeros(len(df), bool); last = -np.inf
for i, t in enumerate(ts):
    if t - last >= 600_000: keep[i] = True; last = t
no = df[keep].reset_index(drop=True)

def vr(x, q=3):
    x = np.asarray(x, float)
    if len(x) < q * 4: return np.nan
    n = len(x) // q * q
    agg = x[:n].reshape(-1, q).sum(1)
    v1 = np.var(x, ddof=1)
    return np.var(agg, ddof=1) / (q * v1) if v1 > 0 else np.nan

def ic(sub, pred='y_pred_raw', true='y_true_ret_bps'):
    return np.corrcoef(sub[pred], sub[true])[0, 1] if len(sub) >= 8 else np.nan

def clean_ic(sub, pred='y_pred_raw', true='y_true_ret_bps'):
    v = [ic(g, pred, true) for _, g in sub.groupby('day')]
    v = [x for x in v if not np.isnan(x)]
    return (np.mean(v), len(v)) if v else (np.nan, 0)

D = []
for d, g in no.groupby('day'):
    y = g['y_true_ret_bps'].values
    D.append(dict(day=d, month=g['month'].iloc[0], VR3=vr(y),
                  AR1=np.corrcoef(y[:-1], y[1:])[0, 1] if len(y) >= 8 else np.nan,
                  day_ic=ic(g)))
D = pd.DataFrame(D).sort_values('day').reset_index(drop=True)
pdd = pd.to_datetime(D['day'])
D['prior_VR3'] = D['VR3'].shift(1); D['prior_AR1'] = D['AR1'].shift(1)
D.loc[(pdd - pdd.shift(1)).dt.days != 1, ['prior_VR3', 'prior_AR1']] = np.nan
no2 = no.merge(D[['day', 'prior_VR3', 'prior_AR1']], on='day')
no2 = no2[no2.prior_VR3.notna()]

print('=== stricter daily gates (pooled across 10 months) ===')
gates = {
    'VR3>=1.0            ': no2.prior_VR3 >= 1.0,
    'VR3>=1.15 (top~25%) ': no2.prior_VR3 >= 1.15,
    'VR3>=1.3  (top~12%) ': no2.prior_VR3 >= 1.3,
    'VR3>=1 & AR1>=0     ': (no2.prior_VR3 >= 1) & (no2.prior_AR1 >= 0),
    'VR3<0.75 (deep chop)': no2.prior_VR3 < 0.75,
}
ndays_all = no2.day.nunique()
for name, m in gates.items():
    s = no2[m]
    cic, nd = clean_ic(s)
    dic = D[D.day.isin(s.day.unique())]['day_ic'].dropna()
    t, p = stats.ttest_1samp(dic, 0) if len(dic) > 3 else (np.nan, np.nan)
    cic_d, _ = clean_ic(s, pred='y_pred_demeaned', true='y_true_demeaned_bps')
    print(f'{name}: ICpool={ic(s):+.4f} ICclean={cic:+.4f} ICclean_dm={cic_d:+.4f} '
          f'ndays={nd} ({nd/ndays_all:.0%}) dayIC t={t:+.2f}')

print('\n=== TREND vs CHOP excluding strong months 2025-10/11 ===')
ex = no2[~no2.month.isin(['2025_10', '2025_11'])]
for name, m in [('TREND', ex.prior_VR3 >= 1), ('CHOP', ex.prior_VR3 < 1)]:
    s = ex[m]; cic, nd = clean_ic(s)
    print(f'{name}: ICpool={ic(s):+.4f} ICclean={cic:+.4f} ndays={nd}')
di_t = D[(D.day.isin(ex[ex.prior_VR3 >= 1].day.unique()))]['day_ic'].dropna()
di_c = D[(D.day.isin(ex[ex.prior_VR3 < 1].day.unique()))]['day_ic'].dropna()
t, p = stats.ttest_ind(di_t, di_c, equal_var=False)
print(f'diff t={t:+.2f} p={p:.3f}')

print('\n=== 2025-10 TREND days detail (7 days driving the 0.165) ===')
oct_t = no2[(no2.month == '2025_10') & (no2.prior_VR3 >= 1)]
for d, g in oct_t.groupby('day'):
    print(f'  {d}: dayIC={ic(g):+.4f} n={len(g)}')

print('\n=== (b) same gate but per-day-CLEAN diff bootstrap (day-level, 10k) ===')
rng = np.random.default_rng(0)
dt_ = D[D.day.isin(no2[no2.prior_VR3 >= 1].day.unique())]['day_ic'].dropna().values
dc_ = D[D.day.isin(no2[no2.prior_VR3 < 1].day.unique())]['day_ic'].dropna().values
diffs = [rng.choice(dt_, len(dt_)).mean() - rng.choice(dc_, len(dc_)).mean() for _ in range(10000)]
print(f'TREND-CHOP clean diff={dt_.mean()-dc_.mean():+.4f}, 95% CI [{np.percentile(diffs,2.5):+.4f}, {np.percentile(diffs,97.5):+.4f}]')
