#!/usr/bin/env python3
"""r10 COINT_PAIR STEP 4 of PREREG -- the full robustness grid. EVERY CELL REPORTED, no max taken.
ENV WHITELIST = THE EMPTY SET (E-0826-D)."""
import os, sys, json, time, math, calendar, hashlib
import numpy as np
_CE=["LEGS","PHI","CAL","WRULE","LOOK","MEMBERS_TOPN","FTRIM","UMASK_SCOPE","UMASK_NPZ","COSTB_JSON",
     "SLOW_NPY","FSEED","FPRED","FEMAT_NPZ","OUT_TAG","TILT","JUDGE_HC","V2","PANEL_IN"]
assert sorted([k for k in _CE if k in os.environ])==[]
def _forbid(*a,**k): raise AssertionError("E-0826-D violation")
os.environ.get=_forbid
sys.path.insert(0,"/workspace/uplift_2026-09-11/r10_coint")
import s1_engine as EN
np=EN.np
OUT="/workspace/uplift_2026-09-11/r10_coint"
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
WARM=900; CUT=T(2026,8,30,20); APY=2190; B=2000
tsA=EN.tsA; recA=EN.recA; ci=EN.ci; NW=EN.NW; AIDX=EN.AIDX
sel=np.zeros(len(tsA),bool); sel[WARM:]=True; sel&=(tsA<=CUT); TS=tsA[sel]; N=int(sel.sum())
gA0=(recA[:,ci["net_ex"]]/recA[:,ci["gross_total"]])[sel]
def sr(x): return float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(APY))
dd=TS//86400; ud,inv=np.unique(dd,return_inverse=True); nd=len(ud)
order=np.argsort(inv,kind="stable"); st=np.searchsorted(inv[order],np.arange(nd)); en=np.append(st[1:],len(order))
rng=np.random.default_rng([20260905,1]); pick=rng.integers(0,nd,size=(B,nd))
BI=[np.concatenate([order[st[j]:en[j]] for j in pick[b]]) for b in range(B)]
q20=float(np.quantile(gA0,0.2)); bot=gA0<=q20
def ci_of(fn):
    v=np.array([fn(ii) for ii in BI],float); v=v[np.isfinite(v)]
    return [round(float(np.percentile(v,2.5)),4), round(float(np.percentile(v,97.5)),4)]
def rho_of(a,b,mask=None):
    if mask is not None: a=a[mask]; b=b[mask]
    if len(a)<30 or np.std(a)<1e-15 or np.std(b)<1e-15: return float("nan")
    return float(np.corrcoef(a,b)[0,1])
rows=tsA
GRID=[]
for ENTRY in (1.5,2.0,2.5):
    for K in (20,40,80):
        for L in (540,1080):
            t0=time.time()
            W,nact,stats=EN.build(ENTRY=ENTRY,K=K,L=L,tag="E%.1f_K%d_L%d"%(ENTRY,K,L))
            Wr=np.zeros((len(rows),NW))
            for r,t in enumerate(rows): Wr[r]=W[AIDX[int(t)]]
            P,C,Kc,G,TU=EN.account(Wr,rows)
            net=(P-C-Kc)[sel]
            g=net   # per unit allocated capital (gross budget 1 by construction: /K)
            row={"ENTRY":ENTRY,"K":K,"L":L,"pairs_searched":stats["pairs_searched"],
                 "pairs_admitted":stats["pairs_admitted"],"entries":stats["entries"],
                 "mean_hold_anchors":stats["mean_hold_anchors"],
                 "deployment_rate_pct":round(float((G[sel]>1e-12).mean()*100),2),
                 "mean_utilisation":round(float(G[sel].mean()),4),
                 "gross_alpha_bps":round(float(P[sel].mean()),4),
                 "carry_bps":round(float(C[sel].mean()),4),
                 "cost_bps":round(float(Kc[sel].mean()),4),
                 "net_mean_g_bps":round(float(g.mean()),4),
                 "net_mean_g_CI95":ci_of(lambda ii: g[ii].mean()),
                 "sharpe":round(sr(g),4),
                 "turnover":round(float(TU[sel].mean()),5),
                 "rho_to_A0":round(rho_of(g,gA0),4),
                 "rho_in_A0_bottom_quintile":round(rho_of(g,gA0,bot),4),
                 "secs":round(time.time()-t0,1)}
            GRID.append(row); print(json.dumps(row),flush=True)
R={"step":"STEP4_GRID","env_whitelist":[],
   "self_sha256":hashlib.sha256(open(__file__,"rb").read()).hexdigest(),
   "prereg_sha256":"ca038101480e76e1ca2ed379a245bc59450315ed19fabc1eec938b87056b6b5e",
   "note":"ALL 18 cells reported; no maximum taken (anti p-hacking). Primary cell = ENTRY 2.0 / K 40 / L 1080, named in PREREG before any number was seen.",
   "A0":{"mean_g_bps":round(float(gA0.mean()),4),"sharpe":round(sr(gA0),4),"n":N},
   "grid":GRID,
   "n_cells_with_CI95_lower_bound_above_0":int(sum(1 for r in GRID if r["net_mean_g_CI95"][0]>0)),
   "n_cells":len(GRID)}
open(OUT+"/STEP4_GRID.json","w").write(json.dumps(R,indent=1))
print("GRID_DONE",R["n_cells_with_CI95_lower_bound_above_0"],"/",R["n_cells"])
