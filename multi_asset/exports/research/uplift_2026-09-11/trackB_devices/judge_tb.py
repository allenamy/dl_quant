"""TRACK B contrast device. Replicates judge_v4.py's FROZEN definition verbatim:
   g = net_ex/gross_total [bps/anchor/gross]; frozen window 2025-03-01 -> 2026-08-10 20Z;
   paired per anchor; UTC-day block bootstrap 2000; rng = default_rng([20260905, contrast_index]).
VALIDATION FIRST: it must reproduce the published A1-A0 dyn contrast (ci=0) before any new number is printed."""
import numpy as np, json, calendar, time, os, sys, hashlib
COLS = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}; APY=2190
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FROZEN=(T(2025,3,1), T(2026,8,10,20)+1)
YR={"2022":(T(2022,1,1),T(2023,1,1)),"2023":(T(2023,1,1),T(2024,1,1)),"2024":(T(2024,1,1),T(2025,1,1)),
    "2025":(T(2025,1,1),T(2026,1,1)),"2026>0810":(T(2026,1,1),T(2026,8,10,20)+1)}
V4="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_%s_dyn_s%s.npz"
TB="/workspace/uplift_2026-09-11/dev_tb/probe_artifacts/w10_ablation_series_TB_%s_dyn_s%s.npz"
COSTM=float(os.environ.get("REPRICE","1.0"))   # analytic re-pricing: net_ex' = pnl_ex - carry_ex - COSTM*cost_ex
def load(p):
    A=np.load(p,allow_pickle=True); R=A["d30_n2_c42_rec"]
    assert R.shape[1]==len(COLS)
    ts=np.round(R[:,0].astype(np.float64)).astype(np.int64)
    ne=R[:,C["net_ex"]] if COSTM==1.0 else (R[:,C["pnl_ex"]]-R[:,C["carry_ex"]]-COSTM*R[:,C["cost_ex"]])
    g=ne/R[:,C["gross_total"]]
    bad = int((~np.isfinite(g)).sum() + (R[:,C["gross_total"]]<=0).sum())
    return ts,g,R,bad
