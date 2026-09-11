import numpy as np, json, sys
sys.path.insert(0,"/workspace/uplift_2026-09-11/r3_integrate")
from integrate import D, SPANS, series, common, sr, dayblocks
print("=== FULL CYCLE post-warm (n=9018) correlation among everything that HAS 2022 ===")
for tag in ("","_X1"):
    ks=[k+tag for k in ("A0_s42","XIB_s42","AMI_lag")]
    ts,G=common(ks,"FULL",True)
    C=np.corrcoef(G); srs=[sr(g) for g in G]
    print(" cost=%s n=%d SR %s"%(tag or "STD",G.shape[1]," ".join("%s=%+.3f"%(k,s) for k,s in zip(ks,srs))))
    for i,k in enumerate(ks): print("   %-14s"%k[:14]+" ".join("%8.4f"%C[i][j] for j in range(len(ks))))
print()
print("=== regime translation factor measured on A0 (post-warm, same arm, two spans) ===")
for tag in ("","_X1"):
    a=D["A0_s42"+tag]
    t1,g1=series("A0_s42"+tag,"FULL",True); t2,g2=series("A0_s42"+tag,"F23",True)
    print("  cost=%-4s A0 FULL_pw SR %.4f (n=%d) ; F23 SR %.4f (n=%d) ; ratio F23/FULL = %.4f"%(
        tag or "STD",sr(g1),len(g1),sr(g2),len(g2),sr(g2)/sr(g1)))
    t3,g3=series("XIB_s42"+tag,"FULL",True); t4,g4=series("XIB_s42"+tag,"F23",True)
    print("       XIB FULL_pw SR %.4f ; F23 SR %.4f ; ratio %.4f"%(sr(g3),sr(g4),sr(g4)/sr(g3)))
print()
print("=== per-year FULL CYCLE post-warm ===")
ks=["A0_s42","XIB_s42","AMI_lag","A0_s42_X1","XIB_s42_X1","AMI_lag_X1"]
ts,G=common(ks,"FULL",True)
yr=np.array([int(str(np.datetime64(int(t),"s"))[:4]) for t in ts])
for y in sorted(set(yr)):
    m=yr==y
    print("  %d n=%4d  "%(y,m.sum())+"  ".join("%s %+.3f/SR%+.2f"%(k.replace("_s42",""),G[i][m].mean(),sr(G[i][m])) for i,k in enumerate(ks)))
print()
print("=== equal-vol A0+AMI full cycle, per year, and paired vs A0 ===")
ks=["A0_s42_X1","AMI_lag_X1"]
ts,G=common(ks,"FULL",True)
sd=G.std(1,ddof=1); w=(1/sd); w=w/w.sum(); p=w@G
print("  SR port %.4f  vs A0 %.4f ; n=%d SE=%.3f"%(sr(p),sr(G[0]),len(ts),np.sqrt(2190/len(ts))))
yr=np.array([int(str(np.datetime64(int(t),"s"))[:4]) for t in ts])
for y in sorted(set(yr)):
    m=yr==y; print("   %d PORT %+.3f/SR%+.2f  A0 %+.3f/SR%+.2f"%(y,p[m].mean(),sr(p[m]),G[0][m].mean(),sr(G[0][m])))
print()
print("=== turnover and carry decomposition, F23, X1 ===")
for k in ("A0_s42_X1","XIB_s42_X1","AMI_lag_X1","RS_s42_X1","RS_s2027_X1"):
    ts,g,c=D[k]; lo,hi=SPANS["F23"]; m=(ts>=lo)&(ts<=hi)
    gt=c["gross_total"][m]
    net=c["net_ex"][m]/gt; pnl=c["pnl_ex"][m]/gt; car=c["carry_ex"][m]/gt; cos=c["cost_ex"][m]/gt
    print("  %-14s net %+.4f = pnl %+.4f - carry %+.4f - cost %+.4f | carry_frac(-carry/net) %+.3f | turnover(raw) %.4f | maxresid %.1e"%(
      k,net.mean(),pnl.mean(),car.mean(),cos.mean(),-car.mean()/net.mean(),c["turnover"][m].mean(),
      float(np.nanmax(np.abs(c["net_ex"][m]-(c["pnl_ex"][m]-c["carry_ex"][m]-c["cost_ex"][m]))))))
print()
print("=== where does the XIB+RS portfolio Sharpe cross 3.0 / 2.0 in K? (linear fit on K grid) ===")
Ks=[0,1,2,3]; tags=["_H0","_X1","_X2","_X3"]; vals=[]
for tag in tags:
    ks=["XIB_s42"+tag,"RS_s42"+tag]; ts,G=common(ks,"F23",True)
    sd=G.std(1,ddof=1); w=(1/sd); w=w/w.sum(); vals.append(sr(w@G))
A=np.polyfit(Ks,vals,1)
print("  SR(K) grid:", ["%.4f"%v for v in vals], " fit slope %.4f intercept %.4f"%(A[0],A[1]))
for target in (3.0,2.5,2.0,1.524):
    print("   crosses %.3f at K = %.3f"%(target,(target-A[1])/A[0]))
