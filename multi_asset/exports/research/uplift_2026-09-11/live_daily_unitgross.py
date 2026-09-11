#!/usr/bin/env python3
"""Live ledger -> flow-adjusted daily returns AND per-anchor bps-of-gross, the unit the w10
replay device reports as net_ex/gross_total. READ-ONLY on the live tree."""
import json, os, glob
BASE="/Users/haosiyu/dl_quant_live/state/live/pilot_log"
days=sorted(os.path.basename(d) for d in glob.glob(BASE+"/2026*"))
rows=[]
for d in days:
    p=os.path.join(BASE,d,"daily_nav.jsonl")
    if not os.path.exists(p): continue
    recs=[json.loads(l) for l in open(p) if l.strip()]
    if not recs: continue
    last=recs[-1]
    nav=last["nav"]; prev=last.get("prev_nav"); flow=last.get("external_flow_usdt",0.0)
    tg=last.get("target_gross"); pol=last.get("sizing_policy")
    ap=os.path.join(BASE,d,"anchors.jsonl")
    gs=[]; 
    if os.path.exists(ap):
        for l in open(ap):
            if not l.strip(): continue
            try: a=json.loads(l)
            except Exception: continue
            g=a.get("realized_gross")
            if g: gs.append(float(g))
    na=len(gs); G=sum(gs)/na if na else None
    if prev is None or prev<=0: continue
    pnl=nav-prev-flow
    r=pnl/prev
    rows.append(dict(day=d,nav=nav,prev=prev,flow=flow,pnl=pnl,ret=r,n_anch=na,
                     gross=G,tg=tg,pol=pol,
                     bps_per_anchor_unit_gross=(pnl/G*1e4/na) if (G and na) else None,
                     lev=(G/prev) if G else None))
print(f"{'day':>9} {'prev_nav':>10} {'nav':>10} {'flow':>9} {'pnl':>9} {'ret%':>7} {'n':>2} {'gross':>9} {'lev':>5} {'bps/anch/gross':>14}")
for r in rows:
    print(f"{r['day']:>9} {r['prev']:10.1f} {r['nav']:10.1f} {r['flow']:9.0f} {r['pnl']:9.1f} {r['ret']*100:7.3f} {r['n_anch']:2d} "
          f"{(r['gross'] or 0):9.0f} {(r['lev'] or 0):5.2f} {(r['bps_per_anchor_unit_gross'] if r['bps_per_anchor_unit_gross'] is not None else float('nan')):14.3f}")
import statistics as st
def block(name, sel):
    rr=[r for r in rows if sel(r['day'])]
    if not rr: return
    rets=[r['ret'] for r in rr]
    bp=[r['bps_per_anchor_unit_gross'] for r in rr if r['bps_per_anchor_unit_gross'] is not None]
    na=sum(r['n_anch'] for r in rr if r['bps_per_anchor_unit_gross'] is not None)
    pnl=sum(r['pnl'] for r in rr); 
    cum=1.0
    for x in rets: cum*=(1+x)
    # anchor-weighted mean bps
    num=sum(r['bps_per_anchor_unit_gross']*r['n_anch'] for r in rr if r['bps_per_anchor_unit_gross'] is not None)
    print(f"\n[{name}] days={len(rr)} anchors={na} cum_ret={100*(cum-1):+.3f}% mean_d={100*st.mean(rets):+.4f}% "
          f"sd_d={100*st.pstdev(rets):.4f}% Sharpe_ann={st.mean(rets)/st.stdev(rets)*365**0.5:+.3f} "
          f"mean_bps_anchor_unit_gross={num/na:+.4f} (simple mean {st.mean(bp):+.4f})")
block("whole 08-01..09-11", lambda d: True)
block("combo era 08-26..09-11", lambda d: d>="20260826")
block("post-deposit 09-03..09-11", lambda d: d>="20260903")
block("pre-combo 08-01..08-25", lambda d: d<"20260826")
json.dump(rows, open("/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/live_daily_rows.json","w"), indent=1)
