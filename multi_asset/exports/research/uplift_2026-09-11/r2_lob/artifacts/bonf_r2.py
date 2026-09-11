"""Bonferroni over the K=48 declared candidate arms (32 tranche-1 + 16 ORTH2; 2 DIAG diagnostics and
8 placebos excluded). Day-block bootstrap distribution -> SE, then a two-sided 95%/K interval."""
import numpy as np, json, calendar, os
from scipy.stats import norm
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FULL=(T(2022,1,1),T(2026,8,10,20)+1)
L=set(int(x) for x in np.load("/workspace/uplift_2026-09-11/r2/LOBTS_frozen.npy"))
K=48; z1=norm.ppf(0.975); zK=norm.ppf(1-0.05/(2*K))
print("K=%d  z(95%%)=%.3f  z(Bonferroni 95%%/K)=%.3f"%(K,z1,zK))
def one(tag,k):
    p="/workspace/uplift_2026-09-11/r2/arms/%s.npz"%tag
    if not os.path.exists(p): p="/workspace/uplift_2026-09-11/trackD_v4/%s.npz"%tag
    R=np.load(p,allow_pickle=True)["rec"]
    ts=np.round(R[:,0].astype(float)).astype(np.int64)
    ok=(R[:,C["w3_fund"]]>0.999)&(R[:,C["gross_total"]]>1e-12)
    ts=ts[ok]; R=R[ok]
    g=R[:,C["net_ex"]]/R[:,C["gross_total"]]
    m=np.array([int(x) in L for x in ts])&(ts>=FULL[0])&(ts<FULL[1])
    v=g[m]; days=ts[m]//86400
    rng=np.random.default_rng([20260905,k])
    ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(2000,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
    se=float(mn.std(ddof=1)); mu=float(v.mean())
    print("%-28s n=%d  g %+.4f  boot SE %.4f | CI95 [%+.3f,%+.3f] | BONF%d [%+.3f,%+.3f] %s"%(
        tag,m.sum(),mu,se,mu-z1*se,mu+z1*se,K,mu-zK*se,mu+zK*se,
        "SURVIVES" if mu-zK*se>0 else "fails"))
    return mu,se
for i,t in enumerate(["R2_DIAG_ORTH_R1MEAN__m","R2_LIVOL__p","R2B_ORTH2_LIVOL__p","R2_ORTH_LIVOL__p","R2B_ORTH2_LDVOL__p","R2_LDVOL__p","SL_ORTH_f_amihud_24h__p"]):
    one(t,700+i)
