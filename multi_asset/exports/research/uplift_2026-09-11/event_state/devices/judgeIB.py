"""Paired per-anchor delta vs A0 for in-book blend arms; UTC-day block bootstrap 2000, rng [20260905,k]."""
import numpy as np, json, calendar, glob, os, sys
C={c:i for i,c in enumerate(["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"])}
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
W={"full":(T(2022,1,1),T(2026,8,10,20)+1),"frozen":(T(2025,3,1),T(2026,8,10,20)+1),
   "ext":(T(2026,8,10,20)+1,T(2026,9,1)),"2023":(T(2023,1,1),T(2024,1,1)),"2026":(T(2026,1,1),T(2026,8,10,20)+1)}
D="/workspace/uplift_2026-09-11/dev_v4ev/probe_artifacts"
def g(p,key):
    A=np.load(p,allow_pickle=True); R=A[key] if key in A.files else A["d30_n2_c42_rec"]
    ts=np.round(np.asarray(R[:,0],float)).astype(np.int64)
    return ts,R[:,C["net_ex"]]/R[:,C["gross_total"]],R
def boot(v,days,k,n=2000):
    rng=np.random.default_rng([20260905,k]); ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(n,nd)); return S[idx].sum(1)/N[idx].sum(1)
out={}; k=101
src=sys.argv[1] if len(sys.argv)>1 else "/workspace/uplift_2026-09-11/event_state/arms_ib2/IBR_*.npz"
for f in sorted(glob.glob(src)):
    tag=os.path.basename(f)[:-4]; seed=tag.split("_s")[-1]
    t0,g0,R0=g(f"{D}/w10_ablation_series_GP_dyn_s{seed}.npz","d30_n2_c42_rec")
    t1,g1,R1=g(f,"rec")
    ca,ia,ib=np.intersect1d(t1,t0,return_indices=True); d=g1[ia]-g0[ib]
    e={"n_common":int(len(ca)),"seed":seed}
    for w,(lo,hi) in W.items():
        s=(ca>=lo)&(ca<hi)
        if s.sum()<3: continue
        mn=boot(d[s],ca[s]//86400,k); k+=1
        e[w]={"delta":float(d[s].mean()),"ci95":[float(np.percentile(mn,2.5)),float(np.percentile(mn,97.5))],
              "bonf20":[float(np.percentile(mn,0.125)),float(np.percentile(mn,99.875))],
              "arm_mean":float(g1[ia][s].mean()),
              "arm_sharpe":float(g1[ia][s].mean()/g1[ia][s].std(ddof=1)*np.sqrt(2190)),
              "A0_sharpe":float(g0[ib][s].mean()/g0[ib][s].std(ddof=1)*np.sqrt(2190)),
              "turn":float(R1[ia][s][:,C["turnover"]].mean())}
    out[tag]=e
json.dump(out,open("/workspace/uplift_2026-09-11/event_state/JUDGE_IB.json","w"),indent=1)
for t,e in out.items():
    print(t,"n=",e["n_common"])
    for w in ["full","frozen","2023","2026","ext"]:
        if w in e:
            v=e[w]; print("   %-7s d %+.3f CI95[%+.3f,%+.3f] BONF20[%+.3f,%+.3f] armSh %+.2f (A0 %+.2f) turn %.4f"%(w,v["delta"],v["ci95"][0],v["ci95"][1],v["bonf20"][0],v["bonf20"][1],v["arm_sharpe"],v["A0_sharpe"],v["turn"]))
