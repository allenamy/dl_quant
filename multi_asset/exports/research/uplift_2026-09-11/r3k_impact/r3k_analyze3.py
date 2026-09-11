"""R3-CRITICAL-1 step F: levels + portfolio at the FITTED impact.
Statistic copied from judge_v4 / round-2 integrate.py: g = net_ex/gross_total, bps per anchor per unit
gross; UTC-day block bootstrap 2000 resamples, rng numpy.default_rng([20260905,k]); Sharpe = mean/sd*sqrt(2190).
E-0911-A: the first LOOK=900 device rows are dropped from every reading (seat warm-up).
"""
import numpy as np, json, os, sys, itertools
R3="/workspace/uplift_2026-09-11/r3k"; OUT=R3+"/arms"
HC="/workspace/review_scratch/health_check"
def rd(p):
    Z=np.load(p,allow_pickle=True)
    k="rec" if "rec" in Z.files else "d30_n2_c42_rec"
    R=np.asarray(Z[k],float); cols=[str(c) for c in Z["cols"]]; ix={c:i for i,c in enumerate(cols)}
    ts=R[:,ix["ts"]].astype(np.int64)
    d={c:R[:,ix[c]] for c in ("net_ex","pnl_ex","carry_ex","cost_ex","gross_total","turnover")}
    g=np.where(d["gross_total"]>0,d["net_ex"]/np.maximum(d["gross_total"],1e-12),np.nan)
    return ts,g,d
D={}
for f in sorted(os.listdir(OUT)):
    if f.endswith(".npz"): D[f[:-4]]=rd(OUT+"/"+f)
D["ARCH_A0_s42"]=rd(HC+"/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz")
def ep(s): return int((np.datetime64(s)-np.datetime64("1970-01-01T00:00:00"))/np.timedelta64(1,"s"))
SPANS={"FULL":(ep("2022-01-01T00:00"),ep("2026-08-10T20:00")),
       "F23":(ep("2023-01-01T00:00"),ep("2026-08-10T20:00")),
       "FROZEN":(ep("2025-03-01T00:00"),ep("2026-08-10T20:00"))}
def series(k,span,postwarm=True):
    ts,g,c=D[k]; lo,hi=SPANS[span]
    m=(ts>=lo)&(ts<=hi)&np.isfinite(g)
    if postwarm:
        w=np.zeros(len(ts),bool); w[:900]=True; m&=~w
    return ts[m],g[m]
sr=lambda x: float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(2190)) if len(x)>2 else float("nan")
def common(keys,span,pw=True):
    S=[series(k,span,pw) for k in keys]; ts=S[0][0]
    for t,_ in S[1:]: ts=np.intersect1d(ts,t)
    G=[]
    for t,g in S:
        ix=np.searchsorted(t,ts); assert np.array_equal(t[ix],ts); G.append(g[ix])
    return ts,np.array(G)
