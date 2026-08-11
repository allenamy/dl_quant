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

P = 'y_pred_demeaned'; Y = 'y_true_ret_bps'; YD = 'y_true_demeaned_bps'

print("="*100)
print("CHECK 0: reproduce headline numbers (sanity)")
print("="*100)
for g in ['strong','normal','drift']:
    sub = dc[dc['grp']==g]
    ics = [stats.pearsonr(gd[P],gd[Y])[0] for d,gd in sub.groupby('day') if len(gd)>=20]
    ics = np.array(ics)
    print(f"{g:7s} n_clean={len(sub)} meanDailyIC={ics.mean():+.4f} t={ics.mean()/(ics.std(ddof=1)/np.sqrt(len(ics))):+.2f}")

print()
print("="*100)
print("CHECK 1: BASE-RATE CONFOUND on short-side asymmetry")
print("  claim: drift bot-decile hit 53.2% z=+2.54 significant, top 50.8% z=+0.65 dead")
print("  alternative: market fell in drift months -> P(y<0) base > 50%, short 'edge' = drift not skill")
print("="*100)
for g in ['strong','normal','drift']:
    sub = dc[dc['grp']==g]
    tops=[];bots=[]
    for m,gm in sub.groupby('month'):
        q10,q90 = gm[P].quantile([.1,.9])
        tops.append(gm[gm[P]>=q90]); bots.append(gm[gm[P]<=q10])
    top=pd.concat(tops); bot=pd.concat(bots)
    base_up = (sub[Y]>0).mean(); base_dn = (sub[Y]<0).mean()
    ht=(top[Y]>0).mean(); hb=(bot[Y]<0).mean()
    # z vs 0.5 (original method)
    zt0=(ht-.5)*np.sqrt(len(top))/.5; zb0=(hb-.5)*np.sqrt(len(bot))/.5
    # z vs group base rate (correct null)
    zt=(ht-base_up)*np.sqrt(len(top))/np.sqrt(base_up*(1-base_up))
    zb=(hb-base_dn)*np.sqrt(len(bot))/np.sqrt(base_dn*(1-base_dn))
    print(f"{g:7s} base P(y>0)={base_up*100:.1f}% P(y<0)={base_dn*100:.1f}% | "
          f"TOP hit={ht*100:.1f}% edge={100*(ht-base_up):+.1f}pp z_base={zt:+.2f} (z_.5={zt0:+.2f}) | "
          f"BOT hit={hb*100:.1f}% edge={100*(hb-base_dn):+.1f}pp z_base={zb:+.2f} (z_.5={zb0:+.2f})")
    # same on DEMEANED y (removes market drift structurally)
    ht_d=(top[YD]>0).mean(); hb_d=(bot[YD]<0).mean()
    base_up_d=(sub[YD]>0).mean(); base_dn_d=(sub[YD]<0).mean()
    zt_d=(ht_d-base_up_d)*np.sqrt(len(top))/np.sqrt(base_up_d*(1-base_up_d))
    zb_d=(hb_d-base_dn_d)*np.sqrt(len(bot))/np.sqrt(base_dn_d*(1-base_dn_d))
    print(f"        DEMEANED-y: base_up={base_up_d*100:.1f}% base_dn={base_dn_d*100:.1f}% | "
          f"TOP hit={ht_d*100:.1f}% z={zt_d:+.2f} | BOT hit={hb_d*100:.1f}% z={zb_d:+.2f}")

# per drift month base rates + mean y
print("\nper drift month: mean y and base rates (clean)")
for m in grp['drift']:
    gm = dc[dc['month']==m]
    print(f"  {m} n={len(gm)} mean_y={gm[Y].mean():+.2f}bps P(y<0)={(gm[Y]<0).mean()*100:.1f}% mean_y_demeaned={gm[YD].mean():+.2f}bps")

