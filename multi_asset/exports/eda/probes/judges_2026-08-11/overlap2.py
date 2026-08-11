import json,urllib.request,re,datetime
def get(u,timeout=25):
    return json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'research/1.0'}),timeout=timeout))
def norm(s):
    s=s.upper(); s=re.sub(r'^(1000000|100000|10000|1000)','',s); s=re.sub(r'^K(?=[A-Z]{2})','',s); return s

info=get('https://fapi.binance.com/fapi/v1/exchangeInfo')
onb={s['symbol']:s.get('onboardDate',0) for s in info['symbols']}
rank=json.load(open('binance_rank.json'))
CUT=datetime.datetime(2024,1,1,tzinfo=datetime.timezone.utc).timestamp()*1000
CUT23=datetime.datetime(2023,1,1,tzinfo=datetime.timezone.utc).timestamp()*1000

# universe = listed before 2024-01-01 (>=2.5yr history), ranked by volume, top 110
elig=[(s,v) for s,v in rank if onb.get(s,0) and onb[s]<CUT]
print('perps listed before 2024-01-01:',len(elig))
u110=[norm(s.replace('USDT','')) for s,_ in elig[:110]]
print('tail (rank110) 24h vol: $%.1fM  = %s'%(elig[109][1]/1e6, elig[109][0]))
elig23=[(s,v) for s,v in rank if onb.get(s,0) and onb[s]<CUT23]
print('perps listed before 2023-01-01:',len(elig23))

sets=json.load(open('venue_sets.json'))
sets={k:set(v) for k,v in sets.items()}
print(f"\nUNIVERSE = top-110 by volume AMONG perps listed before 2024-01-01 (>=2.5yr history)")
print(f"{'venue':16s} {'#perps':>7s} {'∩U110':>7s} {'cover%':>7s}")
print('-'*42)
for k,v in sorted(sets.items(),key=lambda kv:-len(set(u110)&kv[1])):
    n=len(set(u110)&v); print(f'{k:16s} {len(v):7d} {n:7d} {100*n/110:6.0f}%')
print('\nU110 missing from Hyperliquid:',sorted(set(u110)-sets['Hyperliquid']))
print('\nU110 missing from dYdX v4:',sorted(set(u110)-sets['dYdX v4']))
print('\nU110 missing from Lighter:',sorted(set(u110)-sets['Lighter']))
print('\nU110 missing from OKX:',sorted(set(u110)-sets['OKX']))
json.dump(u110,open('u110.json','w'))
# how deep can we go with full HL coverage?
for N in (60,70,80,90,100,110,130,150):
    uN=[norm(s.replace('USDT','')) for s,_ in elig[:N]]
    print(f'  top-{N}: HL {len(set(uN)&sets["Hyperliquid"])}, dYdX {len(set(uN)&sets["dYdX v4"])}, Lighter {len(set(uN)&sets["Lighter"])}, OKX {len(set(uN)&sets["OKX"])}, Bybit {len(set(uN)&sets["Bybit"])}')
