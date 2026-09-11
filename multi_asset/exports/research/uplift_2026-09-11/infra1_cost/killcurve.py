#!/usr/bin/env python3
"""INFRA-1 step 9: the KILL MULTIPLE. Paired D(arm - PAR) vs impact multiple K, with a FIXED
bootstrap substream (rng default_rng([20260905, 777])) so the curve is not blurred by substream noise."""
import numpy as np, json, calendar, os, glob
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}; APY=2190
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
WINS={"frozen":(T(2025,3,1),T(2026,8,10,20)+1),"full":(T(2022,1,1),T(2026,8,10,20)+1),
      "2024on":(T(2024,1,1),T(2026,8,10,20)+1),"oof_aug":(T(2026,8,11),T(2026,8,31,20)+1)}
OUT="/workspace/uplift_2026-09-11/infra1_cost/out"
KMAP={"X1":1.0,"X15":1.5,"X2":2.0,"X25":2.5,"X3":3.0}
def load(p):
    A=np.load(p,allow_pickle=True); R=A["rec"]
    return np.round(np.asarray(R[:,0],float)).astype(np.int64), R[:,C["net_ex"]]/R[:,C["gross_total"]], R
def boot(v,days,k=777):
    rng=np.random.default_rng([20260905,k])
    ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(2000,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
    return float(np.percentile(mn,2.5)),float(np.percentile(mn,97.5)),float((mn>0).mean())
res={}
for seed in (42,2027):
  for arm in ("LAG50","AM50","D60","PERM50"):
    for cb,K in KMAP.items():
        a=f"{OUT}/IB_{arm}_{cb}_s{seed}.npz"; b=f"{OUT}/IB_PAR_{cb}_s{seed}.npz"
        if not (os.path.exists(a) and os.path.exists(b)): continue
        ta,ga,Ra=load(a); tb,gb,Rb=load(b); assert np.array_equal(ta,tb)
        d=ga-gb
        row={"K":K,"cb":cb}
        for w,(lo,hi) in WINS.items():
            m=(ta>=lo)&(ta<hi)
            if m.sum()<3: continue
            l,h,p=boot(d[m],ta[m]//86400)
            v=ga[m]
            row[w]=dict(n=int(m.sum()),D=float(d[m].mean()),lo=l,hi=h,p=p,
                        g=float(v.mean()),SR=float(v.mean()/v.std(ddof=1)*np.sqrt(APY)),
                        cost=float((Ra[m,C["cost_ex"]]/Ra[m,C["gross_total"]]).mean()),
                        cost_base=float((Rb[m,C["cost_ex"]]/Rb[m,C["gross_total"]]).mean()))
        res.setdefault(f"s{seed}",{}).setdefault(arm,[]).append(row)
json.dump(res,open("/workspace/uplift_2026-09-11/infra1_cost/KILLCURVE_EXEC.json","w"),indent=1)
for s in res:
    for arm in res[s]:
        rows=[r for r in res[s][arm] if r["K"] is not None]; rows.sort(key=lambda r:r["K"])
        std=[r for r in res[s][arm] if r["K"] is None]
        print(f"\n=== {s} {arm} : paired D vs PAR (fixed bootstrap substream 777) ===")
        print("%6s %8s %8s %20s %6s | %8s %8s %20s %6s | %8s %8s"%("K","fz D","fz SR","fz CI95","P>0","full D","full SR","full CI95","P>0","cost_arm","cost_PAR"))
        for r in std+rows:
            k="STD" if r["K"] is None else "%.2f"%r["K"]
            fz=r.get("frozen"); fu=r.get("full")
            print("%6s %8.3f %8.2f  [%+.3f,%+.3f] %6.3f | %8.3f %8.2f  [%+.3f,%+.3f] %6.3f | %8.4f %8.4f"%(
                k,fz["D"],fz["SR"],fz["lo"],fz["hi"],fz["p"],fu["D"],fu["SR"],fu["lo"],fu["hi"],fu["p"],fz["cost"],fz["cost_base"]))
        # kill multiple: smallest K where frozen CI lower bound crosses 0
        xs=[(r["K"],r["frozen"]["lo"]) for r in rows if "frozen" in r]
        kill=None
        for (k0,l0),(k1,l1) in zip(xs,xs[1:]):
            if l0>0>=l1: kill=k0+(k1-k0)*l0/(l0-l1); break
        print("  KILL MULTIPLE (frozen CI95 lower bound crosses 0): %s"%("K = %.2f"%kill if kill else "not crossed in [0,6]"))
        xs=[(r["K"],r["full"]["lo"]) for r in rows if "full" in r]
        kill=None
        for (k0,l0),(k1,l1) in zip(xs,xs[1:]):
            if l0>0>=l1: kill=k0+(k1-k0)*l0/(l0-l1); break
        print("  KILL MULTIPLE (FULL CYCLE CI95 lower bound crosses 0): %s"%("K = %.2f"%kill if kill else "not crossed in [0,6]"))
