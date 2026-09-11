"""ROUND-2 INTEGRATION. Reads only frozen/produced artifacts; writes nothing outside r3_integrate.
Statistic copied from judge_v4: g = net_ex/gross_total, bps/anchor/unit gross, UTC-day block bootstrap
2000 resamples, rng numpy.default_rng([20260905,k])."""
import numpy as np, json, os, sys
HC="/workspace/review_scratch/health_check"
U="/workspace/uplift_2026-09-11"
def rd(path,key=None):
    Z=np.load(path,allow_pickle=True)
    k = key if key else ("rec" if "rec" in Z else "d30_n2_c42_rec")
    R=np.asarray(Z[k],float); cols=[str(c) for c in Z["cols"]]
    ix={c:i for i,c in enumerate(cols)}
    ts=R[:,ix["ts"]].astype(np.int64)
    out={c:R[:,ix[c]] for c in ("net_ex","pnl_ex","carry_ex","cost_ex","gross_total","turnover","w3_fund")}
    g=np.where(out["gross_total"]>0, out["net_ex"]/np.maximum(out["gross_total"],1e-12), np.nan)
    return ts,g,out
ARMS={
 "A0_s42":   (HC+"/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz","d30_n2_c42_rec"),
 "A0_s2027": (HC+"/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s2027.npz","d30_n2_c42_rec"),
 "XIB_s42":  (U+"/infra2/arms/w10_ablation_series_V4_XIBLAG50_dyn_s42.npz","d30_n2_c42_rec"),
 "XIB_s2027":(U+"/infra2/arms/w10_ablation_series_V4_XIBLAG50_dyn_s2027.npz","d30_n2_c42_rec"),
 "AMI_lag":  (U+"/infra1_cost/out/SL_ORTHLAG_STD_s42.npz",None),
 "AMI_r1":   (U+"/trackD_v4/SL_ORTH_f_amihud_24h__p.npz",None),
 "RS_s42":   (U+"/r3_integrate/out/RS_RESID_SHARPE_s42_STD.npz",None),
 "RS_s2027": (U+"/r3_integrate/out/RS_RESID_SHARPE_s2027_STD.npz",None),
}
for tag in ("X1","X2","X3","H0"):
    ARMS["AMI_lag_"+tag]=(U+"/infra1_cost/out/SL_ORTHLAG_%s_s42.npz"%tag,None)
    ARMS["RS_s42_"+tag]=(U+"/r3_integrate/out/RS_RESID_SHARPE_s42_%s.npz"%tag,None)
    ARMS["RS_s2027_"+tag]=(U+"/r3_integrate/out/RS_RESID_SHARPE_s2027_%s.npz"%tag,None)
    ARMS["A0_s42_"+tag]=(U+"/infra1_cost/out/IB_PAR_%s_s42.npz"%tag,None)
    ARMS["XIB_s42_"+tag]=(U+"/infra1_cost/out/IB_LAG50_%s_s42.npz"%tag,None)
    ARMS["A0_s2027_"+tag]=(U+"/infra1_cost/out/IB_PAR_%s_s2027.npz"%tag,None)
    ARMS["XIB_s2027_"+tag]=(U+"/infra1_cost/out/IB_LAG50_%s_s2027.npz"%tag,None)
D={}
for k,(p,key) in ARMS.items():
    if not os.path.exists(p): print("MISSING",k,p); continue
    D[k]=rd(p,key)
T0=np.datetime64("2022-01-01T00:00:00"); 
def epoch(s): return int((np.datetime64(s)-np.datetime64("1970-01-01T00:00:00"))/np.timedelta64(1,"s"))
SPANS={"FULL":(epoch("2022-01-01T00:00"),epoch("2026-08-10T20:00")),
       "F23":(epoch("2023-01-01T00:00"),epoch("2026-08-10T20:00")),
       "FROZEN":(epoch("2025-03-01T00:00"),epoch("2026-08-10T20:00")),
       "EXT":(epoch("2026-08-11T00:00"),epoch("2026-08-31T23:00"))}
