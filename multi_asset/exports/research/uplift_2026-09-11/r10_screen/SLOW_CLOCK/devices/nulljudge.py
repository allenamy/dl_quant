import numpy as np, calendar, json, hashlib, os, sys
ENV_WL=["CAL","LEGS","PHI","FTRIM","WRULE","LOOK","MEMBERS_TOPN","UMASK_SCOPE","UMASK_NPZ","COSTB_JSON",
 "SLOW_NPY","FSEED","FPRED","FEMAT_NPZ","OUT_TAG","EXPORT_PANEL","EMA_STATE_JSON","PANEL_IN","JUDGE_HC"]
assert not [k for k in ENV_WL if k in os.environ]
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
W10="/workspace/uplift_2026-09-11/r10_slowclock"; APY=2190; B=2000
WARM=900; CUT=T(2026,8,30,20); HOLD_S=T(2025,1,1,0); TRAIN_END=T(2024,12,31,20)
R8="/workspace/uplift_2026-09-11/r8b2/dev/probe_artifacts/w10_ablation_series_R8_A0_s42.npz"
Z=np.load(R8,allow_pickle=True); cols=[str(c) for c in Z["cols"]]; ix={c:i for i,c in enumerate(cols)}
AA=np.asarray(Z["d30_n2_c42_rec"],float); ts=np.round(AA[:,ix["ts"]]).astype(np.int64)
sel=np.arange(len(ts))[WARM:]; sel=sel[ts[sel]<=CUT]; TS=ts[sel]; assert len(TS)==9138
A0g=(AA[:,ix["net_ex"]]/AA[:,ix["gross_total"]])[sel]
def sr(x): return float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(APY))
def blocks(t):
    dd=t//86400; ud,inv=np.unique(dd,return_inverse=True); nd=len(ud)
    o=np.argsort(inv,kind="stable"); st=np.searchsorted(inv[o],np.arange(nd)); en=np.append(st[1:],len(o))
    return o,st,en,nd,inv,ud
def bs(t,x,k):
    o,st,en,nd,_,_=blocks(t); rng=np.random.default_rng([20260905,k]); out=np.empty(B)
    for b in range(B):
        p=rng.integers(0,nd,nd); ii=np.concatenate([o[st[j]:en[j]] for j in p]); out[b]=x[ii].mean()
    return out
def ci(v): return [round(float(np.percentile(v,2.5)),4),round(float(np.percentile(v,97.5)),4)]
RAWD={}
def Lraw(tag):
    Zz=np.load(W10+"/out/%s.npz"%tag,allow_pickle=True); A=np.asarray(Zz["rec"],float)
    tt=np.round(A[:,ix["ts"]]).astype(np.int64)
    return tt,A,json.loads(str(Zz["config_json"]))
TAGS=["NUL_%s_%s"%(b,s) for b in ("T3","TLAD") for s in ("REAL","RELAB1","RELAB2","RELAB3","SHIFT101","SHIFT503","SHIFT1009")]
common=set(TS.tolist())
for t in TAGS:
    tt,_,_=Lraw(t); common &= set(tt.tolist())
COMMON=np.array(sorted(common),dtype=np.int64)
def L(tag):
    tt,A,cfg=Lraw(tag); pos={int(v):i for i,v in enumerate(tt)}
    j=np.array([pos[int(v)] for v in COMMON])
    return dict(g=(A[:,ix["net_ex"]]/A[:,ix["gross_total"]])[j],
                pnl=(A[:,ix["pnl_ex"]]/A[:,ix["gross_total"]])[j],
                carry=(A[:,ix["carry_ex"]]/A[:,ix["gross_total"]])[j],
                cost=(A[:,ix["cost_ex"]]/A[:,ix["gross_total"]])[j],
                turn=A[:,ix["turnover"]][j], cfg=cfg)
posA={int(v):i for i,v in enumerate(TS)}
jA=np.array([posA[int(v)] for v in COMMON])
A0g=A0g[jA]; TS=COMMON
OUT={"caliber":"g=net_ex/gross_total bps/anchor/unit gross; post-warm 900; cut 2026-08-30 20Z; COSTB=costb_PWR_G230k.json","n_common_axis_all_arms_and_nulls":int(len(COMMON)),"n_pinned_axis":9138,
     "null_families":"RELAB1-3 (one FIXED symbol permutation at every anchor) + SHIFT101/503/1009 (whole score matrix advanced k anchors); both preserve per-anchor rank distribution and lag-1 persistence => TURNOVER MATCHED",
     "note":"the per-anchor permutation placebo is DEFECTIVE and is NOT used","results":{}}
