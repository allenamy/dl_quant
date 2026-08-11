import sys,json,time
from collections import defaultdict
sys.path.insert(0,"/Users/haosiyu/dl_quant_live/live")
import pilot_log as PL
root="/Users/haosiyu/dl_quant_live/state/testnet/pilot_log"
def devs_at(day,ats):
    one=PL.read_day(root,day)
    tg=[a["target_gross"] for a in one["anchors"] if a["anchor_ts"]==ats][0]
    tw={o["symbol"]:o["target_w"] for o in one["orders"] if o["anchor_ts"]==ats}
    rb={r["symbol"]:float(r["venue_position_notional"]) for r in one["position_readback"] if r["anchor_ts"]==ats}
    d=sorted(abs(rb[s]-tw[s]*tg) for s in tw if s in rb)
    return d,tg
import statistics as st
cases=[("20260726",1785024063.312125,"07-26T00:01  LEDGER: 47 names 2x (real break)"),
       ("20260726",1785067248.198903,"07-26T12:00  LEDGER: duplicate rows, book==intent"),
       ("20260727",None,"07-27T00:01  LEDGER: 0 of 21424 USDT recorded"),
       ("20260727","08","07-27T08:01  LEDGER: healthy (22590 vs 22575)"),
       ("20260728","04","07-28T04:00  LEDGER: healthy (23402 vs 23400)")]
one27=PL.read_day(root,"20260727"); a27=sorted({a["anchor_ts"] for a in one27["anchors"]})
one28=PL.read_day(root,"20260728"); a28=sorted({a["anchor_ts"] for a in one28["anchors"]})
resolved=[("20260726",1785024063.312125,cases[0][2]),("20260726",1785067248.198903,cases[1][2]),
          ("20260727",a27[0],cases[2][2]),("20260727",a27[2],cases[3][2]),("20260728",a28[1],cases[4][2])]
print(f"{'case':52s} {'n':>4s} {'sum$':>9s} {'%gross':>7s} {'p50':>7s} {'p90':>7s} {'max':>8s} {'n>50':>5s}")
out=[]
for day,ats,lbl in resolved:
    d,tg=devs_at(day,ats)
    print(f"{lbl:52s} {len(d):4d} {sum(d):9.0f} {sum(d)/tg*100:6.1f}% "
          f"{st.median(d):7.1f} {d[int(.9*len(d))]:7.1f} {max(d):8.1f} {sum(1 for x in d if x>50):5d}")
    out.append({"case":lbl,"n":len(d),"sum_usdt":round(sum(d)),"pct_gross":round(sum(d)/tg*100,1),
                "p50":round(st.median(d),1),"p90":round(d[int(.9*len(d))],1),"max":round(max(d),1),
                "n_gt50":sum(1 for x in d if x>50)})
json.dump(out,open("/Users/haosiyu/Desktop/quant_research/multi_asset/exports/eda/0C_p3_ledger_vs_position_dist.json","w"),indent=1)
