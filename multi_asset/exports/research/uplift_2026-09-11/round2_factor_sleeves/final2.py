import numpy as np, sys, json
sys.path.insert(0,"/workspace/uplift_2026-09-11/r2_factor")
import lib2 as L
R="/workspace/uplift_2026-09-11/r2_factor"
A0p="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz"
A=np.load(A0p,allow_pickle=True); recA=A["d30_n2_c42_rec"]; cols=[str(x) for x in A["cols"]]
recB=np.load(R+"/out/IB2_PARITY.npz",allow_pickle=True)["rec"]
print("=== PARITY DIAGNOSIS: IB2_PARITY vs archived A0_dyn_s42, per column ===")
for i,c in enumerate(cols):
    d=np.abs(recA[:,i]-recB[:,i]); nz=int((d>0).sum())
    print("  %-13s bitwise=%-5s ndiff=%5d  max|d|=%.3e  mean|d|=%.3e"%(
        c, recA[:,i].tobytes()==recB[:,i].tobytes(), nz, d.max(), d.mean()))
gA=recA[:,cols.index("net_ex")]/recA[:,cols.index("gross_total")]
gB=recB[:,cols.index("net_ex")]/recB[:,cols.index("gross_total")]
print("  g series: mean|dg| %.5f bps  max %.4f  mean dg %+.6f"%(np.abs(gA-gB).mean(),np.abs(gA-gB).max(),(gB-gA).mean()))
print()
ts,_=L.gser(L.load(A0p))
def get(p):
    Rr=L.load(p); t,g=L.gser(Rr); assert np.array_equal(t,ts); return g
K=36
print("=== BONFERRONI (K=%d declared): two-sided 95%% and %.4f%% block-bootstrap bounds, full cycle ==="%(K,100*(1-0.05/K)))
import numpy as _np
def boot_pct(d,tsx,k,pcts,n=2000):
    ok=_np.isfinite(d); d=d[ok]; tsx=tsx[ok]
    dk=(tsx//86400).astype(_np.int64); ud,inv=_np.unique(dk,return_inverse=True)
    idx=[_np.where(inv==i)[0] for i in range(len(ud))]
    rng=_np.random.default_rng([20260905,k]); out=_np.empty(n)
    for b in range(n):
        pick=rng.integers(0,len(ud),len(ud)); out[b]=d[_np.concatenate([idx[p] for p in pick])].mean()
    return [float(_np.percentile(out,p)) for p in pcts]
a=100*(0.05/K)/2
CAND=[("SL2_ORTH_AMIRESID__p",11),("SL2_ORTH_ASZSTAB__p",12),("SL2_ORTH_RESSKEW__m",13)]
m=L.msk(ts,*L.W["full22"])
for tag,k in CAND:
    g=get(R+"/out/%s.npz"%tag)[m]
    p=boot_pct(g,ts[m],k,[2.5,97.5,a,100-a])
    print("  %-24s level %+0.4f  CI95 [%+0.4f,%+0.4f]  BONF%d [%+0.4f,%+0.4f]  %s"%(
        tag,_np.nanmean(g),p[0],p[1],K,p[2],p[3],"SURVIVES" if p[2]>0 else "fails Bonferroni"))
base=get(R+"/out/IB2_PARITY.npz")
for tag,k in (("IB2_AMIRESID50",1),("IB2_AMIRESID25",2)):
    d=(get(R+"/out/%s.npz"%tag)-base)[m]
    p=boot_pct(d,ts[m],k,[2.5,97.5,a,100-a])
    print("  %-24s paired D %+0.4f  CI95 [%+0.4f,%+0.4f]  BONF%d [%+0.4f,%+0.4f]  %s"%(
        tag,_np.nanmean(d),p[0],p[1],K,p[2],p[3],"SURVIVES" if p[2]>0 else "fails Bonferroni"))
print()
print("=== candidate set: pairwise correlation and N_eff (full cycle) ===")
SET=["A0","SL2_ORTH_AMIRESID__p","SL2_ORTH_ASZSTAB__p","SL2_ORTH_RESSKEW__m"]
GG={"A0":get(A0p)}
for s in SET[1:]: GG[s]=get(R+"/out/%s.npz"%s)
M=_np.array([GG[s][m] for s in SET]); ok=_np.isfinite(M).all(axis=0); M=M[:,ok]
C=_np.corrcoef(M)
print("      "+"".join("%24s"%s[-14:] for s in SET))
for i,s in enumerate(SET): print("%-22s"%s[-22:]+"".join("%24.3f"%C[i,j] for j in range(len(SET))))
w=_np.linalg.eigvalsh(C); w=_np.maximum(w,0)
print("N_eff(participation ratio) = %.3f of %d"%(w.sum()**2/(w**2).sum(),len(SET)))
w2=_np.linalg.eigvalsh(C[1:,1:]); w2=_np.maximum(w2,0)
print("N_eff(three sleeves only)  = %.3f of 3"%(w2.sum()**2/(w2**2).sum()))
ANN=_np.sqrt(2190.0)
sr=_np.array([M[i].mean()/M[i].std(ddof=1)*ANN for i in range(len(SET))])
print("standalone SR:", dict(zip([s[-14:] for s in SET],[round(float(x),3) for x in sr])))
print("sqrt(sum SR^2) over the 3 sleeves + A0 (ZERO-correlation ideal) = %.3f"%float(_np.sqrt((sr**2).sum())))
mu=M.mean(axis=1); S=_np.cov(M); wopt=_np.linalg.solve(S+_np.eye(len(SET))*1e-14,mu)
print("in-sample optimal combination SR = %.3f (upper bound, weights fitted in sample)"%float(_np.sqrt(max(mu@wopt,0))*ANN))