print()
print("="*100)
print("CHECK 2: GATE LOOK-AHEAD — within-month top-20% |pred| threshold uses full month (future).")
print("  redo with CAUSAL trailing threshold (expanding + 10-day rolling quantile of |pred| on clean rows)")
print("="*100)
dc = dc.sort_values('timestamp_ms').reset_index(drop=True)
dc['abs_p'] = dc[P].abs()
# causal expanding 80th pct within each month (as-you-go), min 200 rows warmup
def causal_gate(sub, q=0.80, warm=200):
    ap = sub['abs_p'].values
    thr = np.full(len(ap), np.nan)
    for i in range(warm, len(ap)):
        thr[i] = np.quantile(ap[:i], q)
    return ap >= thr
# trailing 10-day rolling quantile (global, cross-month causal)
roll_thr = dc.set_index('dt')['abs_p'].rolling('10D', min_periods=500).quantile(0.80).shift(1).values
dc['conf_roll'] = dc['abs_p'].values >= roll_thr

for g in ['strong','drift']:
    sub = dc[dc['grp']==g]
    # (a) original within-month full-month gate
    parts=[]
    for m,gm in sub.groupby('month'):
        thr = gm['abs_p'].quantile(.8); parts.append(gm[gm['abs_p']>=thr])
    hi0 = pd.concat(parts)
    ic0 = stats.pearsonr(hi0[P],hi0[Y])[0]
    # (b) causal expanding within-month
    parts=[]
    for m,gm in sub.groupby('month'):
        gm = gm.reset_index(drop=True)
        mask = causal_gate(gm)
        parts.append(gm[mask])
    hi1 = pd.concat(parts)
    ic1 = stats.pearsonr(hi1[P],hi1[Y])[0]
    # (c) trailing 10-day rolling gate
    hi2 = sub[sub['conf_roll']]
    ic2 = stats.pearsonr(hi2[P],hi2[Y])[0]
    pnl0 = (np.sign(hi0[P])*hi0[Y]).mean(); pnl1=(np.sign(hi1[P])*hi1[Y]).mean(); pnl2=(np.sign(hi2[P])*hi2[Y]).mean()
    print(f"{g:7s} gate=within-month(lookahead): n={len(hi0)} IC={ic0:+.4f} pnl={pnl0:+.2f}bps")
    print(f"        gate=causal expanding     : n={len(hi1)} IC={ic1:+.4f} pnl={pnl1:+.2f}bps")
    print(f"        gate=causal 10d rolling   : n={len(hi2)} IC={ic2:+.4f} pnl={pnl2:+.2f}bps")

print()
print("="*100)
print("CHECK 3: OUTLIER DAYS — drop top-3 contribution days from drift gated IC and ungated CLEAN P")
print("="*100)
sub = dc[dc['grp']=='drift']
parts=[]
for m,gm in sub.groupby('month'):
    thr = gm['abs_p'].quantile(.8); parts.append(gm[gm['abs_p']>=thr])
