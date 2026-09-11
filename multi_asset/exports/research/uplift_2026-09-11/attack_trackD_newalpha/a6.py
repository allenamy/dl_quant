import numpy as np, calendar
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C=dict((c,i) for i,c in enumerate(COLS))
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
HC="/workspace/review_scratch/health_check/dev_v4/probe_artifacts"; TD="/workspace/uplift_2026-09-11/trackD_v4"
def load(p,key="rec"):
    A=np.load(p,allow_pickle=True); R=np.asarray(A[key] if key in A.files else A["rec"],float)
    return np.round(R[:,0]).astype(np.int64),R
FULL=(T(2022,1,1),T(2026,8,10,20)+1); FROZ=(T(2025,3,1),T(2026,8,10,20)+1)
t0,R0=load(HC+"/w10_ablation_series_V4_A0_dyn_s42.npz","d30_n2_c42_rec")
tA,RA=load(TD+"/IB_AM50.npz")
YR={"2022":(T(2022,1,1),T(2023,1,1)),"2023":(T(2023,1,1),T(2024,1,1)),"2024":(T(2024,1,1),T(2025,1,1)),"2025":(T(2025,1,1),T(2026,1,1)),"2026":(T(2026,1,1),T(2026,8,10,20)+1)}
print("=== seat weights w3 (dynamic msharpe): A0 vs IB_AM50 ===")
print("%-8s %26s | %26s"%("win","A0 king/rev24/fund","IB_AM50 king/rev24/fund"))
for w,(lo,hi) in [("full",FULL),("frozen",FROZ)]+list(YR.items()):
    m=(t0>=lo)&(t0<hi)
    a=[R0[m,C["w3_king"]].mean(),R0[m,C["w3_rev24"]].mean(),R0[m,C["w3_fund"]].mean()]
    b=[RA[m,C["w3_king"]].mean(),RA[m,C["w3_rev24"]].mean(),RA[m,C["w3_fund"]].mean()]
    print("%-8s %8.3f %8.3f %8.3f | %8.3f %8.3f %8.3f"%(w,a[0],a[1],a[2],b[0],b[1],b[2]))
print()
print("=== LEG price contributions (leg_king / leg_fund, bps of gross) ===")
for w,(lo,hi) in [("full",FULL),("frozen",FROZ)]:
    m=(t0>=lo)&(t0<hi); gt0=R0[m,C["gross_total"]]; gtA=RA[m,C["gross_total"]]
    print("%-8s A0 king %+0.3f fund %+0.3f | IB king %+0.3f fund %+0.3f"%(w,
      (R0[m,C["leg_king"]]/gt0).mean(),(R0[m,C["leg_fund"]]/gt0).mean(),
      (RA[m,C["leg_king"]]/gtA).mean(),(RA[m,C["leg_fund"]]/gtA).mean()))
print()
print("=== netlong (dollar imbalance) and gross ===")
for w,(lo,hi) in [("full",FULL),("frozen",FROZ)]:
    m=(t0>=lo)&(t0<hi)
    print("%-8s A0 netlong %+0.4f gross %.3f | IB netlong %+0.4f gross %.3f"%(w,
      R0[m,C["netlong"]].mean(),R0[m,C["gross_total"]].mean(),RA[m,C["netlong"]].mean(),RA[m,C["gross_total"]].mean()))
