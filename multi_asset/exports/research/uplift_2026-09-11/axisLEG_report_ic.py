import json,numpy as np,datetime as dt,collections
D=json.load(open('/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/leg_ic_out.json'))
ts=np.array(D['E_ts'],np.int64)
IC={k:np.array(v,float) for k,v in D['IC'].items()}
LR={k:np.array(v,float) for k,v in D['LR'].items()}
REG={k:np.array(v,float) for k,v in D['REG'].items()}
ym=np.array([dt.datetime.utcfromtimestamp(int(t)).strftime('%Y-%m') for t in ts])
yr=np.array([dt.datetime.utcfromtimestamp(int(t)).year for t in ts])
def st(v):
    v=v[np.isfinite(v)]; n=len(v)
    if n<2: return (n,np.nan,np.nan,np.nan)
    m=v.mean(); se=v.std(ddof=1)/np.sqrt(n); return (n,m,se,m/se)
print('=== ANNUAL cross-sectional Spearman rank-IC vs y4 (4h fwd, Sum-of-5m-simple caliber) ===')
print(f"{'year':6}{'n':>6}   "+ '   '.join(f'{l:>22}' for l in ('king','rev24','fund')))
for y in sorted(set(yr)):
    s=yr==y; row=f'{y:6}{s.sum():6d}   '
    for l in ('king','rev24','fund'):
        n,m,se,t=st(IC[l][s]); row+=f'{m:+.4f}±{1.96*se:.4f}(t{t:+5.1f}) '
    print(row)
print()
print('=== MONTHLY rank-IC, 2025-01 .. 2026-08  (mean ± 95%CI, t) ===')
print(f"{'month':9}{'n':>5}  "+'  '.join(f'{l:>24}' for l in ('king','rev24','fund')))
for mm in sorted(set(ym)):
    if mm<'2025-01': continue
    s=ym==mm; row=f'{mm:9}{s.sum():5d}  '
    for l in ('king','rev24','fund'):
        n,m,se,t=st(IC[l][s]); row+=f'{m:+.4f}[{1.96*se:.4f}]t{t:+5.2f}  '
    print(row)
print()
print('=== MONTHLY funding regime (bps per 4h across members) + xs return dispersion ===')
print(f"{'month':9}{'fn_mean':>9}{'fn_sd':>9}{'p90-p10':>9}{'frac<0':>8}{'|fn|mean':>9}{'fe_sd':>10}{'xs_sd(y4)bps':>14}")
for mm in sorted(set(ym)):
    if mm<'2024-01': continue
    s=ym==mm
    f=lambda k: np.nanmean(REG[k][s])
    print(f"{mm:9}{f('fn_mean'):+9.3f}{f('fn_sd'):9.3f}{f('fn_p90')-f('fn_p10'):9.3f}{f('fn_fracneg'):8.3f}{f('fn_absmean'):9.3f}{f('fe_sd'):10.5f}{f('y_sd'):14.1f}")
print()
print('=== SIGNAL DECAY: IC(score_t, y4_{t+k}) by lag k, by era ===')
eras=[('2024',(yr==2024)),('2025',(yr==2025)),('2026H1',(ts>=1767225600)&(ts<1782864000)),('2026-07..08',(ts>=1782864000))]
for l in ('fund','king'):
    print(' leg',l)
    for nm,s in eras:
        r=[]
        for k in range(0,13):
            v=np.array(D['ICL'][l][str(k)],float)[s]; v=v[np.isfinite(v)]
            r.append(v.mean() if len(v)>10 else np.nan)
        print(f'   {nm:12} '+' '.join(f'{k}:{x:+.4f}' for k,x in enumerate(r)))
