import numpy as np
import pandas as pd
from scipy import stats

CSV = '/Users/haosiyu/Desktop/quant_research/exports/final_l01/y600_backtest_dataset.csv'
df = pd.read_csv(CSV).sort_values('timestamp_ms').reset_index(drop=True)
df['day'] = pd.to_datetime(df['timestamp_ms'], unit='ms', utc=True).dt.strftime('%Y-%m-%d')

ts = df['timestamp_ms'].values
keep = np.zeros(len(df), bool); last = -np.inf
for i, t in enumerate(ts):
    if t - last >= 600_000:
        keep[i] = True; last = t
no = df[keep].reset_index(drop=True)

def pooled_ic(sub, pred='y_pred_raw'):
    return np.corrcoef(sub[pred], sub['y_true_ret_bps'])[0, 1] if len(sub) >= 8 else np.nan

def run(win_sec, label):
    no['win'] = no['timestamp_ms'] // (win_sec * 1000)
    st = []
    for w, g in no.groupby('win'):
        y = g['y_true_ret_bps'].values
        if len(y) < max(4, win_sec // 720 // 2):
            st.append(dict(win=w, n=len(y), ER=np.nan, AR1=np.nan, VR2=np.nan, vol=np.nan)); continue
        ER = np.abs(y.sum()) / np.abs(y).sum() if np.abs(y).sum() > 0 else np.nan
        AR1 = np.corrcoef(y[:-1], y[1:])[0, 1] if len(y) >= 6 else np.nan
        n2 = len(y) // 2 * 2
        agg = y[:n2].reshape(-1, 2).sum(1)
        VR2 = np.var(agg, ddof=1) / (2 * np.var(y, ddof=1)) if len(y) >= 8 and np.var(y, ddof=1) > 0 else np.nan
        st.append(dict(win=w, n=len(y), ER=ER, AR1=AR1, VR2=VR2, vol=y.std()))
    S = pd.DataFrame(st).set_index('win')
    S_prior = S.shift(1)
    # require contiguity: prior window id == win-1 (shift on sorted unique index handles it only if dense; enforce)
    wins = S.index.values
    contig = np.r_[False, np.diff(wins) == 1]
    S_prior.loc[~contig] = np.nan

    no_w = no.merge(S_prior.add_prefix('prior_'), left_on='win', right_index=True)
    print(f'\n===== (d) {label}: prior-{label} state -> next-{label} IC (non-overlap rows) =====')
    print(f'windows={S.shape[0]}, with prior state={S_prior.ER.notna().sum()}')
    for state in ['prior_ER', 'prior_AR1', 'prior_VR2', 'prior_vol']:
        v = no_w[no_w[state].notna()].copy()
        # tercile split on full-sample dist of the causal feature (thresholds in-sample; feature causal)
        q1, q2 = v[state].quantile([1/3, 2/3])
        v['b'] = np.where(v[state] <= q1, 'LO', np.where(v[state] >= q2, 'HI', 'MID'))
        parts = []
        for b in ['LO', 'MID', 'HI']:
            s = v[v.b == b]
            nwin = s['win'].nunique()
            parts.append(f'{b}: IC={pooled_ic(s):+.4f} (rows={len(s)}, win={nwin}, frac={nwin/v.win.nunique():.0%})')
        # per-window IC t-test HI vs LO
        wic = v.groupby(['win', 'b']).apply(lambda g: pooled_ic(g), include_groups=False).dropna()
        hi = wic.xs('HI', level='b'); lo = wic.xs('LO', level='b')
        t, p = stats.ttest_ind(hi, lo, equal_var=False)
        print(f'{state:>10}: ' + ' | '.join(parts) + f' || HI-LO perwin t={t:+.2f} p={p:.3f}')
    # quintiles on ER and VR2 to find any state reaching 0.06
    for state in ['prior_ER', 'prior_VR2', 'prior_AR1']:
        v = no_w[no_w[state].notna()].copy()
        v['q'] = pd.qcut(v[state], 5, labels=False, duplicates='drop')
        line = []
        for q, s in v.groupby('q'):
            line.append(f'Q{q+1}={pooled_ic(s):+.4f}({s.win.nunique()}w)')
        print(f'{state} quintile ICs: ' + ' '.join(line))
    return no_w

for ws, lb in [(7200, '2h'), (14400, '4h')]:
    run(ws, lb)
