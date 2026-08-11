import pandas as pd, numpy as np
from scipy import stats

df = pd.read_csv('/Users/haosiyu/Desktop/quant_research/exports/final_l01/y600_backtest_dataset.csv')
df['dt'] = pd.to_datetime(df['datetime_utc'])
df = df.sort_values('timestamp_ms').reset_index(drop=True)
df['day'] = df['dt'].dt.strftime('%Y-%m-%d')
df['week'] = df['dt'].dt.strftime('%G-W%V')

def nonoverlap_mask(ts_ms, gap_ms=600_000):
    mask = np.zeros(len(ts_ms), dtype=bool); last = -np.inf
    for i, t in enumerate(ts_ms):
        if t - last >= gap_ms: mask[i] = True; last = t
    return mask
df['clean'] = nonoverlap_mask(df['timestamp_ms'].values)
dc = df[df['clean']].copy()

grp = {'strong': ['2025_10','2025_11'], 'normal': ['2025_08','2025_09','2025_12'],
       'drift': ['2026_01','2026_02','2026_03','2026_04','2026_05']}
gmap = {m:g for g,ms in grp.items() for m in ms}
dc['grp'] = dc['month'].map(gmap)

# 1) decile profile of mean y_true by y_pred_demeaned decile, per group (deciles within month, mean y in bps)
print("=== decile profile: mean y_true_ret_bps per within-month decile of y_pred_demeaned (clean) ===")
for g in ['strong','normal','drift']:
    sub = dc[dc['grp']==g].copy()
    parts = []
    for m, gm in sub.groupby('month'):
        gm = gm.copy(); gm['dec'] = pd.qcut(gm['y_pred_demeaned'], 10, labels=False, duplicates='drop')
        parts.append(gm)
    sub = pd.concat(parts)
    prof = sub.groupby('dec')['y_true_ret_bps'].mean()
    print(f"{g:7s} " + " ".join(f"{v:+.2f}" for v in prof.values))

# 2) covariance decomposition per group: P = cov/(sp*sy)
print("\n=== cov decomposition (clean, per month) ===")
for m, gm in dc.groupby('month'):
    p,y = gm['y_pred_demeaned'].values, gm['y_true_ret_bps'].values
    print(f"{m} cov={np.cov(p,y)[0,1]:+.4f} sp={p.std():.4f} sy={y.std():.2f} P={stats.pearsonr(p,y)[0]:+.4f}")

# 3) weekly clean IC within drift months — persistent flip vs noise?
print("\n=== weekly clean Pearson (drift months) ===")
sub = dc[dc['grp']=='drift']
for w, gw in sub.groupby('week'):
    if len(gw) >= 100:
        ic = stats.pearsonr(gw['y_pred_demeaned'], gw['y_true_ret_bps'])[0]
        print(f"{w} n={len(gw):4d} IC={ic:+.4f}")

# 4) confidence gating: IC + hitrate in top 20% |y_pred_demeaned| vs bottom 80%, per group; also long-short spread per trade
print("\n=== confidence gate: top-20% |y_pred| (within month) ===")
for g in ['strong','normal','drift']:
    sub = dc[dc['grp']==g].copy()
    parts=[]
    for m, gm in sub.groupby('month'):
        gm = gm.copy(); thr = gm['y_pred_demeaned'].abs().quantile(0.80)
        gm['conf'] = gm['y_pred_demeaned'].abs() >= thr
        parts.append(gm)
    sub = pd.concat(parts)
    hi = sub[sub['conf']]; lo = sub[~sub['conf']]
    ic_hi = stats.pearsonr(hi['y_pred_demeaned'], hi['y_true_ret_bps'])[0]
    ic_lo = stats.pearsonr(lo['y_pred_demeaned'], lo['y_true_ret_bps'])[0]
    hit_hi = (np.sign(hi['y_pred_demeaned'])==np.sign(hi['y_true_ret_bps'])).mean()*100
    # per-trade expected pnl in conf set: sign(pred)*y
    pnl_hi = (np.sign(hi['y_pred_demeaned'])*hi['y_true_ret_bps']).mean()
    pnl_all = (np.sign(sub['y_pred_demeaned'])*sub['y_true_ret_bps']).mean()
    print(f"{g:7s} IC_conf={ic_hi:+.4f} IC_rest={ic_lo:+.4f} hit_conf={hit_hi:.1f}% pnl_conf={pnl_hi:+.2f}bps pnl_all={pnl_all:+.2f}bps")

# 5) per-day daily-IC autocorr & sign persistence in drift (flip vs noise)
print("\n=== daily IC series stats per group ===")
for g in ['strong','normal','drift']:
    sub = dc[dc['grp']==g]
    ics=[]
    for d, gd in sub.groupby('day'):
        if len(gd)>=20: ics.append(stats.pearsonr(gd['y_pred_demeaned'], gd['y_true_ret_bps'])[0])
    ics=np.array(ics)
    ac1 = np.corrcoef(ics[:-1],ics[1:])[0,1]
    print(f"{g:7s} n_days={len(ics)} mean={ics.mean():+.4f} std={ics.std():.4f} AC1={ac1:+.3f} min={ics.min():+.3f} max={ics.max():+.3f}")

# 6) beta on clean per group + demeaned-y version sanity
print("\n=== group beta (clean) y_true ~ y_pred_demeaned ===")
for g in ['strong','normal','drift']:
    sub = dc[dc['grp']==g]
    b = np.polyfit(sub['y_pred_demeaned'], sub['y_true_ret_bps'],1)[0]
    b2 = np.polyfit(sub['y_pred_demeaned'], sub['y_true_demeaned_bps'],1)[0]
    print(f"{g:7s} beta_raw={b:+.2f} beta_demeaned_y={b2:+.2f}")
