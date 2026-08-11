import json,urllib.request,re
def get(u,timeout=25):
    return json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'research/1.0'}),timeout=timeout))
def post(u,b,timeout=25):
    return json.load(urllib.request.urlopen(urllib.request.Request(u,data=json.dumps(b).encode(),headers={'Content-Type':'application/json','User-Agent':'research/1.0'}),timeout=timeout))

def norm(s):
    s=s.upper()
    s=re.sub(r'^(1000000|100000|10000|1000|1M|K)','',s)
    s=re.sub(r'^K(?=[A-Z])','',s)
    return s

rank=json.load(open('binance_rank.json'))
top=[norm(s.replace('USDT','')) for s,_ in rank[:110]]
top150=[norm(s.replace('USDT','')) for s,_ in rank[:150]]
print('Binance top-110 tail vol: $%.1fM/day'%(rank[109][1]/1e6))

sets={}
sets['Binance']=set(norm(s.replace('USDT','')) for s,_ in rank)
b=get('https://api.bybit.com/v5/market/instruments-info?category=linear&limit=1000')['result']['list']
sets['Bybit']=set(norm(x['baseCoin']) for x in b if x['status']=='Trading' and x['quoteCoin']=='USDT')
o=get('https://www.okx.com/api/v5/public/instruments?instType=SWAP')['data']
sets['OKX']=set(norm(x['ctValCcy']) for x in o if x['state']=='live' and x['settleCcy']=='USDT')
h=post('https://api.hyperliquid.xyz/info',{'type':'meta'})['universe']
sets['Hyperliquid']=set(norm(x['name']) for x in h if not x.get('isDelisted'))
a=get('https://fapi.asterdex.com/fapi/v1/exchangeInfo')['symbols']
sets['Aster']=set(norm(x['baseAsset']) for x in a if x.get('status')=='TRADING' and x.get('contractType')=='PERPETUAL')
li=get('https://mainnet.zklighter.elliot.ai/api/v1/orderBooks')
li=li.get('order_books',li)
sets['Lighter']=set(norm(x['symbol'].split('/')[0]) for x in li)
p=get('https://api.prod.paradex.trade/v1/markets')['results']
sets['Paradex']=set(norm(x['base_currency']) for x in p if x.get('asset_kind')=='PERP')
e=get('https://pro.edgex.exchange/api/v1/public/meta/getMetaData')['data']['contractList']
sets['edgeX']=set(norm(re.sub(r'2?USD$','',x['contractName'])) for x in e)
bp=get('https://api.backpack.exchange/api/v1/markets')
sets['Backpack']=set(norm(x['baseSymbol']) for x in bp if x.get('marketType')=='PERP')
dy=get('https://indexer.dydx.trade/v4/perpetualMarkets')['markets']
sets['dYdX v4']=set(norm(v['ticker'].split('-')[0]) for v in dy.values() if v['status']=='ACTIVE')
ci=get('https://api.international.coinbase.com/api/v1/instruments')
sets['Coinbase Intl']=set(norm(x['base_asset_name']) for x in ci if x.get('type')=='PERP')
kr=get('https://futures.kraken.com/derivatives/api/v3/instruments')['instruments']
sets['Kraken Fut']=set(norm(x['symbol'].replace('PF_','').replace('USD','')) for x in kr if x.get('type')=='flexible_futures' and x.get('tradeable'))
bg=get('https://api.bitget.com/api/v2/mix/market/contracts?productType=USDT-FUTURES')['data']
sets['Bitget']=set(norm(x['baseCoin']) for x in bg)
ga=get('https://api.gateio.ws/api/v4/futures/usdt/contracts')
sets['Gate']=set(norm(x['name'].split('_')[0]) for x in ga)

print(f"\n{'venue':16s} {'#perps':>7s} {'∩top110':>8s} {'∩top150':>8s}")
print('-'*45)
for k,v in sorted(sets.items(),key=lambda kv:-len(set(top)&kv[1])):
    print(f'{k:16s} {len(v):7d} {len(set(top)&v):8d} {len(set(top150)&v):8d}')
json.dump({k:sorted(v) for k,v in sets.items()},open('venue_sets.json','w'))
print('\nTop-110 names MISSING from Hyperliquid:',sorted(set(top)-sets['Hyperliquid']))
print('\nTop-110 names MISSING from dYdX:',sorted(set(top)-sets['dYdX v4'])[:60])
