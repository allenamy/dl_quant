import json, glob, time, sys
from collections import defaultdict
sys.path.insert(0,"/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad")
from oc_income_probe import get
now=int(time.time()*1000)
ROOT="/Users/haosiyu/dl_quant_live/state/testnet/pilot_log"
syms=sorted({json.loads(l)["symbol"] for f in glob.glob(ROOT+"/*/position_readback.jsonl") for l in open(f)})
trades=defaultdict(list)
for s in syms:
    time.sleep(0.32)
    r=get("/fapi/v1/userTrades",{"symbol":s,"startTime":now-5*86400_000,"endTime":now,"limit":1000},signed=True)
    if isinstance(r,list):
        for x in r: trades[s].append((int(x["time"]), float(x["qty"])*(1 if x["side"]=="BUY" else -1), float(x["price"])))
for s in trades: trades[s].sort()
json.dump({s:v for s,v in trades.items()}, open("trades_cache.json","w"))

def held(ms, thresh=1e-9):
    n=0; gross=0.0
    for s,v in trades.items():
        q=0.0; px=0.0
        for t,qq,p in v:
            if t<=ms: q+=qq; px=p
            else: break
        if abs(q)>thresh and abs(q*px)>1.0:
            n+=1; gross+=abs(q*px)
    return n, gross

t0=min(t for v in trades.values() for t,_,_ in v)
print("book timeline (30-min grid) — |notional|>$1 counts as a position")
print(" time                 names   gross_usdt   note")
t=(t0//1800_000)*1800_000
while t<=now:
    n,g=held(t)
    tt=time.gmtime(t/1000)
    note=""
    if tt.tm_hour%8==0 and tt.tm_min==0: note="<<< FUNDING SETTLEMENT (8h)"
    elif tt.tm_hour%4==0 and tt.tm_min==0: note="(anchor)"
    if n or note:
        print(f"  {time.strftime('%Y-%m-%dT%H:%M:%SZ',tt)}  {n:5d}   {g:10.0f}   {note}")
    t+=1800_000
nxt=((now//(8*3600_000))+1)*(8*3600_000)
n,g=held(now)
print(f"\n NOW: {n} names, ${g:,.0f} gross")
print(f" NEXT 8h settlement: {time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(nxt/1000))} "
      f"(in {(nxt-now)/60000:.0f} min)")
