"""r10 SLOW_CLOCK judge. usage: judge.py {STD|PWR}
STD = archived r2_horizon arms at costb_fee_steady; PWR = r10 reprice at costb_PWR_G230k.
Axis: rec[900:], ts<=2026-08-30 20Z, n=9138. g=net_ex/gross_total bps/anchor/unit gross."""
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
R8="/workspace/uplift_2026-09-11/r8b2/dev/probe_artifacts"
WARM=900; CUT=T(2026,8,30,20); APY=2190; B=2000
TRAIN_END=T(2024,12,31,20); HOLD_S=T(2025,1,1,0)
S12=json.load(open(W10+"/rc/S12.json")); SIGN=S12["S4_step4_sign_from_TRAIN_mean_g_only"]
Q=S12["S4_step3_Q_selected_by_rho_train_only"]
A0P=(R8+"/w10_ablation_series_R8_A0_s42.npz","d30_n2_c42_rec") if MODE=="PWR" else \
    (HCP+"/w10_ablation_series_V4_A0_dyn_s42.npz","d30_n2_c42_rec")
Z=np.load(A0P[0],allow_pickle=True); cols=[str(c) for c in Z["cols"]]; ix={c:i for i,c in enumerate(cols)}
AA=np.asarray(Z[A0P[1]],float); ts_all=np.round(AA[:,ix["ts"]]).astype(np.int64)
sel=np.arange(len(ts_all))[WARM:]; sel=sel[ts_all[sel]<=CUT]; TS=ts_all[sel]
assert len(TS)==9138, len(TS)
def ser(A):
    return dict(g=(A[:,ix["net_ex"]]/A[:,ix["gross_total"]])[sel],
                pnl=(A[:,ix["pnl_ex"]]/A[:,ix["gross_total"]])[sel],
                cost=(A[:,ix["cost_ex"]]/A[:,ix["gross_total"]])[sel],
                carry=(A[:,ix["carry_ex"]]/A[:,ix["gross_total"]])[sel],
                turn=A[:,ix["turnover"]][sel], netlong=A[:,ix["netlong"]][sel])
A0=ser(AA)
def loadarm(f):
    if MODE=="PWR": p=W10+"/out/PWR_%s%s.npz"%(f,SIGN[f])
    else:           p=R2+"/out/%s%s.npz"%(f,SIGN[f])
    Zz=np.load(p,allow_pickle=True); cc=[str(c) for c in Zz["cols"]]; assert cc==cols
    A=np.asarray(Zz["rec"] if "rec" in Zz else Zz["d30_n2_c42_rec"],float)
    tt=np.round(A[:,ix["ts"]]).astype(np.int64); assert np.array_equal(tt,ts_all), f
    d=ser(A); d["sha16"]=sha(p)[:16]; d["cfg"]=json.loads(str(Zz["config_json"])); d["path"]=p
    return d
ARMS={f:loadarm(f) for f in Q}
# ---- book-layer equal-gross combination ----
def combo(keys):
    o={}
    for k in ("g","pnl","cost","carry","turn","netlong"):
        o[k]=np.mean([ARMS[f][k] for f in keys],axis=0)
    return o
CG=combo(Q)
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
def rho(a,b): return float(np.corrcoef(a,b)[0,1])
tr=TS<=TRAIN_END; ho=TS>=HOLD_S
OUT={"mode":MODE,"n":len(TS),"SE_ann_sharpe":round(float(np.sqrt(APY/len(TS))),4),
     "A0_path":A0P[0],"A0_sha16":sha(A0P[0])[:16],"Q":Q,"SIGN":SIGN,
     "arm_sha16":{f:ARMS[f]["sha16"] for f in Q},
     "costb_in_config":{f:ARMS[f]["cfg"].get("COSTB_JSON") for f in Q},
     "A0":{"mean_g":round(float(A0["g"].mean()),4),"sharpe":round(sr(A0["g"]),4),
           "pnl_ex":round(float(A0["pnl"].mean()),4),"cost":round(float(A0["cost"].mean()),4),
           "turn":round(float(A0["turn"].mean()),5)}}
