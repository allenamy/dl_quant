import json, zipfile, glob, math, statistics, datetime as dt, os
raw = open('y4dump2.txt').read()
dump = json.loads(raw.split('DUMP_BEGIN\n')[1].strip())

# klines: open price at each hour (real market)
op = {}
for z in glob.glob('klines/*.zip') + glob.glob('k8/*.zip'):
    sym = os.path.basename(z).split('-1h-')[0]
    try:
        with zipfile.ZipFile(z) as zf:
            for line in zf.read(zf.namelist()[0]).decode().splitlines():
                p = line.split(',')
                if p and p[0] and p[0][0].isdigit():
                    op.setdefault(sym, {})[int(p[0])] = (float(p[1]), float(p[4]))
    except Exception:
        pass

def f(ms): return dt.datetime.fromtimestamp(ms/1000, dt.timezone.utc).strftime('%m-%dT%H:%MZ')

for sym in ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', '1000RATSUSDT'):
    if sym not in dump or sym not in op: 
        print('skip', sym); continue
    rows = []
    for ms, y4 in dump[sym]:
        if y4 is None: continue
        a, b = op[sym].get(ms), op[sym].get(ms + 4*3600*1000)
        if not a or not b: continue
        # 4 candidate definitions of "the 4h forward return"
        cands = {
            'log(open[t+4]/open[t])':   math.log(b[0]/a[0]),
            'log(close[t+4]/close[t])': math.log(b[1]/a[1]),
            'log(close[t+3]/close[t-1])': None,
            'simple(open[t+4]/open[t])': b[0]/a[0]-1.0,
        }
        c0 = op[sym].get(ms - 3600*1000); c3 = op[sym].get(ms + 3*3600*1000)
        if c0 and c3: cands['log(close[t+3]/close[t-1])'] = math.log(c3[1]/c0[1])
        rows.append((ms, y4, cands))
    if not rows: 
        print('no overlap', sym); continue
    print('\n=== %s : %d 个可比锚 ===' % (sym, len(rows)))
    for name in ('log(open[t+4]/open[t])', 'log(close[t+4]/close[t])',
                 'log(close[t+3]/close[t-1])', 'simple(open[t+4]/open[t])'):
        d = [(y4 - c[name]) for _, y4, c in rows if c.get(name) is not None]
        if not d: continue
        y = [y4 for _, y4, c in rows if c.get(name) is not None]
        x = [c[name] for _, y4, c in rows if c.get(name) is not None]
        n = len(d); mx, my = sum(x)/n, sum(y)/n
        num = sum((x[i]-mx)*(y[i]-my) for i in range(n))
        den = (sum((v-mx)**2 for v in x)*sum((v-my)**2 for v in y))**0.5
        print('  %-28s  n=%3d  bias=%+9.2f bps  |d|中位=%8.2f bps  corr=%+.6f'
              % (name, n, 1e4*statistics.mean(d), 1e4*statistics.median(abs(v) for v in d),
                 num/den if den else float('nan')))
    print('  逐点样本(前 6):')
    print('   %-14s %12s %12s %10s' % ('anchor', 'Y4', 'log(o[t+4]/o[t])', 'diff_bps'))
    for ms, y4, c in rows[:6]:
        k = c['log(open[t+4]/open[t])']
        print('   %-14s %+12.6f %+12.6f %+10.2f' % (f(ms), y4, k, 1e4*(y4-k)))
