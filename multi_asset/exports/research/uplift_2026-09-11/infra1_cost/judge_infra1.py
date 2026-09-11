#!/usr/bin/env python3
"""INFRA-1 step 7: judge the re-priced arms. Windows/statistic/bootstrap copied from judgeD.py
(= judge_v4's frozen definitions). g = net_ex/gross_total bps/anchor/unit gross.
Paired contrast: each arm vs the PAR arm run under the SAME cost model."""
import numpy as np, json, calendar, os, glob, sys, itertools
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}; APY=2190
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FROZEN=(T(2025,3,1),T(2026,8,10,20)+1); FULL=(T(2022,1,1),T(2026,8,10,20)+1)
W24=(T(2024,1,1),T(2026,8,10,20)+1); OOF=(T(2026,8,11),T(2026,8,31,20)+1)
YRS={"2022":(T(2022,1,1),T(2023,1,1)),"2023":(T(2023,1,1),T(2024,1,1)),"2024":(T(2024,1,1),T(2025,1,1)),
     "2025":(T(2025,1,1),T(2026,1,1)),"2026":(T(2026,1,1),T(2026,8,10,20)+1)}
WINS=[("frozen",FROZEN),("full",FULL),("2024on",W24),("oof_aug",OOF)]+list(YRS.items())
OUT="/workspace/uplift_2026-09-11/infra1_cost/out"
def load(p):
    A=np.load(p,allow_pickle=True); R=A["rec"]
    ts=np.round(np.asarray(R[:,0],float)).astype(np.int64)
    return ts, R[:,C["net_ex"]]/R[:,C["gross_total"]], R
def boot(v,days,k):
    rng=np.random.default_rng([20260905,k])
    ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(2000,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
    return float(np.percentile(mn,2.5)),float(np.percentile(mn,97.5)),float((mn>0).mean())
def stats(ts,g,R,lo,hi):
    m=(ts>=lo)&(ts<hi)
    if m.sum()<3: return None
    v=g[m]
    return dict(n=int(m.sum()),mean=float(v.mean()),
        sharpe=float(v.mean()/v.std(ddof=1)*np.sqrt(APY)) if v.std(ddof=1)>0 else float("nan"),
        se_sharpe=float(np.sqrt(2190.0/m.sum())),
        cost_bps=float((R[m,C["cost_ex"]]/R[m,C["gross_total"]]).mean()),
        carry_bps=float((R[m,C["carry_ex"]]/R[m,C["gross_total"]]).mean()),
        pnl_bps=float((R[m,C["pnl_ex"]]/R[m,C["gross_total"]]).mean()),
        turnover=float(R[m,C["turnover"]].mean()))
if __name__=="__main__":
    seeds=[42,2027]; res={}
    k=1
    files=sorted(glob.glob(OUT+"/*.npz"))
    have={os.path.basename(f)[:-4] for f in files}
    for seed in seeds:
        for cb in ("STD","H0","H05","H1","H15","H2","H3","H4","H6"):
            base=f"IB_PAR_{cb}_s{seed}"
            if base not in have: continue
            tb,gb,Rb=load(f"{OUT}/{base}.npz")
            res.setdefault("base",{})[base]={w:stats(tb,gb,Rb,lo,hi) for w,(lo,hi) in WINS}
            for arm in ("PAR","AM50","LAG50","D60","PERM50"):
                tag=f"IB_{arm}_{cb}_s{seed}"
                if tag not in have: continue
                ta,ga,Ra=load(f"{OUT}/{tag}.npz")
                assert np.array_equal(ta,tb), f"anchor axis mismatch {tag}"
                e={w:stats(ta,ga,Ra,lo,hi) for w,(lo,hi) in WINS}
                d=ga-gb; dd={}
                for w,(lo,hi) in WINS:
                    m=(ta>=lo)&(ta<hi)
                    if m.sum()<3: continue
                    lo_,hi_,p_=boot(d[m],ta[m]//86400,k); k+=1
                    dd[w]=dict(n=int(m.sum()),D=float(d[m].mean()),ci=[lo_,hi_],p_pos=p_)
                res.setdefault("arms",{})[tag]=dict(level=e,paired_vs_PAR=dd)
    # sleeve arms: standalone, no pairing (LEGS=001)
    for cb in ("STD","H0","H05","H1","H15","H2","H3","H4","H6"):
        for arm in ("ORTHLAG","ORTHPERM"):
            tag=f"SL_{arm}_{cb}_s42"
            if tag not in have: continue
            ta,ga,Ra=load(f"{OUT}/{tag}.npz")
            res.setdefault("sleeves",{})[tag]={w:stats(ta,ga,Ra,lo,hi) for w,(lo,hi) in WINS}
    json.dump(res,open("/workspace/uplift_2026-09-11/infra1_cost/JUDGE_infra1.json","w"),indent=1)
    print("judged base",len(res.get("base",{})),"arms",len(res.get("arms",{})),"sleeves",len(res.get("sleeves",{})))
