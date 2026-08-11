"""Quantify the 07-26T00:01 structure: venue vs intent per name."""
import sys,json,time
from collections import Counter
sys.path.insert(0,"/Users/haosiyu/dl_quant_live/live")
import pilot_log as PL
root="/Users/haosiyu/dl_quant_live/state/testnet/pilot_log"
for day,ats_want in [("20260726",1785024063.312125),("20260726",1785067248.198903),
                     ("20260727",None)]:
    one=PL.read_day(root,day)
    ancs=sorted({a["anchor_ts"] for a in one["anchors"]})
    targets=[ats_want] if ats_want else [ancs[0]]
    for ats in targets:
        tg=[a.get("target_gross") for a in one["anchors"] if a["anchor_ts"]==ats][0]
        tw={}; filled={}
        for o in one["orders"]:
            if o["anchor_ts"]!=ats: continue
            tw[o["symbol"]]=o["target_w"]
            f=o.get("filled_notional")
            if f: filled[o["symbol"]]=filled.get(o["symbol"],0.0)+float(f)
        rb={r["symbol"]:float(r["venue_position_notional"]) for r in one["position_readback"]
            if r["anchor_ts"]==ats}
        buckets=Counter(); tot_excess=0.0
        rows=[]
        for s,w in tw.items():
            intent=w*tg; v=rb.get(s)
            if v is None: buckets["no_readback"]+=1; continue
            if abs(intent)<1e-9: continue
            ratio=v/intent
            if abs(v)<5: buckets["venue_flat (intent nonzero)"]+=1
            elif 1.8<=ratio<=2.2: buckets["venue ~2x intent"]+=1; tot_excess+=abs(v)-abs(intent)
            elif 0.8<=ratio<=1.2: buckets["venue ~1x intent (ok)"]+=1
            else: buckets["other"]+=1
            rows.append((s,round(intent,1),round(v,1),round(ratio,3),round(filled.get(s,0.0),1)))
        print("==",time.strftime('%m-%dT%H:%M:%SZ',time.gmtime(ats)),"target_gross",round(tg,0))
        for k,c in buckets.most_common(): print(f"   {k:32s} {c}")
        print("   excess notional on doubled names: %.0f USDT" % tot_excess)
        print("   sum|recorded filled| = %.0f ; sum|venue| = %.0f" %
              (sum(abs(x) for x in filled.values()), sum(abs(x) for x in rb.values())))
        oth=[r for r in rows if not(0.8<=r[3]<=1.2)][:6]
        print("   examples (sym,intent,venue,ratio,recorded_filled):",oth)
