"""PROBE 2 — flip (zero-crossing) economics. Read-only, offline, <=t information only."""
import json, glob, collections, statistics, datetime as dt

PL = '/Users/haosiyu/dl_quant_live/state/live/pilot_log'


def utc(t):
    return dt.datetime.fromtimestamp(float(t), dt.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')


# ---- positions (QUANTITY, not notional: qty is immune to revaluation) -------
R = []
for f in sorted(glob.glob(PL + '/*/position_readback.jsonl')):
    R += [json.loads(l) for l in open(f) if l.strip()]
pos = collections.defaultdict(dict)          # anchor_ts -> sym -> row (last readback wins)
for r in R:
    a = r.get('anchor_ts')
    if a is None:
        continue
    p = pos[a].get(r['symbol'])
    if p is None or (r.get('read_ts') or 0) >= (p.get('read_ts') or 0):
        pos[a][r['symbol']] = r

# ---- mids at anchors --------------------------------------------------------
A = []
for f in sorted(glob.glob(PL + '/*/anchors.jsonl')):
    A += [json.loads(l) for l in open(f) if l.strip()]
mids = {a['anchor_ts']: json.loads(a.get('mid_at_anchor_vector') or '{}') for a in A}

# anchors usable = have positions AND mids; ordered
ts = sorted(t for t in pos if t in mids and mids[t])
print('anchors with both positions and mids: %d' % len(ts))
print('  ' + ', '.join(utc(t) for t in ts))

# ---- build per-(anchor,name) trades ----------------------------------------
recs = []
for k in range(1, len(ts) - 1):          # need a previous anchor AND a next anchor
    a0, a1, a2 = ts[k - 1], ts[k], ts[k + 1]
    m1, m2 = mids[a1], mids[a2]
    gross = sum(abs(float(p.get('venue_position_notional') or 0)) for p in pos[a1].values())
    for s, p in pos[a1].items():
        q1 = float(p.get('venue_position_qty') or 0)
        q0 = float((pos[a0].get(s) or {}).get('venue_position_qty') or 0)
        dq = q1 - q0
        if dq == 0 or s not in m1 or s not in m2 or not m1[s]:
            continue
        px1, px2 = float(m1[s]), float(m2[s])
        traded = abs(dq) * px1
        if traded < 1.0:                 # dust; below any venue floor
            continue
        pnl = dq * (px2 - px1)           # incremental PnL of THIS trade to the next anchor
        flip = (q0 != 0 and q1 != 0 and (q0 > 0) != (q1 > 0))
        recs.append(dict(a=a1, sym=s, dq=dq, q0=q0, q1=q1, px1=px1,
                         traded=traded, pnl=pnl, flip=flip, gross=gross,
                         new_notional=abs(q1) * px1))

print('trade records (|traded|>=$1, with a next anchor): %d over %d anchors'
      % (len(recs), len(set(r['a'] for r in recs))))


def summ(rs, label):
    if not rs:
        print('  %-22s n=0' % label)
        return None
    tn = sum(r['traded'] for r in rs)
    pn = sum(r['pnl'] for r in rs)
    bps = 1e4 * pn / tn if tn else float('nan')
    wins = sum(1 for r in rs if r['pnl'] > 0)
    print('  %-22s n=%4d  turnover $%9.0f  PnL $%+8.2f  = %+7.2f bps   win%% %.1f'
          % (label, len(rs), tn, pn, bps, 100.0 * wins / len(rs)))
    return dict(n=len(rs), turnover=tn, pnl=pn, bps=bps)


print()
print('=== FLIP vs NON-FLIP (pooled over all anchors) ===')
F = [r for r in recs if r['flip']]
N = [r for r in recs if not r['flip']]
sf = summ(F, 'FLIP (zero-crossing)')
sn = summ(N, 'non-flip')
sa = summ(recs, 'ALL')

print()
print('=== PER-ANCHOR FLIP CENSUS ===')
print('%-18s %6s %11s %9s %11s %11s' % ('anchor', 'nFlip', 'flip$', 'flip/gross', 'flipPnL$', 'flip_bps'))
per = []
for a in sorted(set(r['a'] for r in recs)):
    fa = [r for r in F if r['a'] == a]
    aa = [r for r in recs if r['a'] == a]
    g = aa[0]['gross'] if aa else 0
    tn = sum(r['traded'] for r in fa)
    pn = sum(r['pnl'] for r in fa)
    per.append(dict(a=a, n=len(fa), tn=tn, pn=pn, g=g,
                    share=(tn / g if g else 0),
                    bps=(1e4 * pn / tn if tn else None)))
    print('%-18s %6d %11.0f %9.4f %+11.2f %11s'
          % (utc(a), len(fa), tn, tn / g if g else 0, pn,
             ('%+.2f' % (1e4 * pn / tn)) if tn else 'n/a'))

if per:
    print()
    print('median flips/anchor        = %.0f' % statistics.median([p['n'] for p in per]))
    print('median flip notional/anchor= $%.0f' % statistics.median([p['tn'] for p in per]))
    print('median flip/gross          = %.4f' % statistics.median([p['share'] for p in per]))
    tot_g = statistics.median([p['g'] for p in per])
    net_bps_per_anchor = [1e4 * p['pn'] / p['g'] for p in per if p['g']]
    print('flip PnL as bps of GROSS, per anchor: med %+.2f  mean %+.2f  (n=%d)'
          % (statistics.median(net_bps_per_anchor),
             statistics.mean(net_bps_per_anchor), len(net_bps_per_anchor)))

# ---- hysteresis scan: FIRST-ORDER only -------------------------------------
print()
print('=== HYSTERESIS SCAN (descriptive; FIRST-ORDER, one anchor at a time) ===')
print('a flip is SUPPRESSED if the NEW position notional |q1|*px1 < band')
print('%8s %7s %11s %11s %12s %12s' %
      ('band$', 'cut_n', 'cut_turn$', 'cut_PnL$', 'kept_bps', 'cut_bps'))
for band in (0, 5, 10, 20, 30, 50, 75, 100, 150, 200):
    cut = [r for r in F if r['new_notional'] < band]
    kept = [r for r in F if r['new_notional'] >= band]
    ct, cp = sum(r['traded'] for r in cut), sum(r['pnl'] for r in cut)
    kt, kp = sum(r['traded'] for r in kept), sum(r['pnl'] for r in kept)
    print('%8d %7d %11.0f %+11.2f %12s %12s'
          % (band, len(cut), ct, cp,
             ('%+.2f' % (1e4 * kp / kt)) if kt else 'n/a',
             ('%+.2f' % (1e4 * cp / ct)) if ct else 'n/a'))
