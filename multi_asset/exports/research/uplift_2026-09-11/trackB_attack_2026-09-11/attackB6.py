"""ATTACK 6: like-for-like freeze / turnover comparison between the REPLAY arms and the LIVE producer."""
import numpy as np, calendar
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FR=(T(2025,3,1),T(2026,8,10,20)+1)
L26=(T(2026,6,1),T(2026,8,10,20)+1)   # a recent slice closest to the live regime
TB="/workspace/uplift_2026-09-11/dev_tb/probe_artifacts/w10_ablation_series_%s.npz"
print("%-13s %-5s %-10s %7s %8s %9s %9s %9s"%("arm","seed","window","gross","tov/gr","frozen%gr","frozen%nm","medstep"))
for nm in ("TB_BASE","TB_BAND35e5","TB_BAND45e5","TB_BAND5e4","TB_BAND6e4","TB_EMA005"):
    for s in ("42",):
        A=np.load(TB%f"{nm}_dyn_s{s}",allow_pickle=True); R=A["d30_n2_c42_rec"]; W=np.asarray(A["d30_n2_c42_W"],np.float64)
        ts=np.round(R[:,0].astype(np.float64)).astype(np.int64)
        for lab,(a,b) in (("FROZENwin",FR),("2026-06..0810",L26)):
            m=(ts>=a)&(ts<b); i=np.where(m)[0]
            cur=W[i]; pr=W[i-1]
            step=np.abs(cur-pr); g=np.abs(cur).sum(1)
            held=np.abs(pr)>1e-12; frz=held&(step<1e-12)
            fg=(np.abs(cur)*frz).sum(1)/g
            fn=frz.sum(1)/np.maximum(held.sum(1),1)
            ms=np.array([np.median(step[k][step[k]>1e-12]) if (step[k]>1e-12).any() else np.nan for k in range(len(i))])
            print("%-13s %-5s %-10s %7.4f %8.4f %9.3f %9.3f %9.6f"%(nm,s,lab,g.mean(),(step.sum(1)/g).mean(),np.median(fg),np.median(fn),np.nanmedian(ms)))
print("\nLIVE producer combo (2026-08-26..09-11, 95 anchor-pairs): gross 0.818 | tov/gr 0.0268 | frozen%gr 0.620 | frozen%nm 0.641 | medstep 0.00016")
