#!/usr/bin/env python3
"""Anchor-level live series in the replay device's unit: bps of GROSS per anchor.
Each daily_nav.jsonl row is one post-anchor equity read. Interval P&L between consecutive
reads is divided by the gross that was ACTUALLY CARRIED over that interval = the gross set at
the PREVIOUS anchor (realized_gross of the previous read's anchor). External flows are removed
using the within-day cumulative external_flow_usdt field (resets at 00:00Z). READ-ONLY."""
import json, os, glob, time
BASE="/Users/haosiyu/dl_quant_live/state/live/pilot_log"
OUT="/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"
recs=[]
for d in sorted(os.path.basename(x) for x in glob.glob(BASE+"/2026*")):
    p=os.path.join(BASE,d,"daily_nav.jsonl")
    if not os.path.exists(p): continue
    rr=[json.loads(l) for l in open(p) if l.strip()]
    # realized gross per anchor from anchors.jsonl, matched by time
    ap=os.path.join(BASE,d,"anchors.jsonl"); anch=[]
    if os.path.exists(ap):
        for l in open(ap):
            if not l.strip(): continue
            try: a=json.loads(l)
            except Exception: continue
            if a.get("realized_gross") and a.get("anchor_ts"): anch.append((float(a["anchor_ts"]),float(a["realized_gross"])))
    anch.sort()
    for i,r in enumerate(rr):
        t=r.get("nav_ts")
        g=None
        if t is not None and anch:
            cand=[x for x in anch if x[0]<=t+120]
            if cand: g=cand[-1][1]
        recs.append(dict(day=d,idx=i,nav=r["nav"],prev_nav=r.get("prev_nav"),
                         flow_cum=r.get("external_flow_usdt",0.0),nav_ts=t,
                         target_gross=r.get("target_gross"),realized_gross=g,
                         first_of_day=(i==0)))
rows=[]
for k,r in enumerate(recs):
    if r["first_of_day"]:
        base=r["prev_nav"]; dflow=r["flow_cum"]
        prev_gross=recs[k-1]["realized_gross"] if k>0 else None
    else:
        prev=recs[k-1]; base=prev["nav"]; dflow=r["flow_cum"]-prev["flow_cum"]
        prev_gross=prev["realized_gross"]
    if base is None or base<=0: continue
    pnl=r["nav"]-base-dflow
    G=prev_gross if prev_gross else (r["realized_gross"] or r["target_gross"])
    rows.append(dict(day=r["day"],ts=r["nav_ts"],pnl=pnl,base=base,flow=dflow,gross=G,
                     bps_gross=(pnl/G*1e4) if G else None,ret=pnl/base))
ok=[x for x in rows if x["bps_gross"] is not None]
print(f"anchor-level rows {len(rows)}, with gross {len(ok)}")
def blk(name,lo,hi):
    sel=[x for x in ok if lo<=x["day"]<=hi]
    tot=sum(x["bps_gross"] for x in sel); n=len(sel)
    pnl=sum(x["pnl"] for x in sel)
    import statistics as st
    sd=st.pstdev([x["bps_gross"] for x in sel]) if n>1 else float('nan')
    print(f"[{name}] {lo}..{hi} anchors={n} SUM={tot/100:+.3f}% of gross  mean={tot/n:+.4f} bps/anchor/gross  sd={sd:.2f}  "
          f"Sharpe_ann={(tot/n)/sd*(2190**0.5):+.2f}  rawPnL={pnl:+.0f} USDT")
    return tot,n
blk("whole live","20260801","20260911")
W=blk("COMBO ERA (live window)","20260826","20260911")
blk("post-deposit","20260903","20260911")
blk("pre-combo","20260801","20260825")
blk("08-26..08-30 (backtest overlap)","20260826","20260830")
blk("09-01..09-11 (no backtest coverage)","20260901","20260911")
print("\nper-day sums (bps of gross):")
bd={}
for x in ok: bd[x["day"]]=bd.get(x["day"],0)+x["bps_gross"]
for k in sorted(bd): print(f"  {k} {bd[k]:+9.1f} bps  ({bd[k]/100:+.3f}% of gross)")
json.dump(dict(rows=ok,day_sums=bd), open(f"{OUT}/live_anchor_rows.json","w"), indent=1)
print("\nWINDOW_TOTAL_BPS_OF_GROSS", W[0], "n_anchors", W[1])
