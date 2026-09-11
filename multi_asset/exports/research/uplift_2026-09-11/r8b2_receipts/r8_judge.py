"""BUILD 2 JUDGE. Reads the frozen prereg's three tests on all 9 declared arms.
Caliber: g = net_ex/gross_total, bps/4h anchor per unit gross; post-warm drop 900 (E-0911-A);
cut 2026-08-30 20Z (E-0911-D, every arm here is PHI=0.45); fitted cost costb_PWR_G230k.json.
Day-block bootstrap B=4000. Bonferroni K=9 => two-sided 99.44% CI for the primary gate."""
import numpy as np, calendar, time, json, hashlib, os, sys
ENV_WL=[]; assert all(k not in os.environ for k in ENV_WL)
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
U="/workspace/uplift_2026-09-11"; R=U+"/r8b2"; APY=2190; WARM=900; CUT=T(2026,8,30,20); B=4000
K_DECL=9; ALPHA=0.05/K_DECL; LO=100*ALPHA/2; HI=100-LO
FITCUT=T(2026,8,10,20); HS=T(2026,8,11,0); HE=T(2026,8,30,20)
GS=T(2026,8,19,0); GE=T(2026,8,21,20)
TAU=4.75
S=np.load(U+"/r7f1/out/sigma_variants.npz",allow_pickle=True)
C=[str(c) for c in S["cols"]]; SR_=S["rec"]; si={c:i for i,c in enumerate(C)}
GL=dict(zip(SR_[:,0].astype(np.int64),SR_[:,si["LIVE_sig"]]))
def load(tag,root=R+"/dev/probe_artifacts"):
    p=root+"/w10_ablation_series_%s.npz"%tag
    Z=np.load(p,allow_pickle=True); cc=[str(c) for c in Z["cols"]]; ix={c:i for i,c in enumerate(cc)}
    A=np.asarray(Z["d30_n2_c42_rec"],float)[WARM:]
    ts=np.round(A[:,ix["ts"]]).astype(np.int64); m=ts<=CUT
    d={"ts":ts[m],"g":(A[:,ix["net_ex"]]/A[:,ix["gross_total"]])[m],
       "pnl":(A[:,ix["pnl_ex"]]/A[:,ix["gross_total"]])[m],
       "cost":(A[:,ix["cost_ex"]]/A[:,ix["gross_total"]])[m],
       "carry":(A[:,ix["carry_ex"]]/A[:,ix["gross_total"]])[m],
       "turn":A[:,ix["turnover"]][m],"w3f":A[:,ix["w3_fund"]][m],
       "sig_int":(A[:,ix["sig_tilt"]][m] if "sig_tilt" in ix else None),
       "cfg":json.loads(str(Z["config_json"])),"sha16":hashlib.sha256(open(p,'rb').read()).hexdigest()[:16]}
    d["sig"]=np.array([GL.get(int(t),np.nan) for t in d["ts"]])
    return d
def sr(x): return float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(APY)) if len(x)>5 else float("nan")
def blocks(ts):
    dd=ts//86400; ud,inv=np.unique(dd,return_inverse=True); nd=len(ud)
    order=np.argsort(inv,kind="stable"); st=np.searchsorted(inv[order],np.arange(nd)); en=np.append(st[1:],len(order))
    return order,st,en,nd
def bstat(ts,fn,seed):
    order,st,en,nd=blocks(ts); rng=np.random.default_rng([20260912,seed])
    pick=rng.integers(0,nd,size=(B,nd)); out=np.empty(B)
    for b in range(B):
        ii=np.concatenate([order[st[j]:en[j]] for j in pick[b]]); out[b]=fn(ii)
    return out
def ci(v,lo=2.5,hi=97.5):
    v=v[np.isfinite(v)]
    return (float(np.percentile(v,lo)),float(np.percentile(v,hi))) if len(v) else (float("nan"),)*2
A0=load("R8_A0_s42")
YR=np.array([time.gmtime(int(t)).tm_year for t in A0["ts"]])
YEARS=sorted(set(YR.tolist()))
def theta_of(d,idx=None,yv=None):
    """year-FE effect = unweighted mean over calendar years of the per-year mean of d"""
    if yv is None: yv=YR
    if idx is None: idx=np.arange(len(d))
    y=yv[idx]; v=[]
    for yy in YEARS:
        m=y==yy
        if m.sum()>0: v.append(d[idx][m].mean())
    return float(np.mean(v)) if v else float("nan")
# sanity: the internally-computed sigma must equal the external LIVE gauge on a tilt arm
chk=load("R8_S50_s42")
ok_s=np.isfinite(chk["sig_int"])&np.isfinite(chk["sig"])
SIGCHK={"n":int(ok_s.sum()),"maxabs_internal_vs_LIVE_gauge":float(np.max(np.abs(chk["sig_int"][ok_s]-chk["sig"][ok_s]))),
        "n_internal_nonfinite":int((~np.isfinite(chk["sig_int"])).sum())}
