#!/usr/bin/env python3
"""Read-only: live NAV per anchor since 08-26 vs BTC 4h return (beta of the real book), plus the last anchors' attribution."""
import json, glob, os, math
from datetime import datetime, timezone
L="/Users/haosiyu/dl_quant_live/state/live/pilot_log"
def jl(p):
    out=[]
    if not os.path.exists(p): return out
    for l in open(p, errors="ignore"):
        try: out.append(json.loads(l))
        except Exception: pass
    return out
nav={}; btc={}; flow={}
for d in sorted(glob.glob(L+"/2026*")):
    for r in jl(d+"/daily_nav.jsonl"):
        a=r.get("nav_ts")
        if a and r.get("nav"):
            k=int(round(float(a)/14400)*14400); nav[k]=float(r["nav"]); flow[k]=float(r.get("external_flow_usdt") or 0.0)
    for r in jl(d+"/anchors.jsonl"):
        a=r.get("anchor_ts"); mv=r.get("mid_at_anchor_vector") or {}
        if isinstance(mv, str):
            try: mv=json.loads(mv)
            except Exception: mv={}
        if a and isinstance(mv, dict) and mv.get("BTCUSDT"): btc[int(round(float(a)/14400)*14400)]=float(mv["BTCUSDT"])
ks=sorted(k for k in nav if k>=1787961600 and k in btc)
rows=[]
for a,b in zip(ks, ks[1:]):
    if b-a!=14400: continue
    if abs(flow.get(b,0.0))>0: 
        print("skip anchor with external flow", datetime.fromtimestamp(b,tz=timezone.utc), flow[b]); continue
    rows.append((b, (nav[b]-flow.get(b,0.0))/nav[a]-1, btc[b]/btc[a]-1))
print("anchors", len(rows), "from", datetime.fromtimestamp(rows[0][0],tz=timezone.utc), "to", datetime.fromtimestamp(rows[-1][0],tz=timezone.utc))
import statistics as st
x=[r[2] for r in rows]; y=[r[1] for r in rows]
mx,my=st.mean(x),st.mean(y); cov=sum((a-mx)*(b-my) for a,b in zip(x,y))/(len(x)-1); vx=st.variance(x); beta=cov/vx; alpha=my-beta*mx
r2=cov**2/(vx*st.variance(y))
print(f"NAV 4h return vs BTC 4h return: beta {beta:+.3f} (NAV per unit BTC), alpha {alpha*1e4:+.2f} bps/anchor, R2 {r2:.2f}, mean NAV/anchor {my*1e4:+.2f} bps, sd {st.stdev(y)*1e4:.1f} bps, Sharpe(anchor) {my/st.stdev(y)*math.sqrt(2190):.2f}")
# gross 2.0 => book beta per unit gross = beta/2
print(f"implied book beta per unit gross ≈ {beta/2:+.3f} (replay: −0.15)")
# worst/best anchors
srt=sorted(rows, key=lambda r:r[1])
print("worst 5 anchors:", [(datetime.fromtimestamp(r[0],tz=timezone.utc).strftime('%m-%d %HZ'), round(r[1]*1e4), round(r[2]*1e4)) for r in srt[:5]])
print("best 5 anchors:", [(datetime.fromtimestamp(r[0],tz=timezone.utc).strftime('%m-%d %HZ'), round(r[1]*1e4), round(r[2]*1e4)) for r in srt[-5:]])
print("last 8 anchors (NAV bps, BTC bps, beta-part, residual):")
for r in rows[-8:]:
    print("  ", datetime.fromtimestamp(r[0],tz=timezone.utc).strftime('%m-%d %HZ'), f"{r[1]*1e4:+7.1f} {r[2]*1e4:+7.1f} {beta*r[2]*1e4:+7.1f} {(r[1]-beta*r[2])*1e4:+7.1f}")
# regime split: anchors where |BTC 4h| > 1.5%
big=[r for r in rows if abs(r[2])>0.015]; small=[r for r in rows if abs(r[2])<=0.015]
for lab,S in (("|BTC|>1.5%",big),("|BTC|<=1.5%",small)):
    if S: print(f"{lab}: n {len(S)} mean NAV {st.mean(r[1] for r in S)*1e4:+.1f} bps, mean BTC {st.mean(r[2] for r in S)*1e4:+.1f}")
