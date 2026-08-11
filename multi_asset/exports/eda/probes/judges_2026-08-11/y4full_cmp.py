import json, zipfile, glob, os, math, statistics, collections, datetime as dt
dump = json.loads(open('y4full.txt').read().split('DUMP_BEGIN\n')[1].strip())
CL = {}
for z in glob.glob('btc_hist/*.zip') + glob.glob('k8/BTCUSDT*.zip'):
    try:
        with zipfile.ZipFile(z) as zf:
            for line in zf.read(zf.namelist()[0]).decode().splitlines():
                p = line.split(',')
                if p and p[0] and p[0][0].isdigit():
                    CL[int(p[0])] = float(p[4])
    except Exception as e:
        print('skip', z, e)
print('kline hourly bars: %d  span %s -> %s' % (
    len(CL),
    dt.datetime.fromtimestamp(min(CL)/1000, dt.timezone.utc).strftime('%Y-%m'),
    dt.datetime.fromtimestamp(max(CL)/1000, dt.timezone.utc).strftime('%Y-%m')))
bym = collections.defaultdict(list)
n_cmp = n_exact = 0
worst = []
for ms, y4 in dump:
    if y4 is None: continue
    a, b = CL.get(ms), CL.get(ms + 4*3600*1000)
    if not a or not b: continue
    d = y4 - math.log(b/a)
    n_cmp += 1
    if abs(d) < 1e-9: n_exact += 1
    ym = dt.datetime.fromtimestamp(ms/1000, dt.timezone.utc).strftime('%Y-%m')
    bym[ym].append(d)
    worst.append((abs(d), ms, y4, math.log(b/a)))
print('可比锚: %d   其中 |Y4 - log(close[t+4]/close[t])| < 1e-9 的: %d  (%.4f%%)'
      % (n_cmp, n_exact, 100.0*n_exact/n_cmp))
bad = {m: v for m, v in bym.items() if max(abs(x) for x in v) >= 1e-9}
print('有任何非零差的月份数: %d / %d' % (len(bad), len(bym)))
if bad:
    print('  逐月最大 |差| (bps), 只列非零月:')
    for m in sorted(bad)[:24]:
        v = bad[m]
        print('    %s  n=%4d  max|d|=%10.4f bps  mean d=%+9.4f bps'
              % (m, len(v), 1e4*max(abs(x) for x in v), 1e4*statistics.mean(v)))
worst.sort(reverse=True)
print()
print('全历史最大的 5 个偏差:')
for a, ms, y4, k in worst[:5]:
    print('   %s  Y4=%+.8f  kline=%+.8f  diff=%+.4f bps'
          % (dt.datetime.fromtimestamp(ms/1000, dt.timezone.utc).strftime('%Y-%m-%dT%H:%MZ'),
             y4, k, 1e4*(y4-k)))
allv = [x for v in bym.values() for x in v]
print()
print('全历史: n=%d  偏置=%+.6f bps  中位|差|=%.6f bps  max|差|=%.4f bps'
      % (len(allv), 1e4*statistics.mean(allv),
         1e4*statistics.median(abs(x) for x in allv), 1e4*max(abs(x) for x in allv)))
