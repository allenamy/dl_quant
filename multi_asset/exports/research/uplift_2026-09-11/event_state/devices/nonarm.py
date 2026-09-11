"""Track G non-arm diagnostics: (i) settlement-anchor phase, (ii) delisting oracle, (iii) universe rank buckets."""
import numpy as np, json, calendar
D="/workspace/uplift_2026-09-11/dev_v4ev"
A=np.load(f"{D}/probe_artifacts/w10_ablation_series_GP_dyn_s42.npz",allow_pickle=True)
R=A["d30_n2_c42_rec"]; W=A["d30_n2_c42_W"]
ts=np.round(np.asarray(R[:,0],float)).astype(np.int64)
MT=np.load(f"{D}/pod_backup_2026-08-21/wide_fea_hist_meta.npz",allow_pickle=True)
E=MT["E_ts"].astype(np.int64); y4=np.asarray(MT["y4"],float); qvk=np.asarray(MT["qvk"],float)
mrow={int(t):i for i,t in enumerate(E)}
mi=np.array([mrow[int(t)] for t in ts])
Y=np.nan_to_num(y4[mi],nan=0.0); Q=qvk[mi]
G=np.abs(W).sum(1)                      # gross_total per anchor
PNL=(W*Y).sum(1)*1e4
g_dev=R[:,18]/R[:,5]
print("attribution check: corr(pnl_recomputed, rec pnl col) =",round(float(np.corrcoef(PNL,R[:,2])[0,1]),6),
      " maxabs diff",float(np.abs(PNL-R[:,2]).max()))
out={}
# --- (i) settlement-anchor phase
hr=((ts//3600)%24).astype(int)
sett=np.isin(hr,[0,8,16])
def sub(mask,label):
    v=g_dev[mask]
    return {"label":label,"n":int(mask.sum()),"mean_g":float(v.mean()),
            "sharpe":float(v.mean()/v.std(ddof=1)*np.sqrt(2190)) if v.std(ddof=1)>0 else None}
out["phase"]={"settlement_anchors_00_08_16":sub(sett,"S"),"non_settlement_04_12_20":sub(~sett,"N"),
              "by_hour":{str(h):sub(hr==h,str(h)) for h in [0,4,8,12,16,20]}}
# --- (iii) universe: per-anchor rank by qvk, contribution of each rank bucket to gross-normalised pnl
rk=np.argsort(np.argsort(-np.nan_to_num(Q,nan=-1e9),axis=1),axis=1)
buckets=[(0,250),(250,450),(450,527),(527,829)]
ub={}
for a,b in buckets:
    m=(rk>=a)&(rk<b)
    contrib=((W*Y*m).sum(1)*1e4)/np.maximum(G,1e-12)
    grossshare=(np.abs(W)*m).sum(1)/np.maximum(G,1e-12)
    ub[f"{a}-{b}"]={"mean_pnl_bps_per_gross":float(contrib.mean()),
                    "mean_gross_share":float(grossshare.mean()),
                    "sharpe":float(contrib.mean()/contrib.std(ddof=1)*np.sqrt(2190)) if contrib.std(ddof=1)>0 else None,
                    "by_year":{y:float(contrib[(ts>=calendar.timegm((int(y),1,1,0,0,0)))&(ts<calendar.timegm((int(y)+1,1,1,0,0,0)))].mean()) for y in ["2022","2023","2024","2025","2026"]}}
out["universe_qvk_rank_buckets"]=ub
out["universe_note"]="rank = per-anchor qvk (4h quote volume) rank among the 829 panel names; W = A0 deployed weights; contribution = price pnl only (no carry/cost), bps per unit gross_total"
# --- (ii) delisting oracle: last 180 anchors before a name last has finite y4
fin=np.isfinite(y4)
last=np.where(fin.any(0),fin.shape[0]-1-fin[::-1].argmax(0),-1)
nfin=fin.sum(0)
dead=(last< len(E)-30)&(nfin>100)
print("names with >100 finite anchors:",int((nfin>100).sum()),"of which end >30 anchors before sample end:",int(dead.sum()))
for H in (180,42):
    M=np.zeros_like(Y,bool)
    for k in np.where(dead)[0]:
        lo=max(0,last[k]-H); hi=last[k]
        sel=(mi>=lo)&(mi<=hi)
        M[sel,k]=True
    contrib=((W*Y*M).sum(1)*1e4)/np.maximum(G,1e-12)
    gs=(np.abs(W)*M).sum(1)/np.maximum(G,1e-12)
    out[f"delist_last{H}"]={"n_dead_names":int(dead.sum()),"mean_pnl_bps_per_gross":float(contrib.mean()),
        "mean_gross_share":float(gs.mean()),
        "share_of_A0_price_pnl":float(contrib.mean()/ (PNL/np.maximum(G,1e-12)).mean())}
out["delist_note"]="ORACLE / NON-CAUSAL: disappearance date is not knowable at the anchor. Sizes the prize only."
json.dump(out,open("/workspace/uplift_2026-09-11/event_state/NONARM.json","w"),indent=1)
print(json.dumps(out,indent=1))
