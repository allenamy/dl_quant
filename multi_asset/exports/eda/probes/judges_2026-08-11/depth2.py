import json,urllib.request,re,time,datetime
def get(u,t=20): return json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'r/1.0'}),timeout=t))
def post(u,b,t=20): return json.load(urllib.request.urlopen(urllib.request.Request(u,data=json.dumps(b).encode(),headers={'Content-Type':'application/json','User-Agent':'r/1.0'}),timeout=t))
def norm(s):
    s=s.upper(); s=re.sub(r'^(1000000|100000|10000|1000)','',s); s=re.sub(r'^K(?=[A-Z]{2})','',s); return s

info=get('https://fapi.binance.com/fapi/v1/exchangeInfo')
onb={s['symbol']:s.get('onboardDate',0) for s in info['symbols']}
rank=json.load(open('binance_rank.json'))
CUT=datetime.datetime(2024,1,1,tzinfo=datetime.timezone.utc).timestamp()*1000
elig=[(s,v) for s,v in rank if onb.get(s,0) and onb[s]<CUT][:110]

# OKX ctVal map
okxi={x['ctValCcy'].upper():(x['instId'],float(x['ctVal'])) for x in get('https://www.okx.com/api/v5/public/instruments?instType=SWAP')['data'] if x['state']=='live' and x['settleCcy']=='USDT'}
hlmeta={x['name'].upper():x['name'] for x in post('https://api.hyperliquid.xyz/info',{'type':'meta'})['universe'] if not x.get('isDelisted')}
hlnorm={norm(k):v for k,v in hlmeta.items()}
byb={norm(x['baseCoin']):x['symbol'] for x in get('https://api.bybit.com/v5/market/instruments-info?category=linear&limit=1000')['result']['list'] if x['status']=='Trading' and x['quoteCoin']=='USDT'}

def m(bids,asks):
    if not bids or not asks: return None
    bb,ba=bids[0][0],asks[0][0]; mid=(bb+ba)/2
    o={'sp':(ba-bb)/mid*1e4}
    for bps in (10,25):
        lo,hi=mid*(1-bps/1e4),mid*(1+bps/1e4)
        o[bps]=min(sum(p*s for p,s in bids if p>=lo),sum(p*s for p,s in asks if p<=hi))
    return o

IDX=[0,4,9,19,29,49,69,89,99,104,109]
print(f"{'rk':>3s} {'coin':9s} {'24hVol$M':>9s} | {'BINANCE sp/d10/d25':>26s} | {'BYBIT sp/d10/d25':>24s} | {'OKX sp/d10/d25':>24s} | {'HYPERLIQ sp/d10/d25':>24s}")
print('-'*140)
for i in IDX:
    sym,vol=elig[i]; base=norm(sym.replace('USDT',''))
    cells=[]
    # binance
    try:
        d=get(f'https://fapi.binance.com/fapi/v1/depth?symbol={sym}&limit=500')
        r=m([(float(p),float(q)) for p,q in d['bids']],[(float(p),float(q)) for p,q in d['asks']])
        cells.append(f"{r['sp']:6.2f} {r[10]:8,.0f} {r[25]:9,.0f}")
    except Exception as ex: cells.append('       ERR              ')
    # bybit
    try:
        s2=byb[base]; d=get(f'https://api.bybit.com/v5/market/orderbook?category=linear&symbol={s2}&limit=200')['result']
        r=m([(float(p),float(q)) for p,q in d['b']],[(float(p),float(q)) for p,q in d['a']])
        cells.append(f"{r['sp']:6.2f} {r[10]:7,.0f} {r[25]:8,.0f}")
    except Exception as ex: cells.append('   n/a                  ')
    # okx
    try:
        iid,cv=okxi[base]; d=get(f'https://www.okx.com/api/v5/market/books?instId={iid}&sz=400')['data'][0]
        r=m([(float(x[0]),float(x[1])*cv) for x in d['bids']],[(float(x[0]),float(x[1])*cv) for x in d['asks']])
        cells.append(f"{r['sp']:6.2f} {r[10]:7,.0f} {r[25]:8,.0f}")
    except Exception as ex: cells.append('   n/a                  ')
    # HL
    try:
        c=hlnorm[base]; d=post('https://api.hyperliquid.xyz/info',{'type':'l2Book','coin':c})['levels']
        r=m([(float(x['px']),float(x['sz'])) for x in d[0]],[(float(x['px']),float(x['sz'])) for x in d[1]])
        cells.append(f"{r['sp']:6.2f} {r[10]:7,.0f} {r[25]:8,.0f}")
    except Exception as ex: cells.append('   n/a                  ')
    print(f"{i+1:3d} {base:9s} {vol/1e6:9,.1f} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]}")
    time.sleep(0.3)
print('\n(d10 = min(bid,ask) USD resting within 10bps of mid; d25 = within 25bps; sp = spread bps)')
