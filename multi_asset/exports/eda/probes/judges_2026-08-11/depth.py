import json,urllib.request,urllib.error,time

def get(u,timeout=20):
    return json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'research/1.0'}),timeout=timeout))
def post(u,body,timeout=20):
    r=urllib.request.Request(u,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','User-Agent':'research/1.0'})
    return json.load(urllib.request.urlopen(r,timeout=timeout))

def metrics(bids,asks):
    # bids/asks: list of (price, size_in_base)
    if not bids or not asks: return None
    bb,ba=bids[0][0],asks[0][0]; mid=(bb+ba)/2
    sp=(ba-bb)/mid*1e4
    out={'mid':mid,'spread_bps':sp}
    for bps in (5,10,25):
        lo=mid*(1-bps/1e4); hi=mid*(1+bps/1e4)
        b=sum(p*s for p,s in bids if p>=lo); a=sum(p*s for p,s in asks if p<=hi)
        out[f'bid{bps}']=b; out[f'ask{bps}']=a
    return out

SYMS=[('BTC','BTCUSDT'),('DOGE','DOGEUSDT'),('ENA','ENAUSDT'),('ERA','ERAUSDT'),
      ('kBONK','1000BONKUSDT'),('BASED','BASEDUSDT'),('ORDI','ORDIUSDT')]

def binance(s):
    d=get(f'https://fapi.binance.com/fapi/v1/depth?symbol={s}&limit=500')
    return metrics([(float(p),float(q)) for p,q in d['bids']],[(float(p),float(q)) for p,q in d['asks']])
def bybit(s):
    d=get(f'https://api.bybit.com/v5/market/orderbook?category=linear&symbol={s}&limit=200')['result']
    return metrics([(float(p),float(q)) for p,q in d['b']],[(float(p),float(q)) for p,q in d['a']])
def okx(s):
    base=s.replace('USDT','')
    if base.startswith('1000'): base='1000'+base[4:]
    d=get(f'https://www.okx.com/api/v5/market/books?instId={base}-USDT-SWAP&sz=400')['data'][0]
    return metrics([(float(x[0]),float(x[1])) for x in d['bids']],[(float(x[0]),float(x[1])) for x in d['asks']])
def hl(coin):
    d=post('https://api.hyperliquid.xyz/info',{'type':'l2Book','coin':coin})
    lv=d['levels']
    return metrics([(float(x['px']),float(x['sz'])) for x in lv[0]],[(float(x['px']),float(x['sz'])) for x in lv[1]])

VEN=[('Binance',binance,1),('Bybit',bybit,1),('OKX',okx,2),('Hyperliquid',hl,0)]
print(f"{'symbol':10s} {'venue':12s} {'spr_bps':>8s} {'±5bps$':>12s} {'±10bps$':>12s} {'±25bps$':>12s}")
print('-'*70)
for hlsym,bsym in SYMS:
    for name,fn,mode in VEN:
        arg = hlsym if mode==0 else bsym
        try:
            m=fn(arg)
            if m is None: print(f'{bsym:10s} {name:12s} no book'); continue
            d5=(m['bid5']+m['ask5'])/2; d10=(m['bid10']+m['ask10'])/2; d25=(m['bid25']+m['ask25'])/2
            print(f'{bsym:10s} {name:12s} {m["spread_bps"]:8.2f} {d5:12,.0f} {d10:12,.0f} {d25:12,.0f}')
        except Exception as e:
            print(f'{bsym:10s} {name:12s} ERR {type(e).__name__} {str(e)[:40]}')
        time.sleep(0.25)
    print()
