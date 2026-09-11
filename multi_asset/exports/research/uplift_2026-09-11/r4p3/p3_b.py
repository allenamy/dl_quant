"""P3 part B: pairwise N_eff, per-year averaged-rho vs conditional-rho arithmetic,
per-cell portfolio levels, and the rankdata-ranked sleeve check."""
import numpy as np, json, calendar, os
U="/workspace/uplift_2026-09-11"; R=U+"/r4p3"
def rd(p):
    Z=np.load(p,allow_pickle=True); k="rec" if "rec" in Z else "d30_n2_c42_rec"
    M=np.asarray(Z[k],float); cols=[str(c) for c in np.asarray(Z["cols"]).ravel()]
    ix={c:i for i,c in enumerate(cols)}
    ts=np.round(M[:,ix["ts"]]).astype(np.int64); gt=M[:,ix["gross_total"]]
    return ts,np.where(gt>0,M[:,ix["net_ex"]]/np.maximum(gt,1e-12),np.nan)
A={"A0_s42":U+"/r3k/arms/A0_PWR230k_s42.npz","A0_s2027":U+"/r3k/arms/A0_PWR230k_s2027.npz",
   "XIB_s42":U+"/r3k/arms/XIB_PWR230k_s42.npz","XIB_s2027":U+"/r3k/arms/XIB_PWR230k_s2027.npz",
   "AMI":R+"/arms/SL_ORTHLAG_PWR230k_s42.npz","AMI_RZ":R+"/arms/SL_ORTHLAG_RZ_PWR230k_s42.npz",
   "RS_s42":U+"/r3k/arms/RS_PWR230k_s42.npz"}
D={k:rd(p) for k,p in A.items()}
T=lambda y,m,d,h=0: calendar.timegm((y,m,d,h,0,0)); HI=T(2026,8,10,20)
WARM=900; WCUT=int(D["A0_s42"][0][WARM])
SP={"FULL_pw":(WCUT,HI),"F24on":(T(2024,1,1),HI),"FROZEN":(T(2025,3,1),HI)}
Z=np.load(U+"/trackF/regime_labels.npz",allow_pickle=True)
lmap={int(t):int(l) for t,l in zip(Z["ts"].astype(np.int64),np.asarray(Z["lab"]))}
NM={-1:"UNLAB",0:"LL",1:"LH",2:"HL",3:"HH"}
ANN=np.sqrt(2190.)
def sr(x): return float(np.mean(x)/np.std(x,ddof=1)*ANN)
def ser(k,sp):
    ts,g=D[k]; lo,hi=SP[sp]; m=(ts>=lo)&(ts<=hi)&np.isfinite(g); m[:WARM]=False
    return ts[m],g[m]
def com(ks,sp):
    S=[ser(k,sp) for k in ks]; t=S[0][0]
    for tt,_ in S[1:]: t=np.intersect1d(t,tt)
    return t,np.array([g[np.searchsorted(tt,t)] for tt,g in S])
def neff(C):
    l=np.linalg.eigvalsh(C); return float(l.sum()**2/(l**2).sum())
