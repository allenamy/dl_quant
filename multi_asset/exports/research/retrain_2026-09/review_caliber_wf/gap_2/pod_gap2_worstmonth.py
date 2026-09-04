# worst calendar month of net_ex (bps NAV-book), definition mirrors /workspace/port_w10/summarize.py L16-18: msum = {m: nx[ym==m].sum()}; wm = min(msum)
import numpy as np, time, json
yr=lambda ts: np.array([time.gmtime(int(t)).tm_year for t in ts]); ym=lambda ts: np.array([time.gmtime(int(t)).tm_year*100+time.gmtime(int(t)).tm_mon for t in ts])
PA="/workspace/port_w10/probe_artifacts"; ALT="/workspace/review_scratch/refute_C6_1/dev/probe_artifacts"
S={"fixed_sum":f"{PA}/w10_ablation_series_pod_live_w3fix_callog_s42.npz","fixed_pi":f"{ALT}/w10_ablation_series_alt_true_new_w3fix.npz","fixed_sumnew":f"{ALT}/w10_ablation_series_alt_sum_new_w3fix.npz","fixed_expm1":f"{PA}/w10_ablation_series_pod_live_w3fix_calsimple_s42.npz",
   "dyn_sum":f"{PA}/w10_ablation_series_pod_live_callog_s42.npz","dyn_pi":f"{ALT}/w10_ablation_series_alt_true_new_dyn.npz","dyn_sumnew":f"{ALT}/w10_ablation_series_alt_sum_new_dyn.npz","dyn_expm1":f"{PA}/w10_ablation_series_pod_live_calsimple_s42.npz"}
out={}
for k,p in S.items():
    z=np.load(p,allow_pickle=True); cols=[str(c) for c in z["cols"]]; rec=z["d30_n2_c42_rec"]
    ts=rec[:,cols.index("ts")].astype(np.int64); nx=rec[:,cols.index("net_ex")].astype(float); gt=rec[:,cols.index("gross_total")].astype(float); Y=yr(ts); M=ym(ts)
    r={}
    for y in (2022,2023,2024):
        s=Y==y; msum={int(m):float(nx[(M==m)].sum()) for m in np.unique(M[s])}; wm=min(msum,key=msum.get); g=float(gt[s].mean())
        r[y]={"worst_month":f"{wm//100}-{wm%100:02d}","bps":round(msum[wm],1),"pct_gross":round(msum[wm]/g/100,2),"pct_nav_2x":round(msum[wm]/g/100*2,2),"gross_year_mean":round(g,3)}
    out[k]=r
json.dump(out,open("/workspace/review_scratch/gap_2/gap2_worstmonth.json","w"),indent=1)
for k,r in out.items(): print(k, {y:(v["worst_month"],v["bps"],v["pct_gross"],v["pct_nav_2x"]) for y,v in r.items()})
