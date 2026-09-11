"""Bonferroni-corrected block-bootstrap intervals for the leading arms (S6). K declared in the prereg."""
import numpy as np, sys, importlib.util, calendar
spec=importlib.util.spec_from_file_location("j","/workspace/uplift_2026-09-11/judgeD.py")
j=importlib.util.module_from_spec(spec); spec.loader.exec_module(j)
K=int(sys.argv[1]); tags=sys.argv[2:]
alpha=0.05/K; lo_q=100*alpha/2; hi_q=100*(1-alpha/2)
print(f"K={K}  Bonferroni two-sided level {100*(1-alpha):.4f}%  percentiles [{lo_q:.4f}, {hi_q:.4f}]")
A0="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz"
t0,g0,R0=j.load(A0,"d30_n2_c42_rec")
for k,tg in enumerate(tags):
    ts,g,R=j.load(f"/workspace/uplift_2026-09-11/trackD_v4/{tg}.npz","rec")
    for wname,(lo,hi) in [("full 2022->08-10",j.FULL),("frozen",j.FROZEN)]:
        m=(ts>=lo)&(ts<hi); v=g[m]; d=ts[m]//86400
        rng=np.random.default_rng([20260905,100+k])
        ud,inv=np.unique(d,return_inverse=True); nd=len(ud)
        S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
        idx=rng.integers(0,nd,size=(20000,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
        print(f"  {tg:26s} {wname:18s} mean {v.mean():+.3f}  CI95 [{np.percentile(mn,2.5):+.3f},{np.percentile(mn,97.5):+.3f}]"
              f"  BONF [{np.percentile(mn,lo_q):+.3f},{np.percentile(mn,hi_q):+.3f}]  P(>0) {float((mn>0).mean()):.4f}")
