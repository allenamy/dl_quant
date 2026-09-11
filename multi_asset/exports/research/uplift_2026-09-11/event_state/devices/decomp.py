"""Per-arm decomposition net_ex = pnl_ex - carry_ex - cost_ex, plus the zero-cost counterfactual."""
import numpy as np, json, glob, os, calendar
C={c:i for i,c in enumerate(["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"])}
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FULL=(T(2022,1,1),T(2026,8,10,20)+1)
def row(p,key):
    A=np.load(p,allow_pickle=True); R=A[key] if key in A.files else A["d30_n2_c42_rec"]
    ts=np.round(np.asarray(R[:,0],float)).astype(np.int64); m=(ts>=FULL[0])&(ts<FULL[1]); R=R[m]
    G=R[:,C["gross_total"]]
    g=R[:,C["net_ex"]]/G; p_=R[:,C["pnl_ex"]]/G; c_=R[:,C["carry_ex"]]/G; k_=R[:,C["cost_ex"]]/G
    g0=p_-c_             # zero trading cost
    g00=p_               # zero cost AND zero carry (pure price alpha)
    def sh(v): return float(v.mean()/v.std(ddof=1)*np.sqrt(2190))
    return dict(n=int(m.sum()),net=float(g.mean()),sh=sh(g),pnl=float(p_.mean()),carry=float(c_.mean()),
                cost=float(k_.mean()),turn=float(R[:,C["turnover"]].mean()),
                net_zerocost=float(g0.mean()),sh_zerocost=sh(g0),
                price_only=float(g00.mean()),sh_price_only=sh(g00))
out={"A0":row("/workspace/uplift_2026-09-11/dev_v4ev/probe_artifacts/w10_ablation_series_GP_dyn_s42.npz","d30_n2_c42_rec")}
for f in sorted(glob.glob("/workspace/uplift_2026-09-11/event_state/arms/SL_*.npz")):
    out[os.path.basename(f)[:-4]]=row(f,"rec")
json.dump(out,open("/workspace/uplift_2026-09-11/event_state/DECOMP.json","w"),indent=1)
print("%-28s %6s %6s | %7s %7s %7s %6s | %8s %6s | %8s %6s"%("arm","net","Sh","pnl","carry","cost","turn","net_c0","Sh_c0","price","Sh_px"))
for k,v in out.items():
    print("%-28s %+6.3f %+6.2f | %+7.3f %+7.3f %+7.3f %6.4f | %+8.3f %+6.2f | %+8.3f %+6.2f"%(k,v["net"],v["sh"],v["pnl"],v["carry"],v["cost"],v["turn"],v["net_zerocost"],v["sh_zerocost"],v["price_only"],v["sh_price_only"]))
