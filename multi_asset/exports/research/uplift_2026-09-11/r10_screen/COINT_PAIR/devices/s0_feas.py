#!/usr/bin/env python3
"""r10 COINT_PAIR STEP 1 -- FEASIBILITY. Reproduce A0 reference first-hand; verify axes, holes,
causality of the price proxy. ENV WHITELIST = THE EMPTY SET (E-0826-D)."""
import os, json, time, calendar, hashlib
import numpy as np
_CE=["LEGS","PHI","CAL","WRULE","LOOK","MEMBERS_TOPN","TRADE_TOPN","FTRIM","FTRIM_TH","LTRIM_TH",
     "CDAMP","UMASK_SCOPE","UMASK_NPZ","COSTB_JSON","SLOW_NPY","FSEED","FPRED","FEMAT_NPZ","OUT_TAG",
     "W3FIX","KMOD","KMOD_L","KMOD_F10","KMOD_AGREE","KTAIL","SEATF10","SEATNET","FUNDSCALE","RNSM",
     "FTPOS","SLEEVE","REF_SKIP","TILT","TILT_TAU","TILT_K","JUDGE_HC","V2","PANEL_IN","EXPORT_PANEL",
     "EMA_STATE_JSON"]
assert sorted([k for k in _CE if k in os.environ])==[], "E-0826-D: config env present"
def _forbid(*a,**k): raise AssertionError("E-0826-D violation: no env var may be read")
os.environ.get=_forbid

OUT="/workspace/uplift_2026-09-11/r10_coint"
META="/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"
A0NPZ="/workspace/uplift_2026-09-11/r8b2/dev/probe_artifacts/w10_ablation_series_R8_A0_s42.npz"
PANEL="/workspace/data/wide_panel_4h_v2ext.npz"
UMSK="/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"
COSTB="/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"
def sha16(p): return hashlib.sha256(open(p,"rb").read()).hexdigest()[:16]
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
WARM=900; CUT=T(2026,8,30,20); APY=2190

R={"step":"STEP1_FEASIBILITY","env_whitelist":[],
   "self_sha256":hashlib.sha256(open(__file__,"rb").read()).hexdigest(),
   "inputs_sha256_16":{p:sha16(p) for p in (META,A0NPZ,PANEL,UMSK,COSTB)}}

M=np.load(META,allow_pickle=True)
E_ts=M["E_ts"].astype(np.int64); y4=np.asarray(M["y4"],np.float64); qvk=np.asarray(M["qvk"],np.float64)
members=M["members"]
A=np.load(A0NPZ,allow_pickle=True); cols=[str(c) for c in A["cols"]]; ci={c:i for i,c in enumerate(cols)}
rec=np.asarray(A["d30_n2_c42_rec"],float); WA=np.asarray(A["d30_n2_c42_W"])
ts=np.round(rec[:,ci["ts"]]).astype(np.int64)
cfg=json.loads(str(A["config_json"]))
R["A0_config_readback"]={k:cfg.get(k) for k in ("LEGS","PHI","CAL","WRULE","LOOK","MEMBERS_TOPN",
    "FTRIM","UMASK_SCOPE","COSTB_JSON","FSEED")}
R["A0_cost_model_in_config"]=cfg.get("COST_B")
CB=json.load(open(COSTB))["tiers"]
R["pinned_cost_tiers_match_config"]=bool(np.allclose(
    np.array(cfg["COST_B"],float),
    np.array([[t["maker_bps"],t["taker_bps"],t["maker_share"]] for t in CB],float)))

