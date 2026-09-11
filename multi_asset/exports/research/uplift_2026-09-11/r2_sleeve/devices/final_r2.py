"""Round-2 final readings: paired in-book deltas vs A0, cross-sleeve correlations, honest Bonferroni,
multi-window table. g = net_ex/gross_total, judge_v4 statistic."""
import numpy as np, calendar, os, json
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C=dict((c,i) for i,c in enumerate(COLS))
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
R="/workspace/uplift_2026-09-11/r2_sleeve"; OUT=R+"/out"
FULL=(T(2022,1,31),T(2026,8,31)+1); R1FULL=(T(2022,1,1),T(2026,8,10,20)+1)
FROZ=(T(2025,3,1),T(2026,8,10,20)+1); EXT=(T(2026,8,11),T(2026,8,31)+1)
YR={y:(T(y,1,1),T(y+1,1,1)) for y in [2022,2023,2024,2025,2026]}
def load(p,key="rec"):
    A=np.load(p,allow_pickle=True); Rr=np.asarray(A[key] if key in A.files else A["rec"],float)
    return np.round(Rr[:,0]).astype(np.int64),Rr
def boot(v,d,seed,B=20000,Ks=(1,16,24,33)):
    rng=np.random.default_rng([20260905,seed]); ud,inv=np.unique(d,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(B,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
    o={}
    for K in Ks:
        a=0.05/K; o[K]=(float(np.percentile(mn,100*a/2)),float(np.percentile(mn,100*(1-a/2))))
    return o,float((mn>0).mean())
def sh(v): return v.mean()/v.std(ddof=1)*np.sqrt(2190)
t0,A0=load(R+"/pa/w10_ablation_series_GATEP_A0_dyn_s42.npz","d30_n2_c42_rec")
g0=A0[:,C["net_ex"]]/A0[:,C["gross_total"]]
def G(tag):
    ts,Rr=load(OUT+"/"+tag+".npz"); assert (ts==t0).all(), tag
    return Rr[:,C["net_ex"]]/Rr[:,C["gross_total"]], Rr
mF=(t0>=FULL[0])&(t0<FULL[1]); mR1=(t0>=R1FULL[0])&(t0<R1FULL[1])
mZ=(t0>=FROZ[0])&(t0<FROZ[1]); mE=(t0>=EXT[0])&(t0<EXT[1])
print("windows: FULL n=%d  R1FULL n=%d  FROZEN n=%d  EXT n=%d"%(mF.sum(),mR1.sum(),mZ.sum(),mE.sum()))
print()
print("=== A0 baseline (this device, GATE-P bitwise) ===")
for nm,m in [("FULL 2022-01-31..2026-08-31",mF),("R1FULL 2022-01-01..2026-08-10",mR1),("FROZEN",mZ),("EXT 08-11..08-31",mE)]:
    print("  %-32s %+0.3f  Sharpe %5.2f  (SE %.2f)"%(nm,g0[m].mean(),sh(g0[m]),np.sqrt(2190/m.sum())))
print()
print("=== SURVIVOR: TBF_ema08 -- standalone, all windows ===")
gT,RT=G("TBF_ema08")
for nm,m in [("FULL",mF),("R1FULL",mR1),("FROZEN",mZ),("EXT(n=%d)"%mE.sum(),mE)]:
    print("  %-12s %+0.3f  Sharpe %5.2f"%(nm,gT[m].mean(),sh(gT[m])))
bo,pp=boot(gT[mF],t0[mF]//86400,777)
print("  bootstrap FULL: CI95 [%+0.3f,%+0.3f]  BONF16 [%+0.3f,%+0.3f]  BONF24 [%+0.3f,%+0.3f]  BONF33 [%+0.3f,%+0.3f]  P(>0)=%.4f"%(
  *bo[1],*bo[16],*bo[24],*bo[33],pp))
print("  identity net_ex = pnl_ex - carry_ex - cost_ex:")
for nm,m in [("FULL",mF)]:
    p=(RT[m,C["pnl_ex"]]/RT[m,C["gross_total"]]).mean(); c=(RT[m,C["carry_ex"]]/RT[m,C["gross_total"]]).mean()
    k=(RT[m,C["cost_ex"]]/RT[m,C["gross_total"]]).mean(); n=gT[m].mean()
    print("    pnl %+0.4f  carry %+0.4f  cost %+0.4f  => net %+0.4f (check %+0.4f, resid %.2e)"%(p,c,k,p-c-k,n,abs(p-c-k-n)))
    print("    carry_ex/net_ex = %+0.3f   cost_ex/net_ex = %+0.3f"%(c/n,k/n))
print()
print("=== PLACEBOS for the survivor ===")
for tag in ["TBF_PLA_permfeat","TBF_PLA_orthperm","TBF_PLA_permsm","TBF_PLA_relabel","TBF_ema08_MINUS"]:
    if not os.path.exists(OUT+"/"+tag+".npz"): print("  %-22s MISSING"%tag); continue
    g,Rr=G(tag); print("  %-22s %+0.3f  Sharpe %5.2f  turnover %.4f"%(tag,g[mF].mean(),sh(g[mF]),Rr[mF,C["turnover"]].mean()))
print("  real arm               %+0.3f  Sharpe %5.2f  turnover %.4f"%(gT[mF].mean(),sh(gT[mF]),RT[mF,C["turnover"]].mean()))
print()
print("=== IN-BOOK paired delta vs A0 (deployable form) ===")
print("  %-16s %8s %8s %9s %9s %9s %8s %8s %8s"%("arm","mean","Sharpe","D_full","CI95lo","CI95hi","BONF24lo","D_froz","turn"))
for i,tag in enumerate(["IB_PARITY_rk","IB_TBF25","IB_TBF50","IB_AMLAG50","IB_AM40_TBF20"]):
    g,Rr=G(tag); d=g-g0
    bo2,_=boot(d[mF],t0[mF]//86400,900+i)
    print("  %-16s %+8.3f %8.2f %+9.3f %+9.3f %+9.3f %+8.3f %+8.3f %8.4f"%(
      tag,g[mF].mean(),sh(g[mF]),d[mF].mean(),bo2[1][0],bo2[1][1],bo2[24][0],d[mZ].mean(),Rr[mF,C["turnover"]].mean()))
print()
print("=== CORRELATION MATRIX (FULL cycle, per-anchor g) ===")
names=["A0","TBF_ema08","PC_amihud_lag"]
V=[g0[mF],gT[mF],G("SL_PC_amihud_lag")[0][mF]]
print("        "+" ".join("%12s"%n for n in names))
for i,n in enumerate(names):
    print("%-8s"%n+" ".join("%12.3f"%np.corrcoef(V[i],V[j])[0,1] for j in range(len(names))))
print()
print("=== PORTFOLIO ARITHMETIC (equal weight, each pays its own cost -- a LOWER bound) ===")
for nm,v in [("A0",g0),("A0+AM 50/50",0.5*g0+0.5*G("SL_PC_amihud_lag")[0]),
             ("A0+TBF 50/50",0.5*g0+0.5*gT),
             ("A0+AM+TBF 1/3",(g0+G("SL_PC_amihud_lag")[0]+gT)/3),
             ("IB_AM40_TBF20 alone",G("IB_AM40_TBF20")[0]),
             ("IB_AM40_TBF20 + TBF sleeve 50/50",0.5*G("IB_AM40_TBF20")[0]+0.5*gT)]:
    print("  %-34s FULL %+0.3f Sharpe %5.2f (SE %.2f) | FROZEN %+0.3f Sharpe %5.2f"%(
      nm,v[mF].mean(),sh(v[mF]),np.sqrt(2190/mF.sum()),v[mZ].mean(),sh(v[mZ])))
