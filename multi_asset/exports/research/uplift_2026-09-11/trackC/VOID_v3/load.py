import numpy as np, time, csv, os, json
S='/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/w10'
OUT=os.path.dirname(os.path.abspath(__file__))
RT='/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/regime_anchor_table_v4holefix_2022_2026-08.csv'
def book(tag='pod_live_w3fix_callog_s42', arm='d30_n2_c42'):
    z=np.load(f'{S}/w10_ablation_series_{tag}.npz',allow_pickle=True)
    cols=[str(c) for c in z['cols']]; rec=z[f'{arm}_rec']
    g=lambda k: rec[:,cols.index(k)].astype(float)
    d={c:g(c) for c in cols}
    d['ts']=rec[:,cols.index('ts')].astype(np.int64)
    d['u']=d['net_ex']/d['gross_total']          # bps per unit gross per anchor (live caliber)
    d['cfg']=json.loads(str(z['config_json']))
    return d
def regime():
    rows=list(csv.DictReader(open(RT)))
    ts=np.array([int(r['ts']) for r in rows])
    out={'ts':ts}
    for k in rows[0]:
        if k=='ts': continue
        out[k]=np.array([float(r[k]) if r[k] not in ('','nan') else np.nan for r in rows])
    return out
def ann_sharpe(x, n_per_yr=2190):
    x=np.asarray(x,float); x=x[np.isfinite(x)]
    if len(x)<3 or x.std(ddof=1)==0: return np.nan
    return x.mean()/x.std(ddof=1)*np.sqrt(n_per_yr)
def se_sharpe(n, n_per_yr=2190): return np.sqrt(n_per_yr/max(n,1))
