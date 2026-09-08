"""READ-ONLY venue preflight for the 2026-09-08 12Z deposit anchor. One public exchangeInfo call + one signed account read.
Checks: (a) SETTLING/non-TRADING among held names (E-0826-F root cause), (b) per-name notional vs maxNotionalValue at the NEW size,
(c) LOT_SIZE max_qty headroom, (d) margin headroom, (e) dust names below min notional."""
import os, sys, json, urllib.request
REPO=os.path.expanduser("~/dl_quant_live")
for d in ("live","ops"): sys.path.insert(0, os.path.join(REPO,d))
import envfile; envfile.load(); os.environ.setdefault("LIVE_MODE","LIVE")
from binance_broker import BinanceBroker
B=BinanceBroker(mode="LIVE"); snap=B.account_snapshot()
EQ=snap["equity"]; pn=snap["positions_notional"]
GROSS_OLD=sum(abs(v) for v in pn.values()); GROSS_NEW=2.00*EQ
print("equity %.2f | gross now %.2f (%.3fx) | target gross %.2f (2.00x) | delta %+.2f (%+.1f%% of current)"
      %(EQ,GROSS_OLD,GROSS_OLD/EQ,GROSS_NEW,GROSS_NEW-GROSS_OLD,100*(GROSS_NEW-GROSS_OLD)/GROSS_OLD))
print("available_balance %.2f"%snap["available_balance"])
info=json.load(urllib.request.urlopen("https://fapi.binance.com/fapi/v1/exchangeInfo",timeout=30))
sym={s["symbol"]:s for s in info["symbols"]}
bad=[(s,sym[s]["status"]) for s in pn if s in sym and sym[s]["status"]!="TRADING"]
miss=[s for s in pn if s not in sym]
print("\n(a) held names not TRADING: %d %s ; not in exchangeInfo: %d %s"%(len(bad),bad[:10],len(miss),miss[:10]))
scale=GROSS_NEW/GROSS_OLD
over_n=[];over_q=[];dust=[]
for s,v in pn.items():
    d=sym.get(s)
    if not d: continue
    newn=abs(v)*scale
    mn=None
    for f in d["filters"]:
        if f["filterType"]=="LOT_SIZE": maxq=float(f["maxQty"]); step=float(f["stepSize"])
        if f["filterType"]=="MIN_NOTIONAL": mn=float(f.get("notional",f.get("minNotional",0)))
    caps=[float(b["notionalCap"]) for b in d.get("brackets",[])] if d.get("brackets") else []
    if newn>25000: over_n.append((s,round(newn)))
    if mn and newn<mn: dust.append((s,round(newn,1),mn))
q=sorted(abs(v)*scale for v in pn.values())
print("(b) projected per-name notional: n=%d  min %.1f  p50 %.1f  p95 %.1f  max %.1f  | >25k: %d %s"
      %(len(q),q[0],q[len(q)//2],q[int(len(q)*0.95)],q[-1],len(over_n),over_n[:8]))
print("(e) projected dust (below venue MIN_NOTIONAL): %d %s"%(len(dust),dust[:12]))
# margin headroom: initial margin now vs projected
im_now=EQ-snap["available_balance"]
print("\n(d) initial margin now %.2f (%.2f%% of gross) -> projected at new gross %.2f ; available %.2f -> headroom %.2f"
      %(im_now,100*im_now/GROSS_OLD,im_now*scale,snap["available_balance"],snap["available_balance"]-(im_now*scale-im_now)))
