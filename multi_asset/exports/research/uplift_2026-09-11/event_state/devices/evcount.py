import numpy as np, json, calendar
D="/workspace/uplift_2026-09-11/dev_v4ev"; ES="/workspace/uplift_2026-09-11/event_state"
Z=np.load(f"{ES}/sett_v4.npz",allow_pickle=True)
ET=Z["ts"].astype(np.int64); EK=Z["k"].astype(np.int64); ER=Z["rate"].astype(np.float64); EM=Z["miss"]; EDR=Z["dr"]
good=np.isfinite(EDR)&(EM==0)
F=np.load(f"{ES}/feats_v4.npz",allow_pickle=True)
PW=np.load(f"{D}/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz",allow_pickle=True)
ts=PW["ts"].astype(np.int64); BASE=np.isfinite(np.asarray(PW["f_fund_ema_v1"],float))
MT=np.load(f"{D}/pod_backup_2026-08-21/wide_fea_hist_meta.npz",allow_pickle=True)
E=MT["E_ts"].astype(np.int64); y4=np.asarray(MT["y4"],float)
out={}
out["settlement_events_total"]=int(good.sum())
av=np.abs(ER[good])
out["cap_events_0.0075"]=int((np.round(av,6)==0.0075).sum())
out["cap_events_0.02"]=int((np.round(av,6)==0.02).sum())
out["cap_events_ge_0.0075"]=int((av>=0.0075).sum())
out["cap_events_share"]=float((av>=0.0075).mean())
out["cap_distinct_names"]=int(len(np.unique(EK[good][av>=0.0075])))
IV=np.asarray(F["IVNOW"],float)
sw=np.zeros(IV.shape,bool); sw[42:]=np.isfinite(IV[42:])&np.isfinite(IV[:-42])&(IV[42:]!=IV[:-42])
out["ivswitch_anchor_name_cells_nonzero"]=int((sw&BASE).sum())
# distinct switch EVENTS = transitions in IVNOW per name
tr=0; names=set()
for k in range(IV.shape[1]):
    v=IV[:,k]; ok=np.isfinite(v); idx=np.where(ok)[0]
    if len(idx)<2: continue
    d=(np.diff(v[idx])!=0).sum(); tr+=int(d)
    if d: names.add(k)
out["ivswitch_distinct_transitions"]=tr; out["ivswitch_distinct_names"]=len(names)
# listing events
fin=np.isfinite(y4); first=np.where(fin.any(0),fin.argmax(0),-1)
inwin=(first>=0)&(E[np.clip(first,0,len(E)-1)]>=ts[0])
out["listing_events_in_window"]=int(inwin.sum()); out["names_total"]=int(fin.shape[1])
out["names_with_any_finite"]=int((fin.any(0)).sum())
# delisting
last=np.where(fin.any(0),fin.shape[0]-1-fin[::-1].argmax(0),-1)
alive=fin.any(0)
out["names_ending_before_sample_end_30anchors"]=int(((last<len(E)-30)&alive).sum())
out["names_ending_before_end_and_gt100_finite"]=int(((last<len(E)-30)&(fin.sum(0)>100)).sum())
# A0 hour 12
A=np.load(f"{D}/probe_artifacts/w10_ablation_series_GP_dyn_s42.npz",allow_pickle=True); R=A["d30_n2_c42_rec"]
tsA=np.round(np.asarray(R[:,0],float)).astype(np.int64); g=R[:,18]/R[:,5]
hr=((tsA//3600)%24).astype(int)
out["A0_by_hour"]={str(h):{"n":int((hr==h).sum()),"mean_g":float(g[hr==h].mean()),
    "sharpe":float(g[hr==h].mean()/g[hr==h].std(ddof=1)*np.sqrt(2190))} for h in [0,4,8,12,16,20]}
json.dump(out,open(f"{ES}/EVENTCOUNTS.json","w"),indent=1); print(json.dumps(out,indent=1))