hi = pd.concat(parts)
# per-day contribution to pooled cov
mu_p, mu_y = hi[P].mean(), hi[Y].mean()
hi = hi.copy(); hi['contrib'] = (hi[P]-mu_p)*(hi[Y]-mu_y)
day_contrib = hi.groupby('day')['contrib'].sum().sort_values(ascending=False)
top3 = day_contrib.head(3).index.tolist()
hi_x = hi[~hi['day'].isin(top3)]
ic_full = stats.pearsonr(hi[P],hi[Y])[0]
ic_drop = stats.pearsonr(hi_x[P],hi_x[Y])[0]
print(f"drift gated: IC_full={ic_full:+.4f} (n={len(hi)}, {hi['day'].nunique()} days) -> drop top-3 contrib days {top3}: IC={ic_drop:+.4f} (n={len(hi_x)})")
pnl_full=(np.sign(hi[P])*hi[Y]).mean(); pnl_drop=(np.sign(hi_x[P])*hi_x[Y]).mean()
print(f"drift gated pnl: full={pnl_full:+.2f}bps -> drop3={pnl_drop:+.2f}bps")
# winsorize y at 5 sigma within group
sd = hi[Y].std(); yw = hi[Y].clip(-5*sd, 5*sd)
print(f"drift gated winsorized-5sig IC={stats.pearsonr(hi[P],yw)[0]:+.4f}; gated Spearman={stats.spearmanr(hi[P],hi[Y])[0]:+.4f}")
# ungated drift clean P drop top-3 days
subc = sub.copy(); mu_p,mu_y = subc[P].mean(), subc[Y].mean()
subc['contrib']=(subc[P]-mu_p)*(subc[Y]-mu_y)
dcontrib = subc.groupby('day')['contrib'].sum().sort_values(ascending=False)
t3 = dcontrib.head(3).index.tolist()
print(f"drift ungated pooled clean P full={stats.pearsonr(subc[P],subc[Y])[0]:+.4f} -> drop {t3}: "
      f"{stats.pearsonr(subc[~subc['day'].isin(t3)][P], subc[~subc['day'].isin(t3)][Y])[0]:+.4f}")
# bottom-decile hit drop top-3 hit days
bots=[]
for m,gm in sub.groupby('month'):
    q10 = gm[P].quantile(.1); bots.append(gm[gm[P]<=q10])
bot = pd.concat(bots)
dhit = bot.groupby('day').apply(lambda g_: ((g_[Y]<0).sum(), len(g_)))
hb_full = (bot[Y]<0).mean()
# drop 3 days with largest (hits - n/2)
excess = bot.groupby('day').apply(lambda g_: (g_[Y]<0).sum() - len(g_)/2).sort_values(ascending=False)
t3b = excess.head(3).index.tolist()
bot_x = bot[~bot['day'].isin(t3b)]
print(f"drift bot-decile hit full={hb_full*100:.1f}% (n={len(bot)}) -> drop top-3 hit days: {(bot_x[Y]<0).mean()*100:.1f}% (n={len(bot_x)})")

print()
print("="*100)
print("CHECK 4: VOL CONFOUND — is the |pred| gate just a vol/day picker?")
print("="*100)
# (a) within-DAY gate (kills day-level vol selection): top-20% |pred| within each day
sub = dc[dc['grp']=='drift']
parts=[]
for d,gd in sub.groupby('day'):
    if len(gd)>=20:
        thr=gd['abs_p'].quantile(.8); parts.append(gd[gd['abs_p']>=thr])
hi_day = pd.concat(parts)
print(f"(a) drift within-DAY gate: n={len(hi_day)} IC={stats.pearsonr(hi_day[P],hi_day[Y])[0]:+.4f} "
      f"pnl={(np.sign(hi_day[P])*hi_day[Y]).mean():+.2f}bps "
      f"hit={(np.sign(hi_day[P])==np.sign(hi_day[Y])).mean()*100:.1f}%")
# strong comparison
subS = dc[dc['grp']=='strong']; partsS=[]
for d,gd in subS.groupby('day'):
    if len(gd)>=20:
        thr=gd['abs_p'].quantile(.8); partsS.append(gd[gd['abs_p']>=thr])
hiS = pd.concat(partsS)
print(f"    strong within-DAY gate: n={len(hiS)} IC={stats.pearsonr(hiS[P],hiS[Y])[0]:+.4f}")
# (b) gate by TRAILING realized vol instead of |pred|: rolling std of y over past 1 day, shifted so fully realized (y looks 600s fwd; clean rows >=600s apart so shift(2) safe)
sub = sub.sort_values('timestamp_ms').copy()
sub['rv'] = sub[Y].abs().rolling(100, min_periods=50).mean().shift(2)
thr = sub['rv'].quantile(.8)
hv = sub[sub['rv']>=thr]
print(f"(b) drift gate by trailing-vol top20%: n={len(hv)} IC={stats.pearsonr(hv[P],hv[Y])[0]:+.4f} "
      f"pnl={(np.sign(hv[P])*hv[Y]).mean():+.2f}bps")
