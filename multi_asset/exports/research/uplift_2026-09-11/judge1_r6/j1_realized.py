"""R6 JUDGE-1 — realized per-anchor ground truth from the live ledgers (READ-ONLY).
Caliber layer: HOLDINGS BOOK.  g = pnl / gross_total, bps per 4h anchor.
Components (all P&L sign, + = we gained):
  price   = sum_s qty_s(post-anchor readback at E) * (mid_s(E+4h) - mid_s(E))
  funding = sum of funding_paid over settlements in (E, E+4h]      [sign VERIFIED against daily_nav FUNDING_FEE]
  fee     = - sum of commission over fills stamped to anchor E      [deduped on trade_id]
  timing  = sum_s qty_traded_s * (mid_s(E) - fill_px_s)             [what the book gained/lost by filling away from the anchor mid]
Dedupe: fills on trade_id (globally unique, VERIFIED); funding on (symbol, settlement_ts).
"""
import json, os, collections, time, hashlib, sys
import numpy as np

BASE = '/Users/haosiyu/dl_quant_live/state/live/pilot_log'
TGT  = '/Users/haosiyu/wide_shadow/state/target_live'
OUT  = os.path.dirname(os.path.abspath(__file__))
READ_UTC = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
ENV_WHITELIST = ['J1_T0','J1_T1']          # this device reads only the ledgers; no model env
ENV_EFFECTIVE = {k: os.environ.get(k) for k in ENV_WHITELIST}

def G(t): return int(float(t) // 14400) * 14400      # rebalance_id is a submit wall-clock (N+~24min) -> floor to grid

days = sorted(d for d in os.listdir(BASE) if d.isdigit())

# ---------- anchors ----------
A = {}
raw_rows = 0
for d in days:
    p = f'{BASE}/{d}/anchors.jsonl'
    if not os.path.exists(p): continue
    for ln in open(p):
        ln = ln.strip()
        if not ln: continue
        try: r = json.loads(ln)
        except Exception: continue
        if r.get('anchor_ts') is None: continue
        raw_rows += 1
        g = G(r['anchor_ts'])
        mv = r.get('mid_at_anchor_vector'); mids = {}
        if isinstance(mv, str):
            try: mids = json.loads(mv)
            except Exception: mids = {}
        elif isinstance(mv, dict): mids = mv
        A[g] = dict(gross=float(r.get('realized_gross') or 0.0),
                    tgt_gross=float(r.get('target_gross') or 0.0),
                    mids=mids, regime=r.get('regime_at_anchor'),
                    skipped=r.get('n_names_skipped'), ats=float(r['anchor_ts']))

# ---------- positions (post-anchor readback) ----------
POS = collections.defaultdict(dict)
for d in days:
    p = f'{BASE}/{d}/position_readback.jsonl'
    if not os.path.exists(p): continue
    for ln in open(p):
        ln = ln.strip()
        if not ln: continue
        try: r = json.loads(ln)
        except Exception: continue
        if r.get('anchor_ts') is None: continue
        q = r.get('venue_position_qty')
        if q is None: continue
        POS[G(r['anchor_ts'])][r['symbol']] = (float(q), float(r.get('venue_position_notional') or 0.0))

# ---------- fills (dedupe trade_id) ----------
FEE  = collections.defaultdict(float)
TRD  = collections.defaultdict(lambda: collections.defaultdict(float))   # anchor -> symbol -> signed notional filled
TRDQ = collections.defaultdict(lambda: collections.defaultdict(float))   # anchor -> symbol -> signed qty filled
FILLPX = collections.defaultdict(lambda: collections.defaultdict(list))
seen_tid = set(); fill_raw = 0; fill_kept = 0
for d in days:
    p = f'{BASE}/{d}/fills.jsonl'
    if not os.path.exists(p): continue
    for ln in open(p):
        ln = ln.strip()
        if not ln: continue
        try: r = json.loads(ln)
        except Exception: continue
        fill_raw += 1
        tid = r.get('trade_id')
        if tid is not None:
            if tid in seen_tid: continue
            seen_tid.add(tid)
        fill_kept += 1
        if r.get('anchor_ts') is None: continue
        g = G(r['anchor_ts']); s = r['symbol']
        sgn = 1.0 if r.get('side') == 'buy' else -1.0
        notl = float(r.get('fill_notional') or 0.0)
        px = float(r.get('fill_px') or 0.0)
        FEE[g] += float(r.get('commission') or 0.0)
        TRD[g][s] += sgn * notl
        if px > 0: TRDQ[g][s] += sgn * notl / px
        FILLPX[g][s].append((px, notl))

# ---------- funding (dedupe (symbol, settlement_ts)); sign = venue P&L, VERIFIED vs daily_nav FUNDING_FEE ----------
FUNDROWS = []
seenf = set()
for d in days:
    p = f'{BASE}/{d}/funding.jsonl'
    if not os.path.exists(p): continue
    for ln in open(p):
        ln = ln.strip()
        if not ln: continue
        try: r = json.loads(ln)
        except Exception: continue
        k = (r['symbol'], r['settlement_ts'])
        if k in seenf: continue
        seenf.add(k)
        FUNDROWS.append((float(r['settlement_ts']), float(r.get('funding_paid') or 0.0)))
FUNDROWS.sort()
fts = np.array([x[0] for x in FUNDROWS]); fpd = np.array([x[1] for x in FUNDROWS])

# ---------- deployed target weights ----------
DEP = {}
for fn in os.listdir(TGT):
    if not fn.endswith('.json'): continue
    try: d = json.load(open(f'{TGT}/{fn}'))
    except Exception: continue
    ts = int(d['anchor_ts'])
    DEP[ts] = dict(w=d['weights'], gross_norm=float(d['gross_norm']), n_names=int(d['n_names']),
                   n_universe=int(d.get('n_universe') or 0), booster=str(d.get('booster_sha'))[:16],
                   producer=str(d.get('producer')), universe=set(d.get('universe') or []))

gs = sorted(A)
FEEUSD = json.load(open(os.path.join(OUT,'j1_fee_usd.json')))['rows']   # E-0911-C: commission re-denominated to USD
rows = []
for g in gs:
    g2 = g + 14400
    if g2 not in A: continue
    m1 = A[g]['mids']; m2 = A[g2]['mids']; pos = POS.get(g)
    if not pos or not m1 or not m2: continue
    price = 0.0; cov = 0.0; unc = 0.0
    wreal = {}
    for s, (q, notl) in pos.items():
        if abs(notl) < 1e-9: continue
        p1 = m1.get(s); p2 = m2.get(s)
        wreal[s] = notl
        if p1 and p2:
            price += q * (p2 - p1); cov += abs(notl)
        else:
            unc += abs(notl)
    fund = float(fpd[(fts > g) & (fts <= g2)].sum())
    _fu = FEEUSD.get(str(g))
    fee  = -(float(_fu['fee_usd']) if _fu else 0.0)          # E-0911-C corrected (USD)
    fee_naive = -FEE.get(g, 0.0)                              # what a naive sum of the `commission` field gives
    timing = 0.0
    for s, lst in FILLPX.get(g, {}).items():
        p1 = m1.get(s)
        if not p1: continue
        for px, notl in lst:
            if px <= 0: continue
            q = notl / px
            sgn = 0.0
        # handled below with signed qty
    # signed timing: buying above the anchor mid costs, selling below costs
    for s, lst in FILLPX.get(g, {}).items():
        p1 = m1.get(s)
        if not p1: continue
        for px, notl in lst: pass
    tim = 0.0
    for s in TRDQ.get(g, {}):
        p1 = m1.get(s)
        if not p1: continue
        # average fill price for the symbol at this anchor, notional-weighted over the signed legs
        legs = FILLPX[g][s]
        tot = sum(n for _, n in legs)
        if tot <= 0: continue
        avg = sum(px * n for px, n in legs) / tot
        qsig = TRDQ[g][s]
        tim += qsig * (p1 - avg)
    gross = A[g]['gross'] or cov
    if gross <= 0: continue
    dep = DEP.get(g)
    rows.append(dict(
        A=g, utc=time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime(g)),
        gross=gross, cov=cov, unc=unc, regime=A[g]['regime'], nskip=A[g]['skipped'],
        price=price, fund=fund, fee=fee, fee_naive=fee_naive, timing=tim,
        traded=(float(_fu['notl']) if _fu else 0.0),
        maker_share=(float(_fu['mk'])/max(float(_fu['mk'])+float(_fu['tk']),1e-9) if _fu else None),
        price_bps=price / gross * 1e4, fund_bps=fund / gross * 1e4,
        fee_bps=fee / gross * 1e4, fee_bps_naive=fee_naive / gross * 1e4,
        timing_bps=tim / gross * 1e4, turn_bps=(float(_fu['notl']) if _fu else 0.0)/gross*1e4,
        net_bps=(price + fund + fee) / gross * 1e4,
        traded_notional=sum(abs(v) for v in TRD.get(g, {}).values()),
        n_pos=len(wreal), has_dep=dep is not None,
        dep_nnames=(dep['n_names'] if dep else None),
        dep_booster=(dep['booster'] if dep else None),
        dep_producer=(dep['producer'] if dep else None),
    ))

