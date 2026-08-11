"""PROBE 1b — is the beta-dispersion tilt PAID FOR?  Read-only, offline.
Shadow period (July, champion caliber) and live (Aug 1-3) computed SEPARATELY, never merged."""
import zipfile, glob, os, json, math, collections, statistics, random, datetime as dt

SP = os.path.dirname(os.path.abspath(__file__))
KL = os.path.join(SP, 'klines')
SH = os.path.join(SP, 'shadow')
LV = '/Users/haosiyu/dl_quant_live/state/live/pilot_log'


def utc(t):
    t = float(t)
    if t > 1e12:
        t /= 1000.0                     # shadow logs ms, live logs seconds
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')


def secs(t):
    t = float(t)
    return t / 1000.0 if t > 1e12 else t


# ---------- betas: JUNE ONLY, so they are causal for a JULY book -------------
closes = collections.defaultdict(dict)
for z in sorted(glob.glob(os.path.join(KL, '*.zip'))):
    sym = os.path.basename(z).split('-1h-')[0]
    with zipfile.ZipFile(z) as zf:
        for line in zf.read(zf.namelist()[0]).decode().splitlines():
            p = line.split(',')
            if p and p[0] and p[0][0].isdigit():
                closes[sym][int(p[0])] = float(p[4])

JUL1 = 1782950400000        # 2026-07-01T00:00Z in ms


def rets(sym, t0=None, t1=None):
    c = closes.get(sym, {})
    ks = sorted(c)
    out, prev = {}, None
    for t in ks:
        if prev is not None and (t0 is None or t >= t0) and (t1 is None or t < t1):
            if c[prev] > 0 and c[t] > 0:
                out[t] = math.log(c[t] / c[prev])
        prev = t
    return out


def betas(t0, t1, label):
    rbtc = rets('BTCUSDT', t0, t1)
    out = {}
    for s in closes:
        r = rets(s, t0, t1)
        ks = [t for t in r if t in rbtc]
        if len(ks) < 200:
            continue
        n = len(ks)
        mx = sum(rbtc[t] for t in ks) / n
        my = sum(r[t] for t in ks) / n
        sxx = sum((rbtc[t] - mx) ** 2 for t in ks)
        if sxx:
            out[s] = sum((rbtc[t] - mx) * (r[t] - my) for t in ks) / sxx
    print('betas[%s]: %d names, %d hourly obs' % (label, len(out), len(rbtc)))
    return out


B_JUN = betas(None, JUL1, 'JUNE only  -> used for the JULY shadow book (causal)')
B_ALL = betas(None, None, 'JUN+JUL    -> sensitivity only')


# ---------- load a book panel ------------------------------------------------
def load(root, ms):
    A = []
    for f in sorted(glob.glob(os.path.join(root, '*', 'anchors.jsonl'))):
        A += [json.loads(l) for l in open(f) if l.strip()]
    R = []
    for f in sorted(glob.glob(os.path.join(root, '*', 'position_readback.jsonl'))):
        R += [json.loads(l) for l in open(f) if l.strip()]
    mids = {}
    for a in A:
        v = a.get('mid_at_anchor_vector')
        if v:
            mids[secs(a['anchor_ts'])] = json.loads(v) if isinstance(v, str) else v
    pos = collections.defaultdict(dict)
    for r in R:
        if r.get('anchor_ts') is None:
            continue
        t = secs(r['anchor_ts'])
        p = pos[t].get(r['symbol'])
        if p is None or (r.get('read_ts') or 0) >= (p.get('read_ts') or 0):
            pos[t][r['symbol']] = r
    return pos, mids


