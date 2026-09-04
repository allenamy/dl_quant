import numpy as np, time
B="pod_backup_2026-08-21"; PD="probe_artifacts"
M=np.load(f"{B}/wide_fea_hist_meta.npz",allow_pickle=True); E=M["E_ts"].astype(np.int64); mem=M["members"]
SLOW=np.load(f"{B}/slow_pred_hist_oos.npy"); ROLL=np.load(f"{PD}/slow_pred_rollq_splice.npy"); R=np.load(f"{PD}/pinned_probe.npz"); pts=R["ts"].astype(np.int64); P=R["pred"]; prow={int(t):k for k,t in enumerate(pts)}
yr=lambda t: time.gmtime(int(t)).tm_year
cov={}
for i,t in enumerate(E):
    m=mem[i]; y=yr(t); d=cov.setdefault(y,{"oos":[],"roll":[],"pin":[],"n":0}); d["n"]+=1
    d["oos"].append(np.isfinite(SLOW[i,m]).mean()); d["roll"].append(np.isfinite(ROLL[i,m]).mean())
    k=prow.get(int(t)); d["pin"].append(np.isfinite(P[k,m]).mean() if k is not None else np.nan)
print("年 | 成员中有 king 分数的占比: 年折 OOS / 季度滚动 / bundle pinned | 锚数")
for y in sorted(cov): d=cov[y]; print(f"{y} | {np.mean(d['oos']):.2f} / {np.mean(d['roll']):.2f} / {np.nanmean(d['pin']):.2f} | {d['n']}")
def legstats(tag):
    z=np.load(f"{PD}/w10_{tag}.npz",allow_pickle=True); cols=[str(c) for c in z["cols"]]; rec=z["d30_n2_c42_rec"]; ts=rec[:,cols.index("ts")].astype(np.int64); lk=rec[:,cols.index("leg_king")].astype(float); Y=np.array([yr(t) for t in ts])
    return {y:(round(lk[Y==y].mean(),2), round(lk[Y==y].std(),1)) for y in (2024,2025,2026)}
print("king 腿收益 均/std(bps/锚): 年折 OOS", legstats("canonpred_s42"), "| 季度滚动", legstats("rk_ms_s42"))
