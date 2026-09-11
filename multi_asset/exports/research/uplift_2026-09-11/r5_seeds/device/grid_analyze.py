"""SUPPLEMENTARY: seat-constant grid. GATE first (k=0.21 must equal the pinned-device artifact BITWISE),
then XIB's paired delta and CI as a function of the FROZEN king weight, in both windows, FITTED cost."""
import numpy as np, json, calendar, os, sys
R="/workspace/uplift_2026-09-11/r5_seeds"; G=R+"/grid"; A=R+"/arms"
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FRZ=(T(2025,3,1),T(2026,8,10,20)+1)
KS=[0.0,0.10,0.21,0.30,0.3568,0.4636,0.5338,0.70,1.0]
def tag(k): return ("%g"%k).replace(".","p")
def load(p):
    Z=np.load(p,allow_pickle=True); c=[str(x) for x in Z["cols"]]; ix={k:i for i,k in enumerate(c)}
    M=np.asarray(Z["d30_n2_c42_rec"],float)
    return np.round(M[:,ix["ts"]]).astype(np.int64), M[:,ix["net_ex"]]/M[:,ix["gross_total"]], M[:,ix["turnover"]]
def boot(v,days,k,B=2000):
    rng=np.random.default_rng([20260905,k]); ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(B,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
    return float(np.percentile(mn,2.5)),float(np.percentile(mn,97.5)),float(mn.std(ddof=1))
# ---- GATE ----
GA={"device":"r5_seeds/w10_sleeve_seatgrid.py","note":"SUPPLEMENTARY; only the W3FIX whitelist widened"}
ok=True
for arm in ("A0","XIBLAG50"):
    for s in ("42","2027"):
        pg="%s/w10_ablation_series_G_%s_k%s_s%s_FIT.npz"%(G,arm,tag(0.21),s)
        pp="%s/w10_ablation_series_R5_FIT_%s_fix_s%s.npz"%(A,arm,s)
        a=np.load(pg,allow_pickle=True); b=np.load(pp,allow_pickle=True)
        r={}
        for k in ("d30_n2_c42_rec","d30_n2_c42_W"):
            x=np.asarray(a[k],float); y=np.asarray(b[k],float)
            nx=np.isnan(x); ny=np.isnan(y)
            r[k]=bool(x.shape==y.shape and np.array_equal(nx,ny) and np.array_equal(x[~nx],y[~ny]))
        GA["%s_s%s"%(arm,s)]=r; ok &= all(r.values())
GA["PASS"]=bool(ok)
print("SEATGRID GATE (k=0.21 vs pinned device, bitwise):",json.dumps(GA))
if not ok: sys.exit(3)
print()
print("="*136)
print("SUPPLEMENTARY -- XIB_LAG50 paired delta vs the FROZEN king weight (fund = 1-king), FITTED cost, mean of s42/s2027")
print("  reference points: 0.21 = the pinned fixed seat (live masked seat circa 2026-09-02/04)")
print("                    0.3568 = the LIVE masked seat measured today 2026-09-11 from wide_shadow state")
print("                    0.4636 = the DYNAMIC seat's own post-warm mean; 0.5338 = its frozen-window mean")
print("="*136)
OUT={"gate":GA}
for win,wn in (("FROZEN",0),("FULL_POSTWARM",1)):
    print("\n--- %s ---"%win)
    print("%9s %8s %9s %9s %9s %-23s %7s %8s %9s %9s"%("king_w","n","g(A0)","g(XIB)","delta","CI95(k=0)","t","clears","SR_A0","SR_XIB"))
    for k in KS:
        DD=[];GA_=[];GB_=[]
        for s in ("42","2027"):
            ta,ga,_=load("%s/w10_ablation_series_G_XIBLAG50_k%s_s%s_FIT.npz"%(G,tag(k),s))
            tb,gb,_=load("%s/w10_ablation_series_G_A0_k%s_s%s_FIT.npz"%(G,tag(k),s))
            com,ia,ib=np.intersect1d(ta,tb,return_indices=True)
            GA_.append(ga[ia]);GB_.append(gb[ib]); ts=com
        ga=np.mean(GA_,0); gb=np.mean(GB_,0)
        warm=np.zeros(len(ts),bool); warm[:900]=True
        m=((ts>=FRZ[0])&(ts<FRZ[1])) if win=="FROZEN" else ((~warm)&(ts<FRZ[1]))
        d=(ga-gb)[m]; days=ts[m]//86400; lo,hi,se=boot(d,days,0); lo9,hi9,_=boot(d,days,9)
        srA=gb[m].mean()/gb[m].std(ddof=1)*np.sqrt(2190); srX=ga[m].mean()/ga[m].std(ddof=1)*np.sqrt(2190)
        cl=bool(lo>0 and lo9>0)
        print("%9.4f %8d %+9.4f %+9.4f %+9.4f [%+8.4f,%+8.4f] %7.2f %8s %+9.3f %+9.3f"%(k,m.sum(),gb[m].mean(),ga[m].mean(),d.mean(),lo,hi,d.mean()/se,cl,srA,srX))
        OUT["%s|k%g"%(win,k)]={"n":int(m.sum()),"gA0":float(gb[m].mean()),"gARM":float(ga[m].mean()),"delta":float(d.mean()),
            "ci95_k0":[lo,hi],"ci95_k9":[lo9,hi9],"t":float(d.mean()/se),"clears_both_k":cl,"sr_A0":float(srA),"sr_ARM":float(srX)}
json.dump(OUT,open(R+"/receipts/SEATGRID.json","w"),indent=1)
print("\nGRID_ANALYSIS_DONE")
