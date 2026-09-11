import numpy as np, json, sys
sys.path.insert(0,"/workspace/uplift_2026-09-11/r3_integrate")
from integrate import D, SPANS, series, common, sr, dayblocks
def boot_pair(a,b,ts,k=9,B=2000):
    blocks=dayblocks(ts); rng=np.random.default_rng([20260905,k]); nb=len(blocks)
    d=a-b; o=np.empty(B); os_=np.empty(B)
    for i in range(B):
        pick=rng.integers(0,nb,nb); idx=np.concatenate([blocks[j] for j in pick])
        o[i]=d[idx].mean()
        x=a[idx]; y=b[idx]
        os_[i]=x.mean()/x.std(ddof=1)*np.sqrt(2190)-y.mean()/y.std(ddof=1)*np.sqrt(2190)
    return (float(d.mean()),float(np.percentile(o,2.5)),float(np.percentile(o,97.5)),
            float(sr(a)-sr(b)),float(np.percentile(os_,2.5)),float(np.percentile(os_,97.5)))
print("=== COMBINED PORTFOLIO vs A0, per impact multiple K, span F23 n=7908, equal-unit-vol weights fixed at K=1 ===")
print("%-6s %-34s %-34s"%("K","paired D on g [CI95]","dSharpe [CI95]"))
rows={}
for tag,lab in (("_H0","K=0 fee+spread"),("_X1","K=1"),("_X2","K=2"),("_X3","K=3"),("","deployed STD")):
    ks=["A0_s42"+tag,"AMI_lag"+tag,"RS_s42"+tag]
    ts,G=common(ks,"F23",True)
    sd=G.std(1,ddof=1); w=(1/sd); w=w/w.sum()
    p=w@G; a0=G[0]
    r=boot_pair(p,a0,ts)
    rows[lab]=dict(SR_port=round(sr(p),4),SR_A0=round(sr(a0),4),D=round(r[0],4),D_CI=[round(r[1],4),round(r[2],4)],
                   dSR=round(r[3],4),dSR_CI=[round(r[4],4),round(r[5],4)],w=[round(float(x),4) for x in w])
    print("%-6s D=%+.4f [%+.4f,%+.4f]   dSR=%+.3f [%+.3f,%+.3f]  SRport=%.3f SRa0=%.3f"%(
        lab,r[0],r[1],r[2],r[3],r[4],r[5],sr(p),sr(a0)))
print()
print("=== XIB+RS portfolio vs A0, same ladder ===")
for tag,lab in (("_H0","K=0"),("_X1","K=1"),("_X2","K=2"),("_X3","K=3"),("","STD")):
    ks=["A0_s42"+tag,"XIB_s42"+tag,"RS_s42"+tag]
    ts,G=common(ks,"F23",True)
    sd=G[1:].std(1,ddof=1); w=(1/sd); w=w/w.sum()
    p=w@G[1:]; a0=G[0]
    r=boot_pair(p,a0,ts)
    print("%-6s D=%+.4f [%+.4f,%+.4f]   dSR=%+.3f [%+.3f,%+.3f]  SRport=%.3f SRa0=%.3f"%(
        lab,r[0],r[1],r[2],r[3],r[4],r[5],sr(p),sr(a0)))
print()
print("=== per-year, equal-vol XIB+RS at X1, and components (bps/anchor/gross) ===")
ks=["A0_s42_X1","XIB_s42_X1","RS_s42_X1"]
ts,G=common(ks,"F23",True)
sd=G[1:].std(1,ddof=1); w=(1/sd); w=w/w.sum(); p=w@G[1:]
yr=np.array([int(str(np.datetime64(int(t),"s"))[:4]) for t in ts])
for y in sorted(set(yr)):
    m=yr==y
    print("  %d n=%4d  A0 %+.3f/SR%+.2f   XIB %+.3f/SR%+.2f   RS %+.3f/SR%+.2f   PORT %+.3f/SR%+.2f"%(
        y,m.sum(),G[0][m].mean(),sr(G[0][m]),G[1][m].mean(),sr(G[1][m]),G[2][m].mean(),sr(G[2][m]),p[m].mean(),sr(p[m])))
print()
print("=== EXT out-of-fit window 2026-08-11..08-31 ===")
ks=["A0_s42_X1","XIB_s42_X1","RS_s42_X1","AMI_lag_X1"]
ts,G=common(ks,"EXT",True)
print("  n=",len(ts))
for k,g in zip(ks,G): print("   %-14s g %+.4f SR %+.3f"%(k,g.mean(),sr(g)))
sd=np.array([G[1].std(ddof=1),G[2].std(ddof=1)]); w=(1/sd); w=w/w.sum(); p=w@G[1:3]
print("   PORT(XIB+RS) g %+.4f SR %+.3f"%(p.mean(),sr(p)))
print()
print("=== what is still missing: two-asset max-Sharpe solve ===")
def need(SR1,rho,target):
    # SR_tot^2 = (SR1^2 + SR2^2 - 2 rho SR1 SR2)/(1-rho^2)  solve for SR2
    import numpy as np
    a=1.0; b=-2*rho*SR1; c=SR1**2-target**2*(1-rho**2)
    disc=b*b-4*a*c
    if disc<0: return None
    return (-b+np.sqrt(disc))/2
for base,lab in ((3.0964,"deployed STD, XIB+RS = 3.096"),(2.6010,"honest X1, XIB+RS = 2.601")):
    for tgt,tl in ((3.0,"point 3.0"),(3.0+1.96*0.526,"lower CI bound > 3.0 (= point %.3f)"%(3.0+1.96*0.526))):
        for rho in (0.0,0.1,0.2,0.3):
            v=need(base,rho,tgt)
            print("  base %-32s target %-44s rho %.1f -> need standalone SR %s"%(lab,tl,rho,("%.3f"%v) if v else "impossible"))
