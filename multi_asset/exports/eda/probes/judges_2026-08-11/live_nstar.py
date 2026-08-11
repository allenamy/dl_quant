import os, math, statistics, random
src = open('probe1b_v2.py').read().split('def px(')[0].replace(
    "SP = os.path.dirname(os.path.abspath(__file__))", "SP = os.getcwd()")
exec(src)
import json, glob, collections
LV = '/Users/haosiyu/dl_quant_live/state/live/pilot_log'
A = []
for f in sorted(glob.glob(LV + '/*/anchors.jsonl')):
    A += [json.loads(l) for l in open(f) if l.strip()]
mids = {a['anchor_ts']: json.loads(a['mid_at_anchor_vector']) for a in A if a.get('mid_at_anchor_vector')}
R = []
for f in sorted(glob.glob(LV + '/*/position_readback.jsonl')):
    R += [json.loads(l) for l in open(f) if l.strip()]
pos = collections.defaultdict(dict)
for r in R:
    p = pos[r['anchor_ts']].get(r['symbol'])
    if p is None or (r.get('read_ts') or 0) >= (p.get('read_ts') or 0):
        pos[r['anchor_ts']][r['symbol']] = r
ts = sorted(t for t in pos if t in mids and mids[t])
v = []
for k in range(len(ts)-1):
    a, b = ts[k], ts[k+1]
    m0, m1 = mids[a], mids[b]
    if 'BTCUSDT' not in m0 or 'BTCUSDT' not in m1: continue
    rbtc = float(m1['BTCUSDT'])/float(m0['BTCUSDT']) - 1.0
    vals = [(s, float(p.get('venue_position_notional') or 0)) for s, p in pos[a].items()]
    vals = [(s, x) for s, x in vals if x and s in B_ALL]
    g = sum(abs(x) for _, x in vals)
    if g <= 100: continue
    bbar = sum(abs(x)*B_ALL[s] for s, x in vals)/g
    disp = sum(x*(B_ALL[s]-bbar) for s, x in vals)
    v.append((disp*rbtc, g))
pn = [x for x, _ in v]; g = statistics.median(gg for _, gg in v)
mu, sd = statistics.mean(pn), statistics.stdev(pn)
print('LIVE: intervals %d  median gross $%.0f' % (len(pn), g))
print('  cumulative disp PnL $%+.2f  (%+.2f bps of gross)' % (sum(pn), 1e4*sum(pn)/g))
print('  per-interval mean $%+.4f  sd $%.4f   (mean %.3f bps, sd %.3f bps)'
      % (mu, sd, 1e4*mu/g, 1e4*sd/g))
random.seed(0)
bs = sorted(sum(pn[random.randrange(len(pn))] for _ in range(len(pn))) for _ in range(20000))
print('  bootstrap 95%%CI of cumulative [$%+.2f, $%+.2f]' % (bs[500], bs[19500]))
print('  n* for 80%% power at this effect size = %d intervals (%.1f days @6/day)'
      % (math.ceil(7.8489*(sd/mu)**2), math.ceil(7.8489*(sd/mu)**2)/6.0))