# (c) double sort: |pred| gate within LOW-vol half vs HIGH-vol half
med = sub['rv'].median()
for lbl, mask in [('lowvol', sub['rv']<med), ('highvol', sub['rv']>=med)]:
    s2 = sub[mask & sub['rv'].notna()]
    parts=[]
    for m,gm in s2.groupby('month'):
        if len(gm)<50: continue
        thr=gm['abs_p'].quantile(.8); parts.append(gm[gm['abs_p']>=thr])
    h2=pd.concat(parts)
    print(f"(c) drift |pred|-gate within {lbl}: n={len(h2)} IC={stats.pearsonr(h2[P],h2[Y])[0]:+.4f} "
          f"pnl={(np.sign(h2[P])*h2[Y]).mean():+.2f}bps")

print()
print("="*100)
print("CHECK 5: gated-IC daily t-stat (drift) — is +0.03 gated IC significant with overlap-aware daily aggregation?")
print("="*100)
sub = dc[dc['grp']=='drift']
parts=[]
for m,gm in sub.groupby('month'):
    thr = gm['abs_p'].quantile(.8); parts.append(gm[gm['abs_p']>=thr])
hi = pd.concat(parts)
ics=[]
for d,gd in hi.groupby('day'):
    if len(gd)>=10: ics.append(stats.pearsonr(gd[P],gd[Y])[0])
ics=np.array(ics)
t = ics.mean()/(ics.std(ddof=1)/np.sqrt(len(ics)))
print(f"drift gated daily IC: n_days={len(ics)} mean={ics.mean():+.4f} t={t:+.2f} negdays={(ics<0).mean()*100:.0f}%")
# pnl daily t
pnls = hi.groupby('day').apply(lambda g_: (np.sign(g_[P])*g_[Y]).mean())
pnls = pnls[hi.groupby('day').size()>=10]
tp = pnls.mean()/(pnls.std(ddof=1)/np.sqrt(len(pnls)))
print(f"drift gated daily pnl: n_days={len(pnls)} mean={pnls.mean():+.2f}bps t={tp:+.2f} negdays={(pnls<0).mean()*100:.0f}%")
# strong for reference
subS=dc[dc['grp']=='strong']; partsS=[]
for m,gm in subS.groupby('month'):
    thr=gm['abs_p'].quantile(.8); partsS.append(gm[gm['abs_p']>=thr])
hiS=pd.concat(partsS)
icsS=[stats.pearsonr(gd[P],gd[Y])[0] for d,gd in hiS.groupby('day') if len(gd)>=10]
icsS=np.array(icsS)
print(f"strong gated daily IC: n_days={len(icsS)} mean={icsS.mean():+.4f} t={icsS.mean()/(icsS.std(ddof=1)/np.sqrt(len(icsS))):+.2f}")

print()
print("="*100)
print("CHECK 6: daily-IC AC1 verify + rest-80% IC verify")
print("="*100)
sub=dc[dc['grp']=='drift']
ics=[]
for d,gd in sub.groupby('day'):
    if len(gd)>=20: ics.append(stats.pearsonr(gd[P],gd[Y])[0])
ics=np.array(ics)
print(f"drift daily IC AC1={np.corrcoef(ics[:-1],ics[1:])[0,1]:+.3f} n_days={len(ics)}")
parts=[]
for m,gm in sub.groupby('month'):
    thr=gm['abs_p'].quantile(.8); parts.append(gm[gm['abs_p']<thr])
lo=pd.concat(parts)
print(f"drift rest-80%% IC={stats.pearsonr(lo[P],lo[Y])[0]:+.4f} (n={len(lo)}); Spearman={stats.spearmanr(lo[P],lo[Y])[0]:+.4f}")
