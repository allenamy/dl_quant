"""ROUND 5 supplement: (1) per-year decomposition of XIB's paired delta in each of the four 2x2 cells,
(2) the seat's own path vs the fixed constant, (3) turnover, (4) where the fix/dyn gap lives.
FITTED cost plane. Paired within seed, averaged across the homogeneous draws."""
import numpy as np, json, calendar, time, os, sys
R="/workspace/uplift_2026-09-11/r5_seeds"; A=R+"/arms"
SEEDS=json.loads(sys.argv[1])
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FRZ=(T(2025,3,1),T(2026,8,10,20)+1)
def load(p):
    Z=np.load(p,allow_pickle=True); c=[str(x) for x in Z["cols"]]; ix={k:i for i,k in enumerate(c)}
    M=np.asarray(Z["d30_n2_c42_rec"],float)
    return np.round(M[:,ix["ts"]]).astype(np.int64), M, ix
def boot(v,days,k,B=2000):
    rng=np.random.default_rng([20260905,k]); ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(B,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
    return float(np.percentile(mn,2.5)),float(np.percentile(mn,97.5)),float(mn.std(ddof=1))
OUT={}
print("="*120); print("PER-YEAR paired delta (FITTED cost), mean over %d homogeneous draws; post-warm rows only"%len(SEEDS)); print("="*120)
print("%-4s %-6s %6s %9s %9s %9s | %9s %9s %9s"%("seat","year","n","g(A0)","g(XIB)","delta","SR_A0","SR_XIB","w3_king"))
store={}
for seat in ("dyn","fix"):
    DA=[];DB=[];WK=[]
    for s in SEEDS:
        ta,Ma,ix=load("%s/w10_ablation_series_R5_FIT_XIBLAG50_%s_s%s.npz"%(A,seat,s))
        tb,Mb,_=load("%s/w10_ablation_series_R5_FIT_A0_%s_s%s.npz"%(A,seat,s))
        com,ia,ib=np.intersect1d(ta,tb,return_indices=True)
        DA.append(Ma[ia,ix["net_ex"]]/Ma[ia,ix["gross_total"]]); DB.append(Mb[ib,ix["net_ex"]]/Mb[ib,ix["gross_total"]])
        WK.append(Mb[ib,ix["w3_king"]])
    ga=np.mean(DA,0); gb=np.mean(DB,0); wk=np.mean(WK,0); ts=com
    store[seat]=(ts,ga,gb,wk)
    pw=np.zeros(len(ts),bool); pw[900:]=True; pw&= ts<FRZ[1]
    yr=np.array([time.gmtime(int(t)).tm_year for t in ts])
    for y in sorted(set(yr[pw])):
        m=pw&(yr==y); d=(ga-gb)[m]
        print("%-4s %-6s %6d %+9.4f %+9.4f %+9.4f | %9.3f %9.3f %9.4f"%(seat,y,m.sum(),gb[m].mean(),ga[m].mean(),d.mean(),
            gb[m].mean()/gb[m].std(ddof=1)*np.sqrt(2190), ga[m].mean()/ga[m].std(ddof=1)*np.sqrt(2190), wk[m].mean()))
        OUT["year|%s|%s"%(seat,y)]={"n":int(m.sum()),"gA0":float(gb[m].mean()),"gARM":float(ga[m].mean()),"delta":float(d.mean()),"w3_king":float(wk[m].mean())}
    m=pw; d=(ga-gb)[m]
    print("%-4s %-6s %6d %+9.4f %+9.4f %+9.4f | %9.3f %9.3f %9.4f"%(seat,"ALL",m.sum(),gb[m].mean(),ga[m].mean(),d.mean(),
        gb[m].mean()/gb[m].std(ddof=1)*np.sqrt(2190), ga[m].mean()/ga[m].std(ddof=1)*np.sqrt(2190), wk[m].mean()))
# --- where the fix/dyn gap lives: drop 2023 and recheck the fix full-cycle cell
print("\n"+"="*120); print("ROBUSTNESS: the FIXED-seat full-cycle pass without 2023 (the year A0 is worst)"); print("="*120)
for seat in ("dyn","fix"):
    ts,ga,gb,wk=store[seat]
    pw=np.zeros(len(ts),bool); pw[900:]=True; pw&= ts<FRZ[1]
    yr=np.array([time.gmtime(int(t)).tm_year for t in ts])
    for lbl,m in (("post-warm ALL",pw),("post-warm ex-2023",pw&(yr!=2023)),("2024-on",pw&(yr>=2024)),("FROZEN",(ts>=FRZ[0])&(ts<FRZ[1]))):
        d=(ga-gb)[m]; days=ts[m]//86400; lo,hi,se=boot(d,days,0)
        print("%-4s %-18s n=%5d delta %+8.4f CI95 [%+8.4f,%+8.4f] t=%5.2f  clears=%s"%(seat,lbl,m.sum(),d.mean(),lo,hi,d.mean()/se,lo>0))
        OUT["rob|%s|%s"%(seat,lbl)]={"n":int(m.sum()),"delta":float(d.mean()),"ci95":[lo,hi],"t":float(d.mean()/se),"clears":bool(lo>0)}
# --- turnover
print("\n"+"="*120); print("TURNOVER (mean per anchor, post-warm)"); print("="*120)
for seat in ("dyn","fix"):
    for arm in ("A0","XIBLAG50"):
        tv=[]
        for s in SEEDS:
            t,M,ix=load("%s/w10_ablation_series_R5_FIT_%s_%s_s%s.npz"%(A,arm,seat,s))
            pw=np.zeros(len(t),bool); pw[900:]=True; pw&= t<FRZ[1]
            tv.append(M[pw,ix["turnover"]].mean())
        print("  %-4s %-10s turnover %.5f"%(seat,arm,np.mean(tv)))
        OUT["turnover|%s|%s"%(seat,arm)]=float(np.mean(tv))
json.dump(OUT,open(R+"/receipts/SUPP_R5.json","w"),indent=1)
print("SUPP_DONE")
