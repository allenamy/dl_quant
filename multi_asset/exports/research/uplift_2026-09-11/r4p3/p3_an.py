"""ROUND-4 P3 ANALYSIS. Correlations never measured + regime-conditional portfolio re-solve.
Caliber: v4 chain. COST = FITTED /workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json (K=0.17).
STATISTIC g = net_ex/gross_total (bps/anchor/unit gross). Post-warm = drop first LOOK=900
device anchors (E-0911-A). Bootstrap = UTC-day block, 2000, rng default_rng([20260905,k])."""
import numpy as np, json, os, itertools, calendar
U="/workspace/uplift_2026-09-11"; R=U+"/r4p3"
def rd(p):
    Z=np.load(p,allow_pickle=True)
    k="rec" if "rec" in Z else "d30_n2_c42_rec"
    M=np.asarray(Z[k],float); cols=[str(c) for c in np.asarray(Z["cols"]).ravel()]
    ix={c:i for i,c in enumerate(cols)}
    ts=np.round(M[:,ix["ts"]]).astype(np.int64)
    gt=M[:,ix["gross_total"]]
    g=np.where(gt>0,M[:,ix["net_ex"]]/np.maximum(gt,1e-12),np.nan)
    return ts,g,{c:M[:,ix[c]] for c in cols if c!="ts"}
ARMS={
 "A0_s42"  : U+"/r3k/arms/A0_PWR230k_s42.npz",
 "A0_s2027": U+"/r3k/arms/A0_PWR230k_s2027.npz",
 "XIB_s42" : U+"/r3k/arms/XIB_PWR230k_s42.npz",
 "XIB_s2027":U+"/r3k/arms/XIB_PWR230k_s2027.npz",
 "AMI"     : R+"/arms/SL_ORTHLAG_PWR230k_s42.npz",
 "PAR_s42" : R+"/arms/IB_PAR_PWR230k_s42.npz",
 "PAR_s2027":R+"/arms/IB_PAR_PWR230k_s2027.npz",
 "MYXIB_s42": R+"/arms/IB_LAG50_PWR230k_s42.npz",
 "MYXIB_s2027": R+"/arms/IB_LAG50_PWR230k_s2027.npz",
 "RS_s42"  : U+"/r3k/arms/RS_PWR230k_s42.npz",
 "RS_s2027": U+"/r3k/arms/RS_PWR230k_s2027.npz",
}
D={}
for k,p in ARMS.items():
    if os.path.exists(p): D[k]=rd(p)
    else: print("MISSING",k,p)
OUT={"_meta":{"cost":"costb_PWR_G230k.json fitted K=0.17","arms":{k:ARMS[k] for k in D}}}
# --- cross-check: does my own LAG50 reproduce the round-3 XIB arm? ---
for s in ("s42","s2027"):
    if "MYXIB_"+s in D and "XIB_"+s in D:
        a=D["MYXIB_"+s][1]; b=D["XIB_"+s][1]
        na,nb=np.isnan(a),np.isnan(b)
        OUT.setdefault("XIB_reconstruction_check",{})[s]={
          "bitwise":bool(np.array_equal(na,nb) and np.array_equal(a[~na],b[~nb])),
          "maxabs":float(np.nanmax(np.abs(a-b)))}
T=lambda y,m,d,h=0: calendar.timegm((y,m,d,h,0,0))
HI=T(2026,8,10,20)
ts0=D["A0_s42"][0]; WARM=900; WCUT=int(ts0[WARM])
SPANS={"FULL_pw":(WCUT,HI),"F24on":(T(2024,1,1),HI),"F23":(T(2023,1,1),HI),
       "FROZEN":(T(2025,3,1),HI)}
