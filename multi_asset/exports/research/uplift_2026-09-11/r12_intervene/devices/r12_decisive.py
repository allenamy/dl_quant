"""r12 DECISIVE tests:
 (A) matched-cost de-levering: does the intra-anchor stop buy halt reduction a leverage dial cannot?
 (B) 'sell the bottom' mechanism check for I-4 (stop_response_reversible_pricing, 2026-08-21)
 (C) CEM mechanism drill-down: what the fires actually cut, and where the gain is concentrated
ENV whitelist = EMPTY SET."""
import os, json, time, calendar, hashlib
import numpy as np
assert not any(k in os.environ for k in ("CAL","PHI","CEM_Q","BYP_STATE","LEGS","FTRIM"))
U="/workspace/uplift_2026-09-11"; R=f"{U}/r12_intervene"; T=f"{R}/dev_ext/probe_artifacts"
MON=np.load(f"{R}/out/monitors.npz",allow_pickle=True)
ts=MON["ts"].astype(np.int64); COLS=[str(c) for c in MON["cols"]]; C={k:i for i,k in enumerate(COLS)}
REC=np.asarray(MON["rec"],float); gt=REC[:,C["gross_total"]]
g0=REC[:,C["net_ex"]]/gt; PATH=np.asarray(MON["path5m"],np.float64)
nA=len(ts); days=ts//86400
ud,cnt=np.unique(days,return_counts=True); full=ud[cnt==6]; mT=np.isin(days,full); NDAY=len(full)
def tail(gv,L):
    G=gv[mT].reshape(NDAY,6); dr=np.prod(1.0+L*G/1e4,1)-1.0; ip=np.cumprod(1.0+L*G/1e4,1)-1.0
    nav=np.concatenate([[1.0],np.cumprod(1.0+dr)])
    return {"cagr":float(((np.prod(1.0+dr))**(365.0/NDAY)-1.0)*100),
            "worst":float(dr.min()*100),"maxDD":float((1.0-nav/np.maximum.accumulate(nav)).max()*100),
            "vol":float(dr.std(ddof=1)*np.sqrt(365)*100),
            "le4":round(float((dr<=-0.04).sum())/NDAY*365,4),"le268":round(float((dr<=-0.0268).sum())/NDAY*365,4),
            "le4_n":int((dr<=-0.04).sum()),"sharpe_d":float(dr.mean()/dr.std(ddof=1)*np.sqrt(365))}
