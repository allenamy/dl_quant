import pandas as pd, numpy as np
from scipy import stats
pd.set_option('display.width', 220)
SP = '/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad'

# ---------- interaction significance: side x funding-state (non-overlap rows) ----------
no = pd.read_csv(f'{SP}/nonoverlap_rows.csv')
f = pd.read_csv('/Users/haosiyu/Desktop/quant_research/data/funding/btcusdt_funding.csv').sort_values('fundingTime_ms')
idx = np.searchsorted(f['fundingTime_ms'].values, no['timestamp_ms'].values + 60_000, side='right') - 1
no['fund_prior'] = f['fundingRate'].values[idx]
no['nday'] = no.groupby('date')['timestamp_ms'].transform('size')
sub = no[no['nday']>=30].copy()
sub['dec'] = sub.groupby('date')['y_pred_demeaned'].transform(lambda s: pd.qcut(s.rank(method='first'),10,labels=False))
sub['fter'] = pd.qcut(sub['fund_prior'].rank(method='first'),3,labels=False)
b1 = sub[(sub['dec']==0)&(sub['fter']==0)]['y_true_ret_bps']; b3 = sub[(sub['dec']==0)&(sub['fter']==2)]['y_true_ret_bps']
t1 = sub[(sub['dec']==9)&(sub['fter']==0)]['y_true_ret_bps']; t3 = sub[(sub['dec']==9)&(sub['fter']==2)]['y_true_ret_bps']
tb,pb = stats.ttest_ind(b3,b1,equal_var=False); tt,pt = stats.ttest_ind(t3,t1,equal_var=False)
print(f"INTERACTION bot-dec y_true F3 vs F1: {b3.mean():+.3f} vs {b1.mean():+.3f} bps, diff={b3.mean()-b1.mean():+.3f}, Welch t={tb:.2f} p={pb:.4f}")
print(f"INTERACTION top-dec y_true F3 vs F1: {t3.mean():+.3f} vs {t1.mean():+.3f} bps, diff={t3.mean()-t1.mean():+.3f}, Welch t={tt:.2f} p={pt:.4f}")

# ---------- intra-day: hour/4h-block IC vs PRIOR-window 5m OI & premium movement ----------
df = pd.read_csv('/Users/haosiyu/Desktop/quant_research/exports/final_l01/y600_backtest_dataset.csv').sort_values('timestamp_ms')
df['date'] = pd.to_datetime(df['timestamp_ms'], unit='ms', utc=True).dt.date

m = pd.read_csv('/Users/haosiyu/Desktop/quant_research/data/funding/btcusdt_metrics_5m.csv',
                usecols=['create_time','sum_open_interest'])
m['tms'] = pd.to_datetime(m['create_time'], utc=True).astype('int64')*1000  # s->ms? check unit below
if m['tms'].iloc[0] > 10**16: m['tms'] = m['tms']//10**6  # normalize ns->ms if needed
m = m.sort_values('tms'); mt = m['tms'].values; moi = m['sum_open_interest'].values

p = pd.read_csv('/Users/haosiyu/Desktop/quant_research/data/funding/btcusdt_premium_index_5m.csv',
                usecols=['openTime_ms','pidx_close']).sort_values('openTime_ms')
pt_ = p['openTime_ms'].values; pc = p['pidx_close'].values

def last_leq(arr_t, arr_v, t):
    i = np.searchsorted(arr_t, t, side='right')-1
    return np.where(i>=0, arr_v[np.clip(i,0,None)], np.nan)

def block_analysis(block_ms, min_rows, label):
    df2 = df.copy()
    df2['blk'] = (df2['timestamp_ms']//block_ms)*block_ms
    rows=[]
    for blk, g in df2.groupby('blk'):
        if len(g) < min_rows: continue
        ic = np.corrcoef(g['y_pred_raw'], g['y_true_ret_bps'])[0,1]
        if not np.isfinite(ic): continue
        rows.append({'blk':blk,'date':g['date'].iloc[0],'ic':ic,'n':len(g)})
    B = pd.DataFrame(rows)
    t0 = B['blk'].values
    W = block_ms  # prior window = one block length
    oi_now  = last_leq(mt, moi, t0); oi_prev = last_leq(mt, moi, t0-W)
    B['oi_chg_prior'] = np.abs(oi_now/oi_prev - 1)
    B['oi_chg_prior_signed'] = oi_now/oi_prev - 1
    pi_now = last_leq(pt_, pc, t0); pi_prev = last_leq(pt_, pc, t0-W)
    B['pidx_move_prior'] = np.abs(pi_now-pi_prev)
    B['pidx_level'] = np.abs(pi_now)
    # premium vol in prior window: std of 5m closes
    pv=[]
    for t in t0:
        i0,i1 = np.searchsorted(pt_, [t-W, t])
        pv.append(np.std(pc[i0:i1]) if i1-i0>=3 else np.nan)
    B['pidx_vol_prior'] = pv
    print(f"\n=== {label}: n_blocks={len(B)}, rows/block median={B['n'].median():.0f} (stride-180 OVERLAPPING; eff n ~ rows*0.3) ===")
    for var in ['oi_chg_prior','oi_chg_prior_signed','pidx_move_prior','pidx_vol_prior','pidx_level']:
        d = B.dropna(subset=[var,'ic']).copy()
        r,pv_ = stats.spearmanr(d[var], d['ic'])
        dd = d.copy()
        dd['ic'] = dd['ic'] - dd.groupby('date')['ic'].transform('mean')
        dd[var]  = dd[var]  - dd.groupby('date')[var].transform('mean')
        r2,pv2 = stats.spearmanr(dd[var], dd['ic'])
        # tercile means for magnitude read
        d['ter']=pd.qcut(d[var].rank(method='first'),3,labels=False)
        mus = d.groupby('ter')['ic'].mean().values
        print(f"{var:22s} rho={r:+.3f}(p={pv_:.3f}) day-demeaned rho={r2:+.3f}(p={pv2:.3f})  tercile mean IC: {mus[0]:+.4f}/{mus[1]:+.4f}/{mus[2]:+.4f}")
    return B

B1 = block_analysis(3_600_000, 15, '1h blocks')
B4 = block_analysis(14_400_000, 60, '4h blocks')

# noise floor for block IC
for B,lbl,effn in [(B1,'1h',6),(B4,'4h',24)]:
    print(f"{lbl}: block IC std={B['ic'].std():.3f}; pure-noise std at eff n={effn} ~ {1/np.sqrt(effn):.3f}")