ho=TS>=HOLD_S; tr=TS<=TRAIN_END
for base in ("T3","TLAD"):
    d={}
    for suf in ("REAL","RELAB1","RELAB2","RELAB3","SHIFT101","SHIFT503","SHIFT1009"):
        a=L("NUL_%s_%s"%(base,suf))
        d[suf]={"mean_g":round(float(a["g"].mean()),4),"ann_sharpe":round(sr(a["g"]),4),
                "turnover":round(float(a["turn"].mean()),5),
                "CI95":ci(bs(TS,a["g"],hash(base+suf)%9000+1)),
                "holdout_mean_g":round(float(a["g"][ho].mean()),4),"holdout_sharpe":round(sr(a["g"][ho]),4),
                "COSTB":a["cfg"]["COSTB_JSON"].split("/")[-1]}
    nulls=[d[s]["mean_g"] for s in d if s!="REAL"]
    nsr=[d[s]["ann_sharpe"] for s in d if s!="REAL"]
    hns=[d[s]["holdout_mean_g"] for s in d if s!="REAL"]
    tn=[d[s]["turnover"] for s in d if s!="REAL"]
    d["_verdict"]={"real_mean_g":d["REAL"]["mean_g"],"null_max_mean_g":round(max(nulls),4),
        "null_min_mean_g":round(min(nulls),4),"real_beats_all_nulls_FULL":bool(d["REAL"]["mean_g"]>max(nulls)),
        "real_sharpe":d["REAL"]["ann_sharpe"],"null_max_sharpe":round(max(nsr),4),
        "real_holdout_mean_g":d["REAL"]["holdout_mean_g"],"null_max_holdout_mean_g":round(max(hns),4),
        "real_beats_all_nulls_HOLDOUT":bool(d["REAL"]["holdout_mean_g"]>max(hns)),
        "turnover_match":{"real":d["REAL"]["turnover"],"null_min":round(min(tn),5),"null_max":round(max(tn),5)}}
    OUT["results"][base]=d
# downside + arithmetic for the best case (TLAD real and T3 real)
def dstats(x):
    _,_,_,_,inv,ud=blocks(TS)
    day=np.array([x[inv==i].sum() for i in range(len(ud))]); c=np.cumsum(x); dd=c-np.maximum.accumulate(c)
    return {"maxDD_bps":round(float(-dd.min()),1),"worst_UTC_day_bps":round(float(day.min()),2),
            "worst5":[round(float(v),2) for v in np.sort(day)[:5]],
            "pct_anchors_negative":round(float((x<0).mean()),4)}
_,_,_,_,inv,ud=blocks(TS)
A0d=np.array([A0g[inv==i].sum() for i in range(len(ud))])
OUT["downside"]={"A0":dstats(A0g)}
ARI={}
for base in ("T3","TLAD"):
    x=L("NUL_%s_REAL"%base)["g"]
    OUT["downside"][base]=dstats(x)
    r=float(np.corrcoef(x,A0g)[0,1]); s1=sr(A0g); s2=sr(x)
    rows={}
    for w in (0.0,0.1,0.2,0.25,0.3,0.4,0.5):
        y=(1-w)*A0g+w*x
        day=np.array([y[inv==i].sum() for i in range(len(ud))]); c=np.cumsum(y); dd=c-np.maximum.accumulate(c)
        rows["w=%.2f"%w]={"mean_g":round(float(y.mean()),4),"ann_sharpe":round(sr(y),4),
           "holdout_sharpe":round(sr(y[ho]),4),"worst_UTC_day_bps":round(float(day.min()),2),
           "maxDD_bps":round(float(-dd.min()),1)}
    # analytic optimum
    m1,m2=A0g.mean(),x.mean(); v1,v2=A0g.var(ddof=1),x.var(ddof=1); c12=np.cov(A0g,x,ddof=1)[0,1]
    best=max(np.arange(0,1.001,0.001),key=lambda w: ((1-w)*m1+w*m2)/np.sqrt(max((1-w)**2*v1+w**2*v2+2*w*(1-w)*c12,1e-30)))
    y=(1-best)*A0g+best*x
    ARI[base]={"rho_to_A0":round(r,4),"A0_sharpe":round(s1,4),"cand_sharpe":round(s2,4),
      "grid":rows,"argmax_w":round(float(best),3),"argmax_sharpe":round(sr(y),4),
      "argmax_CI95_mean_g":ci(bs(TS,y,777)),
      "SE":round(float(np.sqrt(APY/len(TS))),4),
      "gap_to_3.966_in_SE":round((3.966-sr(y))/float(np.sqrt(APY/len(TS))),2)}
OUT["arithmetic"]=ARI
json.dump(OUT,open(W10+"/rc/NULLS.json","w"),indent=1)
print(json.dumps(OUT,indent=1))
