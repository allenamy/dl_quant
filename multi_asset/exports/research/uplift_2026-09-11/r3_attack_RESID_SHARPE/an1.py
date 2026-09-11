import numpy as np, json, calendar
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires",
      "leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}; APY=2190
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
WIN={"full":(T(2022,1,1),T(2026,8,10,20)+1),"f23":(T(2023,1,1),T(2026,8,10,20)+1),
     "frozen":(T(2025,3,1),T(2026,8,10,20)+1),"ext":(T(2026,8,11),T(2026,9,1)),
     "2022":(T(2022,1,1),T(2023,1,1)),"2023":(T(2023,1,1),T(2024,1,1)),"2024":(T(2024,1,1),T(2025,1,1)),
     "2025":(T(2025,1,1),T(2026,1,1)),"2026":(T(2026,1,1),T(2026,8,10,20)+1)}
def load(p,key=None):
    A=np.load(p,allow_pickle=True)
    R=A[key] if (key and key in A.files) else (A["rec"] if "rec" in A.files else A["d30_n2_c42_rec"])
    ts=np.round(np.asarray(R[:,0],float)).astype(np.int64)
    return ts,np.asarray(R,float)
P={
 "RS_s42":"/workspace/uplift_2026-09-11/r2_learned/out/SL_RESID_SHARPE_s42.npz",
 "RS_s2027":"/workspace/uplift_2026-09-11/r2_learned/out/SL_RESID_SHARPE_s2027.npz",
 "RS_PERM_s42":"/workspace/uplift_2026-09-11/r2_learned/out/SL_RESID_SHARPE_PERM_s42.npz",
 "XIB_s42":"/workspace/uplift_2026-09-11/r2_attack/out/XIB_AM50_s42.npz",
 "XIB_s2027":"/workspace/uplift_2026-09-11/r2_attack/out/XIB_AM50_s2027.npz",
 "A0_s42":"/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz",
 "A0_s2027":"/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s2027.npz",
}
D={}
for k,p in P.items():
    try: D[k]=load(p)
    except Exception as e: print("LOADFAIL",k,e)
print("loaded:",sorted(D))
def blk(v,days,k,n=2000):
    rng=np.random.default_rng([20260905,k]); ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(n,nd)); return S[idx].sum(1)/N[idx].sum(1)
def blkSR(v,days,k,n=2000):
    rng=np.random.default_rng([20260905,k]); ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    grp=[np.nonzero(inv==z)[0] for z in range(nd)]
    idx=rng.integers(0,nd,size=(n,nd)); out=[]
    for r in range(n):
        s=np.concatenate([grp[z] for z in idx[r]]); x=v[s]
        if x.std(ddof=1)>0: out.append(x.mean()/x.std(ddof=1)*np.sqrt(APY))
    return np.array(out)
print("\n%-12s %-7s %6s %8s %8s %7s %9s %9s %9s %9s %9s"%("arm","win","n","mean","SR","SEsr","gross","turn","pnl_ex","carry_ex","netlong"))
res={}
for k in ["A0_s42","RS_s42","RS_s2027","XIB_s42","RS_PERM_s42"]:
    if k not in D: continue
    ts,R=D[k]; g=R[:,C["net_ex"]]/R[:,C["gross_total"]]
    for w,(lo,hi) in WIN.items():
        m=(ts>=lo)&(ts<hi)
        if m.sum()<3: continue
        v=g[m]; gt=R[m,C["gross_total"]]
        sr=v.mean()/v.std(ddof=1)*np.sqrt(APY)
        res[(k,w)]=(v.mean(),sr,m.sum())
        print("%-12s %-7s %6d %+8.4f %+8.3f %7.3f %9.4f %9.5f %+9.4f %+9.4f %+9.4f"%(
          k,w,m.sum(),v.mean(),sr,np.sqrt(2190.0/m.sum()),gt.mean(),R[m,C["turnover"]].mean(),
          (R[m,C["pnl_ex"]]/gt).mean(),(R[m,C["carry_ex"]]/gt).mean(),(R[m,C["netlong"]]/gt).mean()))
json.dump({str(k):v for k,v in res.items()},open("/workspace/uplift_2026-09-11/r3_attack_b9646/an1.json","w"),indent=1)
