"""ROUND 5 / ANGLE 3 JUDGE.
Re-derives the pre-registered 6-seed count rule (PREREG_r3_instrument3_xib_seeds sha 18729ce3...) on a
HOMOGENEOUS set of in-service-object (V2=1) draws, at BOTH cost planes, and prints the 2x2
{frozen window, full-cycle post-warm} x {fixed seat, dynamic seat}.

Statistic (PREREG section 4): g = net_ex/gross_total bps/anchor/unit gross; paired per anchor at the SAME seed and
SAME seat; UTC-day block bootstrap 2000, rng default_rng([20260905,k]), k in {0,9}; cell PASSES iff CI95 lower
bound > 0 under BOTH k.  Count rule (section 5): >=5/6 ADMIT, 3-4 UNDECIDED, <=2 REJECT; both seats to promote.
E-0911-A: full-cycle readings DROP the first 900 device anchors.
"""
import numpy as np, json, calendar, os, sys
R="/workspace/uplift_2026-09-11/r5_seeds"; A=R+"/arms"
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FRZ=(T(2025,3,1),T(2026,8,10,20)+1)
import sys as _s; SEEDS=json.loads(_s.argv[1]) if len(_s.argv)>1 else ["42","2027","7","101","1234","31337"]
APY=2190
def load(path,key="d30_n2_c42_rec"):
    Z=np.load(path,allow_pickle=True); cols=[str(c) for c in Z["cols"]]; ix={c:i for i,c in enumerate(cols)}
    Rr=np.asarray(Z[key],float); ts=np.round(Rr[:,ix["ts"]]).astype(np.int64)
    return ts, Rr[:,ix["net_ex"]]/Rr[:,ix["gross_total"]]
def boot(v,days,k,B=2000):
    rng=np.random.default_rng([20260905,k]); ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(B,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
    return float(np.percentile(mn,2.5)),float(np.percentile(mn,97.5)),float((mn>0).mean()),float(mn.std(ddof=1))
def sr(x): return float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(APY))
def cells(cb,seat,seed):
    pa="%s/w10_ablation_series_R5_%s_XIBLAG50_%s_s%s.npz"%(A,cb,seat,seed)
    pb="%s/w10_ablation_series_R5_%s_A0_%s_s%s.npz"%(A,cb,seat,seed)
    ta,ga=load(pa); tb,gb=load(pb)
    com,ia,ib=np.intersect1d(ta,tb,return_indices=True)
    return com,ga[ia],gb[ib]
# windows are defined on the COMMON anchor axis; post-warm = drop first 900 device anchors
def masks(com):
    warm=np.zeros(len(com),bool); warm[:900]=True
    frz=(com>=FRZ[0])&(com<FRZ[1])
    full=(~warm)&(com<FRZ[1])
    return {"FROZEN":frz,"FULL_POSTWARM":full}, warm
OUT={"seeds":SEEDS,"object":"V2=1 in-service composed chain","cost_planes":["STD","FIT"]}
for cb in ("STD","FIT"):
    print("="*132); print("COST PLANE = %s   (%s)"%(cb,{"STD":"costb_fee_steady.json  -- the plane the ORIGINAL 6-seed rule ran at",
        "FIT":"r3k/costb_PWR_G230k.json sha 295b4e7b462373e4, K=0.17 -- the FITTED model"}[cb])); print("="*132)
    for win in ("FROZEN","FULL_POSTWARM"):
        print("\n--- window %s ---"%win)
        print("%-6s %-4s %6s %9s %9s %8s %8s | %9s %-21s %6s | %9s %-21s %6s | %5s"%(
            "seed","seat","n","g(A0)","g(XIB)","SR_A0","SR_XIB","delta","CI95(k=0)","P>0","delta","CI95(k=9)","P>0","PASS"))
        for seat in ("dyn","fix"):
            for s in SEEDS:
                com,ga,gb=cells(cb,seat,s); MK,_=masks(com); m=MK[win]
                d=(ga-gb)[m]; days=com[m]//86400
                c0=boot(d,days,0); c9=boot(d,days,9); pas=bool(c0[0]>0 and c9[0]>0)
                OUT["%s|%s|%s|%s"%(cb,win,seat,s)]={"n":int(m.sum()),"gA0":float(gb[m].mean()),"gARM":float(ga[m].mean()),
                    "sr_A0":sr(gb[m]),"sr_ARM":sr(ga[m]),"delta":float(d.mean()),
                    "ci95_k0":[c0[0],c0[1]],"p_k0":c0[2],"boot_se_k0":c0[3],"ci95_k9":[c9[0],c9[1]],"p_k9":c9[2],"PASS":pas}
                print("%-6s %-4s %6d %+9.4f %+9.4f %8.3f %8.3f | %+9.4f [%+7.4f,%+7.4f] %6.3f | %+9.4f [%+7.4f,%+7.4f] %6.3f | %5s"%(
                    s,seat,m.sum(),gb[m].mean(),ga[m].mean(),sr(gb[m]),sr(ga[m]),d.mean(),c0[0],c0[1],c0[2],d.mean(),c9[0],c9[1],c9[2],"YES" if pas else "no"))
        print("  COUNT RULE (>=5 ADMIT / 3-4 UNDECIDED / <=2 REJECT):")
        for seat in ("dyn","fix"):
            c=sum(1 for s in SEEDS if OUT["%s|%s|%s|%s"%(cb,win,seat,s)]["PASS"])
            v="ADMIT" if c>=5 else ("REJECT" if c<=2 else "UNDECIDED")
            OUT["COUNT|%s|%s|%s"%(cb,win,seat)]={"pass":c,"n":len(SEEDS),"verdict":v}
            print("    seat %-4s  PASS %d/%d -> %s"%(seat,c,len(SEEDS),v))