sel=np.zeros(len(ts),bool); sel[WARM:]=True; sel &= (ts<=CUT)
TS=ts[sel]
gA0=(rec[:,ci["net_ex"]]/rec[:,ci["gross_total"]])[sel]
def sr(x): return float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(APY))
R["A0_reference_first_hand"]={
 "rec_rows_total":int(len(ts)),"n_post_warm_and_cut":int(sel.sum()),
 "window_utc":[time.strftime("%Y-%m-%dT%H:%MZ",time.gmtime(int(TS[0]))),
               time.strftime("%Y-%m-%dT%H:%MZ",time.gmtime(int(TS[-1])))],
 "mean_g_bps":round(float(gA0.mean()),4),"annualised_sharpe":round(sr(gA0),4),
 "SE_annualised_sharpe":round(float(np.sqrt(APY/len(gA0))),4),
 "gross_alpha_pnl_ex_bps":round(float((rec[:,ci["pnl_ex"]]/rec[:,ci["gross_total"]])[sel].mean()),4),
 "carry_ex_bps":round(float((rec[:,ci["carry_ex"]]/rec[:,ci["gross_total"]])[sel].mean()),4),
 "cost_ex_bps":round(float((rec[:,ci["cost_ex"]]/rec[:,ci["gross_total"]])[sel].mean()),4),
 "turnover_mean":round(float(rec[:,ci["turnover"]][sel].mean()),5),
 "brief_claim":{"mean_g":0.6342,"CI95":[0.1653,1.1071],"sharpe":1.2912,"n":9138,"gross_pnl_ex":1.3266}}
# identity: net_ex == pnl_ex - carry_ex - cost_ex ?
ne=rec[:,ci["net_ex"]]; pe=rec[:,ci["pnl_ex"]]; ce=rec[:,ci["carry_ex"]]; ke=rec[:,ci["cost_ex"]]
R["net_identity_maxabs"]={"pnl-carry-cost":float(np.max(np.abs(ne-(pe-ce-ke)))),
                          "pnl+carry-cost":float(np.max(np.abs(ne-(pe+ce-ke))))}
# --- AXIS / DATA for the pair engine
R["axis"]={"meta_E_ts_len":int(len(E_ts)),"A0_rec_len":int(len(ts)),
  "A0_ts_subset_of_meta":bool(np.all(np.isin(ts,E_ts))),
  "meta_first":time.strftime("%Y-%m-%dT%H:%MZ",time.gmtime(int(E_ts[0]))),
  "meta_last":time.strftime("%Y-%m-%dT%H:%MZ",time.gmtime(int(E_ts[-1]))),
  "anchor_spacing_unique_sec":sorted(set(np.diff(E_ts).tolist()))[:5],
  "n_names":int(y4.shape[1])}
fin=np.isfinite(y4)
R["y4_coverage"]={"finite_frac_overall":round(float(fin.mean()),5),
  "names_finite_at_last_anchor":int(fin[-1].sum()),
  "median_names_finite_per_anchor":float(np.median(fin.sum(1))),
  "max_abs_y4":float(np.nanmax(np.abs(y4))),
  "y4_is_sum_of_5m_simple_returns_NO_expm1":"E-0904-F: caliber bound to panel file; no expm1 applied"}
# block bootstrap CI for A0 (reproduce the brief CI)
dd=TS//86400; ud,inv=np.unique(dd,return_inverse=True); nd=len(ud)
order=np.argsort(inv,kind="stable"); st=np.searchsorted(inv[order],np.arange(nd)); en=np.append(st[1:],len(order))
rng=np.random.default_rng([20260905,1]); pick=rng.integers(0,nd,size=(2000,nd))
BI=[np.concatenate([order[st[j]:en[j]] for j in pick[b]]) for b in range(2000)]
v=np.array([gA0[ii].mean() for ii in BI])
R["A0_reference_first_hand"]["mean_g_CI95"]=[round(float(np.percentile(v,2.5)),4),
                                             round(float(np.percentile(v,97.5)),4)]
np.savez_compressed(OUT+"/axis.npz", ts=TS, gA0=gA0, sel=sel, rec_ts=ts,
                    gross=rec[:,ci["gross_total"]][sel], turn=rec[:,ci["turnover"]][sel])
open(OUT+"/STEP1_FEAS.json","w").write(json.dumps(R,indent=1))
print(json.dumps(R,indent=1))
