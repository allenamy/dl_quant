import numpy as np, calendar
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C=dict((c,i) for i,c in enumerate(COLS))
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
HC="/workspace/review_scratch/health_check/dev_v4/probe_artifacts"; TD="/workspace/uplift_2026-09-11/trackD_v4"
def load(p,key="rec"):
    A=np.load(p,allow_pickle=True); R=np.asarray(A[key] if key in A.files else A["rec"],float)
    return np.round(R[:,0]).astype(np.int64),R
MT=np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz",allow_pickle=True)
E=MT["E_ts"].astype(np.int64); mem=MT["members"]; y4=MT["y4"]
MKT={}
for i in range(len(E)):
    m=mem[i]; v=y4[i,m]; v=v[np.isfinite(v)]
    if len(v)>=20: MKT[int(E[i])]=float(np.mean(v))
t0,R0=load(HC+"/w10_ablation_series_V4_A0_dyn_s42.npz","d30_n2_c42_rec")
tA,RA=load(TD+"/IB_AM50.npz")
mk=np.array([MKT.get(int(t),np.nan) for t in t0])
g0=R0[:,C["net_ex"]]/R0[:,C["gross_total"]]; gA=RA[:,C["net_ex"]]/RA[:,C["gross_total"]]
d=gA-g0
dnl=RA[:,C["netlong"]]-R0[:,C["netlong"]]
FULL=(T(2022,1,1),T(2026,8,10,20)+1)
YR={"2022":(T(2022,1,1),T(2023,1,1)),"2023":(T(2023,1,1),T(2024,1,1)),"2024":(T(2024,1,1),T(2025,1,1)),"2025":(T(2025,1,1),T(2026,1,1)),"2026":(T(2026,1,1),T(2026,8,10,20)+1)}
print("=== does the extra NET-SHORT explain the IB_AM50 uplift? ===")
print("  window      D(bps)  mkt4h(bps)  d_netlong  beta_term  residual  corr(D,mkt)")
for w,(lo,hi) in [("full",FULL)]+list(YR.items()):
    m=(t0>=lo)&(t0<hi)&np.isfinite(mk)
    imp=(dnl[m]*mk[m]*1e4).mean()
    print("  %-8s %+8.3f %+11.2f %+10.4f %+10.3f %+9.3f %+7.3f"%(w,d[m].mean(),mk[m].mean()*1e4,dnl[m].mean(),imp,d[m].mean()-imp,np.corrcoef(d[m],mk[m])[0,1]))
print()
print("=== A0 baseline netlong / beta term ===")
for w,(lo,hi) in [("full",FULL)]+list(YR.items()):
    m=(t0>=lo)&(t0<hi)&np.isfinite(mk)
    print("  %-8s A0 netlong %+0.4f  mkt %+0.2f bps  A0 beta term %+0.3f  A0 net %+0.3f"%(w,R0[m,C["netlong"]].mean(),mk[m].mean()*1e4,(R0[m,C["netlong"]]*mk[m]*1e4).mean(),g0[m].mean()))
