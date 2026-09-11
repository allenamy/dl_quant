import numpy as np, json, datetime as dt, sys
BUN='/Users/haosiyu/wide_shadow/shadow_bundle/leg_returns.npz'
z=np.load(BUN); ts=z['ts'].astype(np.int64)
legs=('king','rev24','fund')
L={k:np.array(z[k],float) for k in legs}
mon=np.array([dt.datetime.utcfromtimestamp(int(t)).strftime('%Y-%m') for t in ts])
yr =np.array([dt.datetime.utcfromtimestamp(int(t)).year for t in ts])
def stat(v):
    n=len(v); m=v.mean(); s=v.std(ddof=1) if n>1 else float('nan')
    se=s/np.sqrt(n) if n>1 else float('nan')
    return n,m,s,se,m/se if se and se==se and se>0 else float('nan')
print('=== YEARLY (bps/anchor, unit-gross rank-weighted leg return) ===')
print(f"{'year':6} {'n':>5} "+ ' '.join(f'{l:>28}' for l in legs))
for y in sorted(set(yr)):
    sel=yr==y
    row=f'{y:6} {sel.sum():5d} '
    for l in legs:
        n,m,s,se,t=stat(L[l][sel]); row+=f'  {m:+7.3f}±{1.96*se:5.3f} (t{t:+5.2f}) '
    print(row)
print()
print('=== MONTHLY 2024-01..2026-08 (mean bps/anchor [95%CI halfwidth] t) ===')
print(f"{'month':8} {'n':>4} "+''.join(f'{l:>26}' for l in legs))
for mm in sorted(set(mon)):
    if mm<'2024-01': continue
    sel=mon==mm
    row=f'{mm:8} {sel.sum():4d} '
    for l in legs:
        n,m,s,se,t=stat(L[l][sel]); row+=f'{m:+7.3f}[{1.96*se:5.2f}]t{t:+5.2f} '
    print(row)
