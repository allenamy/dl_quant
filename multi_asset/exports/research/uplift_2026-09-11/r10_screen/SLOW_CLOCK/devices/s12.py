"""r10 SLOW_CLOCK screen - STEP 1 feasibility + STEP 2 independence.
Frozen by PREREG_r10_SLOW_CLOCK_2026-09-12.md (local sha 74b3bc6125e5fa2a...).
Reads ONLY. Writes /workspace/uplift_2026-09-11/r10_slowclock/rc/S12.json"""
import numpy as np, calendar, time, json, hashlib, os, sys
ENV_WL=["CAL","LEGS","PHI","FTRIM","WRULE","LOOK","MEMBERS_TOPN","UMASK_SCOPE","UMASK_NPZ",
 "COSTB_JSON","SLOW_NPY","FSEED","FPRED","FEMAT_NPZ","OUT_TAG","EXPORT_PANEL","EMA_STATE_JSON",
 "PANEL_IN","JUDGE_HC","TILT","TILT_TAU","TILT_K"]
leaked=[k for k in ENV_WL if k in os.environ]
assert not leaked, ("ENV LEAK",leaked)
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<22),b''): h.update(b)
    return h.hexdigest()
U="/workspace/uplift_2026-09-11"; R2=U+"/r2_horizon"
HCP="/workspace/review_scratch/health_check/dev_v4/probe_artifacts"
PB="/workspace/review_scratch/health_check/dev_v4/pod_backup_2026-08-21"
CACHE="/workspace/data/dlnative_5m_wide829_f16_holefix2.npz"
WARM=900; CUT=T(2026,8,30,20); APY=2190
TRAIN_END=T(2024,12,31,20); HOLD_S=T(2025,1,1,0)
OUT={"env_whitelist_asserted_absent":ENV_WL,"prereg":"PREREG_r10_SLOW_CLOCK_2026-09-12.md",
     "threads":{k:os.environ.get(k) for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS")}}

# ---------- STEP 1 FEASIBILITY ----------
FE={}
for p in [CACHE, PB+"/wide_panel_4h_hist_v2.npz", R2+"/feats_r2.npz", R2+"/feats_r2b.npz",
          U+"/w10_sleeve.py", U+"/r3k/costb_PWR_G230k.json",
          "/workspace/review_scratch/health_check/calib/costb_fee_steady.json",
          HCP+"/w10_ablation_series_V4_A0_dyn_s42.npz"]:
    FE[p]={"sha256":sha(p),"bytes":os.path.getsize(p)}
OUT["F3_input_sha256"]=FE

# F2: which panel columns the builders touch (grep-level, then assert the lookahead column is unused)
src=open(R2+"/common.py").read()+open(R2+"/drive_ABCD.py").read()+open(R2+"/build_feats.py").read()+open(R2+"/build_feats2.py").read()
PWk=list(np.load(PB+"/wide_panel_4h_hist_v2.npz",allow_pickle=True).keys())
used=[k for k in PWk if ('PW["%s"]'%k) in src]
OUT["F2_panel"]={"panel_file":PB+"/wide_panel_4h_hist_v2.npz","panel_keys_n":len(PWk),
  "panel_keys_USED_by_r2_horizon_builders":used,
  "known_lookahead_column_betaadj_ret24_present_in_panel":any("betaadj" in k for k in PWk),
  "known_lookahead_column_USED": any("betaadj" in k for k in used),
  "note":"builders load this panel by EXPLICIT path, not via engine/panel_source.py default"}

# F1: recompute the window definition straight from the 5m cache and compare to feats_r2.npz
PW=np.load(PB+"/wide_panel_4h_hist_v2.npz",allow_pickle=True); pts=PW["ts"].astype(np.int64)
z=np.load(CACHE,allow_pickle=True); ts5=z["ts"].astype(np.int64); ch=[str(c) for c in z["ch"]]
pos={int(t):k for k,t in enumerate(ts5)}; K=np.array([pos[int(t)] for t in pts])
F=np.load(R2+"/feats_r2.npz",allow_pickle=True)
ci=ch.index("tbf"); NW=829
rng=np.random.default_rng(20260912)
rows=np.sort(rng.choice(np.arange(3000,len(pts)),40,replace=False))
X=z["data"][:,:,ci].astype(np.float32)
chk={}
for W,key in ((864,"TBF_MEAN_864"),(12,"TBF_MEAN_12")):
    got=np.asarray(F[key],np.float64); mx_ro=0.0; mx_ci_=0.0
    for i in rows:
        k=K[i]; seg=X[max(k-W,0):k,:].astype(np.float64)       # RIGHT-OPEN [k-W, k)
        fin=np.isfinite(seg); n=fin.sum(0)
        v=np.where(n>=0.7*W, np.where(fin,seg,0).sum(0)/np.maximum(n,1), np.nan)
        m=np.isfinite(v)&np.isfinite(got[i])
        mx_ro=max(mx_ro,float(np.max(np.abs(v[m]-got[i][m]))) if m.any() else 0.0)
        seg2=X[max(k-W+1,0):k+1,:].astype(np.float64)          # CLOSED-at-anchor [k-W+1, k] = would be lookahead
        fin2=np.isfinite(seg2); n2=fin2.sum(0)
        v2=np.where(n2>=0.7*W, np.where(fin2,seg2,0).sum(0)/np.maximum(n2,1), np.nan)
        m2=np.isfinite(v2)&np.isfinite(got[i])
        mx_ci_=max(mx_ci_,float(np.max(np.abs(v2[m2]-got[i][m2]))) if m2.any() else 0.0)
    chk[key]={"maxabs_vs_RIGHT_OPEN_[k-W,k)":mx_ro,"maxabs_vs_CLOSED_[k-W+1,k]":mx_ci_,"n_anchors_sampled":len(rows),"W":W}
del X
OUT["F1_window_parity"]=chk

# also confirm the target is forward: Y4 at anchor j = sum ret5 [k, k+48)
cr=ch.index("ret5"); Xr=z["data"][:,:,cr].astype(np.float32)
A0=np.load(HCP+"/w10_ablation_series_V4_A0_dyn_s42.npz",allow_pickle=True)
OUT["F1_target_direction"]={"definition":"pod 5m lineage y4 = SUM of 5-minute SIMPLE returns over [k,k+48); no expm1 (E-0904-F)",
  "verified_here":"window parity above is on the FEATURE side; target side is the device's, untouched"}
del Xr

# ---------- axis ----------
cols=[str(c) for c in A0["cols"]]; ix={c:i for i,c in enumerate(cols)}
def load(p,key=None):
    Z=np.load(p,allow_pickle=True); cc=[str(c) for c in Z["cols"]]
    A=np.asarray(Z[key] if key else Z["rec"],float)
    return cc,A
cc,AA=load(HCP+"/w10_ablation_series_V4_A0_dyn_s42.npz","d30_n2_c42_rec")
ts_all=np.round(AA[:,ix["ts"]]).astype(np.int64)
sel=np.arange(len(ts_all))[WARM:]; sel=sel[ts_all[sel]<=CUT]
TS=ts_all[sel]
def series(A):
    return dict(g=(A[:,ix["net_ex"]]/A[:,ix["gross_total"]])[sel],
                pnl=(A[:,ix["pnl_ex"]]/A[:,ix["gross_total"]])[sel],
                cost=(A[:,ix["cost_ex"]]/A[:,ix["gross_total"]])[sel],
                carry=(A[:,ix["carry_ex"]]/A[:,ix["gross_total"]])[sel],
                turn=A[:,ix["turnover"]][sel], netlong=A[:,ix["netlong"]][sel],
                gross=A[:,ix["gross_total"]][sel])
A0s=series(AA)
def sr(x): return float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(APY))
OUT["F4_axis"]={"rec_len":len(ts_all),"warm_drop":WARM,"cut":"2026-08-30 20Z","n":len(TS),
  "first":time.strftime("%Y-%m-%d %HZ",time.gmtime(TS[0])),"last":time.strftime("%Y-%m-%d %HZ",time.gmtime(TS[-1])),
  "SE_ann_sharpe":round(float(np.sqrt(APY/len(TS))),4)}
OUT["F5_A0_reference_at_ARCHIVED_cost_fee_steady"]={
  "mean_g_bps":round(float(A0s["g"].mean()),4),"ann_sharpe":round(sr(A0s["g"]),4),
  "gross_alpha_pnl_ex_bps":round(float(A0s["pnl"].mean()),4),
  "cost_bps":round(float(A0s["cost"].mean()),4),"turnover":round(float(A0s["turn"].mean()),5),
  "brief_says":{"mean_g":0.6342,"sharpe":1.2912,"pnl_ex":1.3266,"n":9138}}

# ---------- STEP 2 INDEPENDENCE ----------
POOL=["A_AMI1H","A_CPOS1H","A_QVS1H","A_REV1H","A_TBF1H","A_VOL1H","B_AMI12H","B_REV12H","B_TBF12H",
 "C_AMI3D","C_AMI7D","C_QVTR3D","C_TBF3D","C_TBF7D","C_TBF14D","C_TBF30D","D_FCHG12H","D_FCHG3D","D_FSLOPE"]
ARM={}
for f in POOL:
    for s in ("__p","__m"):
        p=R2+"/out/%s%s.npz"%(f,s)
        c2,A2=load(p)
        assert c2==cols
        t2=np.round(A2[:,ix["ts"]]).astype(np.int64)
        assert np.array_equal(t2,ts_all), f+s
        ARM[f+s]=series(A2); ARM[f+s]["sha16"]=sha(p)[:16]
OUT["F3_arm_axis_bitwise_identical_to_A0_ts"]=True
OUT["F3_arm_sha16"]={k:ARM[k]["sha16"] for k in sorted(ARM)}

tr=TS<=TRAIN_END; ho=TS>=HOLD_S
OUT["S4_split"]={"train_n":int(tr.sum()),"train_last":time.strftime("%Y-%m-%d %HZ",time.gmtime(TS[tr][-1])),
  "holdout_n":int(ho.sum()),"holdout_first":time.strftime("%Y-%m-%d %HZ",time.gmtime(TS[ho][0])),
  "holdout_last":time.strftime("%Y-%m-%d %HZ",time.gmtime(TS[ho][-1]))}
def rho(a,b,m=None):
    if m is None: m=np.ones(len(a),bool)
    return float(np.corrcoef(a[m],b[m])[0,1])
RH={}
for f in POOL:
    gp=ARM[f+"__p"]["g"]
    RH[f]={"rho_train":round(rho(gp,A0s["g"],tr),4),"rho_full":round(rho(gp,A0s["g"]),4),
           "rho_hold":round(rho(gp,A0s["g"],ho),4),
           "train_mean_g_p":round(float(gp[tr].mean()),4)}
OUT["S2_rho_by_feature"]=RH
Q=[f for f in POOL if abs(RH[f]["rho_train"])<=0.10]
OUT["S4_step3_Q_selected_by_rho_train_only"]=Q
SIGN={f:("__p" if RH[f]["train_mean_g_p"]>0 else "__m") for f in Q}
OUT["S4_step4_sign_from_TRAIN_mean_g_only"]=SIGN
OUT["S4_step6_pure_rho_single"]=min(POOL,key=lambda f: abs(RH[f]["rho_train"]))
json.dump(OUT,open(U+"/r10_slowclock/rc/S12.json","w"),indent=1)
print(json.dumps({k:OUT[k] for k in ("F1_window_parity","F2_panel","F4_axis","F5_A0_reference_at_ARCHIVED_cost_fee_steady","S4_split","S4_step3_Q_selected_by_rho_train_only","S4_step4_sign_from_TRAIN_mean_g_only","S4_step6_pure_rho_single")},indent=1))
print("RHO TABLE"); 
for f in POOL: print("%-12s %s"%(f,RH[f]))