OUT={"read_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"env_whitelist":[],"NDAY":int(NDAY)}
# ---- (A) de-lever ladder on the SAME series, and matched-CAGR comparison ----
LAD={}
for L in [0.8,0.9,1.0,1.1,1.2,1.25,1.3,1.4,1.5,1.6,1.75,2.0,2.5,2.81]:
    LAD["%.2f"%L]=tail(g0,L)
OUT["A0_leverage_ladder"]=LAD
IAS={}
for tag in ("R12_IAS_th200_phi00","R12_IAS_th268_phi00","R12_IAS_th300_phi00",
            "R12_IAS_th200_phi50","R12_IAS_th268_phi50","R12_IAS_th300_phi50"): IAS[tag]=None
B=json.load(open(f"{R}/out/BATTERY_r12.json"))
def matched_L(target_cagr,L):
    lo,hi=0.2,2.0
    for _ in range(60):
        mid=(lo+hi)/2
        if tail(g0,mid)["cagr"]<target_cagr: lo=mid
        else: hi=mid
    return (lo+hi)/2
MC={}
for tag in IAS:
    a=B["arms"][tag]["tail_2.0x"]; tgt=a["cagr_pct"]
    Ls=matched_L(tgt,2.0); ref=tail(g0,Ls)
    MC[tag]={"arm_cagr":tgt,"arm_worst":a["worst_day_pct"],"arm_maxDD":a["maxDD_pct"],
             "arm_le4_per_yr":a["le4.00"]["per_yr"],"arm_le268_per_yr":a["le2.68"]["per_yr"],
             "matched_L":round(Ls,4),"delev_cagr":ref["cagr"],"delev_worst":ref["worst"],
             "delev_maxDD":ref["maxDD"],"delev_le4_per_yr":ref["le4"],"delev_le268_per_yr":ref["le268"],
             "verdict_worst":"stop better" if a["worst_day_pct"]>ref["worst"] else "delever better",
             "verdict_le4":"stop better" if a["le4.00"]["per_yr"]<ref["le4"] else ("tie" if abs(a["le4.00"]["per_yr"]-ref["le4"])<1e-9 else "delever better"),
             "verdict_maxDD":"stop better" if a["maxDD_pct"]<ref["maxDD"] else "delever better"}
OUT["matched_cost_delever"]=MC
# ---- (B) 'sell the bottom': what happens after an intra-day crossing of -2.0% (A0, untouched) ----
L=2.0; G=g0[mT].reshape(NDAY,6); IP=np.cumprod(1.0+L*G/1e4,1)-1.0
res={}
for th,nm in ((-0.02,"m200"),(-0.0268,"m268"),(-0.03,"m300"),(-0.04,"m400")):
    below=IP<=th; hit=below.any(1)
    first=np.where(hit,below.argmax(1),6)
    rest=[];nxt=[]
    for d in range(NDAY):
        if not hit[d]: continue
        k=first[d]
        rest.append(float(np.prod(1.0+L*G[d,k+1:]/1e4)-1.0) if k<5 else 0.0)
        if d+1<NDAY: nxt.append(float(np.prod(1.0+L*G[d+1]/1e4)-1.0))
    res[nm]={"n_days":int(hit.sum()),"rest_of_day_mean_pct":float(np.mean(rest)*100) if rest else None,
             "rest_of_day_median_pct":float(np.median(rest)*100) if rest else None,
             "next_day_mean_pct":float(np.mean(nxt)*100) if nxt else None,
             "next_day_median_pct":float(np.median(nxt)*100) if nxt else None,
             "uncond_day_mean_pct":float((np.prod(1.0+L*G/1e4,1)-1.0).mean()*100)}
OUT["loss_continuation_after_crossing"]=res
# next-ANCHOR after the first 5m breach (finer, matches stop_response_reversible_pricing's estimand)
anc=[]
for d in range(NDAY):
    if not (IP[d]<=-0.02).any(): continue
    k=int((IP[d]<=-0.02).argmax())
    if k<5: anc.append(float(L*G[d,k+1]/1e4))
OUT["next_anchor_after_m200_bps_NAV"]={"n":len(anc),"mean_bps":float(np.mean(anc)*1e4) if anc else None,
    "median_bps":float(np.median(anc)*1e4) if anc else None,
    "uncond_mean_bps":float(np.mean(L*g0/1e4)*1e4)}
# ---- (C) CEM drill-down ----
DC=["ts","bill_pre","bill_post","cem_fire","cem_n","cem_th","byp_fire","a_ema","s6","byp_q","mkt_med"]
for tag in ("R12_CEM_99_neutral_s42","R12_CEM_95_neutral_s42","R12_CEM_90_neutral_s42"):
    Z=np.load(f"{T}/w10_ablation_series_{tag}.npz",allow_pickle=True)
    D=np.asarray(Z["d30_n2_c42_DIAG"],float); Rr=np.asarray(Z["d30_n2_c42_rec"],float)
    ga=Rr[:,C["net_ex"]]/Rr[:,C["gross_total"]]
    f=D[:,DC.index("cem_fire")]>0.5
    sl=slice(900,None)
    d=(ga-g0)[sl]; ff=f[sl]
    contrib=d.copy()
    o=np.argsort(-np.abs(contrib))
    OUT.setdefault("CEM_drill",{})[tag]={
      "n_fire_postwarm":int(ff.sum()),"fire_rate_pct":float(100*ff.mean()),
      "mean_cem_n_on_fire":float(D[f,DC.index("cem_n")].mean()) if f.any() else None,
      "median_cem_n_on_fire":float(np.median(D[f,DC.index("cem_n")])) if f.any() else None,
      "bill_pre_on_fire_mean":float(D[f,DC.index("bill_pre")].mean()) if f.any() else None,
      "bill_post_on_fire_mean":float(D[f,DC.index("bill_post")].mean()) if f.any() else None,
      "dg_total":float(d.mean()),
      "dg_on_fire_anchors_only":float(d[ff].sum()/len(d)),
      "dg_on_nonfire_anchors":float(d[~ff].sum()/len(d)),
      "dg_excl_top1pct_abs":float(np.delete(contrib,o[:max(1,len(d)//100)]).sum()/len(d)),
      "dg_excl_top5_anchors":float(np.delete(contrib,o[:5]).sum()/len(d)),
      "share_of_dg_from_top10_anchors":float(contrib[o[:10]].sum()/max(d.sum(),1e-12))}
print(json.dumps(OUT,indent=1)[:9000])
json.dump(OUT,open(f"{R}/out/DECISIVE.json","w"),indent=1)
print("DECISIVE_DONE")
