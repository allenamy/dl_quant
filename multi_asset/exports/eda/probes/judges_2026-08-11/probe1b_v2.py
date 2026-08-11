"""PROBE 1b v2 — dispersion tilt: is it paid for?
v1 was INVALID for the shadow period: shadow's mid_at_anchor_vector is a SYNTHETIC ~100 index,
not a price. v2 takes ALL prices from Binance 1h klines (independent source) for both periods."""
import zipfile, glob, os, json, math, collections, statistics, random, datetime as dt

SP = os.path.dirname(os.path.abspath(__file__))
KL, SH = os.path.join(SP, 'klines'), os.path.join(SP, 'shadow')
LV = '/Users/haosiyu/dl_quant_live/state/live/pilot_log'


def secs(t):
    t = float(t)
    return t / 1000.0 if t > 1e12 else t


def utc(t):
    return dt.datetime.fromtimestamp(secs(t), dt.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')


# ---- prices: OPEN of the 1h bar starting at t  = the price AT time t -------
opens, closes = collections.defaultdict(dict), collections.defaultdict(dict)
for z in sorted(glob.glob(os.path.join(KL, '*.zip'))):
    sym = os.path.basename(z).split('-1h-')[0]
    with zipfile.ZipFile(z) as zf:
        for line in zf.read(zf.namelist()[0]).decode().splitlines():
            p = line.split(',')
            if p and p[0] and p[0][0].isdigit():
                opens[sym][int(p[0]) // 1000] = float(p[1])
                closes[sym][int(p[0]) // 1000] = float(p[4])

JUL1 = 1782950400


def hret(sym, t0=None, t1=None):
    c = closes.get(sym, {})
    ks = sorted(c)
    out, prev = {}, None
    for t in ks:
        if prev is not None and (t0 is None or t >= t0) and (t1 is None or t < t1) \
           and c[prev] > 0 and c[t] > 0:
            out[t] = math.log(c[t] / c[prev])
        prev = t
    return out


def betas(t0, t1, label):
    rb = hret('BTCUSDT', t0, t1)
    out = {}
    for s in closes:
        r = hret(s, t0, t1)
        ks = [t for t in r if t in rb]
        if len(ks) < 200:
            continue
        n = len(ks)
        mx, my = sum(rb[t] for t in ks)/n, sum(r[t] for t in ks)/n
        sxx = sum((rb[t]-mx)**2 for t in ks)
        if sxx:
            out[s] = sum((rb[t]-mx)*(r[t]-my) for t in ks)/sxx
    print('betas[%s] %d names / %d obs' % (label, len(out), len(rb)))
    return out


B_JUN = betas(None, JUL1, 'JUNE only -> causal for the JULY shadow book')
B_ALL = betas(None, None, 'JUN+JUL -> used for the AUG live book')


def px(sym, t):
    """price at wall-clock t, from the 1h bar opening at t (exact for 4h-aligned anchors)."""
    t = int(secs(t))
    t -= t % 3600
    return opens.get(sym, {}).get(t)


def positions(root):
    R = []
    for f in sorted(glob.glob(os.path.join(root, '*', 'position_readback.jsonl'))):
        R += [json.loads(l) for l in open(f) if l.strip()]
    pos = collections.defaultdict(dict)
    for r in R:
        if r.get('anchor_ts') is None:
            continue
        t = secs(r['anchor_ts'])
        p = pos[t].get(r['symbol'])
        if p is None or (r.get('read_ts') or 0) >= (p.get('read_ts') or 0):
            pos[t][r['symbol']] = r
    return pos


def analyse(root, label, BETA, max_gap_h=6.0):
    pos = positions(root)
    ts = sorted(pos)
    rows = []
    for k in range(len(ts) - 1):
        a, b = ts[k], ts[k+1]
        if (b - a) / 3600.0 > max_gap_h:            # skip non-standard gaps
            continue
        pa, pb = px('BTCUSDT', a), px('BTCUSDT', b)
        if not pa or not pb:
            continue
        rbtc = pb / pa - 1.0
        vals = [(s, float(p.get('venue_position_notional') or 0)) for s, p in pos[a].items()]
        vals = [(s, v) for s, v in vals if v and s in BETA and px(s, a) and px(s, b)]
        gross = sum(abs(v) for _, v in vals)
        if gross <= 100:
            continue
        net = sum(v for _, v in vals)
        bbar = sum(abs(v)*BETA[s] for s, v in vals)/gross
        disp = sum(v*(BETA[s]-bbar) for s, v in vals)
        book = sum(v*(px(s, b)/px(s, a) - 1.0) for s, v in vals)
        rows.append(dict(a=a, gross=gross, net=net, disp=disp, rbtc=rbtc,
                         pnl_disp=disp*rbtc, pnl_dollar=(bbar*net)*rbtc, book=book))
    if not rows:
        print('\n=== %s ===\n  no usable intervals' % label)
        return rows
    g = statistics.median(r['gross'] for r in rows)
    cd = sum(r['pnl_disp'] for r in rows)
    cb = sum(r['book'] for r in rows)
    cD = sum(r['pnl_dollar'] for r in rows)
    print('\n=== %s ===' % label)
    print('  intervals %d   %s -> %s   median beta-covered gross $%.0f'
          % (len(rows), utc(rows[0]['a']), utc(rows[-1]['a']), g))
    print('  median |disp tilt| $%.0f = %.4f of gross ; negative at %d/%d'
          % (statistics.median(abs(r['disp']) for r in rows),
             statistics.median(abs(r['disp'])/r['gross'] for r in rows),
             sum(1 for r in rows if r['disp'] < 0), len(rows)))
    print('  CUMULATIVE dispersion-tilt PnL $%+9.2f  (%+7.2f bps of gross)' % (cd, 1e4*cd/g))
    print('  cumulative dollar-part    PnL $%+9.2f  (%+7.2f bps)' % (cD, 1e4*cD/g))
    print('  cumulative WHOLE-BOOK     PnL $%+9.2f  (%+7.2f bps)' % (cb, 1e4*cb/g))
    random.seed(0)
    v = [r['pnl_disp'] for r in rows]
    bs = sorted(sum(v[random.randrange(len(v))] for _ in range(len(v))) for _ in range(20000))
    lo, hi = bs[500], bs[19500]
    print('  bootstrap 95%%CI of cumulative disp PnL [$%+.2f, $%+.2f] -> excludes 0? %s'
          % (lo, hi, 'YES' if (lo > 0 or hi < 0) else 'NO'))
    mu = statistics.mean(v)
    sd = statistics.stdev(v) if len(v) > 1 else float('nan')
    print('  per-interval disp PnL: mean $%+.4f  sd $%.4f' % (mu, sd))
    if mu:
        n_star = math.ceil(7.8489 * (sd/mu)**2)
        print('  >>> n* for 80%% power at this effect size: %d intervals (%.0f days @6/day)'
              % (n_star, n_star/6.0))
    return rows


sh = analyse(SH, 'SHADOW 2026-07 (champion caliber, PAPER)  betas=JUNE', B_JUN)
lv = analyse(LV, 'LIVE   2026-08-01..03 (real venue book)   betas=JUN+JUL', B_ALL)
print('\n★ the two periods are NEVER pooled: different weight caliber, different book size.')
