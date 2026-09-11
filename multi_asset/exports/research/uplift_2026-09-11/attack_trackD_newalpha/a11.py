import numpy as np, calendar
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C=dict((c,i) for i,c in enumerate(COLS))
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
AT="/workspace/uplift_2026-09-11/attack_trackD_newalpha/out"; TD="/workspace/uplift_2026-09-11/trackD_v4"
HC="/workspace/review_scratch/health_check/dev_v4/probe_artifacts"
def load(p,key="rec"):
    A=np.load(p,allow_pickle=True); R=np.asarray(A[key] if key in A.files else A["rec"],float)
    return np.round(R[:,0]).astype(np.int64),R
FULL=(T(2022,1,1),T(2026,8,10,20)+1); FROZ=(T(2025,3,1),T(2026,8,10,20)+1)
def boot(v,d,seed,B=20000,K=68):
    rng=np.random.default_rng([20260905,seed]); ud,inv=np.unique(d,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(B,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
    return np.percentile(mn,2.5),np.percentile(mn,97.5),np.percentile(mn,100*(0.05/K)/2)
print("=== ORTH_LIQ standalone sleeve under the two cost regimes ===")
for nm,p in [("theirs (STD)",TD+"/SL_ORTH_f_amihud_24h__p.npz"),("mine (STD)",AT+"/XSL_ORTH_STD.npz"),("mine (ILLQ 2.5x)",AT+"/XSL_ORTH_ILLQ.npz")]:
    ts,R=load(p); g=R[:,C["net_ex"]]/R[:,C["gross_total"]]
    m=(ts>=FULL[0])&(ts<FULL[1]); mf=(ts>=FROZ[0])&(ts<FROZ[1])
    ci=boot(g[m],ts[m]//86400,23)
    print("  %-18s full %+0.3f Sharpe %.2f CI95[%+0.3f,%+0.3f] BONF68lo %+0.3f | frozen %+0.3f  cost %.3f"%(
      nm,g[m].mean(),g[m].mean()/g[m].std(ddof=1)*np.sqrt(2190),ci[0],ci[1],ci[2],g[mf].mean(),
      (R[m,C["cost_ex"]]/R[m,C["gross_total"]]).mean()))
print()
print("=== THE PORTFOLIO CLAIM: the 3-book / 4-book Sharpe uses 2 arms that FAILED the author's own Gate S ===")
t0,R0=load(HC+"/w10_ablation_series_V4_A0_dyn_s42.npz","d30_n2_c42_rec"); g0=R0[:,C["net_ex"]]/R0[:,C["gross_total"]]
def gg(p):
    ts,R=load(p); out=np.full(len(t0),np.nan)
    _,ia,ib=np.intersect1d(t0,ts,return_indices=True); out[ia]=R[ib,C["net_ex"]]/R[ib,C["gross_total"]]; return out
L=gg(TD+"/SL_ORTH_f_amihud_24h__p.npz"); S=gg(TD+"/SL_ORTH_D_SURP__m.npz"); B=gg(TD+"/SL_f_tbf_24h__p.npz")
m=(t0>=FULL[0])&(t0<FULL[1]); mf=(t0>=FROZ[0])&(t0<FROZ[1])
def sh(v): return v.mean()/v.std(ddof=1)*np.sqrt(2190)
for nm,v in [("A0 alone",g0),("A0/ORTH_LIQ 50-50",0.5*g0+0.5*L),
             ("3-book (LIQ+SURP)",(g0+L+S)/3),("4-book (+TBF)",(g0+L+S+B)/4),
             ("A0 + ONLY the admitted sleeve at 1/3",(g0*2+L)/3)]:
    print("  %-38s full %+0.3f Sharpe %.2f (SE %.2f) | frozen %+0.3f Sharpe %.2f (SE %.2f)"%(
        nm,v[m].mean(),sh(v[m]),np.sqrt(2190/m.sum()),v[mf].mean(),sh(v[mf]),np.sqrt(2190/mf.sum())))
print()
print("  note: 3-book and 4-book include ORTH_SURP (Gate S6+S7 FAIL) and TBF (S2+S6+S7 FAIL).")
print("  ORTH_SURP carry/net = %.0f%% full, %.0f%% frozen"%(100*0.597/0.748,100*1.018/0.964))
