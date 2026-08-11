exec(open('probe2_flip.py').read().split('def summ(')[0])
import random, statistics

print()
print('=== A. ZERO-FLIP ANCHORS: real, or a detector defect? ===')
for k in range(1, len(ts)-1):
    a0,a1 = ts[k-1], ts[k]
    both = 0; signch = 0; traded_names = 0
    for s,p in pos[a1].items():
        q1 = float(p.get('venue_position_qty') or 0)
        q0 = float((pos[a0].get(s) or {}).get('venue_position_qty') or 0)
        if q0 and q1:
            both += 1
            if (q0>0)!=(q1>0): signch += 1
        if q1 != q0: traded_names += 1
    fl = sum(1 for r in recs if r['a']==a1 and r['flip'])
    print('  %-18s names_both_nonzero=%3d  sign_changes=%3d  names_with_qty_change=%3d  flips_recorded=%3d'
          % (utc(a1), both, signch, traded_names, fl))

print()
print('=== B. IS -5.65 bps DISTINGUISHABLE FROM NOISE? ===')
F = [r for r in recs if r['flip']]
N = [r for r in recs if not r['flip']]
def wbps(rs):
    t = sum(r['traded'] for r in rs); 
    return 1e4*sum(r['pnl'] for r in rs)/t if t else float('nan')
obs_f, obs_n = wbps(F), wbps(N)
print('observed: flip %+.2f bps   non-flip %+.2f bps   gap %+.2f bps' % (obs_f, obs_n, obs_f-obs_n))

random.seed(0)
# (1) trade-level bootstrap of the flip mean
bs = sorted(wbps([F[random.randrange(len(F))] for _ in range(len(F))]) for _ in range(20000))
print('flip mean, trade-level bootstrap 95%%CI: [%+.2f, %+.2f]  -> excludes 0? %s'
      % (bs[500], bs[19500], 'YES' if (bs[500]>0 or bs[19500]<0) else 'NO'))

# (2) ANCHOR-level bootstrap (the honest unit: names inside an anchor are co-directional)
anchors = sorted(set(r['a'] for r in F))
def wbps_anchors(sel):
    rs = [r for a in sel for r in F if r['a']==a]
    return wbps(rs)
bs2 = sorted(x for x in (wbps_anchors([anchors[random.randrange(len(anchors))] for _ in range(len(anchors))])
             for _ in range(20000)) if x==x)
print('flip mean, ANCHOR-level bootstrap 95%%CI (n=%d anchors): [%+.2f, %+.2f]  -> excludes 0? %s'
      % (len(anchors), bs2[int(.025*len(bs2))], bs2[int(.975*len(bs2))],
         'YES' if (bs2[int(.025*len(bs2))]>0 or bs2[int(.975*len(bs2))]<0) else 'NO'))

# (3) permutation: shuffle the flip label WITHIN each anchor
obs_gap = obs_f - obs_n
byA = {}
for r in recs: byA.setdefault(r['a'], []).append(r)
cnt = 0; NP = 20000
for _ in range(NP):
    fs, ns = [], []
    for a, rs in byA.items():
        nf = sum(1 for r in rs if r['flip'])
        idx = list(range(len(rs))); random.shuffle(idx)
        for j,i in enumerate(idx):
            (fs if j < nf else ns).append(rs[i])
    g = wbps(fs) - wbps(ns)
    if abs(g) >= abs(obs_gap): cnt += 1
print('within-anchor permutation p(|gap| >= observed) = %.4f  (B=%d)' % (cnt/NP, NP))

print()
print('=== C. PER-ANCHOR flip PnL in bps of GROSS (the deployable unit) ===')
vals=[]
for a in anchors:
    fa=[r for r in F if r['a']==a]; g=fa[0]['gross']
    vals.append(1e4*sum(r['pnl'] for r in fa)/g)
vals_s=sorted(vals)
print('  per-anchor values: %s' % ', '.join('%+.2f' % v for v in vals_s))
print('  mean %+.3f  median %+.3f bps of gross' % (statistics.mean(vals), statistics.median(vals)))
bs3=sorted(statistics.mean([vals[random.randrange(len(vals))] for _ in range(len(vals))]) for _ in range(20000))
print('  anchor bootstrap 95%%CI of the mean: [%+.3f, %+.3f]' % (bs3[500], bs3[19500]))
print('  >>> lead threshold: enters mechanism design only if negative AND |.| > 1 bps/anchor')
