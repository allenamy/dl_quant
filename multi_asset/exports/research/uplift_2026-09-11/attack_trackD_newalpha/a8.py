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
YR={"2022":(T(2022,1,1),T(2023,1,1)),"2023":(T(2023,1,1),T(2024,1,1)),"2024":(T(2024,1,1),T(2025,1,1)),"2025":(T(2025,1,1),T(2026,1,1)),"2026":(T(2026,1,1),T(2026,8,10,20)+1)}
def boot(v,d,seed,B=20000,K=68):
    rng=np.random.default_rng([20260905,seed]); ud,inv=np.unique(d,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(B,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
    a=0.05/K
    return np.percentile(mn,2.5),np.percentile(mn,97.5),np.percentile(mn,100*a/2),(mn>0).mean()
t0,R0=load(HC+"/w10_ablation_series_V4_A0_dyn_s42.npz","d30_n2_c42_rec")
g0=R0[:,C["net_ex"]]/R0[:,C["gross_total"]]
tP,RP=load(AT+"/XIB_PARITY.npz"); gP=RP[:,C["net_ex"]]/RP[:,C["gross_total"]]
m=(t0>=FULL[0])&(t0<FULL[1])
print("MY PARITY RECEIPT vs A0: mean|dg| %.4f  max|dg| %.3f  mean dg %+.5f  n=%d"%(np.abs(gP-g0).mean(),np.abs(gP-g0).max(),(gP-g0).mean(),len(t0)))
print()
print("=== PAIRED vs A0 (s42), full cycle + frozen + 2023 ===")
print("%-16s %8s %8s %8s %8s %8s %8s"%("arm","D_full","CI95lo","BONF68lo","P>0","D_froz","D_2023"))
arms=[("IB_AM50(theirs)",TD+"/IB_AM50.npz"),("XIB_AM50_STD",AT+"/XIB_AM50_STD.npz"),
      ("XIB_PERM50",AT+"/XIB_PERM50.npz"),("XIB_LAG50",AT+"/XIB_LAG50.npz"),
      ("XIB_RANGE50",AT+"/XIB_RANGE50.npz"),("XIB_VOLQ50",AT+"/XIB_VOLQ50.npz")]
for w in [10,20,30,40,60,75,90]:
    arms.append(("XIB_D%02d"%w,AT+"/XIB_D%02d.npz"%w))
arms.append(("IB_AM25(theirs)",TD+"/IB_AM25.npz"))
for nm,p in arms:
    if not os.path.exists(p): print(nm,"MISSING"); continue
    ts,R=load(p); g=R[:,C["net_ex"]]/R[:,C["gross_total"]]
    assert (ts==t0).all()
    d=g-g0
    ci_lo,ci_hi,bf_lo,pp=boot(d[m],t0[m]//86400,7)
    mf=(t0>=FROZ[0])&(t0<FROZ[1]); m23=(t0>=YR["2023"][0])&(t0<YR["2023"][1])
    print("%-16s %+8.3f %+8.3f %+8.3f %8.4f %+8.3f %+8.3f"%(nm,d[m].mean(),ci_lo,bf_lo,pp,d[mf].mean(),d[m23].mean()))
print()
print("=== STANDALONE sleeves: placebo orth + lag fix (full cycle) ===")
print("%-22s %8s %7s %8s %8s %8s %8s %8s %8s"%("arm","mean","sharpe","CI95lo","2022","2023","2024","2025","2026"))
sl=[("SL_ORTH_amihud(theirs)",TD+"/SL_ORTH_f_amihud_24h__p.npz"),
    ("XSL_ORTHPERM(placebo)",AT+"/XSL_ORTHPERM.npz"),
    ("XSL_ORTHLAG(S7 fix)",AT+"/XSL_ORTHLAG.npz"),
    ("XSL_AMLAG(raw,S7 fix)",AT+"/XSL_AMLAG.npz"),
    ("SL_raw_amihud(theirs)",TD+"/SL_f_amihud_24h__p.npz")]
for nm,p in sl:
    ts,R=load(p); g=R[:,C["net_ex"]]/R[:,C["gross_total"]]
    mm=(ts>=FULL[0])&(ts<FULL[1])
    ci_lo,ci_hi,bf_lo,pp=boot(g[mm],ts[mm]//86400,11)
    row="%-22s %+8.3f %7.2f %+8.3f"%(nm,g[mm].mean(),g[mm].mean()/g[mm].std(ddof=1)*np.sqrt(2190),ci_lo)
    for y,(lo,hi) in YR.items():
        k=(ts>=lo)&(ts<hi); row+=" %+8.3f"%g[k].mean()
    print(row)