# ---- per-arm ----
PA={}
for f in Q:
    a=ARMS[f]
    PA[f]={"arm":f+SIGN[f],"mean_g":round(float(a["g"].mean()),4),"sharpe":round(sr(a["g"]),4),
      "pnl_ex":round(float(a["pnl"].mean()),4),"cost":round(float(a["cost"].mean()),4),
      "carry":round(float(a["carry"].mean()),4),"turn":round(float(a["turn"].mean()),5),
      "rho_full":round(rho(a["g"],A0["g"]),4),"rho_train":round(rho(a["g"][tr],A0["g"][tr]),4),
      "rho_hold":round(rho(a["g"][ho],A0["g"][ho]),4),
      "hold_mean_g":round(float(a["g"][ho].mean()),4),"hold_sharpe":round(sr(a["g"][ho]),4),
      "cost_survival_pct":round(100*float(a["g"].mean())/float(a["pnl"].mean()-a["carry"].mean()),1) if abs(a["pnl"].mean()-a["carry"].mean())>1e-9 else None}
OUT["per_arm"]=PA
# ---- combination ----
def blk(d,m,tag,k0):
    x=d["g"][m]; t=TS[m]
    return {"n":int(m.sum()),"mean_g":round(float(x.mean()),4),
            "CI95":ci(bs(t,lambda ii: x[ii].mean(),k0)),
            "ann_sharpe":round(sr(x),4),"SE":round(float(np.sqrt(APY/m.sum())),4),
            "gross_pnl_ex":round(float(d["pnl"][m].mean()),4),
            "carry_ex":round(float(d["carry"][m].mean()),4),
            "cost_ex":round(float(d["cost"][m].mean()),4),
            "turnover":round(float(d["turn"][m].mean()),5),
            "cost_survival_pct_of_gross":round(100*float(x.mean())/float(d["pnl"][m].mean()-d["carry"][m].mean()),1)}
ALL=np.ones(len(TS),bool)
OUT["COMBO_G_bookLayer_equalGross"]={"members":[f+SIGN[f] for f in Q],
  "FULL":blk(CG,ALL,"full",11),"TRAIN":blk(CG,tr,"train",12),"HOLDOUT":blk(CG,ho,"hold",13)}
# pure-rho single
pr=S12["S4_step6_pure_rho_single"]
OUT["PURE_RHO_SINGLE"]={"arm":pr+SIGN.get(pr,"?")}
if pr in ARMS:
    OUT["PURE_RHO_SINGLE"].update({"FULL":blk(ARMS[pr],ALL,"f",14),"HOLDOUT":blk(ARMS[pr],ho,"h",15)})
# ---- independence ----
def rho_ci(a,b,ts,k):
    order,st,en,nd=blocks(ts); rng=np.random.default_rng([20260905,k]); out=np.empty(B)
    for bb in range(B):
        pick=rng.integers(0,nd,nd); ii=np.concatenate([order[st[j]:en[j]] for j in pick])
        out[bb]=np.corrcoef(a[ii],b[ii])[0,1]
    return out
IND={"rho_uncond_full":round(rho(CG["g"],A0["g"]),4),
     "rho_uncond_full_CI95":ci(rho_ci(CG["g"],A0["g"],TS,21)),
     "rho_train":round(rho(CG["g"][tr],A0["g"][tr]),4),
     "rho_hold":round(rho(CG["g"][ho],A0["g"][ho]),4)}
# conditional on A0 bottom quintile: (a) per-anchor, (b) per UTC day
qa=np.quantile(A0["g"],0.20); ma=A0["g"]<=qa
IND["A0_bottom_quintile_ANCHOR"]={"threshold_g":round(float(qa),4),"n":int(ma.sum()),
  "rho":round(rho(CG["g"][ma],A0["g"][ma]),4),"CI95":ci(rho_ci(CG["g"][ma],A0["g"][ma],TS[ma],22)),
  "A0_mean_g":round(float(A0["g"][ma].mean()),4),"COMBO_mean_g":round(float(CG["g"][ma].mean()),4),
  "COMBO_CI95":ci(bs(TS[ma],lambda ii: CG["g"][ma][ii].mean(),23))}
