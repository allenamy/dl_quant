"""carry_composition (pod, READ-ONLY): stop-layer (d30_n2_c42) vs no-stop (S0) carry, per gross dm caliber, for the replay live-form
with FTRIM=off (V1, scratch run) and FTRIM=zero (deployed form): 28-anchor overlap with se, by year, and S0 net_ex/carry_ex per NAV
(= 'what if the 08-26 live form, no FTRIM + no active stop, ran over history')."""
import numpy as np, json, time
def f(t): return time.strftime("%m-%d %HZ", time.gmtime(int(t)))
OV=[N for N in range(1787716800, 1788120000+1, 14400) if N!=1788033600]
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True); pts=PW["ts"].astype(np.int64); prow={int(t):i for i,t in enumerate(pts)}
FN=np.asarray(PW["f_fund_now"],float); IV=np.asarray(PW["f_fund_iv"],float); IVf=np.where(np.isfinite(IV)&(IV>0),IV,8.0); R4=np.nan_to_num(FN)*(4.0/IVf)
def dm(w):
    nz=np.abs(w)>1e-12; o=w.copy()
    if nz.any():
        o[nz]-=o[nz].mean(); g0=np.abs(w).sum(); g1=np.abs(o).sum()
        if g1>1e-9: o*=g0/g1
    return o
out={}
for tag,p in (("V1_noftrim","/workspace/review_scratch/carry_composition/dev/probe_artifacts/w10_ablation_series_cc_live_w3fix_noftrim_callog_s42.npz"),("deployed_ftrim","/workspace/port_w10/probe_artifacts/w10_ablation_series_pod_live_w3fix_callog_s42.npz")):
    z=np.load(p,allow_pickle=True); cols=[str(c) for c in z["cols"]]; res={}
    for arm in ("S0","d30_n2_c42"):
        R=z[arm+"_rec"]; W=z[arm+"_W"]; ts=R[:,cols.index("ts")].astype(np.int64); yy=np.array([time.gmtime(int(t)).tm_year for t in ts])
        c=np.full(len(ts),np.nan)
        for k in range(len(ts)):
            i=prow.get(int(ts[k]))
            if i is None: continue
            w=W[k].astype(float); g=np.abs(w).sum()
            if g>1e-9: c[k]=(dm(w)*R4[i]).sum()/g*1e4
        ovm=np.isin(ts,OV); nx=R[:,cols.index("net_ex")]; ce=R[:,cols.index("carry_ex")]; gt=R[:,cols.index("gross_total")]
        res[arm]={"overlap_c":c[ovm].tolist(),"by_year":{int(y):{"carry_dm":float(np.nanmean(c[yy==y])),"net_ex":float(nx[yy==y].mean()),"carry_ex":float(ce[yy==y].mean()),"gross":float(gt[yy==y].mean())} for y in sorted(set(yy.tolist()))},
                  "2024on":{"net_ex":float(nx[yy>=2024].mean()),"carry_ex":float(ce[yy>=2024].mean()),"sharpe_ex":float(nx[yy>=2024].mean()/nx[yy>=2024].std(ddof=1)*np.sqrt(2190)),"carry_dm":float(np.nanmean(c[yy>=2024]))}}
    d=np.array(res["d30_n2_c42"]["overlap_c"])-np.array(res["S0"]["overlap_c"])
    print(f"### {tag}: overlap28 carry_dm S0 {np.mean(res['S0']['overlap_c']):+.3f} | d30 {np.mean(res['d30_n2_c42']['overlap_c']):+.3f} | stop effect d30-S0 {d.mean():+.3f} (se {d.std(ddof=1)/np.sqrt(len(d)):.3f})")
    for y in res["S0"]["by_year"]:
        a=res["S0"]["by_year"][y]; b=res["d30_n2_c42"]["by_year"][y]
        print(f"  {y}: carry_dm S0 {a['carry_dm']:+.3f} d30 {b['carry_dm']:+.3f} (stop {b['carry_dm']-a['carry_dm']:+.3f}) | net_ex/NAV S0 {a['net_ex']:+.3f} d30 {b['net_ex']:+.3f} | carry_ex/NAV S0 {a['carry_ex']:+.3f} d30 {b['carry_ex']:+.3f} | gross S0 {a['gross']:.3f} d30 {b['gross']:.3f}")
    a=res["S0"]["2024on"]; b=res["d30_n2_c42"]["2024on"]
    print(f"  2024on: S0 net_ex {a['net_ex']:+.4f} sharpe {a['sharpe_ex']:.2f} carry_ex {a['carry_ex']:+.4f} carry_dm {a['carry_dm']:+.3f} | d30 net_ex {b['net_ex']:+.4f} sharpe {b['sharpe_ex']:.2f} carry_ex {b['carry_ex']:+.4f} carry_dm {b['carry_dm']:+.3f}")
    out[tag]=res
json.dump(out,open("/workspace/review_scratch/carry_composition/stop_arm.json","w"),indent=1)
