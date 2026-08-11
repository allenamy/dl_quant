"""Re-run the intra-anchor overshoot test AFTER de-duplicating (symbol, trade_id)."""
import sys,json,time
from collections import defaultdict
sys.path.insert(0,"/Users/haosiyu/dl_quant_live/live")
import pilot_log as PL
root="/Users/haosiyu/dl_quant_live/state/testnet/pilot_log"
out=[]
for day in ["20260726","20260727","20260728"]:
    one=PL.read_day(root,day)
    tgs={a["anchor_ts"]:a["target_gross"] for a in one["anchors"]}
    tw=defaultdict(dict)
    for o in one["orders"]: tw[o["anchor_ts"]][o["symbol"]]=o["target_w"]
    rb=defaultdict(dict)
    for r in one["position_readback"]: rb[r["anchor_ts"]][r["symbol"]]=float(r["venue_position_notional"])
    seen=set(); byanch=defaultdict(list)
    for f in one["fills"]:
        k=(f["symbol"],f["trade_id"])
        if k in seen: continue
        seen.add(k); byanch[f["anchor_ts"]].append(f)
    prev_rb=None
    for ats in sorted(rb):
        fs=byanch.get(ats,[]); g=tgs.get(ats,0)
        if not fs: prev_rb=rb[ats]; continue
        start = prev_rb if prev_rb is not None else {}
        pos=defaultdict(float); mx=defaultdict(float)
        for s,v in start.items(): pos[s]=v; mx[s]=abs(v)
        for f in sorted(fs,key=lambda x:x["fill_ts"]):
            sg=1 if f["side"]=="buy" else -1
            pos[f["symbol"]]+=sg*abs(f["fill_notional"])
            mx[f["symbol"]]=max(mx[f["symbol"]],abs(pos[f["symbol"]]))
        over=[]
        for sym,m in mx.items():
            t=abs(tw[ats].get(sym,0.0)*g); e=abs(rb[ats].get(sym,0.0))
            ref=max(t,e)
            if m>1.5*ref+50: over.append((sym,round(m),round(t),round(e)))
        traded=sum(abs(f["fill_notional"]) for f in fs)
        ledger=sum(abs(float(o["filled_notional"])) for o in one["orders"]
                   if o["anchor_ts"]==ats and o.get("filled_notional"))
        lbl=time.strftime('%m-%dT%H:%M:%SZ',time.gmtime(ats))
        print(f"{lbl:18s} venue_traded_dedup={traded:9.0f} our_ledger={ledger:9.0f} "
              f"ratio={traded/ledger if ledger else float('nan'):5.2f} n_overshoot={len(over)} {over[:3]}")
        out.append({"anchor":lbl,"venue_traded_dedup":round(traded),"our_ledger":round(ledger),
                    "ratio":round(traded/ledger,3) if ledger else None,
                    "n_names_peak_gt_1.5x":len(over),"examples":over[:5]})
        prev_rb=rb[ats]
json.dump(out,open("/Users/haosiyu/Desktop/quant_research/multi_asset/exports/eda/0C_p3_overshoot_dedup.json","w"),indent=1)
