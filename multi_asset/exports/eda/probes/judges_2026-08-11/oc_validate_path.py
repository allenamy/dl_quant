"""VALIDATE the trade-reconstructed position path against two independent records:
   (a) our own position_readback batches, (b) the venue's CURRENT positionRisk.
If it does not match those, the settlement finding is worthless."""
import json, glob, time, sys
from collections import defaultdict
sys.path.insert(0, "/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad")
from oc_income_probe import get

now = int(time.time()*1000)
ROOT="/Users/haosiyu/dl_quant_live/state/testnet/pilot_log"
readbacks=defaultdict(dict)
for f in sorted(glob.glob(ROOT+"/*/position_readback.jsonl")):
    for line in open(f):
        r=json.loads(line)
        t=float(r.get("read_ts") or r.get("anchor_ts"))
        readbacks[round(t,3)][r["symbol"]]=float(r.get("venue_position_notional") or 0.0)
syms=sorted({s for v in readbacks.values() for s in v})

trades=defaultdict(list)
for i,s in enumerate(syms):
    time.sleep(0.35)
    r=get("/fapi/v1/userTrades",{"symbol":s,"startTime":now-5*86400_000,"endTime":now,"limit":1000},signed=True)
    if isinstance(r,list):
        for x in r:
            trades[s].append((int(x["time"]), float(x["qty"])*(1 if x["side"]=="BUY" else -1), float(x["price"])))
for s in trades: trades[s].sort()

def pos_at(ms):
    out={}
    for s,v in trades.items():
        q=sum(q for t,q,_ in v if t<=ms)
        if abs(q)>1e-12: out[s]=q
    return out

print("VALIDATION: trade-reconstructed vs our own readback, at each readback instant")
print(" readback_ts            readback_nonzero   trade_recon_nonzero   agree?")
ok=True
for t in sorted(readbacks):
    rb=sum(1 for v in readbacks[t].values() if abs(v)>1e-9)
    tr=len(pos_at(int(t*1000)))
    flag = "OK" if abs(rb-tr)<=2 else "MISMATCH"
    if flag!="OK": ok=False
    print(f"  {time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(t))}   {rb:5d}            {tr:5d}          {flag}")

time.sleep(0.5)
acc=get("/fapi/v3/account",{},signed=True)
live={p["symbol"]:float(p["positionAmt"]) for p in acc.get("positions",[]) if abs(float(p["positionAmt"]))>0}
recon=pos_at(now)
print(f"\n  venue positionRisk NOW: {len(live)} non-zero;  trade-recon NOW: {len(recon)} non-zero")
common=set(live)&set(recon)
bad=[s for s in common if abs(live[s]-recon[s])>1e-6*max(1,abs(live[s]))]
print(f"  symbols in both: {len(common)}   qty disagreements: {len(bad)} {bad[:5]}")
print(f"  only-in-venue: {sorted(set(live)-set(recon))[:5]}   only-in-recon: {sorted(set(recon)-set(live))[:5]}")
print(f"\n  => reconstruction {'VALIDATED' if ok and not bad and len(live)==len(recon) else 'CHECK ABOVE'}")
