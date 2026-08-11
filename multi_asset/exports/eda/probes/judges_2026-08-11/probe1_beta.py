"""PROBE 1 — the filled book's actual BTC-beta path. Read-only, offline."""
import zipfile, glob, os, json, math, collections, datetime as dt

SP = os.path.dirname(os.path.abspath(__file__))
KL = os.path.join(SP, 'klines')
PL = '/Users/haosiyu/dl_quant_live/state/live/pilot_log'


def utc(t):
    return dt.datetime.fromtimestamp(float(t), dt.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')


# ---------- 1. hourly closes -------------------------------------------------
closes = collections.defaultdict(dict)          # sym -> {open_time_ms: close}
for z in sorted(glob.glob(os.path.join(KL, '*.zip'))):
    sym = os.path.basename(z).split('-1h-')[0]
    try:
        with zipfile.ZipFile(z) as zf:
            name = zf.namelist()[0]
            for line in zf.read(name).decode().splitlines():
                p = line.split(',')
                if not p or not p[0] or not p[0][0].isdigit():
                    continue            # header row
                closes[sym][int(p[0])] = float(p[4])
    except Exception as e:
        print('  ! parse fail', z, e)

nsym = len(closes)
print('symbols with klines: %d ; BTC bars: %d' % (nsym, len(closes.get('BTCUSDT', {}))))

btc = closes['BTCUSDT']
times = sorted(btc)
# hourly log returns aligned on BTC's clock
def rets(sym):
    c = closes.get(sym, {})
    out = {}
    prev_t = None
    for t in times:
        if t in c and prev_t is not None and prev_t in c and c[prev_t] > 0 and c[t] > 0:
            out[t] = math.log(c[t] / c[prev_t])
        prev_t = t
    return out

rb = rets('BTCUSDT')
var_b = sum(v * v for v in rb.values()) / len(rb) - (sum(rb.values()) / len(rb)) ** 2
sd_b_1h = var_b ** 0.5
print('BTC 1h return sd = %.5f (%.1f bps) ; 4h sd = %.1f bps'
      % (sd_b_1h, sd_b_1h * 1e4, sd_b_1h * 2 * 1e4))

# ---------- 2. betas ---------------------------------------------------------
def beta_of(sym, t0=None, t1=None):
    r = rets(sym)
    ks = [t for t in r if t in rb and (t0 is None or t >= t0) and (t1 is None or t < t1)]
    n = len(ks)
    if n < 200:
        return None, n
    mx = sum(rb[t] for t in ks) / n
    my = sum(r[t] for t in ks) / n
    sxy = sum((rb[t] - mx) * (r[t] - my) for t in ks)
    sxx = sum((rb[t] - mx) ** 2 for t in ks)
    return (sxy / sxx if sxx else None), n

BETA, NOBS = {}, {}
for s in sorted(closes):
    b, n = beta_of(s)
    BETA[s], NOBS[s] = b, n
ok = {s: b for s, b in BETA.items() if b is not None}
print('betas estimated: %d / %d (need >=200 hourly obs)' % (len(ok), nsym))
bs = sorted(ok.values())
print('beta distribution: min %.2f  p25 %.2f  med %.2f  p75 %.2f  max %.2f'
      % (bs[0], bs[len(bs)//4], bs[len(bs)//2], bs[3*len(bs)//4], bs[-1]))

# split-half stability (first month vs second) -- reported, not used for the path
mid_t = times[len(times) // 2]
stab = []
for s in ok:
    b1, n1 = beta_of(s, None, mid_t)
    b2, n2 = beta_of(s, mid_t, None)
    if b1 is not None and b2 is not None:
        stab.append((s, b1, b2))
if stab:
    d = [abs(a - b) for _, a, b in stab]
    d.sort()
    print('beta split-half |Δ| : med %.3f  p90 %.3f  (n=%d)' % (d[len(d)//2], d[int(0.9*len(d))], len(d)))

# ---------- 3. positions per anchor -----------------------------------------
R = []
for f in sorted(glob.glob(os.path.join(PL, '*', 'position_readback.jsonl'))):
    R += [json.loads(l) for l in open(f) if l.strip()]
by_anchor = collections.defaultdict(dict)
for r in R:
    a = r.get('anchor_ts')
    if a is None:
        continue
    # keep the LAST readback row per (anchor, symbol)
    prev = by_anchor[a].get(r['symbol'])
    if prev is None or (r.get('read_ts') or 0) >= (prev.get('read_ts') or 0):
        by_anchor[a][r['symbol']] = r

# anchors.jsonl for gross/net
A = []
for f in sorted(glob.glob(os.path.join(PL, '*', 'anchors.jsonl'))):
    A += [json.loads(l) for l in open(f) if l.strip()]
anch = {a['anchor_ts']: a for a in A}

print()
print('=== PER-ANCHOR BOOK BETA PATH ===')
hdr = ('%-18s %9s %9s %10s %11s %10s %9s' %
       ('anchor', 'gross$', 'net$', 'net/gross', 'dollarBeta$', 'beta/gross', 'risk_bps'))
print(hdr)
rows = []
for a in sorted(by_anchor):
    pos = by_anchor[a]
    gross = sum(abs(float(p.get('venue_position_notional') or 0)) for p in pos.values())
    net = sum(float(p.get('venue_position_notional') or 0) for p in pos.values())
    if gross <= 0:
        continue
    dbeta, cov_n, uncov = 0.0, 0, 0.0
    for s, p in pos.items():
        v = float(p.get('venue_position_notional') or 0)
        if v == 0:
            continue
        b = ok.get(s)
        if b is None:
            uncov += abs(v)
            continue
        dbeta += v * b
        cov_n += 1
    risk_bps = abs(dbeta) * (sd_b_1h * 2) / gross * 1e4
    rows.append(dict(a=a, gross=gross, net=net, nog=net / gross, dbeta=dbeta,
                     bog=dbeta / gross, risk=risk_bps, uncov=uncov / gross, n=cov_n))
    print('%-18s %9.0f %+9.0f %+10.4f %+11.0f %+10.4f %9.2f'
          % (utc(a), gross, net, net / gross, dbeta, dbeta / gross, risk_bps))

print()
live = [r for r in rows if r['gross'] > 100]
print('anchors with a real book: %d' % len(live))
if live:
    rk = sorted(r['risk'] for r in live)
    print('beta risk (bps of gross, 1σ BTC 4h move): min %.2f  med %.2f  max %.2f'
          % (rk[0], rk[len(rk)//2], rk[-1]))
    pos_n = sum(1 for r in live if r['dbeta'] > 0)
    print('dollar-beta sign: %d positive / %d negative  -> sign-stable? %s'
          % (pos_n, len(live) - pos_n, 'NO' if 0 < pos_n < len(live) else 'YES'))
    bog = [r['bog'] for r in live]
    nog = [r['nog'] for r in live]
    n = len(live)
    mb, mn = sum(bog)/n, sum(nog)/n
    num = sum((bog[i]-mb)*(nog[i]-mn) for i in range(n))
    den = (sum((x-mb)**2 for x in bog)*sum((x-mn)**2 for x in nog))**0.5
    print('corr( beta/gross , net/gross ) = %.3f   (n=%d)' % (num/den if den else float('nan'), n))
    print('mean |beta/gross| = %.4f   mean |net/gross| = %.4f'
          % (sum(abs(x) for x in bog)/n, sum(abs(x) for x in nog)/n))
    print('uncovered notional share (no beta): med %.4f'
          % sorted(r['uncov'] for r in live)[len(live)//2])
    print()
    print('>>> COMPARISON POINT: measured blended cost magnitude ~4 bps/anchor (lead)')
    print('    beta risk median %.2f bps  => ratio %.2fx' % (rk[len(rk)//2], rk[len(rk)//2]/4.0))

# ---------- 4. THE DECOMPOSITION THAT DECIDES THE QUESTION -------------------
# dollar_beta = beta_bar * net  +  sum_i v_i (beta_i - beta_bar)
#               ^ removable by DOLLAR-neutrality (already the target)
#                                 ^ the part dollar-neutrality CANNOT remove
#                                   <- this is what the external note is about
print()
print('=== DECOMPOSITION: which part of the beta tilt is NOT already addressed ===')
gross_w_beta = {}
for a in sorted(by_anchor):
    pos = by_anchor[a]
    vals = [(s, float(p.get('venue_position_notional') or 0)) for s, p in pos.items()]
    vals = [(s, v) for s, v in vals if v != 0 and ok.get(s) is not None]
    if not vals:
        continue
    gross = sum(abs(v) for _, v in vals)
    if gross <= 100:
        continue
    net = sum(v for _, v in vals)
    # gross-weighted mean beta of the book
    bbar = sum(abs(v) * ok[s] for s, v in vals) / gross
    term_dollar = bbar * net
    term_disp = sum(v * (ok[s] - bbar) for s, v in vals)
    tot = term_dollar + term_disp
    gross_w_beta[a] = (gross, net, bbar, term_dollar, term_disp, tot)

print('%-18s %7s %11s %11s %11s %10s %10s' %
      ('anchor', 'betabar', 'dollar-part', 'disp-part', 'total', 'disp_bps', 'disp/tot'))
dbps = []
for a in sorted(gross_w_beta):
    gross, net, bbar, td, tdp, tot = gross_w_beta[a]
    rb_ = abs(tdp) * (sd_b_1h * 2) / gross * 1e4
    dbps.append(rb_)
    print('%-18s %7.3f %+11.0f %+11.0f %+11.0f %10.2f %9s'
          % (utc(a), bbar, td, tdp, tot, rb_,
             ('%.2f' % (abs(tdp)/abs(tot))) if tot else 'n/a'))

dbps.sort()
print()
print('RESIDUAL (dispersion) beta risk, bps of gross per anchor: min %.2f  med %.2f  max %.2f'
      % (dbps[0], dbps[len(dbps)//2], dbps[-1]))
print('  vs TOTAL beta risk median %.2f bps' % sorted(r['risk'] for r in live)[len(live)//2])
print('  vs blended cost magnitude ~4 bps/anchor')
