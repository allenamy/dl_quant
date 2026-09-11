import numpy as np, calendar, json, glob, os
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires",
 "leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}
R="/workspace/uplift_2026-09-11/r5_lob"; END=T(2026,8,10,20)+1
tA=np.round(np.asarray(np.load("/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s42.npz",allow_pickle=True)["rec"],float)[:,0]).astype(np.int64)
POSTWARM=tA[900]
def get(tg):
    A=np.load(R+"/out/%s.npz"%tg,allow_pickle=True); Rr=np.asarray(A["rec"],float)
    t=np.round(Rr[:,0]).astype(np.int64); return t,Rr
# COMMON mask recomputed exactly as analyze5
tags=sorted(os.path.basename(p)[:-4] for p in glob.glob(R+"/out/*.npz"))
live=np.ones(len(tA),bool)
for tg in tags:
    if tg.startswith("NULL_"): continue
    t,Rr=get(tg); gg=np.full(len(tA),np.nan); G=np.full(len(tA),0.0)
    pos=np.searchsorted(tA,t); gg[pos]=Rr[:,C["net_ex"]]; G[pos]=Rr[:,C["gross_total"]]
    live&=np.isfinite(gg)&(G>1e-9)
M=live&(tA>=POSTWARM)&(tA<END)
print("COMMON n=%d"%M.sum())
def sh(v): return v.mean()/v.std(ddof=1)*np.sqrt(2190)
print("%-22s %9s %9s %9s %9s %9s %8s"%("arm","pnl_ex","carry_ex","cost_ex","net_ex","SR(net)","turn"))
rows={}
for tg in tags:
    t,Rr=get(tg); F=np.full((len(tA),Rr.shape[1]),np.nan); pos=np.searchsorted(tA,t); F[pos]=Rr
    G=F[M,C["gross_total"]]
    pn=(F[M,C["pnl_ex"]]/G).mean(); ca=(F[M,C["carry_ex"]]/G).mean(); co=(F[M,C["cost_ex"]]/G).mean()
    nx=F[M,C["net_ex"]]/G
    print("%-22s %+9.4f %+9.4f %+9.4f %+9.4f %+9.3f %8.4f"%(tg,pn,ca,co,nx.mean(),sh(nx),F[M,C["turnover"]].mean()))
    rows[tg]={"pnl_ex":round(float(pn),4),"carry_ex":round(float(ca),4),"cost_ex":round(float(co),4),
              "net_ex":round(float(nx.mean()),4),"SR_net":round(float(sh(nx)),3),
              "SR_gross":round(float(sh(F[M,C["pnl_ex"]]/G)),3),
              "turnover":round(float(F[M,C["turnover"]].mean()),5)}
json.dump(rows,open(R+"/DECOMP_r5.json","w"),indent=1)