def series(k,span,postwarm=True):
    ts,g,c=D[k]
    lo,hi=SPANS[span]
    m=(ts>=lo)&(ts<=hi)&np.isfinite(g)
    if postwarm:
        # E-0911-A: drop LOOK=900 seat warm-up rows -> identified by w3_fund != 1 for LEGS=001,
        # or simply the first 900 rows of the arm's own device axis
        warm=np.zeros(len(ts),bool); warm[:900]=True
        m &= ~warm
    return ts[m],g[m]
def sr(x): 
    return float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(2190)) if len(x)>2 else float("nan")
def common(keys,span,postwarm=True):
    S=[series(k,span,postwarm) for k in keys]
    ts=S[0][0]
    for t,_ in S[1:]: ts=np.intersect1d(ts,t)
    out=[]
    for (t,g) in S:
        ix=np.searchsorted(t,ts); assert np.array_equal(t[ix],ts)
        out.append(g[ix])
    return ts,np.array(out)
def dayblocks(ts):
    d=(ts//86400).astype(np.int64); u,inv=np.unique(d,return_inverse=True)
    return [np.where(inv==i)[0] for i in range(len(u))]
def boot_sr(w,G,ts,k=9,B=2000):
    blocks=dayblocks(ts); rng=np.random.default_rng([20260905,k]); nb=len(blocks)
    r=w@G; out=np.empty(B)
    for b in range(B):
        pick=rng.integers(0,nb,nb)
        idx=np.concatenate([blocks[i] for i in pick])
        x=r[idx]; out[b]=np.mean(x)/np.std(x,ddof=1)*np.sqrt(2190)
    return float(np.percentile(out,2.5)),float(np.percentile(out,97.5))
def report(keys,span,postwarm=True,label=""):
    ts,G=common(keys,span,postwarm)
    n=G.shape[1]
    mu=G.mean(1); sd=G.std(1,ddof=1); srs=mu/sd*np.sqrt(2190)
    C=np.corrcoef(G)
    lam=np.linalg.eigvalsh(C); neff=float(lam.sum()**2/ (lam**2).sum())
    Sig=np.cov(G); w=np.linalg.solve(Sig,mu); 
    wn=w/np.abs(w).sum()
    rp=wn@G; SRp=sr(rp)
    # equal-unit-vol fixed weights (no fitting)
    we=(1/sd); we=we/np.abs(we).sum(); SRe=sr(we@G)
    res=dict(label=label,span=span,n=int(n),keys=keys,
             SR={k:round(float(s),4) for k,s in zip(keys,srs)},
             mean_g={k:round(float(m),4) for k,m in zip(keys,mu)},
             corr=[[round(float(C[i,j]),4) for j in range(len(keys))] for i in range(len(keys))],
             N_eff=round(neff,4), w_opt={k:round(float(x),4) for k,x in zip(keys,wn)},
             SR_opt=round(SRp,4), SR_equalvol=round(SRe,4), SE=round(float(np.sqrt(2190/n)),4),
             SR_zero_corr_ideal=round(float(np.sqrt((srs**2).sum())),4))
    res["SR_opt_CI95"]=[round(x,4) for x in boot_sr(wn,G,ts)]
    res["SR_equalvol_CI95"]=[round(x,4) for x in boot_sr(we,G,ts)]
    return res
if __name__=="__main__":
    OUT={}
    avail=set(D)
    # levels table
    lv={}
    for k in sorted(D):
        row={}
        for sp in SPANS:
            for pw in (True,False):
                t,g=series(k,sp,pw)
                if len(g)>2: row["%s%s"%(sp,"_pw" if pw else "")]=dict(n=len(g),g=round(float(g.mean()),4),SR=round(sr(g),4))
        lv[k]=row
    OUT["levels"]=lv
    print(json.dumps(OUT["levels"],indent=1))
    json.dump(OUT,open("/workspace/uplift_2026-09-11/r3_integrate/LEVELS.json","w"),indent=1)