def blocks(ts):
    d=(ts//86400).astype(np.int64); u,inv=np.unique(d,return_inverse=True)
    return [np.where(inv==i)[0] for i in range(len(u))]
def boot(fn,ts,G,k=0,B=2000):
    bl=blocks(ts); rng=np.random.default_rng([20260905,k]); nb=len(bl); o=np.empty(B)
    for b in range(B): o[b]=fn(G[:,np.concatenate([bl[i] for i in rng.integers(0,nb,nb)])])
    return [round(float(np.percentile(o,2.5)),4),round(float(np.percentile(o,97.5)),4)]
O={}
# --- A. pairwise N_eff ---
O["A_pairwise_Neff"]={}
for sp in SP:
    r={}
    for ks in (["A0_s42","AMI"],["A0_s42","XIB_s42"],["XIB_s42","AMI"],["A0_s42","RS_s42"],
               ["A0_s42","XIB_s42","AMI"],["A0_s42","AMI","RS_s42"],["A0_s42","XIB_s42","AMI","RS_s42"]):
        t,G=com(ks,sp); C=np.corrcoef(G)
        r["+".join(ks)]={"n":int(G.shape[1]),"N_eff":round(neff(C),4),
           "rho":[[round(float(C[i,j]),4) for j in range(len(ks))] for i in range(len(ks))]}
    O["A_pairwise_Neff"][sp]=r
# --- B. per-year: averaged-rho arithmetic vs conditional-rho arithmetic vs realized ---
O["B_peryear_arith"]={}
for sd in ("s42","s2027"):
    ks=["A0_"+sd,"AMI"]; t,G=com(ks,"FULL_pw")
    rho_bar=float(np.corrcoef(G)[0,1]); sdv=G.std(1,ddof=1); we=(1/sdv)/np.sum(1/sdv)
    yr=np.array([int(str(np.datetime64(int(x),"s"))[:4]) for x in t]); rows={}
    for y in sorted(set(yr)):
        m=yr==y; g=G[:,m]; s1,s2=sr(g[0]),sr(g[1]); r=float(np.corrcoef(g)[0,1])
        sdy=g.std(1,ddof=1); wy=(1/sdy)/np.sum(1/sdy)
        def pred(rr,w=0.5): return float((w*s1+(1-w)*s2)/np.sqrt(w*w+(1-w)**2+2*w*(1-w)*rr))
        rows[str(y)]={"n":int(m.sum()),"SR_A0":round(s1,4),"SR_AMI":round(s2,4),
          "rho_year":round(r,4),"rho_bar_fullcycle":round(rho_bar,4),
          "SR_pred_with_rho_bar":round(pred(rho_bar),4),"SR_pred_with_rho_year":round(pred(r),4),
          "SR_realized_fixed_fullcycle_weights":round(sr(we@g),4),
          "SR_realized_year_eqvol_weights":round(sr(wy@g),4)}
        rows[str(y)]["avg_rho_error_vs_year_rho"]=round(rows[str(y)]["SR_pred_with_rho_bar"]-rows[str(y)]["SR_pred_with_rho_year"],4)
    O["B_peryear_arith"][sd]=rows
# --- C. per-cell / frozen A0+AMI portfolio levels (fixed full-cycle eq-vol weights, no refit) ---
O["C_percell_portfolio"]={}
for sd in ("s42","s2027"):
    ks=["A0_"+sd,"AMI"]; t,G=com(ks,"FULL_pw")
    sdv=G.std(1,ddof=1); we=(1/sdv)/np.sum(1/sdv); lb=np.array([lmap.get(int(x),-1) for x in t])
    rows={}
    for L in (-1,0,1,2,3):
        m=lb==L
        if m.sum()<50: continue
        g=G[:,m]
        rows[NM[L]]={"n":int(m.sum()),"rho":round(float(np.corrcoef(g)[0,1]),4),
          "SR_A0":round(sr(g[0]),4),"SR_AMI":round(sr(g[1]),4),"SR_port":round(sr(we@g),4),
          "N_eff":round(neff(np.corrcoef(g)),4)}
    fz=t>=SP["FROZEN"][0]; g=G[:,fz]
    rows["FROZEN_WINDOW"]={"n":int(fz.sum()),"rho":round(float(np.corrcoef(g)[0,1]),4),
      "SR_A0":round(sr(g[0]),4),"SR_AMI":round(sr(g[1]),4),"SR_port":round(sr(we@g),4),
      "SR_port_CI95_k0":boot(lambda X: sr(we@X),t[fz],g,0),"N_eff":round(neff(np.corrcoef(g)),4)}
    t2,G2=com(ks,"F24on"); sd2=G2.std(1,ddof=1); w2=(1/sd2)/np.sum(1/sd2)
    rows["2024on"]={"n":int(G2.shape[1]),"rho":round(float(np.corrcoef(G2)[0,1]),4),
      "SR_A0":round(sr(G2[0]),4),"SR_AMI":round(sr(G2[1]),4),"SR_port":round(sr(w2@G2),4),
      "SR_port_CI95_k0":boot(lambda X: sr(w2@X),t2,G2,0),"N_eff":round(neff(np.corrcoef(G2)),4)}
    O["C_percell_portfolio"][sd]=rows
# --- D. rankdata sleeve vs argsort sleeve ---
O["D_ranker_hole"]={}
for sp in SP:
    t,G=com(["AMI","AMI_RZ","A0_s42","XIB_s42"],sp)
    O["D_ranker_hole"][sp]={"n":int(G.shape[1]),
      "SR_AMI_argsort":round(sr(G[0]),4),"SR_AMI_rankdata":round(sr(G[1]),4),
      "g_argsort":round(float(G[0].mean()),4),"g_rankdata":round(float(G[1].mean()),4),
      "rho_argsort_rankdata":round(float(np.corrcoef(G[0],G[1])[0,1]),4),
      "maxabs_g_diff":round(float(np.max(np.abs(G[0]-G[1]))),4),
      "rho_A0_AMIrz":round(float(np.corrcoef(G[2],G[1])[0,1]),4),
      "rho_XIB_AMIrz":round(float(np.corrcoef(G[3],G[1])[0,1]),4)}
    sdv=G[[2,1]].std(1,ddof=1); w=(1/sdv)/np.sum(1/sdv)
    O["D_ranker_hole"][sp]["SR_A0+AMIrz_eqvol"]=round(sr(w@G[[2,1]]),4)
json.dump(O,open(R+"/RESULT_P3B.json","w"),indent=1); print(json.dumps(O,indent=1))
