import pandas as pd, numpy as np
from scipy import stats

df = pd.read_csv('/Users/haosiyu/Desktop/quant_research/exports/final_l01/y600_backtest_dataset.csv')
df['dt'] = pd.to_datetime(df['datetime_utc'])
df = df.sort_values('timestamp_ms').reset_index(drop=True)
df['day'] = df['dt'].dt.strftime('%Y-%m-%d')

def nonoverlap_mask(ts, gap=600_000):
    m = np.zeros(len(ts), bool); last = -np.inf
    for i, t in enumerate(ts):
        if t - last >= gap: m[i] = True; last = t
    return m

df['clean'] = nonoverlap_mask(df['timestamp_ms'].values)
dc = df[df['clean']].copy()
grp = {'strong': ['2025_10','2025_11'], 'normal': ['2025_08','2025_09','2025_12'],
       'drift': ['2026_01','2026_02','2026_03','2026_04','2026_05']}
gmap = {m:g for g,ms in grp.items() for m in ms}
dc['grp'] = dc['month'].map(gmap)
P='y_pred_demeaned'; Y='y_true_ret_bps'

print("CHECK 7: day-clustered significance of drift bot-decile hit (short-side claim)")
sub = dc[dc['grp']=='drift']
bots=[]
for m,gm in sub.groupby('month'):
    q10 = gm[P].quantile(.1); bots.append(gm[gm[P]<=q10])
bot = pd.concat(bots)
# daily hit rates weighted t (days with >=5 bot rows)
dh = bot.groupby('day').agg(h=(Y, lambda s:(s<0).mean()), n=(Y,'size'))
dh = dh[dh['n']>=5]
t = (dh['h'].mean()-0.5)/(dh['h'].std(ddof=1)/np.sqrt(len(dh)))
print(f"  bot-decile daily hit: n_days={len(dh)} mean={dh['h'].mean()*100:.1f}% t_vs_50={t:+.2f}")
# block bootstrap by day, 2000 reps, pooled hit
days = bot['day'].unique(); rng = np.random.default_rng(0)
boots=[]
gb = {d:g_[Y].values for d,g_ in bot.groupby('day')}
for _ in range(2000):
    pick = rng.choice(days, len(days), replace=True)
    v = np.concatenate([gb[d] for d in pick])
    boots.append((v<0).mean())
boots=np.array(boots)
print(f"  bot-decile pooled hit=53.2%, day-block bootstrap 95% CI=[{np.percentile(boots,2.5)*100:.1f}%, {np.percentile(boots,97.5)*100:.1f}%], P(hit<=50%)={ (boots<=0.5).mean():.3f}")

print("\nCHECK 8: day-block bootstrap of drift gated IC (pooled, 2000 reps)")
parts=[]
for m,gm in sub.groupby('month'):
    thr = gm[P].abs().quantile(.8); parts.append(gm[gm[P].abs()>=thr])
hi = pd.concat(parts)
gbi = {d:(g_[P].values, g_[Y].values) for d,g_ in hi.groupby('day')}
days = list(gbi.keys()); boots=[]
for _ in range(2000):
    pick = rng.choice(days, len(days), replace=True)
    pv = np.concatenate([gbi[d][0] for d in pick]); yv = np.concatenate([gbi[d][1] for d in pick])
    boots.append(stats.pearsonr(pv,yv)[0])
boots=np.array(boots)
print(f"  drift gated IC=+0.0303, day-block bootstrap 95% CI=[{np.percentile(boots,2.5):+.4f}, {np.percentile(boots,97.5):+.4f}], P(IC<=0)={(boots<=0).mean():.3f}")

print("\nCHECK 9: sub-split claims — 2026-01..03 gated IC 0.049-0.057 recoverable, 2026-04/05 dead")
for m in grp['drift']:
    gm = dc[dc['month']==m].copy(); thr = gm[P].abs().quantile(.8)
    hi = gm[gm[P].abs()>=thr]
    ic = stats.pearsonr(hi[P],hi[Y])[0]
    # day-block bootstrap per month
    gbi = {d:(g_[P].values,g_[Y].values) for d,g_ in hi.groupby('day')}
    days=list(gbi.keys()); bs=[]
    for _ in range(1000):
        pick = rng.choice(days,len(days),replace=True)
        pv=np.concatenate([gbi[d][0] for d in pick]); yv=np.concatenate([gbi[d][1] for d in pick])
        bs.append(stats.pearsonr(pv,yv)[0])
    bs=np.array(bs)
    print(f"  {m} gated IC={ic:+.4f} 95%CI=[{np.percentile(bs,2.5):+.4f},{np.percentile(bs,97.5):+.4f}] P(<=0)={(bs<=0).mean():.2f}")

print("\nCHECK 10: verify NOT-sign-flip / NOT-intact-ranking claims (per-month clean P & S)")
for m in sorted(dc['month'].unique()):
    gm = dc[dc['month']==m]
    ics=[]; ss=[]
    for d,gd in gm.groupby('day'):
        if len(gd)>=20:
            ics.append(stats.pearsonr(gd[P],gd[Y])[0]); ss.append(stats.spearmanr(gd[P],gd[Y])[0])
    print(f"  {m} P_clean={np.mean(ics):+.4f} S_clean={np.mean(ss):+.4f}")

print("\nCHECK 11: beta attenuation robustness — clean per-group beta with day-block bootstrap CI")
for g in ['strong','normal','drift']:
    sub2 = dc[dc['grp']==g]
    b = np.polyfit(sub2[P], sub2[Y],1)[0]
    gbi = {d:(g_[P].values,g_[Y].values) for d,g_ in sub2.groupby('day')}
    days=list(gbi.keys()); bs=[]
    for _ in range(500):
        pick=rng.choice(days,len(days),replace=True)
        pv=np.concatenate([gbi[d][0] for d in pick]); yv=np.concatenate([gbi[d][1] for d in pick])
        bs.append(np.polyfit(pv,yv,1)[0])
    bs=np.array(bs)
    print(f"  {g:7s} beta={b:+.2f} 95%CI=[{np.percentile(bs,2.5):+.1f},{np.percentile(bs,97.5):+.1f}]")
