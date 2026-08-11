import pandas as pd, numpy as np
from scipy import stats
pd.set_option('display.width', 220)

SP = '/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad'
no = pd.read_csv(f'{SP}/nonoverlap_rows.csv')
D  = pd.read_csv(f'{SP}/daily_ic_cond.csv')

# ---------- row-level prior funding print ----------
f = pd.read_csv('/Users/haosiyu/Desktop/quant_research/data/funding/btcusdt_funding.csv').sort_values('fundingTime_ms')
fms = f['fundingTime_ms'].values; frate = f['fundingRate'].values
idx = np.searchsorted(fms, no['timestamp_ms'].values + 60_000, side='right') - 1
no['fund_prior'] = frate[idx]

# per-day deciles of y_pred_demeaned (trading signal), days with >=30 rows
no['nday'] = no.groupby('date')['timestamp_ms'].transform('size')
sub = no[no['nday'] >= 30].copy()
sub['dec'] = sub.groupby('date')['y_pred_demeaned'].transform(
    lambda s: pd.qcut(s.rank(method='first'), 10, labels=False))
# funding tercile over rows
sub['fter'] = pd.qcut(sub['fund_prior'].rank(method='first'), 3, labels=['F1(low)','F2(mid)','F3(high)'])
print("funding tercile edges (row-level prior print):")
print(sub.groupby('fter', observed=True)['fund_prior'].agg(['min','max','size']).to_string(float_format='%.6f'))

print("\n=== per-side conditional mean y_true (bps) in top/bottom y_pred decile BY funding tercile ===")
rows = []
for ft, g in sub.groupby('fter', observed=True):
    top = g[g['dec']==9]['y_true_ret_bps']; bot = g[g['dec']==0]['y_true_ret_bps']
    allm = g['y_true_ret_bps'].mean()
    rows.append({'fund_ter': ft, 'n_state': len(g), 'mean_y_all': allm,
                 'long_topdec_mean_y': top.mean(), 'long_edge_vs_state': top.mean()-allm,
                 'long_t': top.mean()/ (top.std()/np.sqrt(len(top))),
                 'short_botdec_mean_y': bot.mean(), 'short_edge_vs_state': allm-bot.mean(),
                 'short_t': -bot.mean()/(bot.std()/np.sqrt(len(bot))),
                 'n_top': len(top), 'n_bot': len(bot)})
print(pd.DataFrame(rows).to_string(float_format='%.3f'))

# extreme funding: top/bottom decile of funding
sub['fdec'] = pd.qcut(sub['fund_prior'].rank(method='first'), 10, labels=False)
print("\n--- extreme funding states (top/bottom funding decile) ---")
for name, g in [('funding bottom decile', sub[sub['fdec']==0]), ('funding top decile', sub[sub['fdec']==9])]:
    top = g[g['dec']==9]['y_true_ret_bps']; bot = g[g['dec']==0]['y_true_ret_bps']
    print(f"{name}: n={len(g)} mean_y_all={g['y_true_ret_bps'].mean():+.3f} | "
          f"LONG top-dec mean_y={top.mean():+.3f} (n={len(top)}, t={top.mean()/(top.std()/np.sqrt(len(top))):.2f}) | "
          f"SHORT bot-dec mean_y={bot.mean():+.3f} (n={len(bot)}, t={-bot.mean()/(bot.std()/np.sqrt(len(bot))):.2f})")

# ---------- HONEST UPPER BOUND: perfect state-level day reweighting ----------
IC = 'ic_raw'
print(f"\n=== honest upper bound (day reweighting by conditional mean IC, caliber={IC}) ===")
print("formula: scale day-d preds by state weight w_s; pooled per-day-CLEAN IC = sum_s f_s w_s mu_s / sqrt(sum_s f_s w_s^2)")
print("optimum w_s = mu_s  ->  IC_max = sqrt(sum_s f_s mu_s^2); no-flip: drop states with mu_s<0")
base = D[IC].mean()
res = []
for var in ['funding_prior','abs_funding_prior','oi_chg_prior_day','ttls_prior_day','pidxvol_prior_day']:
    d = D.dropna(subset=[var, IC]).copy()
    d['ter'] = pd.qcut(d[var].rank(method='first'), 3, labels=False)
    g = d.groupby('ter')[IC].agg(['mean','size'])
    fS = g['size']/g['size'].sum(); mu = g['mean']
    ub_flip  = np.sqrt((fS*mu**2).sum())
    ub_noflip= np.sqrt((fS[mu>0]*mu[mu>0]**2).sum())
    res.append({'conditioner': var, 'mu_T1': mu.iloc[0], 'mu_T2': mu.iloc[1], 'mu_T3': mu.iloc[2],
                'baseline': (fS*mu).sum(), 'UB_flip': ub_flip, 'UB_noflip': ub_noflip,
                'lift_noflip': ub_noflip-(fS*mu).sum()})
print(pd.DataFrame(res).to_string(float_format='%.4f'))
# oracle ceiling: weight each day by its own realized IC (NOT achievable from conditioning)
print(f"\nbaseline mean daily IC = {base:.4f}")
print(f"day-level ORACLE ceiling sqrt(mean(IC_d^2)) = {np.sqrt((D[IC]**2).mean()):.4f}  (weights by realized IC_d itself; absolute ceiling of ANY day-scale conditioner)")
# joint 3x3 of best two (pidxvol x oi_chg) - overfit flag
d = D.dropna(subset=['pidxvol_prior_day','oi_chg_prior_day',IC]).copy()
d['a'] = pd.qcut(d['pidxvol_prior_day'].rank(method='first'),3,labels=False)
d['b'] = pd.qcut(d['oi_chg_prior_day'].rank(method='first'),3,labels=False)
g = d.groupby(['a','b'])[IC].agg(['mean','size'])
fS = g['size']/g['size'].sum(); mu = g['mean']
print(f"joint pidxvol x oi_chg (9 cells, ~{int(g['size'].mean())} days/cell, IN-SAMPLE overfit): UB_flip={np.sqrt((fS*mu**2).sum()):.4f} UB_noflip={np.sqrt((fS[mu>0]*mu[mu>0]**2).sum()):.4f}")

# ---------- month-confound check: does conditioner survive month fixed effects? ----------
print("\n=== month fixed-effect check (day-level Spearman of conditioner vs IC, raw and month-demeaned) ===")
D['month'] = pd.to_datetime(D['date']).astype(str).str[:7]
for var in ['funding_prior','abs_funding_prior','oi_chg_prior_day','ttls_prior_day','pidxvol_prior_day']:
    d = D.dropna(subset=[var,IC]).copy()
    r_raw, p_raw = stats.spearmanr(d[var], d[IC])
    dm = d.copy()
    dm[var] = dm[var] - dm.groupby('month')[var].transform('mean')
    dm[IC]  = dm[IC]  - dm.groupby('month')[IC].transform('mean')
    r_dm, p_dm = stats.spearmanr(dm[var], dm[IC])
    print(f"{var:22s} raw rho={r_raw:+.3f} (p={p_raw:.3f})   month-demeaned rho={r_dm:+.3f} (p={p_dm:.3f})")
