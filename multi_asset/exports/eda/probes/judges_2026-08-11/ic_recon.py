import json, glob, collections, math, statistics, datetime as dt
LV = '/Users/haosiyu/dl_quant_live/state/live/pilot_log'
f = lambda x: dt.datetime.fromtimestamp(x, dt.timezone.utc).strftime('%m-%dT%H:%MZ')

A = []
for g in sorted(glob.glob(LV + '/*/anchors.jsonl')): A += [json.loads(l) for l in open(g) if l.strip()]
A.sort(key=lambda r: r['anchor_ts'])
O = []
for g in sorted(glob.glob(LV + '/*/orders.jsonl')): O += [json.loads(l) for l in open(g) if l.strip()]
R = []
for g in sorted(glob.glob(LV + '/*/position_readback.jsonl')): R += [json.loads(l) for l in open(g) if l.strip()]

mids = {a['anchor_ts']: json.loads(a['mid_at_anchor_vector']) for a in A if a.get('mid_at_anchor_vector')}
tw = collections.defaultdict(dict)
for o in O:
    if o.get('order_type') == 'maker': tw[o['anchor_ts']][o['symbol']] = float(o.get('target_w') or 0)
pos = collections.defaultdict(dict)
for r in R:
    p = pos[r['anchor_ts']].get(r['symbol'])
    if p is None or (r.get('read_ts') or 0) >= (p.get('read_ts') or 0):
        pos[r['anchor_ts']][r['symbol']] = r

ts = sorted(mids)
def rank(v):
    idx = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0]*len(v); i = 0
    while i < len(idx):
        j = i
        while j+1 < len(idx) and v[idx[j+1]] == v[idx[i]]: j += 1
        avg = (i+j)/2.0 + 1
        for k in range(i, j+1): r[idx[k]] = avg
        i = j+1
    return r
def corr(x, y):
    n = len(x)
    if n < 8: return None
    mx, my = sum(x)/n, sum(y)/n
    num = sum((x[i]-mx)*(y[i]-my) for i in range(n))
    den = (sum((v-mx)**2 for v in x)*sum((v-my)**2 for v in y))**0.5
    return num/den if den else None

def run(signal, method, label):
    out = []
    for k in range(len(ts)-1):
        T, T2 = ts[k], ts[k+1]
        m0, m1 = mids[T], mids[T2]
        xs, ys = [], []
        src = tw.get(T, {}) if signal == 'target_w' else {
            s: float(p.get('venue_position_notional') or 0) for s, p in pos.get(T, {}).items()}
        for s, w in src.items():
            if w == 0: continue
            a, b = float(m0.get(s, 0) or 0), float(m1.get(s, 0) or 0)
            if a and b: xs.append(w); ys.append(b/a - 1)
        if len(xs) < 8: continue
        c = corr(rank(xs), rank(ys)) if method == 'spearman' else corr(xs, ys)
        if c is not None: out.append((T, len(xs), c))
    v = [c for _, _, c in out]
    m = statistics.mean(v); sd = statistics.stdev(v) if len(v) > 1 else float('nan')
    t = m/(sd/len(v)**0.5) if len(v) > 1 and sd else float('nan')
    print('%-46s  锚对 %2d   IC均值 %+7.4f   sd %6.4f   t %+5.2f' % (label, len(v), m, sd, t))
    return out, m

print('=== 对平阶梯: 一次只换一个因素 ===')
_, a = run('target_w', 'pearson', 'A 我的: target_w × Pearson × 全部可用锚对')
_, b = run('target_w', 'spearman', 'B  换 Spearman')
_, c = run('position', 'spearman', 'C  再换 实际持仓 venue_position_notional')
_, d = run('position', 'pearson', 'D  (对照) 实际持仓 × Pearson')
print()
print('分解: A→B (Pearson→Spearman) %+.4f ; B→C (目标权重→实际持仓) %+.4f ; 合计 A→C %+.4f'
      % (b-a, c-b, c-a))
print()
print('★ 逐锚明细 (C = 你的口径):')
rows, _ = run('position', 'spearman', '   (重列)')
for T, n, cc in rows:
    print('     %-14s n=%3d  IC=%+.4f' % (f(T), n, cc))