def boot(v,days,rng):
    ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(2000,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
    return float(np.percentile(mn,2.5)),float(np.percentile(mn,97.5)),float((mn>0).mean())
def contrast(ta,ga,tb,gb,ci,lo=FROZEN[0],hi=FROZEN[1],pct=(2.5,97.5)):
    assert np.array_equal(ta,tb),"axis mismatch"
    m=(ta>=lo)&(ta<hi); d=(ga-gb)[m]
    rng=np.random.default_rng([20260905,ci])
    ud,inv=np.unique(ta[m]//86400,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=d,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(2000,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
    return float(d.mean()),float(np.percentile(mn,pct[0])),float(np.percentile(mn,pct[1])),float((mn>0).mean()),int(m.sum())
def stats(ts,g,R,lo=FROZEN[0],hi=FROZEN[1]):
    m=(ts>=lo)&(ts<hi); v=g[m]
    if m.sum()<3: return None
    c=np.concatenate([[0.0],np.cumsum(v)]); dd=float(np.max(np.maximum.accumulate(c)-c))
    return dict(n=int(m.sum()),g=float(v.mean()),sharpe=float(v.mean()/v.std(ddof=1)*np.sqrt(APY)),
                se_sharpe=float(np.sqrt(APY/m.sum())),maxdd=dd,
                turnover=float(R[m,C["turnover"]].mean()),gross=float(R[m,C["gross_total"]].mean()),
                tov_per_gross=float((R[m,C["turnover"]]/R[m,C["gross_total"]]).mean()),
                cost=float((R[m,C["cost_ex"]]/R[m,C["gross_total"]]).mean()),
                pnl=float((R[m,C["pnl_ex"]]/R[m,C["gross_total"]]).mean()),
                carry=float((R[m,C["carry_ex"]]/R[m,C["gross_total"]]).mean()))
# ---------- VALIDATION: reproduce the published A1-A0 dyn contrast (judge CON index 0) ----------
print("== VALIDATION: judge_v4 published A1-A0 dyn = s42 +0.061 [-0.168,+0.287] ; s2027 +0.048 [-0.171,+0.270] ==")
ok=True
for s,exp in (("42",(0.061,-0.168,0.287)),("2027",(0.048,-0.171,0.270))):
    ta,ga,_,_=load(V4%("A1",s)); tb,gb,_,_=load(V4%("A0",s))
    d,lo_,hi_,p,n=contrast(ta,ga,tb,gb,0)
    good=abs(d-exp[0])<6e-4 and abs(lo_-exp[1])<6e-4 and abs(hi_-exp[2])<6e-4
    ok&=good
    print(f"   s{s}: {d:+.4f} [{lo_:+.4f},{hi_:+.4f}] p={p:.3f} n={n}   expected {exp}   {'MATCH' if good else 'MISMATCH'}")
if not ok: print("VALIDATION FAILED - refusing to print new numbers"); sys.exit(2)
print("   VALIDATION PASS: this device reproduces the frozen judge.\n")
# ---------- arms ----------
ARMS=[a.strip() for a in open("/workspace/uplift_2026-09-11/ARMLIST.txt")]
base={s:load(TB%("BASE",s)) for s in ("42","2027")}
bs={s:stats(*base[s][:3]) for s in ("42","2027")}
print(f"== BASELINE  TB_BASE (= A1_dyn, bitwise) reprice x{COSTM} ==")
for s in ("42","2027"):
    b=bs[s]; print(f"   s{s}: g={b['g']:+.4f} SR={b['sharpe']:.3f} (SE {b['se_sharpe']:.3f}) maxDD={b['maxdd']:.0f}bps tov={b['turnover']:.5f} tov/gross={b['tov_per_gross']:.4f} cost={b['cost']:+.4f} pnl={b['pnl']:+.4f} carry={b['carry']:+.4f}")
print("\n%-10s %-5s %9s %20s %6s | %8s %7s %8s %8s %8s | %s"%("arm","seed","dG","CI95","P>0","g","SR","tov/gr","cost","pnl","yearly dG vs BASE (2022/23/24/25/26)"))
res={}
for ai,nm in enumerate(ARMS):
    if nm=="BASE": continue
    for s in ("42","2027"):
        p=TB%(nm,s)
        if not os.path.exists(p): print(f"{nm:10s} s{s:4s} MISSING"); continue
        ta,ga,Ra,bad=load(p); tb,gb,Rb,_=base[s]
        if bad:
            print(f"{nm:10s} s{s:5s} DEGENERATE: {bad} anchors with gross_total<=0 or non-finite g -> arm excluded"); continue
        d,lo_,hi_,pp,n=contrast(ta,ga,tb,gb,ai)
        st=stats(ta,ga,Ra)
        yr=[]
        for yn,(y0,y1) in YR.items():
            m=(ta>=y0)&(ta<y1)
            yr.append((ga-gb)[m].mean() if m.sum()>10 else float('nan'))
        res[(nm,s)]=dict(d=d,lo=lo_,hi=hi_,p=pp,ncon=n,**st,yr=yr)
        print("%-10s %-5s %+9.4f [%+8.4f,%+8.4f] %6.3f | %+8.4f %7.3f %8.4f %+8.4f %+8.4f | %s"%(
            nm,s,d,lo_,hi_,pp,st["g"],st["sharpe"],st["tov_per_gross"],st["cost"],st["pnl"],
            " ".join(f"{x:+.2f}" for x in yr)))
json.dump({f"{k[0]}_s{k[1]}":v for k,v in res.items()},open(f"/workspace/uplift_2026-09-11/RESULT_trackB_arms_reprice{COSTM}.json","w"),indent=1)
# ---------- gate table ----------
print("\n== GATE TABLE (G1 both seeds point>0 & CI95 lower>0 | G2 |dg|>0.23 | G4 no year worse than -0.23) ==")
print("%-10s %-8s %-8s %-8s %-10s %s"%("arm","G1","G2","G4","VERDICT","note"))
for nm in ARMS:
    if nm=="BASE": continue
    if (nm,"42") not in res or (nm,"2027") not in res: continue
    a,b=res[(nm,"42")],res[(nm,"2027")]
    g1 = (a["d"]>0 and a["lo"]>0 and b["d"]>0 and b["lo"]>0)
    g2 = (abs(a["d"])>0.23 and abs(b["d"])>0.23)
    g4 = all((not np.isnan(x)) and x>-0.23 for x in a["yr"]) and all((not np.isnan(x)) and x>-0.23 for x in b["yr"])
    v = "ADMIT" if (g1 and g2 and g4) else ("NOT A RESULT" if not g2 else "REJECT")
    print("%-10s %-8s %-8s %-8s %-10s %s"%(nm,"PASS" if g1 else "fail","PASS" if g2 else "fail","PASS" if g4 else "fail",v,
        f"dg {a['d']:+.3f}/{b['d']:+.3f}  SR {a['sharpe']:.2f}/{b['sharpe']:.2f}  tov/gross {a['tov_per_gross']:.4f} (base {bs['42']['tov_per_gross']:.4f})"))
