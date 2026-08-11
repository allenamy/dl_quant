"""P3: simulate the PROPOSED direct measurement — venue position vs INTENDED position —
at every anchor, and ask whether it would have seen what §4-5b saw."""
import sys,json,time
from collections import defaultdict
sys.path.insert(0,"/Users/haosiyu/dl_quant_live/live")
import pilot_log as PL
root="/Users/haosiyu/dl_quant_live/state/testnet/pilot_log"
days=PL.available_days(root)
out=[]
for d in days:
    one=PL.read_day(root,d)
    tg={a["anchor_ts"]:(a.get("target_gross") or 0.0) for a in one["anchors"]}
    tw=defaultdict(dict)
    for o in one["orders"]:
        tw[o["anchor_ts"]][o["symbol"]]=o.get("target_w")
    rb=defaultdict(dict)
    for r in one["position_readback"]:
        rb[r["anchor_ts"]][r["symbol"]]=float(r["venue_position_notional"])
    for ats in sorted(rb):
        if ats not in tg: continue
        g=tg[ats]; W=tw.get(ats,{})
        devs=[]
        for sym,n in rb[ats].items():
            w=W.get(sym)
            if w is None: continue
            intent=w*g
            devs.append((abs(n-intent),sym,round(intent,1),round(n,1)))
        if not devs: continue
        devs.sort(reverse=True)
        tot=sum(x[0] for x in devs)
        n5=sum(1 for x in devs if x[0]>5.0)
        n50=sum(1 for x in devs if x[0]>50.0)
        pctile=devs[0]
        lbl=time.strftime('%m-%dT%H:%M:%SZ',time.gmtime(ats))
        print(f"{lbl:18s} names={len(devs):4d} sum|dev|={tot:10.1f} ({tot/g*100:5.1f}% of gross) "
              f"n>5={n5:4d} n>50={n50:4d} worst={pctile[1]:>13s} intent={pctile[2]:9.1f} venue={pctile[3]:9.1f}")
        out.append({"anchor":lbl,"n":len(devs),"sum_abs_dev_usdt":round(tot,1),
                    "pct_of_gross":round(tot/g*100,2),"n_gt5":n5,"n_gt50":n50,
                    "worst":[pctile[1],pctile[2],pctile[3]]})
json.dump(out,open("/Users/haosiyu/Desktop/quant_research/multi_asset/exports/eda/0C_p3_direct_measure_sim.json","w"),indent=1)
