import numpy as np, calendar, os
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C=dict((c,i) for i,c in enumerate(COLS))
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
HC="/workspace/review_scratch/health_check/dev_v4/probe_artifacts"; TD="/workspace/uplift_2026-09-11/trackD_v4"
AT="/workspace/uplift_2026-09-11/attack_trackD_newalpha/out"
def load(p,key="rec"):
    A=np.load(p,allow_pickle=True); R=np.asarray(A[key] if key in A.files else A["rec"],float)
    return np.round(R[:,0]).astype(np.int64),R
FULL=(T(2022,1,1),T(2026,8,10,20)+1); FROZ=(T(2025,3,1),T(2026,8,10,20)+1)
def boot(v,d,seed,B=20000,K=68):
    rng=np.random.default_rng([20260905,seed]); ud,inv=np.unique(d,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(B,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
    return np.percentile(mn,2.5),np.percentile(mn,97.5),np.percentile(mn,100*(0.05/K)/2),(mn>0).mean()
print("=== COST STRESS: device tiers charge the LEAST liquid tier LESS (2.013) than the most (2.202) ===")
print("regimes: STD=live-calibrated (2.202/2.003/2.013)  FLAT=all 2.202  ILLQ=2.202/3.303/5.505 bps/unit")
print()
print("%-8s %-12s %8s %8s %8s %8s %8s"%("regime","arm","full","frozen","cost_full","turn","D_vs_par"))
for reg,par,am in [("STD",AT+"/XIB_PARITY.npz",AT+"/XIB_AM50_STD.npz"),
                   ("FLAT",AT+"/XIB_PAR_FLAT.npz",AT+"/XIB_AM50_FLAT.npz"),
                   ("ILLQ",AT+"/XIB_PAR_ILLQ.npz",AT+"/XIB_AM50_ILLQ.npz")]:
    tp,Rp=load(par); ta,Ra=load(am)
    gp=Rp[:,C["net_ex"]]/Rp[:,C["gross_total"]]; ga=Ra[:,C["net_ex"]]/Ra[:,C["gross_total"]]
    m=(tp>=FULL[0])&(tp<FULL[1]); mf=(tp>=FROZ[0])&(tp<FROZ[1])
    for nm,g,R in [("A0-shaped",gp,Rp),("IB_AM50",ga,Ra)]:
        cf=(R[m,C["cost_ex"]]/R[m,C["gross_total"]]).mean()
        print("%-8s %-12s %+8.3f %+8.3f %8.3f %8.4f"%(reg,nm,g[m].mean(),g[mf].mean(),cf,R[m,C["turnover"]].mean()))
    d=ga-gp
    ci=boot(d[m],tp[m]//86400,3); cif=boot(d[mf],tp[mf]//86400,4)
    print("   ->  D full %+0.3f CI95[%+0.3f,%+0.3f] BONF68lo %+0.3f | D frozen %+0.3f CI95[%+0.3f,%+0.3f]"%(
        d[m].mean(),ci[0],ci[1],ci[2],d[mf].mean(),cif[0],cif[1]))
print()
print("=== S7-FIXED (lagged Amihud) in-book arm, BOTH A0 seeds, frozen window = the PRE-REGISTERED PRIMARY ===")
for seed in ["s42","s2027"]:
    t0,R0=load(HC+"/w10_ablation_series_V4_A0_dyn_"+seed+".npz","d30_n2_c42_rec")
    g0=R0[:,C["net_ex"]]/R0[:,C["gross_total"]]
    for nm,p in [("IB_AM50",TD+"/IB_AM50.npz"),("XIB_LAG50",AT+"/XIB_LAG50.npz"),("XIB_D60",AT+"/XIB_D60.npz")]:
        ts,R=load(p); g=R[:,C["net_ex"]]/R[:,C["gross_total"]]
        d=g-g0
        for wn,(lo,hi) in [("full",FULL),("frozen",FROZ)]:
            m=(ts>=lo)&(ts<hi)
            ci=boot(d[m],ts[m]//86400,17)
            print("  %-6s %-10s %-7s D %+0.3f  CI95[%+0.3f,%+0.3f]  BONF68lo %+0.3f  P>0 %.4f"%(seed,nm,wn,d[m].mean(),ci[0],ci[1],ci[2],ci[3]))