OUT["_meta"]["warm_cut_utc"]=str(np.datetime64(WCUT,"s"))
# --- regime labels (round-2 expanding-median, strictly past) ---
Z=np.load(U+"/trackF/regime_labels.npz",allow_pickle=True)
ts_r=Z["ts"].astype(np.int64); LAB=np.asarray(Z["lab"])
lmap={int(t):int(LAB[i]) for i,t in enumerate(ts_r)}
NAMES={-1:"UNLAB",0:"LL",1:"LH",2:"HL",3:"HH"}
def series(k,span):
    ts,g,_=D[k]; lo,hi=SPANS[span]
    m=(ts>=lo)&(ts<=hi)&np.isfinite(g); m[:WARM]=False
    return ts[m],g[m]
def common(keys,span):
    S=[series(k,span) for k in keys]
    t=S[0][0]
    for tt,_ in S[1:]: t=np.intersect1d(t,tt)
    G=[]
    for (tt,g) in S:
        ix=np.searchsorted(tt,t); assert np.array_equal(tt[ix],t); G.append(g[ix])
    return t,np.array(G)
ANN=np.sqrt(2190.0)
def sr(x): return float(np.mean(x)/np.std(x,ddof=1)*ANN) if len(x)>2 else float("nan")
def dayblocks(ts):
    d=(ts//86400).astype(np.int64); u,inv=np.unique(d,return_inverse=True)
    return [np.where(inv==i)[0] for i in range(len(u))]
def boot(fn,ts,G,k=0,B=2000):
    bl=dayblocks(ts); rng=np.random.default_rng([20260905,k]); nb=len(bl); out=np.empty(B)
    for b in range(B):
        idx=np.concatenate([bl[i] for i in rng.integers(0,nb,nb)])
        out[b]=fn(G[:,idx])
    return [float(np.percentile(out,2.5)),float(np.percentile(out,97.5))]
def rho(G): return float(np.corrcoef(G[0],G[1])[0,1])
from scipy.stats import spearmanr, rankdata

# =========== 1. THE MISSING CORRELATIONS ===========
PAIRS=[("A0_s42","XIB_s42"),("A0_s42","AMI"),("XIB_s42","AMI"),
       ("A0_s2027","XIB_s2027"),("A0_s2027","AMI"),("XIB_s2027","AMI"),
       ("A0_s42","PAR_s42"),("PAR_s42","AMI"),("PAR_s42","XIB_s42"),
       ("A0_s42","RS_s42"),("XIB_s42","RS_s42"),("AMI","RS_s42")]
OUT["Q1_pairwise_rho"]={}
for span in ("FULL_pw","F24on"):
    row={}
    for a,b in PAIRS:
        if a not in D or b not in D: continue
        t,G=common([a,b],span)
        row[f"{a}|{b}"]={"n":int(G.shape[1]),"pearson":round(rho(G),4),
          "spearman":round(float(spearmanr(G[0],G[1]).statistic),4),
          "pearson_CI95_dayblock_k0":[round(x,4) for x in boot(rho,t,G,0)],
          "pearson_CI95_dayblock_k9":[round(x,4) for x in boot(rho,t,G,9)]}
    OUT["Q1_pairwise_rho"][span]=row
# levels
OUT["Q1_levels"]={}
for span in SPANS:
    r={}
    for k in D:
        t,g=series(k,span)
        r[k]={"n":len(g),"g_bps":round(float(g.mean()),4),"SR":round(sr(g),4),
              "sd":round(float(g.std(ddof=1)),4),"SE_SR":round(float(np.sqrt(2190/len(g))),4)}
    OUT["Q1_levels"][span]=r

# =========== 2. rho BY YEAR and BY REGIME CELL ===========
TRIOS={"s42":["A0_s42","XIB_s42","AMI"],"s2027":["A0_s2027","XIB_s2027","AMI"]}
OUT["Q2_rho_by_year"]={}; OUT["Q2_rho_by_cell"]={}; OUT["Q2_neff"]={}
for sd,ks in TRIOS.items():
    t,G=common(ks,"FULL_pw")
    yr=np.array([int(str(np.datetime64(int(x),"s"))[:4]) for x in t])
    lb=np.array([lmap.get(int(x),-1) for x in t])
    def mat(mask,label):
        n=int(mask.sum())
        if n<50: return {"n":n,"note":"too few"}
        C=np.corrcoef(G[:,mask]); lam=np.linalg.eigvalsh(C)
        return {"n":n,"SR":{k:round(sr(G[i][mask]),3) for i,k in enumerate(ks)},
                "g_bps":{k:round(float(G[i][mask].mean()),4) for i,k in enumerate(ks)},
                "rho_A0_XIB":round(float(C[0,1]),4),"rho_A0_AMI":round(float(C[0,2]),4),
                "rho_XIB_AMI":round(float(C[1,2]),4),
                "N_eff_eig":round(float(lam.sum()**2/(lam**2).sum()),4)}
    OUT["Q2_rho_by_year"][sd]={str(y):mat(yr==y,str(y)) for y in sorted(set(yr))}
    OUT["Q2_rho_by_year"][sd]["ALL"]=mat(np.ones(len(t),bool),"ALL")
    OUT["Q2_rho_by_cell"][sd]={NAMES[L]:mat(lb==L,NAMES[L]) for L in (-1,0,1,2,3)}
    OUT["Q2_rho_by_cell"][sd]["LABELLED_ALL"]=mat(lb>=0,"LAB")
    # frozen window
    fz=(t>=SPANS["FROZEN"][0])
    OUT["Q2_rho_by_cell"][sd]["FROZEN_WINDOW"]=mat(fz,"FROZEN")

# =========== 3. PORTFOLIO SOLVES ===========
def solve_mvo(G):
    mu=G.mean(1); S=np.cov(G)
    w=np.linalg.solve(S,mu); w=w/np.abs(w).sum(); return w
def solve_eqvol(G):
    sd=G.std(1,ddof=1); w=1/sd; return w/np.abs(w).sum()
def pred_sr_2asset(sr1,sr2,r,w1):
    # SR of w1*x1+(1-w1)*x2 with unit-vol-normalised legs
    w2=1-w1; num=w1*sr1+w2*sr2; den=np.sqrt(w1*w1+w2*w2+2*w1*w2*r)
    return float(num/den)
OUT["Q3_portfolio"]={}
for sd,ks in TRIOS.items():
    res={}
    t,G=common(ks,"FULL_pw")
    lb=np.array([lmap.get(int(x),-1) for x in t])
    yr=np.array([int(str(np.datetime64(int(x),"s"))[:4]) for x in t])
    srs=np.array([sr(G[i]) for i in range(3)]); sds=G.std(1,ddof=1)
    C=np.corrcoef(G); lam=np.linalg.eigvalsh(C)
    res["inputs"]={"keys":ks,"n":int(G.shape[1]),"SR":[round(float(x),4) for x in srs],
      "corr":[[round(float(C[i,j]),4) for j in range(3)] for i in range(3)],
      "N_eff_eig_3asset":round(float(lam.sum()**2/(lam**2).sum()),4),
      "eigs":[round(float(x),4) for x in lam[::-1]],
      "SR_zero_corr_ideal":round(float(np.sqrt((srs**2).sum())),4)}
    # --- pair solves, averaged rho, closed form vs realized ---
    for (i,j,nm) in ((0,2,"A0+AMI"),(0,1,"A0+XIB"),(1,2,"XIB+AMI")):
        g2=G[[i,j]]; t2=t
        we=solve_eqvol(g2); wm=solve_mvo(g2)
        r=float(np.corrcoef(g2)[0,1])
        # averaged-rho closed form at the equal-vol weights and at the optimal weights
        best_w=(srs[i]-r*srs[j])/(srs[i]+srs[j]-2*r*srs[j]) if abs(srs[i]+srs[j]-2*r*srs[j])>1e-9 else 0.5
        res[nm]={"rho_avg":round(r,4),
          "SR_eqvol_realized":round(sr(we@g2),4),
          "SR_eqvol_closedform":round(pred_sr_2asset(srs[i],srs[j],r,0.5),4),
          "w_eqvol":[round(float(x),4) for x in we],
          "SR_mvo_insample_realized":round(sr(wm@g2),4),
          "w_mvo":[round(float(x),4) for x in wm],
          "SR_mvo_closedform":round(float(np.sqrt(np.array([srs[i],srs[j]])@np.linalg.solve(np.corrcoef(g2),np.array([srs[i],srs[j]])))),4),
          "SR_eqvol_CI95_k0":[round(x,4) for x in boot(lambda X: sr(we@X),t2,g2,0)],
          "SR_eqvol_CI95_k9":[round(x,4) for x in boot(lambda X: sr(we@X),t2,g2,9)],
          "SR_mvo_CI95_k0":[round(x,4) for x in boot(lambda X: sr(wm@X),t2,g2,0)]}
    # 3-asset
    we3=solve_eqvol(G); wm3=solve_mvo(G)
    res["A0+XIB+AMI"]={"SR_eqvol_realized":round(sr(we3@G),4),"w_eqvol":[round(float(x),4) for x in we3],
      "SR_mvo_insample_realized":round(sr(wm3@G),4),"w_mvo":[round(float(x),4) for x in wm3],
      "SR_mvo_closedform":round(float(np.sqrt(srs@np.linalg.solve(C,srs))),4),
      "SR_eqvol_CI95_k0":[round(x,4) for x in boot(lambda X: sr(we3@X),t,G,0)],
      "SR_mvo_CI95_k0":[round(x,4) for x in boot(lambda X: sr(wm3@X),t,G,0)]}
    # --- regime-conditional solves ---
    # (a) in-sample per-cell MVO (upper bound)
    for pairnm,idx in (("A0+AMI",[0,2]),("A0+XIB+AMI",[0,1,2])):
        g=G[idx]
        w_static=solve_mvo(g); rp_static=w_static@g
        rp_cell=np.full(len(t),np.nan)
        cellw={}
        for L in (-1,0,1,2,3):
            m=lb==L
            if m.sum()<50:
                if m.sum()>0: rp_cell[m]=w_static@g[:,m]
                continue
            w=solve_mvo(g[:,m]); cellw[NAMES[L]]=[round(float(x),4) for x in w]
            rp_cell[m]=w@g[:,m]
        # (b) walk-forward per-cell: expanding, strictly past, same cell, min 250 obs else static-so-far
        rp_wf=np.full(len(t),np.nan); used=0
        for L in (-1,0,1,2,3):
            m=np.where(lb==L)[0]
            for pos,i in enumerate(m):
                if pos<250:
                    hist=np.arange(0,i)
                    if len(hist)<250: rp_wf[i]=solve_eqvol(g)@g[:,i]; continue
                    w=solve_mvo(g[:,hist])
                else:
                    w=solve_mvo(g[:,m[:pos]]); used+=1
                rp_wf[i]=w@g[:,i]
        ok=np.isfinite(rp_wf)
        res.setdefault("REGIME_CONDITIONAL",{})[pairnm]={
          "SR_static_mvo_insample":round(sr(rp_static),4),
          "SR_cellwise_mvo_insample":round(sr(rp_cell),4),
          "SR_cellwise_walkforward":round(sr(rp_wf[ok]),4),
          "n_wf":int(ok.sum()),"n_wf_cellfitted":used,
          "cell_weights_insample":cellw,
          "SR_cellwise_wf_CI95_k0":[round(x,4) for x in boot(lambda X: sr(X[0]),t[ok],rp_wf[ok][None,:],0)],
          "SR_static_CI95_k0":[round(x,4) for x in boot(lambda X: sr(w_static@X),t,g,0)]}
    OUT["Q3_portfolio"][sd]=res
json.dump(OUT,open(R+"/RESULT_P3.json","w"),indent=1)
print(json.dumps(OUT,indent=1))
