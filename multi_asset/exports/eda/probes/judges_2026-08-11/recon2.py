exec(open('recon.py').read().split('def book(')[0])
import math
def book2(use_log, restrict_finite_y4):
    y4 = {}
    if restrict_finite_y4:
        raw = open('y4dump2.txt').read()
        pass
    day = collections.defaultdict(float)
    for t in ts:
        s = 0.0
        for sym, v in pos[t].items():
            if not v: continue
            a, b = CL.get(sym, {}).get(t), CL.get(sym, {}).get(t + 4*3600)
            if not a or not b: continue
            s += v * (math.log(b/a) if use_log else (b/a - 1.0))
        day[utc(t)] += s
    return day
sysT = sum(nav.values())
for use_log in (False, True):
    d = book2(use_log, False); ks = sorted(set(d) & set(nav))
    md = statistics.mean(d[k] for k in ks); mn = statistics.mean(nav[k] for k in ks)
    num = sum((d[k]-md)*(nav[k]-mn) for k in ks)
    den = (sum((d[k]-md)**2 for k in ks)*sum((nav[k]-mn)**2 for k in ks))**0.5
    print('CLOSE + %-6s : mine %+9.2f  system %+9.2f  gap %+8.2f (%.1f%%)  corr %.4f'
          % ('log' if use_log else 'simple', sum(d.values()), sysT,
             sum(d.values())-sysT, 100*(sum(d.values())-sysT)/abs(sysT), num/den))
# how many held names are missing a kline at all (coverage of my price side)
miss = collections.Counter()
for t in ts:
    for sym, v in pos[t].items():
        if v and (not CL.get(sym, {}).get(t) or not CL.get(sym, {}).get(t+4*3600)):
            miss[sym] += 1
print()
print('持仓但缺 kline 的名字数: %d  (总计 %d 个锚-名)' % (len(miss), sum(miss.values())))
print('  前几个:', miss.most_common(6))
