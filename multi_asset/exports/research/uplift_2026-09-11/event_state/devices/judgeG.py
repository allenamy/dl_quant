"""Track G judge — judge_v4 frozen g/window/bootstrap definitions (exploratory, NOT the eligibility gate)."""
import numpy as np, json, calendar, os, glob, sys
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}; APY=2190
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FROZEN=(T(2025,3,1),T(2026,8,10,20)+1); FULL=(T(2022,1,1),T(2026,8,10,20)+1)
W24=(T(2024,1,1),T(2026,8,10,20)+1); EXT=(T(2026,8,10,20)+1,T(2026,9,1))
YRS={"2022":(T(2022,1,1),T(2023,1,1)),"2023":(T(2023,1,1),T(2024,1,1)),"2024":(T(2024,1,1),T(2025,1,1)),
     "2025":(T(2025,1,1),T(2026,1,1)),"2026":(T(2026,1,1),T(2026,8,10,20)+1)}
WINS=[("frozen",FROZEN),("full",FULL),("2024on",W24),("ext",EXT)]+list(YRS.items())
def load(p,key="rec"):
    A=np.load(p,allow_pickle=True); R=A[key] if key in A.files else A["d30_n2_c42_rec"]
    ts=np.round(np.asarray(R[:,0],float)).astype(np.int64)
    return ts,R[:,C["net_ex"]]/R[:,C["gross_total"]],R
def boot(v,days,k,n=2000):
    rng=np.random.default_rng([20260905,k]); ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(n,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
    return mn
def ci(mn,a=2.5): return float(np.percentile(mn,a)),float(np.percentile(mn,100-a))
def stats(ts,g,R,lo,hi):
    m=(ts>=lo)&(ts<hi)
    if m.sum()<3: return None
    v=g[m]; c=np.concatenate([[0.0],np.cumsum(v)])
    return {"n":int(m.sum()),"mean":float(v.mean()),
            "sharpe":float(v.mean()/v.std(ddof=1)*np.sqrt(APY)) if v.std(ddof=1)>0 else float("nan"),
            "se_sharpe":float(np.sqrt(2190.0/m.sum())),
            "maxdd":float(np.max(np.maximum.accumulate(c)-c)),
            "turnover":float(R[m,C["turnover"]].mean()),
            "cost_bps":float((R[m,C["cost_ex"]]/R[m,C["gross_total"]]).mean()),
            "carry_bps":float((R[m,C["carry_ex"]]/R[m,C["gross_total"]]).mean()),
            "pnl_bps":float((R[m,C["pnl_ex"]]/R[m,C["gross_total"]]).mean())}
if __name__=="__main__":
    A0P="/workspace/uplift_2026-09-11/dev_v4ev/probe_artifacts/w10_ablation_series_GP_dyn_s42.npz"
    t0,g0,R0=load(A0P,"d30_n2_c42_rec")
    files=sorted(glob.glob(sys.argv[1] if len(sys.argv)>1 else "/workspace/uplift_2026-09-11/event_state/arms/SL_*.npz"))
    K=int(sys.argv[2]) if len(sys.argv)>2 else 20
    aB=100.0*(0.05/K)/2.0
    out={"baseline":{},"arms":{},"meta":{"K":K,"bonf_alpha_pct":aB,"n_arms":len(files),
         "device":"w10_sleeve.py b88e35a46b93d712 (GATE P bitwise PASS)","A0":A0P}}
    for w,(lo,hi) in WINS: out["baseline"][w]=stats(t0,g0,R0,lo,hi)
    mf=(t0>=FULL[0])&(t0<FULL[1]); mn0=boot(g0[mf],t0[mf]//86400,0)
    out["baseline"]["full_ci"]=list(ci(mn0))
    k=1
    for f in files:
        tag=os.path.basename(f)[:-4]; ts,g,R=load(f,"rec")
        fa=ts[(ts>=FROZEN[0])&(ts<FROZEN[1])]; f0=t0[(t0>=FROZEN[0])&(t0<FROZEN[1])]
        e={"anchor_axis_equals_A0_frozen":bool(len(fa)==len(f0) and (fa==f0).all())}
        for w,(lo,hi) in WINS: e[w]=stats(ts,g,R,lo,hi)
        m=(ts>=FULL[0])&(ts<FULL[1]); mn=boot(g[m],ts[m]//86400,k)
        e["full_ci"]=list(ci(mn)); e["full_bonf"]=list(ci(mn,aB)); e["full_p_pos"]=float((mn>0).mean()); k+=1
        ca,ia,ib=np.intersect1d(ts,t0,return_indices=True)
        for nm,(lo,hi) in [("corr_frozen",FROZEN),("corr_2024on",W24),("corr_full",FULL)]:
            s=(ca>=lo)&(ca<hi)
            e[nm]=float(np.corrcoef(g[ia[s]],g0[ib[s]])[0,1]) if s.sum()>10 else None
        gb=0.5*g[ia]+0.5*g0[ib]; e["blend50"]={}
        for w,(lo,hi) in WINS:
            s=(ca>=lo)&(ca<hi)
            if s.sum()>3:
                v=gb[s]; e["blend50"][w]={"mean":float(v.mean()),"sharpe":float(v.mean()/v.std(ddof=1)*np.sqrt(APY))}
        fu=e["full"]
        e["carry_fraction_of_net"]=(fu["carry_bps"]/fu["mean"]) if fu and abs(fu["mean"])>1e-9 else None
        out["arms"][tag]=e
    json.dump(out,open("/workspace/uplift_2026-09-11/event_state/JUDGE_G.json","w"),indent=1)
    print("judged",len(files))