meta = dict(read_utc=READ_UTC, env_effective=ENV_EFFECTIVE,
            self_sha256=hashlib.sha256(open(__file__, 'rb').read()).hexdigest(),
            anchors_raw_rows=raw_rows, anchors_canonical=len(A),
            fills_raw=fill_raw, fills_deduped=fill_kept,
            funding_rows_deduped=len(FUNDROWS),
            target_live_files=len(DEP), rows=len(rows))
json.dump(dict(meta=meta, rows=rows), open(f'{OUT}/j1_realized.json', 'w'), indent=1)

# also dump per-anchor realized weight vectors + deployed weight vectors (npz, symbol-keyed json for clarity)
wr = {}; wd = {}
for g in gs:
    if g in POS:
        d = {s: n for s, (q, n) in POS[g].items() if abs(n) > 1e-9}
        if d: wr[str(g)] = d
    if g in DEP: wd[str(g)] = DEP[g]['w']
json.dump(wr, open(f'{OUT}/j1_w_realized.json', 'w'))
json.dump(wd, open(f'{OUT}/j1_w_deployed.json', 'w'))

print('READ_UTC', READ_UTC)
print(json.dumps(meta, indent=1))
def stat(sel, lab):
    if not sel: print(f'{lab}: n=0'); return
    import statistics as st
    for k in ('price_bps','fund_bps','fee_bps','fee_bps_naive','timing_bps','turn_bps','net_bps'):
        x = [r[k] for r in sel]
        mu = st.mean(x); sd = st.pstdev(x)*(len(x)/(len(x)-1))**.5 if len(x) > 1 else float('nan')
        se = sd/len(x)**.5
        print(f'  {lab:10s} {k:11s} n={len(x):4d} mean {mu:9.4f} sd {sd:8.3f} se {se:7.4f} t {mu/se if se else float("nan"):7.2f}')
CE = 1787716800   # 2026-08-26 04:00Z
W5 = [r for r in rows if CE <= r['A'] <= 1788998400]
W4 = [r for r in rows if 1785542400 <= r['A'] <= 1788998400]
stat(W4, 'W4')
stat(W5, 'W5')
