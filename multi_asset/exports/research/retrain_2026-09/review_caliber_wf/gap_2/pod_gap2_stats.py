import numpy as np, time, json, os, glob, sys
out={}
PD="/workspace/port_w10/probe_artifacts"
runs={"fixed_callog":"pod_live_w3fix_callog_s42","fixed_calsimple":"pod_live_w3fix_calsimple_s42","dyn_callog":"pod_live_callog_s42","dyn_calsimple":"pod_live_calsimple_s42","canon_callog":"pod_canon_callog_s42"}
# also R-C6.1 alt (Pi) runs if present
alt=glob.glob("/workspace/review_scratch/refute_C6_1/dev/probe_artifacts/w10_ablation_series_alt_*.npz")
for p in alt:
    tag=os.path.basename(p).replace("w10_ablation_series_","").replace(".npz","")
    runs["ALT_"+tag]=p
yr=lambda ts: np.array([time.gmtime(int(t)).tm_year for t in ts])
def stats(x):
    n=len(x); m=float(x.mean()); s=float(x.std(ddof=1)); sh=m/s*np.sqrt(2190) if s>0 else float('nan')
    c=np.cumsum(x); dd=float((np.maximum.accumulate(c)-c).max())
    return n,m,sh,dd
for k,v in runs.items():
    p=v if v.endswith(".npz") else f"{PD}/w10_ablation_series_{v}.npz"
    if not os.path.exists(p):
        # try alternate naming
        cands=glob.glob(f"{PD}/*{v}*.npz")
        if not cands: out[k]={"missing":p}; continue
        p=cands[0]
    z=np.load(p,allow_pickle=True); cols=[str(c) for c in z["cols"]]; rec=z["d30_n2_c42_rec"]
    ts=rec[:,cols.index("ts")].astype(np.int64); Y=yr(ts)
    nx=rec[:,cols.index("net_ex")].astype(float); gt=rec[:,cols.index("gross_total")].astype(float)
    wk=rec[:,cols.index("w3_king")].astype(float); wf=rec[:,cols.index("w3_fund")].astype(float); lk=rec[:,cols.index("leg_king")].astype(float)
    cfg=json.loads(str(z["config_json"])) if "config_json" in z else None
    r={"file":p,"CAL":cfg.get("CAL") if cfg else None,"W3FIX":cfg.get("W3FIX") if cfg else None,"MEMBERS_TOPN":cfg.get("MEMBERS_TOPN") if cfg else None,"TRADE_TOPN":cfg.get("TRADE_TOPN") if cfg else None,"FTRIM":cfg.get("FTRIM") if cfg else None,"LEGS":cfg.get("LEGS") if cfg else None,"by_year":{}}
    for y in (2022,2023,2024,2025,2026):
        s=Y==y
        if s.sum()==0: continue
        n,m,sh,dd=stats(nx[s])
        r["by_year"][y]={"n":n,"net_ex_mean":round(m,4),"sharpe":round(sh,3),"maxDD_bps":round(dd,1),"gross_mean":round(float(gt[s].mean()),3),
                         "w3_king_mean":round(float(wk[s].mean()),4),"w3_king_max":round(float(wk[s].max()),4),"w3_fund_mean":round(float(wf[s].mean()),4),
                         "leg_king_absmax":round(float(np.abs(lk[s]).max()),6),"net_ex_per_gross_mean_ratio":round(float((nx[s]/gt[s]).mean()),4)}
    s=Y<=2023; n,m,sh,dd=stats(nx[s]); r["2022_23"]={"n":n,"net_ex_mean":round(m,4),"sharpe":round(sh,3),"maxDD_bps":round(dd,1)}
    s=Y>=2022; n,m,sh,dd=stats(nx[s]); r["2022_26_all"]={"n":n,"net_ex_mean":round(m,4),"sharpe":round(sh,3),"maxDD_bps":round(dd,1)}
    r["first"]=time.strftime("%Y-%m-%d %H:%M",time.gmtime(int(ts[0]))); r["last"]=time.strftime("%Y-%m-%d %H:%M",time.gmtime(int(ts[-1])))
    out[k]=r
# coverage facts
M=np.load("/workspace/data/wide_fea_v2ext_meta.npz",allow_pickle=True); E=M["E_ts"].astype(np.int64); Ym=yr(E)
K=np.load("/workspace/shadow_bundle_v3/slow_pred_pinned.npy",mmap_mode="r")
cov={"king_pinned_shape":list(K.shape),"king_finite_frac_by_year":{int(y):round(float(np.isfinite(K[Ym==y]).mean()),4) for y in sorted(set(Ym.tolist()))}}
D=np.load("/workspace/data/dlw_targets.npz",allow_pickle=True); Ed=D["E_ts"].astype(np.int64); Yd=yr(Ed)
for sd in ("42","2027"):
    fp=f"/workspace/f8_2026-08-22/preds/f10_V2MAIN_s{sd}.npy"
    if os.path.exists(fp):
        F=np.load(fp,mmap_mode="r"); cov[f"f10_s{sd}_shape"]=list(F.shape)
        if F.shape[0]==len(Ed): cov[f"f10_s{sd}_finite_frac_by_year"]={int(y):round(float(np.isfinite(F[Yd==y]).mean()),4) for y in sorted(set(Yd.tolist()))}
        else: cov[f"f10_s{sd}_note"]=f"rows {F.shape[0]} != dlw E_ts {len(Ed)}"
    else: cov[f"f10_s{sd}"]="missing"
cov["meta_E_ts_first"]=time.strftime("%Y-%m-%d",time.gmtime(int(E[0]))); cov["meta_E_ts_last"]=time.strftime("%Y-%m-%d",time.gmtime(int(E[-1])))
cov["dlw_E_ts_first"]=time.strftime("%Y-%m-%d",time.gmtime(int(Ed[0]))); cov["dlw_E_ts_last"]=time.strftime("%Y-%m-%d",time.gmtime(int(Ed[-1])))
# search for hist_oos king anywhere
hits=[]
for root in ("/workspace",):
    for dp,dn,fn in os.walk(root):
        if any(x in dp for x in ("/venv","/proc","/sys")): continue
        for f in fn:
            if "slow_pred" in f and f.endswith(".npy"):
                p=os.path.join(dp,f)
                try:
                    st=os.stat(p); islink=os.path.islink(p); hits.append({"path":p,"size":st.st_size,"symlink":islink,"target":os.readlink(p) if islink else None})
                except Exception as e: hits.append({"path":p,"err":str(e)})
cov["slow_pred_files"]=hits
# panel v1 coverage (pre-2022)
try:
    P1=np.load("/workspace/data/wide_panel_4h_v1.npz",mmap_mode="r"); t1=P1["ts"].astype(np.int64)
    cov["panel_v1_ts_first"]=time.strftime("%Y-%m-%d",time.gmtime(int(t1[0]))); cov["panel_v1_ts_last"]=time.strftime("%Y-%m-%d",time.gmtime(int(t1[-1]))); cov["panel_v1_n"]=int(len(t1))
except Exception as e: cov["panel_v1"]=str(e)
out["coverage"]=cov
os.makedirs("/workspace/review_scratch/gap_2",exist_ok=True)
json.dump(out,open("/workspace/review_scratch/gap_2/gap2_stats.json","w"),indent=1)
print(json.dumps(out,indent=1))
