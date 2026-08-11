"""Is the dispersion-beta term real, or is it beta-estimation noise?
Direct test: recompute it with two INDEPENDENT beta estimates (month 1 vs month 2)."""
exec(open('probe1_beta.py').read().split('# ---------- 3.')[0])   # reuse loaders + beta_of

import glob, json, collections
PL = '/Users/haosiyu/dl_quant_live/state/live/pilot_log'
R = []
for f in sorted(glob.glob(PL + '/*/position_readback.jsonl')):
    R += [json.loads(l) for l in open(f) if l.strip()]
by_anchor = collections.defaultdict(dict)
for r in R:
    a = r.get('anchor_ts')
    if a is None: continue
    prev = by_anchor[a].get(r['symbol'])
    if prev is None or (r.get('read_ts') or 0) >= (prev.get('read_ts') or 0):
        by_anchor[a][r['symbol']] = r

B1 = {s: beta_of(s, None, mid_t)[0] for s in ok}
B2 = {s: beta_of(s, mid_t, None)[0] for s in ok}
B1 = {s: b for s, b in B1.items() if b is not None}
B2 = {s: b for s, b in B2.items() if b is not None}
common = sorted(set(B1) & set(B2))
print('names with both half-betas: %d' % len(common))

def disp_term(pos, B):
    vals = [(s, float(p.get('venue_position_notional') or 0)) for s, p in pos.items()]
    vals = [(s, v) for s, v in vals if v != 0 and s in B]
    if not vals: return None, None
    gross = sum(abs(v) for _, v in vals)
    if gross <= 100: return None, None
    bbar = sum(abs(v) * B[s] for s, v in vals) / gross
    return sum(v * (B[s] - bbar) for s, v in vals), gross

print()
print('%-18s %12s %12s %12s %10s' % ('anchor', 'disp(full)', 'disp(M1)', 'disp(M2)', '|M1-M2|'))
rows = []
for a in sorted(by_anchor):
    df, g = disp_term(by_anchor[a], ok)
    d1, _ = disp_term(by_anchor[a], B1)
    d2, _ = disp_term(by_anchor[a], B2)
    if df is None or d1 is None or d2 is None: continue
    rows.append((a, df, d1, d2, g))
    print('%-18s %+12.0f %+12.0f %+12.0f %10.0f' % (utc(a), df, d1, d2, abs(d1 - d2)))

import statistics
sig = statistics.median([abs(r[1]) for r in rows])
noise = statistics.median([abs(r[2] - r[3]) for r in rows])
print()
print('median |disp(full)|      = %.0f USDT     <- the "signal"' % sig)
print('median |disp(M1)-disp(M2)| = %.0f USDT   <- how much it moves when betas are re-estimated' % noise)
print('ratio signal/noise = %.2f' % (sig / noise if noise else float('nan')))
sgn1 = sum(1 for r in rows if r[2] < 0); sgn2 = sum(1 for r in rows if r[3] < 0)
print('sign agreement between the two beta vintages: %d / %d anchors'
      % (sum(1 for r in rows if (r[2] < 0) == (r[3] < 0)), len(rows)))
print('  disp(M1) negative at %d/%d anchors ; disp(M2) negative at %d/%d'
      % (sgn1, len(rows), sgn2, len(rows)))
g = statistics.median([r[4] for r in rows])
print()
print('in bps of gross (1sigma BTC 4h = %.1f bps):' % (sd_b_1h * 2 * 1e4))
print('  signal %.2f bps   noise %.2f bps' % (sig*(sd_b_1h*2)/g*1e4, noise*(sd_b_1h*2)/g*1e4))
