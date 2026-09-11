"""E-0911-C: fills.jsonl `commission` is denominated in `commission_asset`, NOT USD.
From 2026-08-06 to 2026-09-06 the account paid fees in BNB, so any naive USD sum under-counts
the live fee bill by the BNB price (~600-750x). daily_nav.realised_by_type.COMMISSION inherits
the same defect (it sums /fapi/v1/income amounts across assets).
This device converts every non-USDT commission at the SAME anchor's own mid_at_anchor_vector price
(the ledger's own price source, so no external data is introduced) and re-states the fee series.
"""
import json, os, collections, time, hashlib
base = '/Users/haosiyu/dl_quant_live/state/live/pilot_log'
def G(t): return int(float(t)//14400)*14400
MID = {}
days = sorted(d for d in os.listdir(base) if d.isdigit())
for d in days:
    p = f'{base}/{d}/anchors.jsonl'
    if not os.path.exists(p): continue
    for ln in open(p):
        try: r = json.loads(ln)
        except Exception: continue
        if r.get('anchor_ts') is None: continue
        mv = r.get('mid_at_anchor_vector'); m = {}
        if isinstance(mv, str):
            try: m = json.loads(mv)
            except Exception: m = {}
        elif isinstance(mv, dict): m = mv
        if m: MID[G(r['anchor_ts'])] = m
# nearest anchor price for an asset
anchors = sorted(MID)
def px(asset, g):
    if asset == 'USDT': return 1.0
    sym = f'{asset}USDT'
    for cand in [g] + [a for a in anchors if abs(a-g) <= 4*14400]:
        v = MID.get(cand, {}).get(sym)
        if v: return float(v)
    return None
FEE = collections.defaultdict(float); FEEraw = collections.defaultdict(float)
NOTL = collections.defaultdict(float); MKN = collections.defaultdict(float); TKN = collections.defaultdict(float)
seen = set(); unres = 0; byasset = collections.Counter()
for d in days:
    p = f'{base}/{d}/fills.jsonl'
    if not os.path.exists(p): continue
    for ln in open(p):
        try: r = json.loads(ln)
        except Exception: continue
        t = r.get('trade_id')
        if t is not None:
            if t in seen: continue
            seen.add(t)
        if r.get('anchor_ts') is None: continue
        g = G(r['anchor_ts']); a = r.get('commission_asset') or 'USDT'
        c = float(r.get('commission') or 0.0); n = float(r.get('fill_notional') or 0.0)
        byasset[a] += 1
        P = px(a, g)
        if P is None: unres += 1; P = 1.0
        FEE[g] += c*P; FEEraw[g] += c; NOTL[g] += n
        (MKN if r.get('venue_maker_flag') else TKN)[g] += n
out = {str(k): dict(fee_usd=FEE[k], fee_raw=FEEraw[k], notl=NOTL[k], mk=MKN[k], tk=TKN[k]) for k in FEE}
json.dump(dict(meta=dict(read_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                         self_sha256=hashlib.sha256(open(__file__,'rb').read()).hexdigest(),
                         assets=dict(byasset), unresolved_price=unres), rows=out),
          open('j1_fee_usd.json','w'), indent=1)
print('commission_asset counts:', dict(byasset), 'unresolved', unres)
for lo, hi, lab in ((1785542400,1788998400,'W4'), (1787716800,1788998400,'W5'), (1788220800,1788998400,'SEP')):
    ks = [k for k in FEE if lo <= k <= hi]
    fu = sum(FEE[k] for k in ks); fr = sum(FEEraw[k] for k in ks); nt = sum(NOTL[k] for k in ks)
    mk = sum(MKN[k] for k in ks); tk = sum(TKN[k] for k in ks)
    print(f"{lab}: anchors {len(ks)}  traded ${nt:,.0f}  fee_USD ${fu:,.2f} ({fu/nt*1e4:.3f} bps of traded)  "
          f"fee_naive ${fr:,.2f} ({fr/nt*1e4:.5f} bps)  ratio {fu/max(fr,1e-12):.1f}x  maker share {mk/max(mk+tk,1e-9):.3f}")
