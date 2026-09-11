import numpy as np, importlib.util, calendar
spec=importlib.util.spec_from_file_location("j","/workspace/uplift_2026-09-11/judgeD.py"); j=importlib.util.module_from_spec(spec); spec.loader.exec_module(j)
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
HC="/workspace/review_scratch/health_check/dev_v4/probe_artifacts"
W={"full 2022->26-08-10":(T(2022,1,1),T(2026,8,10,20)+1),"frozen":(T(2025,3,1),T(2026,8,10,20)+1),
   "EXT 08-11->08-31":(T(2026,8,11),T(2026,8,31,20)+1),"2023":(T(2023,1,1),T(2024,1,1)),
   "2022":(T(2022,1,1),T(2023,1,1)),"2024":(T(2024,1,1),T(2025,1,1)),"2025":(T(2025,1,1),T(2026,1,1)),"2026":(T(2026,1,1),T(2026,8,10,20)+1)}
def boot(v,d,k,K=68):
    rng=np.random.default_rng([20260905,k]); ud,inv=np.unique(d,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(20000,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
    a=0.05/K
    return np.percentile(mn,2.5),np.percentile(mn,97.5),np.percentile(mn,100*a/2),np.percentile(mn,100*(1-a/2)),(mn>0).mean()
for seed,ver in (("s42",""),("s2027","")):
    t0,g0,_=j.load(f"{HC}/w10_ablation_series_V4_A0_dyn_{seed}.npz","d30_n2_c42_rec")
    for arm in ["IB_AM25","IB_AM50","IB_AMSU","IB_PARITY"]:
        ts,g,_=j.load(f"/workspace/uplift_2026-09-11/trackD_v4/{arm}.npz","rec")
        c,ia,ib=np.intersect1d(ts,t0,return_indices=True); d=g[ia]-g0[ib]
        if arm=="IB_PARITY":
            print(f"[{seed}] PARITY vs A0: n={len(c)} mean|dg| {np.abs(d).mean():.4f}  max|dg| {np.abs(d).max():.3f}  mean dg {d.mean():+.5f} bps/anchor"); continue
        for w,(lo,hi) in W.items():
            m=(c>=lo)&(c<hi)
            if m.sum()<5: continue
            lo95,hi95,lob,hib,p=boot(d[m],c[m]//86400,hash(arm+w+seed)%1000)
            print(f"[{seed}] {arm:9s} {w:22s} D={d[m].mean():+7.3f}  CI95 [{lo95:+.3f},{hi95:+.3f}]  BONF68 [{lob:+.3f},{hib:+.3f}]  P(>0) {p:.4f}")
        print()