def dayblocks(ts):
    d=(ts//86400).astype(np.int64); u,inv=np.unique(d,return_inverse=True)
    return [np.where(inv==i)[0] for i in range(len(u))]
def boot(w,G,ts,k=9,B=2000):
    bl=dayblocks(ts); rng=np.random.default_rng([20260905,k]); nb=len(bl); r=w@G; o=np.empty(B)
    for b in range(B):
        pick=rng.integers(0,nb,nb); ix=np.concatenate([bl[i] for i in pick]); x=r[ix]
        o[b]=np.mean(x)/np.std(x,ddof=1)*np.sqrt(2190)
    return [round(float(np.percentile(o,2.5)),4),round(float(np.percentile(o,97.5)),4)]
RES={}
# 0. parity check: my A0 at STD vs archived A0
t,G=common(["A0_STD_s42","ARCH_A0_s42"],"FULL",False)
RES["parity_A0_STD_vs_archived"]=dict(n=int(G.shape[1]),max_abs_dg=float(np.max(np.abs(G[0]-G[1]))),
                                      bitwise=bool(np.array_equal(G[0],G[1])))
# 1. levels
LV={}
for k in sorted(D):
    row={}
    for sp in SPANS:
        t,g=series(k,sp,True)
        if len(g)>2: row[sp+"_pw"]=dict(n=len(g),g=round(float(g.mean()),4),SR=round(sr(g),4),
                                        SE=round(float(np.sqrt(2190/len(g))),4))
    t,g=series(k,"FULL",False)
    row["FULL_nowarm"]=dict(n=len(g),g=round(float(g.mean()),4),SR=round(sr(g),4))
    LV[k]=row
RES["levels"]=LV
# 2. cost decomposition at each cost model (F23)
CD={}
for k in sorted(D):
    ts,g,c=D[k]; lo,hi=SPANS["F23"]; m=(ts>=lo)&(ts<=hi); m[:900]=False
    gt=c["gross_total"][m]
    CD[k]=dict(net=round(float((c["net_ex"][m]/gt).mean()),4),pnl=round(float((c["pnl_ex"][m]/gt).mean()),4),
               carry=round(float((c["carry_ex"][m]/gt).mean()),4),cost=round(float((c["cost_ex"][m]/gt).mean()),4),
               turnover=round(float(c["turnover"][m].mean()),4),
               cost_bps_per_unit_turnover=round(float((c["cost_ex"][m]/gt).mean()/c["turnover"][m].mean()),4))
RES["cost_decomp_F23_pw"]=CD
# 3. portfolios
def report(keys,span,label):
    ts,G=common(keys,span,True); mu=G.mean(1); sd=G.std(1,ddof=1); srs=mu/sd*np.sqrt(2190)
    C=np.corrcoef(G); lam=np.linalg.eigvalsh(C); neff=float(lam.sum()**2/(lam**2).sum())
    Sig=np.cov(G); w=np.linalg.solve(Sig,mu); wn=w/np.abs(w).sum()
    we=(1/sd); we=we/np.abs(we).sum()
    return dict(label=label,span=span,n=int(G.shape[1]),keys=keys,
        SR={k:round(float(s),4) for k,s in zip(keys,srs)},
        corr=[[round(float(C[i,j]),4) for j in range(len(keys))] for i in range(len(keys))],
        N_eff=round(neff,4),w_opt={k:round(float(x),4) for k,x in zip(keys,wn)},
        SR_opt=round(sr(wn@G),4),SR_opt_CI95=boot(wn,G,ts),
        SR_equalvol=round(sr(we@G),4),SR_equalvol_CI95=boot(we,G,ts),
        SE=round(float(np.sqrt(2190/G.shape[1])),4))
P={}
for cb in ("STD","X1","FIT230k","FITU230k","PWR230k"):
    for s in ("42","2027"):
        ks=["XIB_%s_s%s"%(cb,s),"RS_%s_s%s"%(cb,s)]
        if all(k in D for k in ks):
            P["XIB+RS_%s_s%s"%(cb,s)]=report(ks,"F23","XIB_LAG50 + RESID_SHARPE cost=%s seed=%s"%(cb,s))
        ks2=["A0_%s_s%s"%(cb,s),"RS_%s_s%s"%(cb,s)]
        if all(k in D for k in ks2):
            P["A0+RS_%s_s%s"%(cb,s)]=report(ks2,"F23","A0 + RESID_SHARPE cost=%s seed=%s"%(cb,s))
RES["portfolios"]=P
# 4. capacity: A0 (and XIB/RS where built) vs gross
CAP={}
LAD=[230,345,460,690,920,1380,1840,2300,2760,3220,3680,4140,4600,9200,23000]
for pref in ("FIT","PWR"):
  for arm in ("A0","XIB","RS"):
    row={}
    for G in LAD:
        k="%s_%s%dk_s42"%(arm,pref,G)
        if k in D:
            t,g=series(k,"FULL" if arm!="RS" else "F23",True)
            row[str(G*1000)]=dict(n=len(g),SR=round(sr(g),4),g=round(float(g.mean()),4))
    if row: CAP[pref+"_"+arm]=row
# portfolio capacity where both legs exist
pc={}
for pref in ("FIT","PWR"):
  for G in LAD:
    ks=["XIB_%s%dk_s42"%(pref,G),"RS_%s%dk_s42"%(pref,G)]
    if all(k in D for k in ks):
        r=report(ks,"F23","cap G=%dk"%G); pc[pref+"_"+str(G*1000)]=dict(SR_opt=r["SR_opt"],SR_equalvol=r["SR_equalvol"],CI=r["SR_opt_CI95"])
CAP["XIB+RS_F23"]=pc
RES["capacity"]=CAP
json.dump(RES,open(R3+"/RESULT_R3K.json","w"),indent=1)
print(json.dumps(RES["parity_A0_STD_vs_archived"],indent=1))
print("\n=== LEVELS (post-warm) ===")
for k in sorted(LV):
    r=LV[k]
    print("%-22s FULL n=%4s SR %7s | F23 n=%4s SR %7s | FROZEN SR %7s"%(k,
      r.get("FULL_pw",{}).get("n"),r.get("FULL_pw",{}).get("SR"),
      r.get("F23_pw",{}).get("n"),r.get("F23_pw",{}).get("SR"),r.get("FROZEN_pw",{}).get("SR")))
print("\n=== COST DECOMP F23 pw (bps/anchor/unit gross) ===")
for k in sorted(CD): print("%-22s net %+8.4f pnl %+8.4f carry %+8.4f cost %8.4f turn %.4f cost/turn %.4f"%(
    k,CD[k]["net"],CD[k]["pnl"],CD[k]["carry"],CD[k]["cost"],CD[k]["turnover"],CD[k]["cost_bps_per_unit_turnover"]))
print("\n=== PORTFOLIOS F23 ===")
for k in sorted(P):
    r=P[k]; print("%-24s n=%d SR %s | N_eff %.3f | SR_opt %.4f %s | SR_eqvol %.4f %s"%(
      k,r["n"],r["SR"],r["N_eff"],r["SR_opt"],r["SR_opt_CI95"],r["SR_equalvol"],r["SR_equalvol_CI95"]))
print("\n=== CAPACITY ===")
print(json.dumps(CAP,indent=1))
