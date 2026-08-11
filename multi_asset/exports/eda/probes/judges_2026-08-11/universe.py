import json,urllib.request

def get(u,timeout=25):
    return json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'research/1.0'}),timeout=timeout))

# Binance perp 24h volume ranking
info=get('https://fapi.binance.com/fapi/v1/exchangeInfo')
perp={s['symbol'] for s in info['symbols'] if s['contractType']=='PERPETUAL' and s['status']=='TRADING' and s['quoteAsset']=='USDT'}
tk=get('https://fapi.binance.com/fapi/v1/ticker/24hr')
rows=sorted([(t['symbol'],float(t['quoteVolume'])) for t in tk if t['symbol'] in perp],key=lambda x:-x[1])
print('binance usdt perps:',len(rows))
for i in (0,9,29,49,79,99,109,119,149,199,299,399,len(rows)-1):
    if i<len(rows): print(f'  rank {i+1:4d}: {rows[i][0]:16s} 24h quoteVol ${rows[i][1]/1e6:,.1f}M')
json.dump(rows,open('binance_rank.json','w'))

# how many exceed liquidity thresholds
for thr in (1e9,5e8,1e8,5e7,2e7,1e7,5e6):
    print(f'  #perps with 24h vol > ${thr/1e6:.0f}M: {sum(1 for _,v in rows if v>thr)}')
