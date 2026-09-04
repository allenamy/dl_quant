import numpy as np, time
B="pod_backup_2026-08-21"; PD="probe_artifacts"
M=np.load(f"{B}/wide_fea_hist_meta.npz",allow_pickle=True); E=M["E_ts"].astype(np.int64); mem=M["members"]; y4=M["y4"]
SLOW=np.load(f"{B}/slow_pred_hist_oos.npy"); ROLL=np.load(f"{PD}/slow_pred_rollq_splice.npy"); R=np.load(f"{PD}/pinned_probe.npz"); pts=R["ts"].astype(np.int64); P=R["pred"]; prow={int(t):k for k,t in enumerate(pts)}
def probe(i,lab):
    m=mem[i]; k=prow.get(int(E[i]))
    for nm,v in (("OOS年折",SLOW[i,m]),("滚动",ROLL[i,m]),("pinned",P[k,m] if k is not None else np.full(len(m),np.nan))):
        f=v[np.isfinite(v)]; print(f"  {lab} {nm}: n有限 {len(f)}/{len(m)} 唯一值 {len(np.unique(np.round(f,8)))} std {f.std() if len(f) else float('nan'):.5f} 均 {f.mean() if len(f) else float('nan'):+.5f} 前5 {np.round(f[:5],5)}")
for T,lab in ((1786838400-14400*100,"2026-08-09"),(1767225600+14400*300,"2026-03-22"),(1735689600+14400*1000,"2025-06-15"),(1704067200+14400*500,"2024-04-23")):
    i=int(np.argmin(np.abs(E-T))); probe(i,time.strftime("%Y-%m-%d",time.gmtime(int(E[i]))))