# ---------------- t-ceiling ----------------
print("\n"+"="*132); print("t-CEILING  (model SE(N)=SE1*sqrt(rho+(1-rho)/N); ceiling t = mu/(SE1*sqrt(rho)))"); print("="*132)
print("%-5s %-14s %-4s %9s %9s %8s %8s %8s %8s %8s %10s"%("cost","window","seat","mu","sd_seed","SE1","rho_bar","t(N=1)","t(N=6)","t_ceil","emp_t(N=6)"))
for cb in ("STD","FIT"):
    for win in ("FROZEN","FULL_POSTWARM"):
        for seat in ("dyn","fix"):
            DS=[]; mus=[]; se1=[]
            for s in SEEDS:
                com,ga,gb=cells(cb,seat,s); MK,_=masks(com); m=MK[win]
                d=(ga-gb)[m]; DS.append(d); mus.append(d.mean()); days=com[m]//86400
                se1.append(boot(d,days,0)[3])
            DS=np.array(DS); mus=np.array(mus); SE1=float(np.mean(se1))
            C=np.corrcoef(DS); iu=np.triu_indices(len(SEEDS),1); rho=float(C[iu].mean())
            mu=float(mus.mean()); dbar=DS.mean(0)
            emp=boot(dbar,days,0); emp_t=mu/emp[3]
            mod=lambda N: mu/(SE1*np.sqrt(rho+(1-rho)/N))
            OUT["TCEIL|%s|%s|%s"%(cb,win,seat)]={"mu":mu,"sd_seed":float(mus.std(ddof=1)),"SE1":SE1,"rho_bar":rho,
                "t_N1":float(mu/SE1),"t_N6_model":float(mod(6)),"t_ceiling":float(mu/(SE1*np.sqrt(rho))),
                "t_N6_empirical":float(emp_t),"emp_SE_N6":emp[3],"model_SE_N6":float(SE1*np.sqrt(rho+(1-rho)/6)),
                "ci95_meanseries_k0":[emp[0],emp[1]]}
            print("%-5s %-14s %-4s %+9.4f %9.4f %8.4f %8.4f %8.2f %8.2f %8.2f %10.2f"%(
                cb,win,seat,mu,mus.std(ddof=1),SE1,rho,mu/SE1,mod(6),mu/(SE1*np.sqrt(rho)),emp_t))
# ---------------- 2x2 on the across-seed mean delta series ----------------
print("\n"+"="*132); print("THE 2x2  --  XIB_LAG50 paired delta, across-seed mean series (6 homogeneous draws), FITTED cost"); print("="*132)
print("%-14s %-4s %7s %+10s %-23s %-23s %8s"%("window","seat","n","delta","CI95(k=0)","CI95(k=9)","t"))
for win in ("FROZEN","FULL_POSTWARM"):
    for seat in ("fix","dyn"):
        DS=[]
        for s in SEEDS:
            com,ga,gb=cells("FIT",seat,s); MK,_=masks(com); m=MK[win]; DS.append((ga-gb)[m])
        days=com[m]//86400; dbar=np.array(DS).mean(0)
        c0=boot(dbar,days,0); c9=boot(dbar,days,9)
        OUT["2x2|%s|%s"%(win,seat)]={"n":int(m.sum()),"delta":float(dbar.mean()),"ci95_k0":[c0[0],c0[1]],
            "ci95_k9":[c9[0],c9[1]],"t":float(dbar.mean()/c0[3]),"lower_clears_zero":bool(c0[0]>0 and c9[0]>0)}
        print("%-14s %-4s %7d %+10.4f [%+8.4f,%+8.4f] [%+8.4f,%+8.4f] %8.2f"%(
            win,seat,m.sum(),dbar.mean(),c0[0],c0[1],c9[0],c9[1],dbar.mean()/c0[3]))
json.dump(OUT,open(R+"/receipts/JUDGE_R5_%d.json"%len(SEEDS),"w"),indent=1,default=str)
print("\nJUDGE_DONE")