dd=TS//86400; ud,inv=np.unique(dd,return_inverse=True)
dayA0=np.array([A0["g"][inv==i].mean() for i in range(len(ud))])
dayCB=np.array([CG["g"][inv==i].mean() for i in range(len(ud))])
qd=np.quantile(dayA0,0.20); md=dayA0<=qd
IND["A0_bottom_quintile_UTCDAY"]={"n_days":int(md.sum()),"rho_day":round(float(np.corrcoef(dayCB[md],dayA0[md])[0,1]),4),
  "A0_mean_day_g":round(float(dayA0[md].mean()),4),"COMBO_mean_day_g":round(float(dayCB[md].mean()),4),
  "rho_day_all":round(float(np.corrcoef(dayCB,dayA0)[0,1]),4)}
# per-arm conditional rho
IND["per_arm_rho_in_A0_bottom_quintile_anchors"]={f:round(rho(ARMS[f]["g"][ma],A0["g"][ma]),4) for f in Q}
OUT["INDEPENDENCE"]=IND
# ---- downside ----
M=np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz",allow_pickle=True)
E=M["E_ts"].astype(np.int64); Y=np.asarray(M["y4"],np.float64)
rm={int(t):i for i,t in enumerate(E)}; ri=np.array([rm.get(int(t),-1) for t in TS])
mkt=np.array([np.nanmean(Y[i]) if i>=0 else np.nan for i in ri])*1e4  # bps, EW universe
okm=np.isfinite(mkt)
def dstats(x,tag):
    c=np.cumsum(x); dd_=c-np.maximum.accumulate(c)
    day=np.array([x[inv==i].sum() for i in range(len(ud))])
    srt=np.sort(x)[::-1]; top=int(max(1,round(0.01*len(x))))
    bet=float(np.polyfit(mkt[okm],x[okm],1)[0])
    return {"maxDD_bps_per_unit_gross":round(float(-dd_.min()),1),
            "worst_UTC_day_bps":round(float(day.min()),2),
            "worst5_UTC_days_bps":[round(float(v),2) for v in np.sort(day)[:5]],
            "best_UTC_day_bps":round(float(day.max()),2),
            "share_of_total_net_from_top1pct_anchors":round(float(srt[:top].sum()/x.sum()),3) if x.sum()!=0 else None,
            "beta_to_EW_universe_ret":round(bet,5),
            "mean_netlong":None,"pct_anchors_negative":round(float((x<0).mean()),4)}
OUT["DOWNSIDE"]={"A0":dstats(A0["g"],"A0"),"COMBO_G":dstats(CG["g"],"C")}
OUT["DOWNSIDE"]["A0"]["mean_netlong"]=round(float(A0["netlong"].mean()),5)
OUT["DOWNSIDE"]["COMBO_G"]["mean_netlong"]=round(float(CG["netlong"].mean()),5)
# combined book at allocations
def comb_sr(w):
    x=w*CG["g"]+(1-w)*A0["g"]; return x
CB_={}
for w in (0.1,0.2,0.25,0.3,0.4,0.5):
    x=comb_sr(w)
    day=np.array([x[inv==i].sum() for i in range(len(ud))]); c=np.cumsum(x); dd_=c-np.maximum.accumulate(c)
    CB_["w=%.2f"%w]={"mean_g":round(float(x.mean()),4),"ann_sharpe":round(sr(x),4),
      "CI95_mean":ci(bs(TS,lambda ii: x[ii].mean(),int(100+w*100))),
      "worst_UTC_day_bps":round(float(day.min()),2),"maxDD_bps":round(float(-dd_.min()),1),
      "holdout_sharpe":round(sr(x[ho]),4)}
OUT["COMBINED_with_A0"]=CB_
OUT["TARGET_ARITH"]={"SE":round(float(np.sqrt(APY/len(TS))),4),
  "point_needed_for_CI95_lb_over_3":round(3.0+1.96*float(np.sqrt(APY/len(TS))),4),
  "brief_target":3.966}
json.dump(OUT,open(W10+"/rc/JUDGE_%s.json"%MODE,"w"),indent=1)
print(json.dumps({k:OUT[k] for k in ("mode","n","A0","COMBO_G_bookLayer_equalGross","INDEPENDENCE","DOWNSIDE","COMBINED_with_A0","PURE_RHO_SINGLE")},indent=1))
print("PER ARM")
for f in Q: print("%-12s"%f, PA[f])
