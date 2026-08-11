import pandas as pd, numpy as np

df = pd.read_csv('/Users/haosiyu/Desktop/quant_research/exports/final_l01/y600_backtest_dataset.csv')
df = df.sort_values('timestamp_ms').reset_index(drop=True)
df['day'] = df['datetime_utc'].str[:10]

# sanity: consecutive gaps
gaps = np.diff(df['timestamp_ms'].values)
print("min gap (s):", gaps.min()/1000, "| frac gaps==180s:", (gaps==180000).mean().round(4))
print("months:", sorted(df['month'].unique()))

def pearson(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    a = a - a.mean(); b = b - b.mean()
    d = np.sqrt((a*a).sum() * (b*b).sum())
    return (a*b).sum()/d if d > 0 else np.nan

def spearman(a, b):
    ra = pd.Series(a).rank().values; rb = pd.Series(b).rank().values
    return pearson(ra, rb)

# DIFFERENT clean subsample: every 4th row per month (>=720s apart), two phase offsets
def clean_mask(df, offset):
    m = np.zeros(len(df), dtype=bool)
    for _, g in df.groupby('month'):
        idx = g.index.values[offset::4]
        m[idx] = True
    return m

drift = ['2026_01','2026_02','2026_03','2026_04','2026_05']
strong = ['2025_10','2025_11']
normal = ['2025_08','2025_09','2025_12']

for off in (0, 2):
    df[f'clean{off}'] = clean_mask(df, off)
    sub = df[df[f'clean{off}']]
    g = np.diff(sub['timestamp_ms'].values)
    assert g.min() >= 600_000, g.min()

print("\n=== per-month: DENSE P | CLEAN(off0) per-day P | CLEAN(off2) per-day P | CLEAN(off0) per-day S | pooled-clean P ===")
rows = {}
for m in sorted(df['month'].unique()):
    gm = df[df['month'] == m]
    P_dense = pearson(gm['y_pred_demeaned'], gm['y_true_ret_bps'])
    out = [P_dense]
    for off in (0, 2):
        gc = gm[gm[f'clean{off}']]
        dics = [pearson(gd['y_pred_demeaned'], gd['y_true_ret_bps'])
                for _, gd in gc.groupby('day') if len(gd) >= 20]
        out.append(np.mean(dics))
    gc0 = gm[gm['clean0']]
    dS = [spearman(gd['y_pred_demeaned'], gd['y_true_ret_bps'])
          for _, gd in gc0.groupby('day') if len(gd) >= 20]
    out.append(np.mean(dS))
    out.append(pearson(gc0['y_pred_demeaned'], gc0['y_true_ret_bps']))
    rows[m] = out
    print(f"{m}: dense={out[0]:+.4f} cleanP0={out[1]:+.4f} cleanP2={out[2]:+.4f} cleanS0={out[3]:+.4f} pooledCleanP={out[4]:+.4f}")

# group-level: beta (clean pooled), confidence gate, deciles
print("\n=== group diagnostics (clean off0) ===")
dc = df[df['clean0']].copy()
# within-month gates
dc['absp'] = dc['y_pred_demeaned'].abs()
dc['thr80'] = dc.groupby('month')['absp'].transform(lambda s: s.quantile(0.80))
dc['q10'] = dc.groupby('month')['y_pred_demeaned'].transform(lambda s: s.quantile(0.10))
dc['q90'] = dc.groupby('month')['y_pred_demeaned'].transform(lambda s: s.quantile(0.90))

for name, ms in [('strong', strong), ('normal', normal), ('drift', drift)]:
    s = dc[dc['month'].isin(ms)]
    p, y = s['y_pred_demeaned'].values, s['y_true_ret_bps'].values
    beta = np.cov(p, y, ddof=1)[0,1] / np.var(p, ddof=1)
    conf = s['absp'] >= s['thr80']
    ic_conf = pearson(s.loc[conf,'y_pred_demeaned'], s.loc[conf,'y_true_ret_bps'])
    ic_rest = pearson(s.loc[~conf,'y_pred_demeaned'], s.loc[~conf,'y_true_ret_bps'])
    pnl_conf = (np.sign(s.loc[conf,'y_pred_demeaned']) * s.loc[conf,'y_true_ret_bps']).mean()
    pnl_all = (np.sign(p) * y).mean()
    top = s['y_pred_demeaned'] >= s['q90']; bot = s['y_pred_demeaned'] <= s['q10']
    ht = (s.loc[top,'y_true_ret_bps'] > 0).mean(); nt = int(top.sum())
    hb = (s.loc[bot,'y_true_ret_bps'] < 0).mean(); nb = int(bot.sum())
    zt = (ht - 0.5) / np.sqrt(0.25/nt); zb = (hb - 0.5) / np.sqrt(0.25/nb)
    print(f"{name:7s} n={len(s):6d} beta={beta:+.2f} IC_conf={ic_conf:+.4f} IC_rest={ic_rest:+.4f} "
          f"pnl_conf={pnl_conf:+.2f}bps pnl_all={pnl_all:+.2f}bps | topDec hit={ht*100:.1f}% z={zt:+.2f} n={nt} | "
          f"botDec hit={hb*100:.1f}% z={zb:+.2f} n={nb}")

# CAUSAL-gate stress test: trailing 30-day 80th pct of |pred| (dense history, causal), evaluate on clean rows
print("\n=== causal-threshold stress test (trailing 30d q80 of |pred|, shifted 1 row) ===")
df['absp'] = df['y_pred_demeaned'].abs()
df['dtx'] = pd.to_datetime(df['datetime_utc'])
d2 = df.set_index('dtx')
thr = d2['absp'].rolling('30D', min_periods=100).quantile(0.80).shift(1)
d2['thr_causal'] = thr
dcc = d2[d2['clean0']].copy()
for name, ms in [('strong', strong), ('drift', drift)]:
    s = dcc[dcc['month'].isin(ms)].dropna(subset=['thr_causal'])
    conf = s['absp'] >= s['thr_causal']
    ic_conf = pearson(s.loc[conf,'y_pred_demeaned'], s.loc[conf,'y_true_ret_bps'])
    ic_rest = pearson(s.loc[~conf,'y_pred_demeaned'], s.loc[~conf,'y_true_ret_bps'])
    pnl_conf = (np.sign(s.loc[conf,'y_pred_demeaned']) * s.loc[conf,'y_true_ret_bps']).mean()
    print(f"{name:7s} causal gate: n_conf={int(conf.sum())} ({conf.mean()*100:.0f}%) IC_conf={ic_conf:+.4f} IC_rest={ic_rest:+.4f} pnl_conf={pnl_conf:+.2f}bps")

# sigma ratio + cov decomposition per drift month (clean)
print("\n=== drift months: sigma_p, sigma_y, cov (clean off0) ===")
for m in drift + strong:
    s = dc[dc['month'] == m]
    p, y = s['y_pred_demeaned'].values, s['y_true_ret_bps'].values
    print(f"{m}: sig_p={p.std():.4f} sig_y={y.std():.2f}bps ratio={p.std()/y.std():.4f} cov={np.cov(p,y,ddof=1)[0,1]:+.4f} beta={np.cov(p,y,ddof=1)[0,1]/np.var(p,ddof=1):+.2f}")
