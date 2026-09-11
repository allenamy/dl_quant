"""Portfolio arithmetic for the surviving sleeves: blend curves, effective bets, multi-test correction."""
import numpy as np, json, glob, os, calendar, itertools
import importlib.util
spec=importlib.util.spec_from_file_location("j","/workspace/uplift_2026-09-11/judgeD.py"); j=importlib.util.module_from_spec(spec); spec.loader.exec_module(j)
A0="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz"
t0,g0,R0=j.load(A0,"d30_n2_c42_rec")
import sys
tags=sys.argv[1:]
S={}
for tg in tags:
    ts,g,R=j.load(f"/workspace/uplift_2026-09-11/trackD_v4/{tg}.npz","rec"); S[tg]=(ts,g)
def align(series):
    common=t0
    for ts,_ in series: common=np.intersect1d(common,ts)
    out=[]
    for ts,g in series:
        idx=np.searchsorted(ts,common); out.append(g[idx])
    i0=np.searchsorted(t0,common)
    return common,g0[i0],out
WIN={"full":(j.FULL),"frozen":(j.FROZEN),"2023on":(calendar.timegm((2023,1,1,0,0,0)),j.FULL[1])}
for y in ["2022","2023","2024","2025","2026"]: WIN[y]=j.YRS[y]
common,gg0,gs=align([S[t] for t in tags])
print("common anchors", len(common))
def sh(v): return float(v.mean()/v.std(ddof=1)*np.sqrt(2190)) if len(v)>2 and v.std(ddof=1)>0 else float("nan")
print("\n=== correlation matrix on 2023-01 -> 2026-08-10 (A0 first) ===")
lo,hi=WIN["2023on"]; m=(common>=lo)&(common<hi)
Mx=np.vstack([gg0[m]]+[x[m] for x in gs])
labels=["A0"]+tags
Cm=np.corrcoef(Mx)
print("      "+" ".join(f"{l[:12]:>13s}" for l in labels))
for i,l in enumerate(labels):
    print(f"{l[:12]:>13s} "+" ".join(f"{Cm[i,k]:+13.3f}" for k in range(len(labels))))
ev=np.linalg.eigvalsh(Cm); ev=np.maximum(ev,1e-12)
print("effective independent bets (equal-weight, exp of entropy of eigenvalue shares):",
      round(float(np.exp(-(ev/ev.sum()*np.log(ev/ev.sum())).sum())),3), " n series", len(labels))
print("\n=== blend curves: (1-w)*A0 + w*sleeve, equal-gross, cost NOT netted (lower bound) ===")
for tg,x in zip(tags,gs):
    print(f"-- {tg}")
    for w in [0.0,0.1,0.2,0.3,0.4,0.5]:
        line=[]
        for nm in ["full","2023on","frozen","2023","2024","2025","2026"]:
            lo,hi=WIN[nm]; mm=(common>=lo)&(common<hi)
            if mm.sum()<3: line.append(f"{nm}: n/a"); continue
            v=(1-w)*gg0[mm]+w*x[mm]
            line.append(f"{nm} {v.mean():+.3f}/{sh(v):+.2f}")
        print(f"   w={w:.1f}  "+"  ".join(line))

# multi-sleeve combination on the common set
print("\n=== multi-sleeve equal-gross combinations (same anchor set as above) ===")
def rep(name, v, mask):
    x=v[mask]; print(f"   {name:44s} mean {x.mean():+.3f}  Sharpe {sh(x):+.2f}")
for nm,(lo,hi) in [("full",WIN["full"]),("2023",WIN["2023"]),("2024",WIN["2024"]),("2025",WIN["2025"]),("2026",WIN["2026"]),("frozen",WIN["frozen"])]:
    mm=(common>=lo)&(common<hi)
    if mm.sum()<3: continue
    print(f"-- window {nm} (n={int(mm.sum())})")
    rep("A0 alone", gg0, mm)
    for w in [0.3,0.4,0.5]:
        for i,tg in enumerate(tags):
            rep(f"{1-w:.1f}*A0 + {w:.1f}*{tg}", (1-w)*gg0+w*gs[i], mm)
        if len(tags)>=2:
            rep(f"{1-w:.1f}*A0 + {w/2:.2f}*each of 2 sleeves", (1-w)*gg0+ (w/2)*(gs[0]+gs[1]), mm)
