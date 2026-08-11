import json, time, sys
from collections import defaultdict
sys.path.insert(0,"/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad")
from oc_income_probe import get
now=int(time.time()*1000)
out={}
for s in ["IOTAUSDT","TNSRUSDT"]:
    time.sleep(0.3)
    r=get("/fapi/v1/userTrades",{"symbol":s,"startTime":now-5*86400_000,"endTime":now,"limit":1000},signed=True)
    tr=sorted((int(x["time"]), float(x["qty"])*(1 if x["side"]=="BUY" else -1), float(x["price"])) for x in r)
    out[s]=tr
for st_s in ["2026-07-26T16:00:00Z","2026-07-27T00:00:00Z","2026-07-27T08:00:00Z"]:
    st=int(time.mktime(time.strptime(st_s,"%Y-%m-%dT%H:%M:%SZ"))-time.timezone)*1000
    print(st_s)
    for s,tr in out.items():
        q=sum(x[1] for x in tr if x[0]<=st)
        px=[x[2] for x in tr if x[0]<=st]
        if abs(q)>1e-12:
            print(f"   {s}: qty={q!r}  notional≈${abs(q)*(px[-1] if px else 0):.6f}  "
                  f"n_trades_so_far={len([x for x in tr if x[0]<=st])}")
