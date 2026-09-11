import numpy as np, json, calendar, os, glob
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
HC="/workspace/review_scratch/health_check/dev_v4/probe_artifacts"
TD="/workspace/uplift_2026-09-11/trackD_v4"
def load(p,key):
    A=np.load(p,allow_pickle=True); R=A[key] if key in A.files else A["rec"]
    ts=np.round(np.asarray(R[:,0],float)).astype(np.int64)
    return ts,np.asarray(R,float)
# 0. verify the cols array stored in the artifact matches my assumed COLS
A=np.load(f"{TD}/IB_AM50.npz",allow_pickle=True)
print("COLS stored:",[str(x) for x in A["cols"]])
print("match:",[str(x) for x in A["cols"]]==COLS)
t0,R0=load(f"{HC}/w10_ablation_series_V4_A0_dyn_s42.npz","d30_n2_c42_rec")
t0b,R0b=load(f"{HC}/w10_ablation_series_V4_A0_dyn_s2027.npz","d30_n2_c42_rec")
tA,RA=load(f"{TD}/IB_AM50.npz","rec")
tP,RP=load(f"{TD}/IB_PARITY.npz","rec")
print("A0 n",len(t0),"IB_AM50 n",len(tA),"identical full axis:",len(t0)==len(tA) and bool((t0==tA).all()))
FULL=(T(2022,1,1),T(2026,8,10,20)+1); FROZEN=(T(2025,3,1),T(2026,8,10,20)+1)
EXT=(T(2026,8,11),T(2026,8,31,20)+1)
def g(R): return R[:,C["net_ex"]]/R[:,C["gross_total"]]
for nm,(lo,hi) in [("full",FULL),("frozen",FROZEN),("ext",EXT)]:
    m0=(t0>=lo)&(t0<hi); mA=(tA>=lo)&(tA<hi)
    print(f"{nm}: A0 n={m0.sum()} mean={g(R0)[m0].mean():+.4f} sh={g(R0)[m0].mean()/g(R0)[m0].std(ddof=1)*np.sqrt(2190):+.3f} | IB_AM50 n={mA.sum()} mean={g(RA)[mA].mean():+.4f} sh={g(RA)[mA].mean()/g(RA)[mA].std(ddof=1)*np.sqrt(2190):+.3f}")
    print(f"   anchors identical in window: {bool(m0.sum()==mA.sum() and (t0[m0]==tA[mA]).all())}")
