#!/usr/bin/env python3
"""Venue coverage + tail-depth for an arbitrary coin universe.

Usage:
    python3 run_universe.py members.txt            # coverage table + depth scan
    python3 run_universe.py members.txt --no-depth # coverage only (fast)

members.txt: one coin per line. Accepts base symbols (BTC, SNX) or Binance
perp symbols (BTCUSDT, 1000BONKUSDT) - both are normalised the same way.
Blank lines and lines starting with # are ignored.
"""
import json, urllib.request, re, sys, time

def get(u, t=25):
    return json.load(urllib.request.urlopen(
        urllib.request.Request(u, headers={'User-Agent': 'research/1.0'}), timeout=t))

def post(u, b, t=25):
    return json.load(urllib.request.urlopen(
        urllib.request.Request(u, data=json.dumps(b).encode(),
        headers={'Content-Type': 'application/json', 'User-Agent': 'research/1.0'}), timeout=t))

ALIAS = {'XBT': 'BTC'}          # Kraken quotes Bitcoin as XBT

def norm(s):
    """Reduce a venue ticker to a bare base symbol.

    Venues express the same coin many ways: BTCUSDT / BTC-USDT-SWAP / PF_XBTUSD,
    and cheap coins carry a size multiplier as either a prefix (1000PEPE), a
    suffix (SHIB1000), or Hyperliquid's lowercase k (kPEPE).

    The k-strip runs on the ORIGINAL case, before upper(): Hyperliquid's marker is
    a lowercase k, so uppercasing first would eat the real leading K of KNC, KAVA,
    KAS and KSM. Every strip is skipped if it would empty the string, so USDC
    survives the quote-suffix rule.
    """
    s = s.strip()
    s = re.sub(r'^k(?=[A-Z]{2})', '', s)          # kPEPE -> PEPE; leaves KNC/KAVA/KAS/KSM alone
    s = s.upper()
    s = re.sub(r'^(PF|PI)_', '', s)               # Kraken PF_XBTUSD / PI_XBTUSD
    while True:                                    # ETH_USD_PERP needs two passes
        t = re.sub(r'[-_]?(USDT|USDC|USD|PERP|SWAP)$', '', s)
        if not t or t == s:
            break
        s = t
    for pat in (r'^(1000000|100000|10000|1000)',   # 1000PEPE
                r'(1000000|100000|10000|1000)$'):  # SHIB1000
        t = re.sub(pat, '', s)
        if t:
            s = t
    return ALIAS.get(s, s)

def venue_sets():
    """base-symbol set of live/tradeable perps per venue. Failures -> venue skipped."""
    S, err = {}, {}
    def try_(name, fn):
        try: S[name] = fn()
        except Exception as e: err[name] = f'{type(e).__name__}: {e}'
    try_('Binance', lambda: {norm(x['baseAsset']) for x in
        get('https://fapi.binance.com/fapi/v1/exchangeInfo')['symbols']
        if x['contractType'] == 'PERPETUAL' and x['status'] == 'TRADING'})
    try_('Bybit', lambda: {norm(x['baseCoin']) for x in
        get('https://api.bybit.com/v5/market/instruments-info?category=linear&limit=1000')['result']['list']
        if x['status'] == 'Trading' and x['quoteCoin'] == 'USDT'})
    try_('OKX', lambda: {norm(x['ctValCcy']) for x in
        get('https://www.okx.com/api/v5/public/instruments?instType=SWAP')['data']
        if x['state'] == 'live' and x['settleCcy'] == 'USDT'})
    try_('Hyperliquid', lambda: {norm(x['name']) for x in
        post('https://api.hyperliquid.xyz/info', {'type': 'meta'})['universe'] if not x.get('isDelisted')})
    try_('dYdX v4', lambda: {norm(v['ticker'].split('-')[0]) for v in
        get('https://indexer.dydx.trade/v4/perpetualMarkets')['markets'].values() if v['status'] == 'ACTIVE'})
    try_('Gate', lambda: {norm(x['name'].split('_')[0]) for x in
        get('https://api.gateio.ws/api/v4/futures/usdt/contracts')})
    try_('Kraken Fut', lambda: {norm(x['symbol'].replace('PF_', '')) for x in
        get('https://futures.kraken.com/derivatives/api/v3/instruments')['instruments']
        if x.get('type') == 'flexible_futures' and x.get('tradeable')})
    try_('Bitget', lambda: {norm(x['baseCoin']) for x in
        get('https://api.bitget.com/api/v2/mix/market/contracts?productType=USDT-FUTURES')['data']})
    try_('Aster', lambda: {norm(x['baseAsset']) for x in
        get('https://fapi.asterdex.com/fapi/v1/exchangeInfo')['symbols']
        if x.get('status') == 'TRADING' and x.get('contractType') == 'PERPETUAL'})
    try_('Lighter', lambda: {norm(x['symbol'].split('/')[0]) for x in
        (lambda d: d.get('order_books', d))(get('https://mainnet.zklighter.elliot.ai/api/v1/orderBooks'))})
    try_('edgeX', lambda: {norm(re.sub(r'2?USD$', '', x['contractName'])) for x in
        get('https://pro.edgex.exchange/api/v1/public/meta/getMetaData')['data']['contractList']})
    try_('Paradex', lambda: {norm(x['base_currency']) for x in
        get('https://api.prod.paradex.trade/v1/markets')['results'] if x.get('asset_kind') == 'PERP'})
    try_('Backpack', lambda: {norm(x['baseSymbol']) for x in
        get('https://api.backpack.exchange/api/v1/markets') if x.get('marketType') == 'PERP'})
    try_('Coinbase Intl', lambda: {norm(x['base_asset_name']) for x in
        get('https://api.international.coinbase.com/api/v1/instruments') if x.get('type') == 'PERP'})
    for k, v in err.items():
        print(f'  ! {k} unavailable ({v})', file=sys.stderr)
    return S