print("SIGMA GAUGE CHECK",json.dumps(SIGCHK),flush=True)
GRID=["S00","S25","S50","S75","R00","R25","R50","P05","P10"]
OUT={"caliber":"g = net_ex/gross_total bps/anchor per unit gross; post-warm 900; cut 2026-08-30 20Z; fitted cost costb_PWR_G230k.json",
     "gauge":"LIVE 829-base INTER m1 CRYPTO umask","B":B,"K_declared":K_DECL,
     "bonferroni_ci_pct":round(100-100*ALPHA,2),"years":YEARS,"sigma_gauge_check":SIGCHK,
     "A0":{"n":len(A0["g"]),"mean_g":round(float(A0["g"].mean()),4),"SR":round(sr(A0["g"]),4),
           "turnover_mean":round(float(A0["turn"].mean()),5),"cost_mean_bps":round(float(A0["cost"].mean()),4)},
     "arms":{}}
print("A0",json.dumps(OUT["A0"]),flush=True)
for nm in GRID:
    a=load("R8_%s_s42"%nm)
    # An arm may legitimately DROP anchors: if the tilt drives w3 to the all-zero vector the device's
    # `if g < 1e-9: continue` skips the anchor (no book at all). Pair on the intersection and report it.
    com,ia,ib=np.intersect1d(a["ts"],A0["ts"],return_indices=True)
    n_drop=len(A0["ts"])-len(com)
    for k in ("g","pnl","cost","carry","turn","w3f"): a[k]=a[k][ia]
    a["ts"]=com
    A0s={k:(A0[k][ib] if isinstance(A0[k],np.ndarray) and A0[k] is not None and len(A0[k])==len(A0["ts"]) else A0[k]) for k in ("ts","g","pnl","cost","carry","turn","w3f","sig")}
    YRp=YR[ib]
    d=a["g"]-A0s["g"]; dp=a["pnl"]-A0s["pnl"]; dc=a["cost"]-A0s["cost"]; dk=a["carry"]-A0s["carry"]
    r={"cfg":{k:a["cfg"][k] for k in ("TILT","TILT_TAU","TILT_K","LEGS","PHI","COSTB_JSON")},"sha16":a["sha16"],
       "n":len(d),"n_anchors_dropped_vs_A0":int(n_drop),
       "overall_delta_g":round(float(d.mean()),4),
       "overall_delta_g_CI95":[round(x,4) for x in ci(bstat(a["ts"],lambda ii: d[ii].mean(),101))],
       "delta_sharpe_vs_A0":round(sr(a["g"])-sr(A0s["g"]),4),
       "arm_sharpe":round(sr(a["g"]),4),
       "delta_pnl_ex":round(float(dp.mean()),4),"delta_cost_ex":round(float(dc.mean()),4),
       "delta_carry_ex":round(float(dk.mean()),4),
       "marginal_turnover_vs_A0":round(float(a["turn"].mean()-A0s["turn"].mean()),6),
       "turnover_ratio":round(float(a["turn"].mean()/A0s["turn"].mean()),4),
       "w3_fund_mean":round(float(a["w3f"].mean()),4),
       "w3_fund_mean_lowsig":round(float(a["w3f"][A0s["sig"]<TAU].mean()),4)}
    # (a) WITHIN-YEAR
    th=theta_of(d,yv=YRp)
    bt=bstat(a["ts"],lambda ii: theta_of(d,ii,YRp),102)
    r["a_withinyear"]={"theta_yearFE":round(th,4),
        "CI95":[round(x,4) for x in ci(bt)],
        "CI_bonf_%.2f"%(100-100*ALPHA):[round(x,4) for x in ci(bt,LO,HI)],
        "per_year_mean_delta_g":{int(y):round(float(d[YRp==y].mean()),4) for y in YEARS},
        "n_years_positive":int(sum(1 for y in YEARS if d[YRp==y].mean()>0)),
        "PASS":bool(th>0 and ci(bt,LO,HI)[0]>0 and sum(1 for y in YEARS if d[YRp==y].mean()>0)>=4)}
    # split by regime: where the tilt is active vs not
    lo=A0s["sig"]<TAU
    r["by_regime"]={"low_sigma_lt_4.75":{"n":int(lo.sum()),"delta_g":round(float(d[lo].mean()),4),
                        "CI95":[round(x,4) for x in ci(bstat(a["ts"][lo],lambda ii: d[lo][ii].mean(),103))],
                        "A0_g":round(float(A0s["g"][lo].mean()),4),"arm_g":round(float(a["g"][lo].mean()),4)},
                    "high_sigma_ge_4.75":{"n":int((~lo).sum()),"delta_g":round(float(d[~lo].mean()),4),
                        "CI95":[round(x,4) for x in ci(bstat(a["ts"][~lo],lambda ii: d[~lo][ii].mean(),104))],
                        "A0_g":round(float(A0s["g"][~lo].mean()),4),"arm_g":round(float(a["g"][~lo].mean()),4)}}
    # (b) HELD OUT
    fit=a["ts"]<=FITCUT; ho=(a["ts"]>=HS)&(a["ts"]<=HE)
    r["b_heldout"]={"fit_n":int(fit.sum()),"fit_theta_yearFE":round(theta_of(d,np.where(fit)[0],YRp),4),
        "fit_mean_delta_g":round(float(d[fit].mean()),4),
        "heldout_n":int(ho.sum()),"heldout_n_sigma_lt_tau":int((ho&lo).sum()),
        "heldout_mean_delta_g":round(float(d[ho].mean()),4),
        "heldout_CI95":[round(x,4) for x in ci(bstat(a["ts"][ho],lambda ii: d[ho][ii].mean(),105))],
        "heldout_n_anchors_tilt_active":int((ho&(np.abs(a["w3f"]-A0s["w3f"])>1e-9)).sum()),
        "heldout_A0_mean_g":round(float(A0s["g"][ho].mean()),4),
        "heldout_arm_mean_g":round(float(a["g"][ho].mean()),4)}
    # (c) GIVEBACK
    gv=(a["ts"]>=GS)&(a["ts"]<=GE)
    r["c_giveback"]={"n":int(gv.sum()),"n_sigma_lt_tau":int((gv&lo).sum()),
        "n_anchors_tilt_active":int((gv&(np.abs(a["w3f"]-A0s["w3f"])>1e-9)).sum()),
        "delta_g":round(float(d[gv].mean()),4),
        "A0_mean_g":round(float(A0s["g"][gv].mean()),4),"A0_SR":round(sr(A0s["g"][gv]),4),
        "arm_mean_g":round(float(a["g"][gv].mean()),4),"arm_SR":round(sr(a["g"][gv]),4),
        "delta_sharpe":round(sr(a["g"][gv])-sr(A0s["g"][gv]),4)}
    r["a_PASS"]=r["a_withinyear"]["PASS"]
    r["b_PASS"]=None  # decided after the fit selects K within family
    r["c_PASS"]=bool(r["c_giveback"]["delta_g"]>=0)
    OUT["arms"][nm]=r
    print(nm,"dg=%+.4f CI%s dSR=%+.4f theta=%+.4f bonfCI%s yrs+=%d | low dg=%+.4f high dg=%+.4f | HO dg=%+.4f (act %d/%d) | GB dg=%+.4f"%(
        r["overall_delta_g"],r["overall_delta_g_CI95"],r["delta_sharpe_vs_A0"],r["a_withinyear"]["theta_yearFE"],
        r["a_withinyear"]["CI_bonf_%.2f"%(100-100*ALPHA)],r["a_withinyear"]["n_years_positive"],
        r["by_regime"]["low_sigma_lt_4.75"]["delta_g"],r["by_regime"]["high_sigma_ge_4.75"]["delta_g"],
        r["b_heldout"]["heldout_mean_delta_g"],r["b_heldout"]["heldout_n_anchors_tilt_active"],r["b_heldout"]["heldout_n"],
        r["c_giveback"]["delta_g"]),flush=True)
