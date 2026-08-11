import sys, os
sys.argv = ['x']
src = open('probe1b_v2.py').read().split('def analyse(')[0].replace(
    "SP = os.path.dirname(os.path.abspath(__file__))",
    "SP = os.getcwd()")
exec(src)
import statistics, collections, glob, json

pos = positions(SH)
ts = sorted(pos)
nav = {}
for f in sorted(glob.glob(SH + '/202607*/daily_nav.jsonl')):
    for l in open(f):
        if l.strip():
            r = json.loads(l); d = str(r['day'])
            nav['%s-%s-%s' % (d[:4], d[4:6], d[6:])] = r['realised_pnl']

def book_pnl(shift):
    day = collections.defaultdict(float)
    for k in range(len(ts) - 1):
        a = ts[k]
        if shift == 0:
            t0, t1 = ts[k], ts[k+1]
        else:
            if k == 0: continue
            t0, t1 = ts[k-1], ts[k]
        if (t1 - t0) / 3600.0 > 6: continue
        s = 0.0
        for sym, p in pos[a].items():
            v = float(p.get('venue_position_notional') or 0)
            p0, p1 = px(sym, t0), px(sym, t1)
            if v and p0 and p1:
                s += v * (p1 / p0 - 1.0)
        day[utc(a)[:10]] += s
    return day

for name, shift in (('FORWARD  [a,a+1]', 0), ('TRAILING [a-1,a]', -1)):
    d = book_pnl(shift)
    ks = sorted(set(d) & set(nav))
    md = statistics.mean(d[k] for k in ks); mn = statistics.mean(nav[k] for k in ks)
    num = sum((d[k]-md)*(nav[k]-mn) for k in ks)
    den = (sum((d[k]-md)**2 for k in ks) * sum((nav[k]-mn)**2 for k in ks)) ** 0.5
    print('%-18s my_total=%+9.2f   sys_total=%+9.2f   corr(daily,n=%d)=%+.3f'
          % (name, sum(d.values()), sum(nav.values()), len(ks), num/den if den else float('nan')))
