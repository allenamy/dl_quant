"""GAP#4 sensitivity: (1) LOW-tercile calendar blocks; (2) σ_fund over meta members only (instruction wording) vs all-finite (jp_allweather.py L15)."""
import numpy as np, time, json
P=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True); pts=P["ts"].astype(np.int64); FN=P["f_fund_now"]; IV=P["f_fund_iv"]; prow={int(t):j for j,t in enumerate(pts)}
MT=np.load("/workspace/data/wide_fea_v2ext_meta.npz",allow_pickle=True); E=MT["E_ts"].astype(np.int64); MB=MT["members"]; mrow={int(t):i for i,t in enumerate(E)}
print("members dtype/shape",MB.dtype,MB.shape,"first elem",type(MB[0]),np.asarray(MB[0]).dtype,len(MB[0]),"mean len",np.mean([len(x) for x in MB]))
def sigfund(ts,members_only=False):
    out=np.full(len(ts),np.nan)
    for k,t in enumerate(ts):
        j=prow.get(int(t))
        if j is None: continue
        f=FN[j]; iv=IV[j]; iv=np.where(np.isfinite(iv)&(iv>0),iv,8.0); r=f*(8.0/iv)
        if members_only:
            i=mrow.get(int(t))
            if i is None: continue
            r=r[np.asarray(MB[i]).astype(int)]
        r=r[np.isfinite(r)]
        if len(r)>50: out[k]=np.std(r)*1e4
    return out
yr=lambda ts: np.array([time.gmtime(int(t)).tm_year for t in ts]); d=lambda t: time.strftime("%Y-%m-%d",time.gmtime(int(t)))
for tag,f in (("pod_live_w3fix_callog_s42","/workspace/port_w10/probe_artifacts/w10_ablation_series_pod_live_w3fix_callog_s42.npz"),("alt_true_new_w3fix","/workspace/review_scratch/refute_C6_1/dev/probe_artifacts/w10_ablation_series_alt_true_new_w3fix.npz"),("pod_live_callog_s42","/workspace/port_w10/probe_artifacts/w10_ablation_series_pod_live_callog_s42.npz")):
    z=np.load(f,allow_pickle=True); cols=[str(c) for c in z["cols"]]; R=z["d30_n2_c42_rec"]; ts=R[:,cols.index("ts")].astype(np.int64); ne=R[:,cols.index("net_ex")]; gt=R[:,cols.index("gross_total")]; Y=yr(ts)
    for mo in (False,True):
        sf=sigfund(ts,mo); roll=np.array([np.nanmean(sf[max(0,i-29):i+1]) for i in range(len(sf))]); sel=(Y>=2024)&np.isfinite(roll); q=np.quantile(roll[sel],[1/3,2/3])
        low=sel&(roll<=q[0]); mid=sel&(roll>q[0])&(roll<=q[1]); high=sel&(roll>q[1])
        def st(s): x=ne[s]; return f"n{int(s.sum())} net {x.mean():+.3f} → {x.mean()/gt[s].mean()*2190/100:+.1f}%/gross/yr S{x.mean()/x.std(ddof=1)*np.sqrt(2190):+.2f}"
        print(f"{tag} members_only={mo} cuts {q[0]:.2f}/{q[1]:.2f} | LOW {st(low)} | MID {st(mid)} | HIGH {st(high)}")
        if not mo:
            idx=np.where(low)[0]; br=np.where(np.diff(idx)>1)[0]; starts=np.r_[idx[0],idx[br+1]]; ends=np.r_[idx[br],idx[-1]]
            print("   LOW blocks (>=30 anchors): "+"; ".join(f"{d(ts[a])}→{d(ts[b])}({b-a+1})" for a,b in zip(starts,ends) if b-a+1>=30))
            idx=np.where(high)[0]; br=np.where(np.diff(idx)>1)[0]; starts=np.r_[idx[0],idx[br+1]]; ends=np.r_[idx[br],idx[-1]]
            print("   HIGH blocks (>=30 anchors): "+"; ".join(f"{d(ts[a])}→{d(ts[b])}({b-a+1})" for a,b in zip(starts,ends) if b-a+1>=30))
            # monthly σ_fund roll mean 2024→26 for the record
            mm=np.array([time.strftime("%Y-%m",time.gmtime(int(t))) for t in ts]); print("   monthly roll σ_fund: "+" ".join(f"{m}:{np.nanmean(roll[mm==m]):.1f}" for m in sorted(set(mm[Y>=2024]))))
print("SENS_DONE")
