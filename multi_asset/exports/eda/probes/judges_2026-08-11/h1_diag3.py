import pandas as pd, numpy as np
from scipy import stats

df = pd.read_csv('/Users/haosiyu/Desktop/quant_research/exports/final_l01/y600_backtest_dataset.csv')
df['dt'] = pd.to_datetime(df['datetime_utc'])
df = df.sort_values('timestamp_ms').reset_index(drop=True)
def nonoverlap_mask(ts, gap=600_000):
    m = np.zeros(len(ts), bool); last=-np.inf
    for i,t in enumerate(ts):
        if t-last>=gap: m[i]=True; last=t
    return m
df['clean']=nonoverlap_mask(df['timestamp_ms'].values)
dc=df[df['clean']].copy()
grp={'strong':['2025_10','2025_11'],'normal':['2025_08','2025_09','2025_12'],'drift':['2026_01','2026_02','2026_03','2026_04','2026_05']}
gmap={m:g for g,ms in grp.items() for m in ms}; dc['grp']=dc['month'].map(gmap)

print("=== pooled tail hit rates (within-month deciles, clean) + binomial z ===")
for g in ['strong','normal','drift']:
    sub=dc[dc['grp']==g]
    tops=[];bots=[]
    for m,gm in sub.groupby('month'):
        q10,q90=gm['y_pred_demeaned'].quantile([.1,.9])
        tops.append(gm[gm['y_pred_demeaned']>=q90]); bots.append(gm[gm['y_pred_demeaned']<=q10])
    top=pd.concat(tops); bot=pd.concat(bots)
    ht=(top['y_true_ret_bps']>0).mean(); hb=(bot['y_true_ret_bps']<0).mean()
    zt=(ht-.5)*np.sqrt(len(top))/.5; zb=(hb-.5)*np.sqrt(len(bot))/.5
    myt=top['y_true_ret_bps'].mean(); myb=bot['y_true_ret_bps'].mean()
    print(f"{g:7s} TOP n={len(top)} hit={ht*100:.1f}% z={zt:+.2f} mean_y={myt:+.2f}bps | BOT n={len(bot)} hit={hb*100:.1f}% z={zb:+.2f} mean_y={myb:+.2f}bps")

print("\n=== pooled clean daily-IC t-stats per group ===")
dc['day']=dc['dt'].dt.strftime('%Y-%m-%d')
for g in ['strong','normal','drift']:
    sub=dc[dc['grp']==g]; ics=[]
    for d,gd in sub.groupby('day'):
        if len(gd)>=20: ics.append(stats.pearsonr(gd['y_pred_demeaned'],gd['y_true_ret_bps'])[0])
    ics=np.array(ics); t=ics.mean()/(ics.std(ddof=1)/np.sqrt(len(ics)))
    print(f"{g:7s} n_days={len(ics)} meanIC={ics.mean():+.4f} t={t:+.2f} negdays={(ics<0).mean()*100:.0f}%")

print("\n=== drift: does |pred| predict |y|? (vol-forecast content vs direction) ===")
for g in ['strong','drift']:
    sub=dc[dc['grp']==g]
    r=stats.spearmanr(sub['y_pred_demeaned'].abs(),sub['y_true_ret_bps'].abs())[0]
    print(f"{g:7s} spearman(|pred|,|y|)={r:+.4f}")

print("\n=== per-drift-month confidence gate (top20% |pred|) ===")
for m in ['2026_01','2026_02','2026_03','2026_04','2026_05']:
    gm=dc[dc['month']==m].copy(); thr=gm['y_pred_demeaned'].abs().quantile(.8)
    hi=gm[gm['y_pred_demeaned'].abs()>=thr]
    ic=stats.pearsonr(hi['y_pred_demeaned'],hi['y_true_ret_bps'])[0]
    hit=(np.sign(hi['y_pred_demeaned'])==np.sign(hi['y_true_ret_bps'])).mean()*100
    pnl=(np.sign(hi['y_pred_demeaned'])*hi['y_true_ret_bps']).mean()
    print(f"{m} n={len(hi)} IC_conf={ic:+.4f} hit={hit:.1f}% pnl={pnl:+.2f}bps")
