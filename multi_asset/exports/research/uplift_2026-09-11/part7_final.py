#!/usr/bin/env python3
"""Part 7: (a) pooled latency estimate with CI; (b) frozen-book counterfactual — does TRADING at all
add anything?; (c) the cadence question via the trade-decay cumulative; (d) tail/stop inventory."""
import os, json, glob, time
import numpy as np
exec(open("/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/smooth_latency_core.py").read().split("# ---- 1.")[0])

KA=[a for a in kw if (a-14400) in SMK and y4_of(a) is not None]
CA=[a for a in cw if (a-14400) in SMC and y4_of(a) is not None]
def unit(w):
    g=np.abs(w).sum(); return w/g if g>1e-12 else w

# ---------- (a) latency, finer, with CI ----------
print("[LATENCY] dw . r over minutes-after-anchor. Executor reads target_live at N+24min "
      "(config/book.json external_book.anchor_offset_min=24), quotes k_seconds=900 (=15min).")
def prof(SM, A):
    M=np.full((len(A),48),np.nan)
    for i,a in enumerate(A):
        s=seg_of(a)
        if s is None: continue
        dw=SM[a]-SM[a-14400]
        M[i]=(np.nan_to_num(s,nan=0.0)*dw[None,:]).sum(1)*1e4
    return M
MK=prof(SMK,KA); MC=prof(SMC,CA)
def ci(v):
    v=v[np.isfinite(v)]; m=v.mean(); se=v.std(ddof=1)/np.sqrt(len(v)); return m,se,m/se,len(v)
for lab,M in (("king  n=145",MK),("combo n=93 ",MC)):
    for lo,hi,t in ((0,5,"N+0..25m LOST to latency"),(0,6,"N+0..30m"),(0,8,"N+0..40m (through quote window)"),(0,48,"whole 4h")):
        m,se,tt,n=ci(np.nansum(M[:,lo:hi],1))
        print(f"  {lab} {t:<34s} {m:+8.4f} +- {se:.4f}  t={tt:+5.2f}")
# pooled (independent windows: king pre-combo era + combo era)
kpre=[i for i,a in enumerate(KA) if a < CA[0]]
pool=np.r_[np.nansum(MK[kpre,0:5],1), np.nansum(MC[:,0:5],1)]
m,se,tt,n=ci(pool)
print(f"  POOLED (king pre-08-26 n={len(kpre)} + combo n={len(CA)}): latency cost {m:+.4f} +- {se:.4f} bps/anchor  t={tt:+.2f}  n={n}")
print(f"    95% CI [{m-1.96*se:+.4f}, {m+1.96*se:+.4f}] bps/anchor")
print(f"    upper bound in NAV terms @2x, 6 anchors/day: {(m+1.96*se)*6*2:+.3f} bps NAV/day = {(m+1.96*se)*6*2*365/100:+.3f} %NAV/yr")

# ---------- (b) frozen book: does trading add anything at all? ----------
print("\n[FROZEN-BOOK COUNTERFACTUAL] hold the book fixed from the first anchor of the window; "
      "same unit-gross scoring, zero turnover thereafter.")
for lab,SM,A in (("king ",SMK,KA),("combo",SMC,CA)):
    Y=[np.nan_to_num(y4_of(a),nan=0.0) for a in A]
    live=np.array([float((unit(SM[a])*Y[i]).sum()*1e4) for i,a in enumerate(A)])
    w0=unit(SM[A[0]-14400])
    froz=np.array([float((w0*Y[i]).sum()*1e4) for i in range(len(A))])
    d=live-froz
    print(f"  {lab}: live {live.mean():+.4f}  frozen {froz.mean():+.4f}  ALL TRADING SINCE WINDOW START = "
          f"{d.mean():+.4f} +- {d.std(ddof=1)/np.sqrt(len(d)):.4f} bps/anchor (t={d.mean()/(d.std(ddof=1)/np.sqrt(len(d))):+.2f})")
    # frozen at each anchor, 1 anchor ahead only (pure "is the new book better than the old book")
    fresh=np.array([float((unit(SM[a])-unit(SM[a-14400])).dot(Y[i])*1e4) for i,a in enumerate(A)])
    print(f"         one-step freshness (w_t - w_{{t-1}}).y4_t = {fresh.mean():+.4f} +- {fresh.std(ddof=1)/np.sqrt(len(fresh)):.4f} (t={fresh.mean()/(fresh.std(ddof=1)/np.sqrt(len(fresh))):+.2f})")

# ---------- (c) tails, stop trips ----------
print("\n[TAIL INVENTORY, live]")
PLP="/Users/haosiyu/dl_quant_live/state/live/pilot_log"
nav={}
for d in sorted(os.path.basename(x) for x in glob.glob(f"{PLP}/2026*")):
    f=f"{PLP}/{d}/daily_nav.jsonl"
    if os.path.exists(f):
        for ln in open(f):
            try: r=json.loads(ln)
            except: continue
            nav[r["day"]]=r
dd=sorted(nav); ret=[]; lab=[]
for d in dd:
    r=nav[d]; pv=float(r.get("prev_nav") or 0); nv=float(r.get("nav") or 0); fl=float(r.get("external_flow_usdt") or 0)
    if pv>0: ret.append((nv-fl-pv)/pv); lab.append(d)
ret=np.array(ret)
for nm_,mask in (("whole 41d",np.ones(len(ret),bool)),
                 ("combo era 08-26+",np.array([l>="2026-08-26" for l in lab])),
                 ("post-deposit 09-03+",np.array([l>="2026-09-03" for l in lab]))):
    v=ret[mask]
    print(f"  {nm_:<20s} n={len(v):2d} mean {100*v.mean():+.4f}%/d sd {100*v.std(ddof=1):.4f} "
          f"Sh {v.mean()/v.std(ddof=1)*np.sqrt(365):+.2f} worst {100*v.min():+.3f}% "
          f"CVaR20 {100*v[v<=np.percentile(v,20)].mean():+.3f}% cum {100*(np.prod(1+v)-1):+.3f}%")
# how much of the loss is the worst day?
v=ret[np.array([l>="2026-08-26" for l in lab])]
print(f"  combo era: cum with worst day removed = {100*(np.prod(1+np.delete(v,np.argmin(v)))-1):+.3f}%  "
      f"(actual {100*(np.prod(1+v)-1):+.3f}%)")
# known risk events
ev=[]
for d in sorted(os.path.basename(x) for x in glob.glob(f"{PLP}/2026*")):
    f=f"{PLP}/{d}/anchors.jsonl"
    if not os.path.exists(f): continue
    n=0; kg=0
    for ln in open(f):
        try: r=json.loads(ln)
        except: continue
        n+=1
        if r.get("known_gaps"): kg+=1
    ev.append((d,n,kg))
print(f"  anchors/day: {[f'{d[-4:]}:{n}' for d,n,kg in ev if n!=6]}  (days not equal to 6 anchors)")
