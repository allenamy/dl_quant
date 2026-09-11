#!/usr/bin/env python3
"""Part 9: price the EXECUTION tracking gap. The venue book differs from the producer's target by
13.8% of gross (L1). That gap exists only live -- the backtest deploys the target exactly. Score it."""
import os, json, glob, time
import numpy as np
exec(open("/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/smooth_latency_core.py").read().split("# ---- 1.")[0])
PL="/Users/haosiyu/dl_quant_live/state/live/pilot_log"
TLV="/Users/haosiyu/wide_shadow/state/target_live"
col={s:j for j,s in enumerate(syms)}
rows=[]
for d in sorted(os.path.basename(x) for x in glob.glob(f"{PL}/2026*")):
    f=f"{PL}/{d}/position_readback.jsonl"
    if not os.path.exists(f): continue
    byA={}
    for ln in open(f):
        try:r=json.loads(ln)
        except:continue
        a=r.get("anchor_ts")
        if a is None: continue
        byA.setdefault(int(float(a)//14400*14400),{})[r["symbol"]]=float(r.get("venue_position_notional") or 0.0)
    for nom,pos in byA.items():
        p=f"{TLV}/{nom}.json"
        y=y4_of(nom)
        if not os.path.exists(p) or y is None: continue
        t=json.load(open(p)); w=t["weights"]; g=sum(abs(v) for v in w.values())
        gp=sum(abs(v) for v in pos.values())
        if g<=0 or gp<=0: continue
        TW=np.zeros(NW); VW=np.zeros(NW); miss=0.0
        for k,v in w.items():
            j=col.get(k)
            if j is not None: TW[j]=v/g
        for k,v in pos.items():
            j=col.get(k)
            if j is not None: VW[j]=v/gp
            else: miss+=abs(v)/gp
        yy=np.nan_to_num(y,nan=0.0)
        rows.append((nom, float((TW*yy).sum()*1e4), float((VW*yy).sum()*1e4), float(np.abs(VW-TW).sum()), miss))
rows.sort()
A=np.array([r[0] for r in rows]); tg=np.array([r[1] for r in rows]); vn=np.array([r[2] for r in rows])
te=np.array([r[3] for r in rows]); ms=np.array([r[4] for r in rows])
d=vn-tg
print(f"[TRACKING GAP PRICED] n={len(rows)} anchors {time.strftime('%m-%d %H',time.gmtime(A[0]))}..{time.strftime('%m-%d %H',time.gmtime(A[-1]))}")
print(f"  paper (producer target, unit gross)      {tg.mean():+8.4f} bps/anchor  sd {tg.std(ddof=1):.2f}")
print(f"  venue book as read back (unit gross)     {vn.mean():+8.4f} bps/anchor  sd {vn.std(ddof=1):.2f}")
print(f"  DIFFERENCE (venue - target)              {d.mean():+8.4f} +- {d.std(ddof=1)/np.sqrt(len(d)):.4f}  t={d.mean()/(d.std(ddof=1)/np.sqrt(len(d))):+.2f}")
print(f"  L1 tracking error mean {te.mean():.4f} ; gross in names outside the panel {ms.mean():.4f}")
cal=np.array([time.strftime('%Y%m%d',time.gmtime(a)) not in ('20260906','20260907','20260909','20260910') for a in A])
dc=d[cal]
print(f"  calm-days-only (drop 09-06/07/09/10 risk events) n={cal.sum()}: {dc.mean():+.4f} +- {dc.std(ddof=1)/np.sqrt(len(dc)):.4f} t={dc.mean()/(dc.std(ddof=1)/np.sqrt(len(dc))):+.2f}")
co=A>=1787702400
print(f"  combo era only n={co.sum()}: target {tg[co].mean():+.4f}  venue {vn[co].mean():+.4f}  diff {d[co].mean():+.4f} +- {d[co].std(ddof=1)/np.sqrt(co.sum()):.4f}")
np.savez(f"{OUT}/tracking_gap.npz", A=A, target_bps=tg, venue_bps=vn, te=te)
