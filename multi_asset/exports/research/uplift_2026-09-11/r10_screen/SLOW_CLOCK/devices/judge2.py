"""r10 SLOW_CLOCK judge part 2. usage: judge2.py {STD|PWR}
(b) TRAIN-fitted subset selection, HOLDOUT evaluation (no outcome leakage into the choice)
(c) CONTAMINATED full-sample ceiling, explicitly labelled
(d) G4 offset spectrum on the pinned RAW target (meta_newprod_v4.y4)"""
import numpy as np, calendar, time, json, hashlib, os, sys
ENV_WL=["CAL","LEGS","PHI","FTRIM","WRULE","LOOK","MEMBERS_TOPN","UMASK_SCOPE","UMASK_NPZ",
 "COSTB_JSON","SLOW_NPY","FSEED","FPRED","FEMAT_NPZ","OUT_TAG","EXPORT_PANEL","EMA_STATE_JSON",
 "PANEL_IN","JUDGE_HC","TILT","TILT_TAU","TILT_K"]
assert not [k for k in ENV_WL if k in os.environ]
MODE=sys.argv[1]
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<22),b''): h.update(b)
    return h.hexdigest()
U="/workspace/uplift_2026-09-11"; R2=U+"/r2_horizon"; W10=U+"/r10_slowclock"
HCP="/workspace/review_scratch/health_check/dev_v4/probe_artifacts"
R8=U+"/r8b2/dev/probe_artifacts"
WARM=900; CUT=T(2026,8,30,20); APY=2190; B=2000
TRAIN_END=T(2024,12,31,20); HOLD_S=T(2025,1,1,0)
S12=json.load(open(W10+"/rc/S12.json")); SIGN=S12["S4_step4_sign_from_TRAIN_mean_g_only"]
Q=S12["S4_step3_Q_selected_by_rho_train_only"]
A0P=(R8+"/w10_ablation_series_R8_A0_s42.npz") if MODE=="PWR" else (HCP+"/w10_ablation_series_V4_A0_dyn_s42.npz")
Z=np.load(A0P,allow_pickle=True); cols=[str(c) for c in Z["cols"]]; ix={c:i for i,c in enumerate(cols)}
AA=np.asarray(Z["d30_n2_c42_rec"],float); ts_all=np.round(AA[:,ix["ts"]]).astype(np.int64)
sel=np.arange(len(ts_all))[WARM:]; sel=sel[ts_all[sel]<=CUT]; TS=ts_all[sel]; assert len(TS)==9138
def ser(A):
    return dict(g=(A[:,ix["net_ex"]]/A[:,ix["gross_total"]])[sel],
                pnl=(A[:,ix["pnl_ex"]]/A[:,ix["gross_total"]])[sel],
                cost=(A[:,ix["cost_ex"]]/A[:,ix["gross_total"]])[sel],
                carry=(A[:,ix["carry_ex"]]/A[:,ix["gross_total"]])[sel],
                turn=A[:,ix["turnover"]][sel])
A0=ser(AA)
def loadarm(f):
    p=(W10+"/out/PWR_%s%s.npz"%(f,SIGN[f])) if MODE=="PWR" else (R2+"/out/%s%s.npz"%(f,SIGN[f]))
    Zz=np.load(p,allow_pickle=True); assert [str(c) for c in Zz["cols"]]==cols
    A=np.asarray(Zz["rec"],float); assert np.array_equal(np.round(A[:,ix["ts"]]).astype(np.int64),ts_all)
    return ser(A)
ARMS={f:loadarm(f) for f in Q}
tr=TS<=TRAIN_END; ho=TS>=HOLD_S
def sr(x): return float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(APY))
def blocks(ts):
    dd=ts//86400; ud,inv=np.unique(dd,return_inverse=True); nd=len(ud)
    order=np.argsort(inv,kind="stable"); st=np.searchsorted(inv[order],np.arange(nd)); en=np.append(st[1:],len(order))
    return order,st,en,nd
def bs(ts,fn,k):
    order,st,en,nd=blocks(ts); rng=np.random.default_rng([20260905,k]); out=np.empty(B)
    for b in range(B):
        pick=rng.integers(0,nd,nd); ii=np.concatenate([order[st[j]:en[j]] for j in pick]); out[b]=fn(ii)
    return out
def ci(v,lo=2.5,hi=97.5):
    v=v[np.isfinite(v)]; return [round(float(np.percentile(v,lo)),4),round(float(np.percentile(v,hi)),4)]
def mix(keys):
    return {k:np.mean([ARMS[f][k] for f in keys],axis=0) for k in ("g","pnl","cost","carry","turn")}
def blk(d,m,k0):
    x=d["g"][m]
    return {"n":int(m.sum()),"mean_g":round(float(x.mean()),4),"CI95":ci(bs(TS[m],lambda ii:x[ii].mean(),k0)),
            "ann_sharpe":round(sr(x),4),"SE":round(float(np.sqrt(APY/m.sum())),4),
            "gross_before_cost":round(float((d["pnl"][m]-d["carry"][m]).mean()),4),
            "cost_ex":round(float(d["cost"][m].mean()),4),"turnover":round(float(d["turn"][m].mean()),5),
            "cost_survival_pct":round(100*float(x.mean())/float((d["pnl"][m]-d["carry"][m]).mean()),1),
            "rho_to_A0":round(float(np.corrcoef(x,A0["g"][m])[0,1]),4)}
OUT={"mode":MODE,"n":len(TS)}
# (b) TRAIN-fitted subsets
trS={f:sr(ARMS[f]["g"][tr]) for f in Q}
order=sorted(Q,key=lambda f:-trS[f])
OUT["b_train_sharpe_rank"]={f:round(trS[f],4) for f in order}
OUT["b_heldout_eval_of_TRAIN_fitted_topk"]={}
for k in (1,3,5,8,13):
    keys=order[:k]; d=mix(keys)
    OUT["b_heldout_eval_of_TRAIN_fitted_topk"]["top%d"%k]={
      "members_chosen_on_TRAIN_only":[f+SIGN[f] for f in keys],
      "TRAIN":blk(d,tr,300+k),"HOLDOUT":blk(d,ho,400+k)}
# (c) CONTAMINATED ceiling: full-sample best
fuS={f:sr(ARMS[f]["g"]) for f in Q}
fo=sorted(Q,key=lambda f:-fuS[f]); ALL=np.ones(len(TS),bool)
OUT["c_CONTAMINATED_fullsample_ceiling"]={"full_sample_sharpe_rank":{f:round(fuS[f],4) for f in fo}}
for k in (1,3,4,5):
    keys=fo[:k]; d=mix(keys)
    OUT["c_CONTAMINATED_fullsample_ceiling"]["top%d"%k]={"members":[f+SIGN[f] for f in keys],"FULL":blk(d,ALL,500+k)}
TBF=[f for f in Q if "TBF" in f and f.startswith("C_")]
d=mix(TBF); OUT["c_CONTAMINATED_fullsample_ceiling"]["TBF_ladder_3d_7d_14d_30d"]={
  "members":[f+SIGN[f] for f in TBF],"FULL":blk(d,ALL,560),"TRAIN":blk(d,tr,561),"HOLDOUT":blk(d,ho,562)}
json.dump(OUT,open(W10+"/rc/JUDGE2_%s.json"%MODE,"w"),indent=1)
print(json.dumps(OUT,indent=1))
