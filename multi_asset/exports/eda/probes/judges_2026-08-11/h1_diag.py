import pandas as pd, numpy as np
from scipy import stats

df = pd.read_csv('/Users/haosiyu/Desktop/quant_research/exports/final_l01/y600_backtest_dataset.csv')
df['dt'] = pd.to_datetime(df['datetime_utc'])
df = df.sort_values('timestamp_ms').reset_index(drop=True)
df['day'] = df['dt'].dt.strftime('%Y-%m-%d')

# non-overlap subsample: greedy >=600s apart (global, per continuity)
def nonoverlap_mask(ts_ms, gap_ms=600_000):
    mask = np.zeros(len(ts_ms), dtype=bool)
    last = -np.inf
    for i, t in enumerate(ts_ms):
        if t - last >= gap_ms:
            mask[i] = True
            last = t
    return mask

df['clean'] = nonoverlap_mask(df['timestamp_ms'].values)

months = sorted(df['month'].unique())
rows = []
for m in months:
    g = df[df['month'] == m]
    p, y = g['y_pred_demeaned'].values, g['y_true_ret_bps'].values
    n = len(g)
    pearson_d = stats.pearsonr(p, y)[0]
    spearman_d = stats.spearmanr(p, y)[0]
    # clean per-day
    gc = g[g['clean']]
    day_ics = []
    for d, gd in gc.groupby('day'):
        if len(gd) >= 20:
            day_ics.append(stats.pearsonr(gd['y_pred_demeaned'], gd['y_true_ret_bps'])[0])
    day_ics = np.array(day_ics)
    clean_p = day_ics.mean()
    neg_days = (day_ics < 0).mean() * 100
    tstat = day_ics.mean() / (day_ics.std(ddof=1) / np.sqrt(len(day_ics)))
    # also clean spearman per day
    day_s = []
    for d, gd in gc.groupby('day'):
        if len(gd) >= 20:
            day_s.append(stats.spearmanr(gd['y_pred_demeaned'], gd['y_true_ret_bps'])[0])
    clean_s = np.mean(day_s)
    # sigma ratio & OLS beta (dense, month-level)
    sig_ratio = p.std() / y.std()
    beta = np.polyfit(p, y, 1)[0]  # y_true on y_pred
    # tail diagnostics on CLEAN subsample (deciles of y_pred_demeaned within month)
    pc, yc = gc['y_pred_demeaned'].values, gc['y_true_ret_bps'].values
    q10, q90 = np.quantile(pc, [0.10, 0.90])
    top = pc >= q90; bot = pc <= q10
    mean_y_top = yc[top].mean(); mean_y_bot = yc[bot].mean()
    ic_top = stats.pearsonr(pc[top], yc[top])[0]
    ic_bot = stats.pearsonr(pc[bot], yc[bot])[0]
    # hit rates
    hit_all = (np.sign(pc) == np.sign(yc)).mean()
    hit_top = (yc[top] > 0).mean()   # top decile: predict up
    hit_bot = (yc[bot] < 0).mean()   # bottom decile: predict down
    # magnitudes for context
    rows.append(dict(month=m, n_dense=n, n_clean=len(gc), n_days=len(day_ics),
        P_dense=pearson_d, S_dense=spearman_d, P_clean=clean_p, S_clean=clean_s,
        pct_neg_days=neg_days, t_daily=tstat, sig_ratio=sig_ratio, beta=beta,
        mean_y_top=mean_y_top, mean_y_bot=mean_y_bot, ic_top=ic_top, ic_bot=ic_bot,
        hit_all=hit_all*100, hit_top=hit_top*100, hit_bot=hit_bot*100,
        y_std=y.std(), p_std=p.std()))

res = pd.DataFrame(rows)
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 50)
print(res.round(4).to_string(index=False))

# group summary
grp = {'strong': ['2025_10','2025_11'], 'normal': ['2025_08','2025_09','2025_12'],
       'drift': ['2026_01','2026_02','2026_03','2026_04','2026_05']}
print()
for gname, ms in grp.items():
    sub = res[res['month'].isin(ms)]
    if len(sub)==0: continue
    print(f"{gname:7s} P_dense={sub.P_dense.mean():+.4f} S_dense={sub.S_dense.mean():+.4f} P_clean={sub.P_clean.mean():+.4f} "
          f"negdays={sub.pct_neg_days.mean():.0f}% sig={sub.sig_ratio.mean():.4f} beta={sub.beta.mean():+.2f} "
          f"y_top={sub.mean_y_top.mean():+.2f} y_bot={sub.mean_y_bot.mean():+.2f} hit={sub.hit_all.mean():.1f}% "
          f"hitT={sub.hit_top.mean():.1f}% hitB={sub.hit_bot.mean():.1f}%")
