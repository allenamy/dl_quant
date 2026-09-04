# Replicates jp_live_caliber_tables.py stats() L18-22 (equity x (1+L*net_ex/1e4), ann = eq^(2190/n)-1, sharpe = mean/(std ddof0+1e-12)*sqrt(2190), dd = min(eq/cummax-1), worst month = min monthly prod-1) on pod series.
import numpy as np, time, json
yr=lambda ts: np.array([time.gmtime(int(t)).tm_year for t in ts]); ym=lambda ts: np.array([time.gmtime(int(t)).tm_year*100+time.gmtime(int(t)).tm_mon for t in ts])
def stats(r, L, ts):
    x=L*r/1e4; eq=np.cumprod(1+x); n=len(x); ann=eq[-1]**(2190/n)-1 if n>0 else np.nan; sh=x.mean()/(x.std()+1e-12)*np.sqrt(2190)
    dd=(eq/np.maximum.accumulate(eq)-1).min(); mm=ym(ts); months=np.unique(mm); wm=min(np.prod(1+x[mm==m])-1 for m in months)
    return ann, sh, dd, wm, n
S={"fixed_live_calsimple":"/workspace/port_w10/probe_artifacts/w10_ablation_series_pod_live_w3fix_calsimple_s42.npz",
   "fixed_live_callog":"/workspace/port_w10/probe_artifacts/w10_ablation_series_pod_live_w3fix_callog_s42.npz",
   "armB_N400_FTRIM_fx_calsimple":"/workspace/review_scratch/gap_2/dev/probe_artifacts/w10_ablation_series_gap2_armB_calsimple.npz",
   "armB_N400_FTRIM_fx_callog":"/workspace/review_scratch/gap_2/dev/probe_artifacts/w10_ablation_series_gap2_armB_callog.npz",
   "dyn_live_calsimple":"/workspace/port_w10/probe_artifacts/w10_ablation_series_pod_live_calsimple_s42.npz",
   "dyn_live_callog":"/workspace/port_w10/probe_artifacts/w10_ablation_series_pod_live_callog_s42.npz"}
out={}
for k,p in S.items():
    z=np.load(p,allow_pickle=True); cols=[str(c) for c in z["cols"]]; rec=z["d30_n2_c42_rec"]; cfg=json.loads(str(z["config_json"]))
    ts=rec[:,cols.index("ts")].astype(np.int64); ne=rec[:,cols.index("net_ex")].astype(float); gt=rec[:,cols.index("gross_total")].astype(float); Y=yr(ts)
    r={"CAL":cfg.get("CAL"),"MEMBERS_TOPN":cfg.get("MEMBERS_TOPN"),"TRADE_TOPN":cfg.get("TRADE_TOPN"),"FTRIM":cfg.get("FTRIM"),"W3FIX":cfg.get("W3FIX"),"rows":{}}
    for y in range(2022,2027):
        s=Y==y
        if s.sum()<100: continue
        ann,sh,dd,wm,n=stats(ne[s],2.0,ts[s]); annG,_,ddG,_,_=stats(ne[s]/gt[s],2.0,ts[s])
        r["rows"][y]={"AUDIT_formula_2x_ann":round(float(ann),4),"sharpe_ddof0":round(float(sh),3),"DD_2x":round(float(dd),4),"worst_month_2x":round(float(wm),4),"n":int(n),"mean_net_ex":round(float(ne[s].mean()),4),"gross_mean":round(float(gt[s].mean()),3),"per_gross_2x_ann_compounded":round(float(annG),4),"per_gross_DD_2x":round(float(ddG),4)}
    for lab,s in (("2023+",Y>=2023),("2025-26",Y>=2025),("2024-26",Y>=2024)):
        ann,sh,dd,wm,n=stats(ne[s],2.0,ts[s]); r["rows"][lab]={"AUDIT_formula_2x_ann":round(float(ann),4),"sharpe_ddof0":round(float(sh),3),"DD_2x":round(float(dd),4),"worst_month_2x":round(float(wm),4),"n":int(n)}
    out[k]=r
json.dump(out,open("/workspace/review_scratch/gap_2/gap2_auditformula.json","w"),indent=1)
for k,r in out.items():
    print(f"[{k}] CAL={r['CAL']} M={r['MEMBERS_TOPN']} T={r['TRADE_TOPN']} FTRIM={r['FTRIM']} W3FIX={r['W3FIX']}")
    for y,v in r["rows"].items():
        if isinstance(y,int) or y.isdigit(): print(f"   {y}: 2x ann {v['AUDIT_formula_2x_ann']:+.1%} S {v['sharpe_ddof0']:+.2f} DD {v['DD_2x']:+.1%} worstM {v['worst_month_2x']:+.1%} n {v['n']} mean {v['mean_net_ex']:+.4f} gross {v['gross_mean']} | per-gross 2x ann {v['per_gross_2x_ann_compounded']:+.1%} DD {v['per_gross_DD_2x']:+.1%}")
        else: print(f"   {y}: 2x ann {v['AUDIT_formula_2x_ann']:+.1%} S {v['sharpe_ddof0']:+.2f} DD {v['DD_2x']:+.1%} worstM {v['worst_month_2x']:+.1%} n {v['n']}")
