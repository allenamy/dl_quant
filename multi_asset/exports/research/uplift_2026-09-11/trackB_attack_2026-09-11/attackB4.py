"""ATTACK 4: the H5/robustness falsifier the candidate specified but never ran.
Null-tests first: AT_FIXBASE must == V4_A1_fix ; AT_A0BASE must == V4_A0_dyn (bitwise)."""
import numpy as np, calendar, os
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FR=(T(2025,3,1),T(2026,8,10,20)+1)
P_TB="/workspace/uplift_2026-09-11/dev_tb/probe_artifacts/w10_ablation_series_%s.npz"
P_V4="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_%s.npz"
print("=== NULL TESTS for MY runs ===")
for mine,ref in (("AT_FIXBASE_dyn_s42","A1_fix_s42"),("AT_FIXBASE_dyn_s2027","A1_fix_s2027"),
                 ("AT_A0BASE_dyn_s42","A0_dyn_s42"),("AT_A0BASE_dyn_s2027","A0_dyn_s2027")):
    A=np.load(P_TB%mine,allow_pickle=True); B=np.load(P_V4%ref,allow_pickle=True)
    ok=all(np.array_equal(np.asarray(A[k]),np.asarray(B[k])) for k in ("d30_n2_c42_rec","d30_n2_c42_W","S0_rec","legs_king","legs_fund"))
    print(f"  {mine:24s} vs V4_{ref:14s} bitwise_equal={ok}")
def ld(tag):
    R=np.load(P_TB%tag,allow_pickle=True)["d30_n2_c42_rec"]
    ts=np.round(R[:,0].astype(np.float64)).astype(np.int64); return ts,R
def boot(ts,d,ci):
    m=(ts>=FR[0])&(ts<FR[1]); dd=d[m]
    rng=np.random.default_rng([20260905,ci])
    ud,inv=np.unique(ts[m]//86400,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=dd,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(2000,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
    return dd.mean(),np.percentile(mn,2.5),np.percentile(mn,97.5),(mn>0).mean(),m.sum()
print("\n=== FALSIFIER: does BAND5e-4 / EMA0.05 survive a SEAT change (fixed seat) and a KING change (v3 king, A0)? ===")
print("%-12s %-5s %9s %20s %6s | %8s %7s %8s %9s"%("contrast","seed","dG","CI95","P>0","g_arm","SR_arm","gross","absnet"))
for base,arms,lab in (("AT_FIXBASE",("AT_FIXB5e4","AT_FIXE005"),"FIXSEAT"),
                      ("AT_A0BASE",("AT_A0B5e4","AT_A0E005"),"A0king"),
                      ("TB_BASE",("TB_BAND5e4","TB_EMA005"),"DYN/v4(ref)")):
    for a in arms:
        for s in ("42","2027"):
            tb,Rb=ld(f"{base}_dyn_s{s}"); ta,Ra=ld(f"{a}_dyn_s{s}")
            assert np.array_equal(ta,tb)
            gb=Rb[:,C["net_ex"]]/Rb[:,C["gross_total"]]; ga=Ra[:,C["net_ex"]]/Ra[:,C["gross_total"]]
            r=boot(ta,ga-gb,11)
            m=(ta>=FR[0])&(ta<FR[1])
            sr=ga[m].mean()/ga[m].std(ddof=1)*np.sqrt(2190)
            print("%-12s %-5s %+9.4f [%+8.4f,%+8.4f] %6.3f | %+8.4f %7.3f %8.4f %+9.4f   [%s]"%(
                a.replace("AT_","").replace("TB_",""),s,r[0],r[1],r[2],r[3],ga[m].mean(),sr,Ra[m,C["gross_total"]].mean(),Ra[m,C["net_ex"]].mean(),lab))
    # baselines
    for s in ("42","2027"):
        tb,Rb=ld(f"{base}_dyn_s{s}"); m=(tb>=FR[0])&(tb<FR[1]); gb=(Rb[:,C["net_ex"]]/Rb[:,C["gross_total"]])
        print("   base %-8s s%-5s g=%+7.4f SR=%6.3f gross=%.4f absnet=%+7.4f"%(base,s,gb[m].mean(),gb[m].mean()/gb[m].std(ddof=1)*np.sqrt(2190),Rb[m,C["gross_total"]].mean(),Rb[m,C["net_ex"]].mean()))