def analyse(root, label, BETA):
    pos, mids = load(root, True)
    ts = sorted(t for t in pos if t in mids and mids[t])
    rows = []
    for k in range(len(ts) - 1):
        a, b = ts[k], ts[k + 1]
        m0, m1 = mids[a], mids[b]
        if 'BTCUSDT' not in m0 or 'BTCUSDT' not in m1:
            continue
        rbtc = float(m1['BTCUSDT']) / float(m0['BTCUSDT']) - 1.0
        vals = [(s, float(p.get('venue_position_notional') or 0)) for s, p in pos[a].items()]
        vals = [(s, v) for s, v in vals if v and s in BETA]
        gross = sum(abs(v) for _, v in vals)
        if gross <= 100:
            continue
        net = sum(v for _, v in vals)
        bbar = sum(abs(v) * BETA[s] for s, v in vals) / gross
        disp = sum(v * (BETA[s] - bbar) for s, v in vals)
        dollarpart = bbar * net
        # realised PnL of each exposure over THIS interval
        pnl_disp = disp * rbtc
        pnl_dollar = dollarpart * rbtc
        book = 0.0
        for s, v in vals:
            if s in m0 and s in m1 and float(m0[s]):
                book += v * (float(m1[s]) / float(m0[s]) - 1.0)
        rows.append(dict(a=a, b=b, gross=gross, net=net, disp=disp, dollarpart=dollarpart,
                         rbtc=rbtc, pnl_disp=pnl_disp, pnl_dollar=pnl_dollar, book=book))
    if not rows:
        print('  %s: no usable intervals' % label)
        return rows
    g = statistics.median(r['gross'] for r in rows)
    cd = sum(r['pnl_disp'] for r in rows)
    cD = sum(r['pnl_dollar'] for r in rows)
    cb = sum(r['book'] for r in rows)
    print()
    print('=== %s ===' % label)
    print('  intervals %d   span %s -> %s   median gross $%.0f'
          % (len(rows), utc(rows[0]['a']), utc(rows[-1]['b']), g))
    print('  median |disp tilt|  $%.0f  (%.4f of gross)'
          % (statistics.median(abs(r['disp']) for r in rows),
             statistics.median(abs(r['disp']) / r['gross'] for r in rows)))
    print('  disp tilt sign: %d neg / %d total'
          % (sum(1 for r in rows if r['disp'] < 0), len(rows)))
    print('  CUMULATIVE dispersion-tilt PnL  $%+8.2f   (%+7.2f bps of median gross)'
          % (cd, 1e4 * cd / g))
    print('  cumulative dollar-part  PnL     $%+8.2f   (%+7.2f bps)' % (cD, 1e4 * cD / g))
    print('  cumulative WHOLE-BOOK   PnL     $%+8.2f   (%+7.2f bps)' % (cb, 1e4 * cb / g))
    print('  dispersion PnL as share of book PnL: %s'
          % ('%.1f%%' % (100 * cd / cb) if cb else 'n/a (book PnL 0)'))
    # significance on the dispersion PnL: bootstrap over intervals
    random.seed(0)
    vals = [r['pnl_disp'] for r in rows]
    bs = sorted(sum(vals[random.randrange(len(vals))] for _ in range(len(vals)))
                for _ in range(20000))
    lo, hi = bs[500], bs[19500]
    print('  bootstrap 95%%CI of cumulative disp PnL: [$%+.2f, $%+.2f] -> excludes 0? %s'
          % (lo, hi, 'YES' if (lo > 0 or hi < 0) else 'NO'))
    per = statistics.mean(vals)
    print('  mean per-interval disp PnL $%+.4f   (%.2f bps of gross)' % (per, 1e4 * per / g))
    return rows


print()
sh = analyse(SH, 'SHADOW  2026-07 (champion caliber, PAPER book)  betas=JUNE', B_JUN)
lv = analyse(LV, 'LIVE    2026-08-01..03 (real venue book)        betas=JUN+JUL', B_ALL)

print()
print('=== SENSITIVITY: shadow with JUN+JUL betas (partly contemporaneous) ===')
_ = analyse(SH, 'SHADOW  betas=JUN+JUL (sensitivity only)', B_ALL)
