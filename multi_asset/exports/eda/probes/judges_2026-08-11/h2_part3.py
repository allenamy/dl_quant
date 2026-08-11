import pandas as pd, numpy as np
from scipy import stats
SP='/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad'
V = pd.read_csv(f'{SP}/h2_daily_table.csv',index_col=0,parse_dates=True).sort_index()

print('==== SPLIT-HALF STABILITY: 2025-08..12 vs 2026-01..05 pooled Spearman(L_desc, IC) ====')
h1 = V[V.index < '2026-01-01']; h2 = V[V.index >= '2026-01-01']
for c in ['L_mabs','L_rv','L_pidx_std','L_trend']:
    a=h1[[c,'ic']].dropna(); b=h2[[c,'ic']].dropna()
    r1,p1=stats.spearmanr(a[c],a['ic']); r2,p2=stats.spearmanr(b[c],b['ic'])
    print(f'{c:12s} 2025(n={len(a)}): rho={r1:+.3f} p={p1:.3f} | 2026(n={len(b)}): rho={r2:+.3f} p={p2:.3f}')

print('\n==== also split-half for IC level: mean daily IC ====')
print(f'2025 mean dailyIC={h1.ic.mean():+.4f} (n={len(h1)}) | 2026={h2.ic.mean():+.4f} (n={len(h2)})')

print('\n==== BOOTSTRAP: pidx_std>expanding-med gate pooled lift (day-level bootstrap, 10k) ====')
# reconstruct gate
V2=V.copy(); x=V2['L_pidx_std'].values; ic=V2['ic'].values
keep=np.zeros(len(V2),bool); active=np.zeros(len(V2),bool)
for i in range(len(V2)):
    if i<40 or np.isnan(x[i]): continue
    past=x[:i]; past=past[~np.isnan(past)]
    if len(past)<40: continue
    thr=np.quantile(past,0.5); active[i]=True
    keep[i]=x[i]>thr
icA=ic[active]; kA=keep[active]
obs = np.nanmean(icA[kA])-np.nanmean(icA)
rng=np.random.default_rng(0); n=len(icA); lifts=[]
for _ in range(10000):
    idx=rng.integers(0,n,n)
    ib=icA[idx]; kb=kA[idx]
    if kb.sum()<5: continue
    lifts.append(np.nanmean(ib[kb])-np.nanmean(ib))
lifts=np.array(lifts)
print(f'observed lift={obs:+.4f}  boot 95% CI=[{np.percentile(lifts,2.5):+.4f},{np.percentile(lifts,97.5):+.4f}]  P(lift<=0)={np.mean(lifts<=0):.3f}')

# null: shuffle gate labels within month (kills descriptor info, keeps month structure)
months=V2['month'].values[active]
null=[]
for _ in range(10000):
    kb=kA.copy()
    for mo in np.unique(months):
        m=months==mo; kb[m]=rng.permutation(kb[m])
    null.append(np.nanmean(icA[kb])-np.nanmean(icA))
null=np.array(null)
print(f'within-month-shuffle null: P(null>=obs)={np.mean(null>=obs):.3f}  null 95%=[{np.percentile(null,2.5):+.4f},{np.percentile(null,97.5):+.4f}]')

# same for L_mabs gate
x=V2['L_mabs'].values
keep=np.zeros(len(V2),bool); active=np.zeros(len(V2),bool)
for i in range(len(V2)):
    if i<40 or np.isnan(x[i]): continue
    past=x[:i]; past=past[~np.isnan(past)]
    if len(past)<40: continue
    active[i]=True; keep[i]=x[i]>np.quantile(past,0.5)
icA=ic[active]; kA=keep[active]; months=V2['month'].values[active]
obs = np.nanmean(icA[kA])-np.nanmean(icA)
null=[]
for _ in range(10000):
    kb=kA.copy()
    for mo in np.unique(months):
        m=months==mo; kb[m]=rng.permutation(kb[m])
    null.append(np.nanmean(icA[kb])-np.nanmean(icA))
null=np.array(null)
print(f'L_mabs gate: obs lift={obs:+.4f}  within-month-shuffle P(null>=obs)={np.mean(null>=obs):.3f}')

print('\n==== how much IC variance can ANY daily descriptor explain? ====')
# daily IC noise floor: per-day IC sampling SE with n~108 -> SE ~ 1/sqrt(108)=0.096
sd=V['ic'].std(); se_noise=1/np.sqrt(V['n'].mean())
print(f'daily IC std={sd:.4f}; sampling-noise SE (1/sqrt(n̄), n̄={V["n"].mean():.0f})={se_noise:.4f}')
print(f'=> implied TRUE daily-IC signal std = sqrt(max(0,var-noise)) = {np.sqrt(max(0,sd**2-se_noise**2)):.4f}')
print(f'best pooled rho=0.143 => explains ~{0.143**2*100:.1f}% of OBSERVED daily IC variance')