# (b) family-wise in-sample selection then held-out read
FAM={"S":["S00","S25","S50","S75"],"R":["R00","R25","R50"],"P":["P05","P10"]}
SEL={}
for f,arms in FAM.items():
    best=max(arms,key=lambda n: OUT["arms"][n]["b_heldout"]["fit_theta_yearFE"])
    b=OUT["arms"][best]["b_heldout"]
    SEL[f]={"selected_by_insample_theta":best,
            "insample_theta":b["fit_theta_yearFE"],"insample_mean_delta_g":b["fit_mean_delta_g"],
            "prediction_for_heldout":b["fit_mean_delta_g"],
            "realised_heldout_mean_delta_g":b["heldout_mean_delta_g"],
            "realised_CI95":b["heldout_CI95"],
            "heldout_anchors_where_tilt_active":b["heldout_n_anchors_tilt_active"],
            "sign_agrees":bool(np.sign(b["fit_mean_delta_g"])==np.sign(b["heldout_mean_delta_g"]) and b["heldout_mean_delta_g"]!=0)}
    OUT["arms"][best]["b_PASS"]=SEL[f]["sign_agrees"]
    print("HELDOUT family",f,json.dumps(SEL[f]),flush=True)
OUT["b_family_selection"]=SEL
OUT["self_sha256"]=hashlib.sha256(open(__file__,'rb').read()).hexdigest()
json.dump(OUT,open(R+"/out/R8_JUDGE.json","w"),indent=1)
print("JUDGE_DONE")
