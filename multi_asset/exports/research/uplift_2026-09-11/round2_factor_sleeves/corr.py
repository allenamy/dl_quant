"""Correlation matrix of candidate sleeve g-series on the FULL CYCLE (2022-01-31..2026-08-10, n=9918),
plus the effective number of independent bets computed properly from the correlation matrix:
N_eff = (sum_i sum_j |C|_ij)^-1 * (n^2)  ... we use the standard participation-ratio definition
N_eff = (sum_k lambda_k)^2 / sum_k lambda_k^2 on the eigenvalues of the correlation matrix."""
import numpy as np, sys, os, json
sys.path.insert(0,"/workspace/uplift_2026-09-11/r2_factor")
import lib2 as L
R="/workspace/uplift_2026-09-11/r2_factor"
SETS={
 "A0":"/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz",
 "R1_ORTH_amihud":"/workspace/uplift_2026-09-11/trackD_v4/SL_ORTH_f_amihud_24h__p.npz",
 "R1_ORTH_asz":"/workspace/uplift_2026-09-11/trackD_v4/SL_ORTH_f_asz_24h__m.npz",
 "R1_ORTHLAG":"/workspace/uplift_2026-09-11/attack_trackD_newalpha/out/XSL_ORTHLAG.npz",
 "R1_ORTH_SURP":"/workspace/uplift_2026-09-11/trackD_v4/SL_ORTH_D_SURP__m.npz",
}
for f in sorted(os.listdir(R+"/out")):
    if f.startswith("SL2_ORTH_") and f.endswith(".npz"): SETS[f[9:-4]]=R+"/out/"+f
G={}; ts0=None
for k,p in SETS.items():
    Rr=L.load(p); ts,g=L.gser(Rr)
    if ts0 is None: ts0=ts
    if not np.array_equal(ts,ts0): print("skip ts",k); continue
    G[k]=g
m=L.msk(ts0,*L.W["full22"])
names=list(G)
M=np.array([G[k][m] for k in names])
ok=np.isfinite(M).all(axis=0); M=M[:,ok]
C=np.corrcoef(M)
print("full-cycle (n=%d) correlations vs A0 and vs the round-1 sleeves:"%ok.sum())
print("%-22s %7s %7s %7s %7s %7s"%("arm","A0","R1_AMI","R1_ASZ","R1_LAG","R1_SURP"))
ref=[names.index(x) for x in ("A0","R1_ORTH_amihud","R1_ORTH_asz","R1_ORTHLAG","R1_ORTH_SURP")]
for i,n in enumerate(names):
    print("%-22s %+7.3f %+7.3f %+7.3f %+7.3f %+7.3f"%(n,*[C[i,j] for j in ref]))
json.dump({"names":names,"corr":C.tolist(),"n":int(ok.sum())},open(R+"/corr_full.json","w"),indent=1)
def neff(sub):
    idx=[names.index(s) for s in sub]
    Cs=C[np.ix_(idx,idx)]
    w=np.linalg.eigvalsh(Cs); w=np.maximum(w,0)
    return float(w.sum()**2/ (w**2).sum()), Cs
for sub in (["A0","R1_ORTH_amihud"],["A0","R1_ORTH_amihud","AMIRESID__p"],
            ["A0","R1_ORTH_amihud","R1_ORTH_asz","AMIRESID__p"]):
    ne,Cs=neff(sub)
    print("N_eff %-58s = %.3f  (of %d)"%(str(sub),ne,len(sub)))
