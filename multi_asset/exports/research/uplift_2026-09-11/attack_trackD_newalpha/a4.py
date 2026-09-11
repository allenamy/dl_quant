import numpy as np, calendar
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C=dict((c,i) for i,c in enumerate(COLS))
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
HC="/workspace/review_scratch/health_check/dev_v4/probe_artifacts"; TD="/workspace/uplift_2026-09-11/trackD_v4"
def load(p,key="rec"):
    A=np.load(p,allow_pickle=True); R=np.asarray(A[key] if key in A.files else A["rec"],float)
    return np.round(R[:,0]).astype(np.int64),R[:,C["net_ex"]]/R[:,C["gross_total"]]
FULL=(T(2022,1,1),T(2026,8,10,20)+1)
def bonf_lo(v,d,seed,B,K=68):
    rng=np.random.default_rng([20260905,seed]); ud,inv=np.unique(d,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(B,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
    a=0.05/K
    return np.percentile(mn,100*a/2),np.percentile(mn,2.5)
for seed in ["s42","s2027"]:
    t0,g0=load(HC+"/w10_ablation_series_V4_A0_dyn_"+seed+".npz","d30_n2_c42_rec")
    tA,gA=load(TD+"/IB_AM50.npz")
    d=gA-g0; m=(t0>=FULL[0])&(t0<FULL[1]); v=d[m]; day=t0[m]//86400
    print("=== "+seed+" IB_AM50-A0 full cycle: BONF68 lower bound across 12 bootstrap substreams (B=20000) ===")
    los=[];ci=[]
    for k in range(12):
        lo,l95=bonf_lo(v,day,k,20000); los.append(lo); ci.append(l95)
    los=np.array(los)
    print("   BONF68 lo: min %+0.4f  max %+0.4f  mean %+0.4f  frac<=0: %.2f" % (los.min(),los.max(),los.mean(),(los<=0).mean()))
    print("   values:", np.round(los,3).tolist())
    print("   CI95 lo: min %+0.4f max %+0.4f" % (min(ci),max(ci)))
    # B=200000 reference
    lo,l95=bonf_lo(v,day,777,200000)
    print("   B=200000 substream 777: BONF68 lo %+0.4f  CI95 lo %+0.4f" % (lo,l95))
