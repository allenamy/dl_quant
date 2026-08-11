import pandas as pd, numpy as np

df = pd.read_csv('/Users/haosiyu/Desktop/quant_research/exports/final_l01/y600_backtest_dataset.csv')
df = df.sort_values('timestamp_ms').reset_index(drop=True)
df['day'] = df['datetime_utc'].str[:10]

def pearson(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    a = a - a.mean(); b = b - b.mean()
    d = np.sqrt((a*a).sum()*(b*b).sum())
    return (a*b).sum()/d if d>0 else np.nan

# greedy global >=600s (their method, re-implemented)
ts = df['timestamp_ms'].values
keep = np.zeros(len(ts), bool); last = -1e18
for i, t in enumerate(ts):
    if t - last >= 600_000: keep[i] = True; last = t
df['clean'] = keep
dc = df[df['clean']].copy()
print("greedy clean n =", len(dc))

drift = ['2026_01','2026_02','2026_03','2026_04','2026_05']
strong = ['2025_10','2025_11']
normal = ['2025_08','2025_09','2025_12']

print("\n=== per-month CLEAN per-day P (greedy) + gated IC_conf (within-month top20% |pred|) ===")
dc['absp'] = dc['y_pred_demeaned'].abs()
dc['thr80'] = dc.groupby('month')['absp'].transform(lambda s: s.quantile(0.80))
for m in sorted(df['month'].unique()):
    g = dc[dc['month']==m]
    dics = [pearson(gd['y_pred_demeaned'], gd['y_true_ret_bps']) for _,gd in g.groupby('day') if len(gd)>=20]
    conf = g['absp'] >= g['thr80']
    icc = pearson(g.loc[conf,'y_pred_demeaned'], g.loc[conf,'y_true_ret_bps'])
    print(f"{m}: cleanP={np.mean(dics):+.4f} (n_days={len(dics)}) IC_conf={icc:+.4f} n_conf={int(conf.sum())}")

print("\n=== group (greedy): beta / IC_conf / IC_rest / deciles ===")
dc['q10'] = dc.groupby('month')['y_pred_demeaned'].transform(lambda s: s.quantile(0.10))
dc['q90'] = dc.groupby('month')['y_pred_demeaned'].transform(lambda s: s.quantile(0.90))
for name, ms in [('strong',strong),('normal',normal),('drift',drift)]:
    s = dc[dc['month'].isin(ms)]
    p,y = s['y_pred_demeaned'].values, s['y_true_ret_bps'].values
    beta = np.cov(p,y,ddof=1)[0,1]/np.var(p,ddof=1)
    conf = s['absp']>=s['thr80']
    icc = pearson(s.loc[conf,'y_pred_demeaned'], s.loc[conf,'y_true_ret_bps'])
    icr = pearson(s.loc[~conf,'y_pred_demeaned'], s.loc[~conf,'y_true_ret_bps'])
    pnl_c = (np.sign(s.loc[conf,'y_pred_demeaned'])*s.loc[conf,'y_true_ret_bps']).mean()
    pnl_a = (np.sign(p)*y).mean()
    top = s['y_pred_demeaned']>=s['q90']; bot = s['y_pred_demeaned']<=s['q10']
    ht=(s.loc[top,'y_true_ret_bps']>0).mean(); nt=int(top.sum())
    hb=(s.loc[bot,'y_true_ret_bps']<0).mean(); nb=int(bot.sum())
    zt=(ht-.5)/np.sqrt(.25/nt); zb=(hb-.5)/np.sqrt(.25/nb)
    print(f"{name:7s} beta={beta:+.2f} IC_conf={icc:+.4f} IC_rest={icr:+.4f} pnl_conf={pnl_c:+.2f} pnl_all={pnl_a:+.2f} | top hit={ht*100:.1f}% z={zt:+.2f} n={nt} | bot hit={hb*100:.1f}% z={zb:+.2f} n={nb}")
