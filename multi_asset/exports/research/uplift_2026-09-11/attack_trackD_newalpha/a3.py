import numpy as np, calendar
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C=dict((c,i) for i,c in enumerate(COLS))
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
HC="/workspace/review_scratch/health_check/dev_v4/probe_artifacts"; TD="/workspace/uplift_2026-09-11/trackD_v4"
def load(p,key="rec"):
    A=np.load(p,allow_pickle=True); R=np.asarray(A[key] if key in A.files else A["rec"],float)
    return np.round(R[:,0]).astype(np.int64),R[:,C["net_ex"]]/R[:,C["gross_total"]],R
W={"full":(T(2022,1,1),T(2026,8,10,20)+1),"frozen":(T(2025,3,1),T(2026,8,10,20)+1),
   "2022":(T(2022,1,1),T(2023,1,1)),"2023":(T(2023,1,1),T(2024,1,1)),"2024":(T(2024,1,1),T(2025,1,1)),
   "2025":(T(2025,1,1),T(2026,1,1)),"2026":(T(2026,1,1),T(2026,8,10,20)+1),
   "ext":(T(2026,8,11),T(2026,8,31,20)+1)}
def boot(v,d,seed,B=20000):
    rng=np.random.default_rng([20260905,seed]); ud,inv=np.unique(d,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(B,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
    return np.percentile(mn,[2.5,97.5]),np.percentile(mn,[100*0.05/68/2,100*(1-0.05/68/2)]),(mn>0).mean()
for seed in ["s42","s2027"]:
    t0,g0,_=load(HC+"/w10_ablation_series_V4_A0_dyn_"+seed+".npz","d30_n2_c42_rec")
    tA,gA,_=load(TD+"/IB_AM50.npz")
    assert (t0==tA).all()
    d=gA-g0
    print("=== seed",seed,"IB_AM50 - A0 (my own bootstrap, 20000) ===")
    for wn,(lo,hi) in W.items():
        m=(t0>=lo)&(t0<hi)
        if m.sum()<5: continue
        ci,bf,p=boot(d[m],t0[m]//86400,abs(hash(wn+seed))%997)
        # naive iid t for reference
        se=d[m].std(ddof=1)/np.sqrt(m.sum())
        print("  %-7s n=%5d D=%+7.3f  CI95[%+.3f,%+.3f] BONF68[%+.3f,%+.3f] P>0=%.4f  iid_t=%+.2f" % (wn,m.sum(),d[m].mean(),ci[0],ci[1],bf[0],bf[1],p,d[m].mean()/se))
    # CONCENTRATION: drop the top-K UTC days by |paired difference|
    mf=(t0>=W["full"][0])&(t0<W["full"][1]); dd=d[mf]; day=t0[mf]//86400
    ud,inv=np.unique(day,return_inverse=True)
    S=np.bincount(inv,weights=dd); N=np.bincount(inv)
    dm=S/N
    order=np.argsort(-np.abs(dm))
    print("  concentration (full cycle, %d UTC days):" % len(ud))
    for K in [0,1,2,5,10,20,40]:
        keep=np.ones(len(ud),bool); keep[order[:K]]=False
        sel=keep[inv]
        print("     drop top-%2d |day| days -> D=%+7.3f  (n=%d anchors)" % (K,dd[sel].mean(),sel.sum()))
    # top days by contribution to positive D
    order2=np.argsort(-dm)
    print("  top-8 best days:", [(str(np.datetime64(int(ud[i]*86400),"s"))[:10], round(float(dm[i]),2)) for i in order2[:8]])
    print("  top-8 worst days:", [(str(np.datetime64(int(ud[i]*86400),"s"))[:10], round(float(dm[i]),2)) for i in order2[-8:]])