# ---------- depth ----------
def _m(bids, asks):
    if not bids or not asks: return None
    bb, ba = bids[0][0], asks[0][0]; mid = (bb + ba) / 2
    o = {'sp': (ba - bb) / mid * 1e4}
    for bps in (10, 25):
        lo, hi = mid * (1 - bps / 1e4), mid * (1 + bps / 1e4)
        o[bps] = min(sum(p * s for p, s in bids if p >= lo), sum(p * s for p, s in asks if p <= hi))
    return o

def depth_scan(coins):
    """min-side USD resting within 10/25bps, per venue, for the given base symbols."""
    bmap = {norm(x['baseAsset']): x['symbol'] for x in
            get('https://fapi.binance.com/fapi/v1/exchangeInfo')['symbols']
            if x['contractType'] == 'PERPETUAL' and x['status'] == 'TRADING' and x['quoteAsset'] == 'USDT'}
    ymap = {norm(x['baseCoin']): x['symbol'] for x in
            get('https://api.bybit.com/v5/market/instruments-info?category=linear&limit=1000')['result']['list']
            if x['status'] == 'Trading' and x['quoteCoin'] == 'USDT'}
    # OKX sizes are in CONTRACTS - must multiply by ctVal to get base units
    omap = {norm(x['ctValCcy']): (x['instId'], float(x['ctVal'])) for x in
            get('https://www.okx.com/api/v5/public/instruments?instType=SWAP')['data']
            if x['state'] == 'live' and x['settleCcy'] == 'USDT'}
    hmap = {norm(x['name']): x['name'] for x in
            post('https://api.hyperliquid.xyz/info', {'type': 'meta'})['universe'] if not x.get('isDelisted')}

    def binance(c):
        d = get(f'https://fapi.binance.com/fapi/v1/depth?symbol={bmap[c]}&limit=500')
        return _m([(float(p), float(q)) for p, q in d['bids']], [(float(p), float(q)) for p, q in d['asks']])
    def bybit(c):
        d = get(f'https://api.bybit.com/v5/market/orderbook?category=linear&symbol={ymap[c]}&limit=200')['result']
        return _m([(float(p), float(q)) for p, q in d['b']], [(float(p), float(q)) for p, q in d['a']])
    def okx(c):
        iid, cv = omap[c]
        d = get(f'https://www.okx.com/api/v5/market/books?instId={iid}&sz=400')['data'][0]
        return _m([(float(x[0]), float(x[1]) * cv) for x in d['bids']],
                  [(float(x[0]), float(x[1]) * cv) for x in d['asks']])
    def hl(c):
        d = post('https://api.hyperliquid.xyz/info', {'type': 'l2Book', 'coin': hmap[c]})['levels']
        return _m([(float(x['px']), float(x['sz'])) for x in d[0]], [(float(x['px']), float(x['sz'])) for x in d[1]])

    VEN = [('Binance', binance), ('Bybit', bybit), ('OKX', okx), ('Hyperliquid', hl)]
    print(f"\nDEPTH  (min-side USD resting within 10 / 25 bps of mid; sp = spread bps)")
    print(f"{'coin':10s} " + ' | '.join(f'{n:>24s}' for n, _ in VEN))
    print('-' * 115)
    agg = {n: [] for n, _ in VEN}
    for c in coins:
        cells = []
        for name, fn in VEN:
            try:
                r = fn(c)
                cells.append(f"{r['sp']:6.2f} {r[10]:7,.0f} {r[25]:8,.0f}")
                agg[name].append(r[25])
            except Exception:
                cells.append(f"{'--':>24s}")
            time.sleep(0.25)
        print(f'{c:10s} ' + ' | '.join(cells))
    print('\nmedian d25 over scanned coins:')
    for n, v in agg.items():
        if v:
            s = sorted(v)
            print(f'  {n:12s} ${s[len(s)//2]:,.0f}   (n={len(v)}/{len(coins)} listed)')

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        print(__doc__); sys.exit(1)
    raw = [l.strip() for l in open(args[0]) if l.strip() and not l.startswith('#')]
    U = [norm(x) for x in raw]
    U = list(dict.fromkeys(U))
    N = len(U)
    print(f'universe: {N} coins (from {len(raw)} lines in {args[0]})')

    S = venue_sets()
    print(f"\nCOVERAGE\n{'venue':16s} {'#perps':>7s} {'covered':>8s} {'cover%':>7s}")
    print('-' * 42)
    rows = sorted(S.items(), key=lambda kv: -len(set(U) & kv[1]))
    for k, v in rows:
        n = len(set(U) & v)
        print(f'{k:16s} {len(v):7d} {n:8d} {100*n/N:6.1f}%')
    print()
    for k, v in rows:
        miss = sorted(set(U) - v)
        if miss:
            print(f'{k} missing {len(miss)}: {" ".join(miss)}\n')

    if '--no-depth' not in sys.argv:
        # scan a liquidity-spread sample rather than all N (rate limits)
        tk = get('https://fapi.binance.com/fapi/v1/ticker/24hr')
        vol = {norm(t['symbol']): float(t['quoteVolume']) for t in tk}
        ranked = sorted(U, key=lambda c: -vol.get(c, 0))
        idx = sorted({0, N//20, N//10, N//5, N//3, N//2, 2*N//3, 4*N//5, 9*N//10, N-1} & set(range(N)))
        depth_scan([ranked[i] for i in idx])

if __name__ == '__main__':
    main()
