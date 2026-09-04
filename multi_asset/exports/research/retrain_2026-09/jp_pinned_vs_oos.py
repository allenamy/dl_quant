"""实盘 bundle 的 pinned king 预测是否样本内: 与年折 OOS / 季度滚动 OOS 在同一面板上比 IC 与腿收益(生产者 LR 定义)。"""
import numpy as np, time
from scipy.stats import spearmanr, rankdata
B="pod_backup_2026-08-21"; M=np.load(f"{B}/wide_fea_hist_meta.npz",allow_pickle=True); E=M["E_ts"].astype(np.int64); y4=M["y4"]; mem=M["members"]
SLOW=np.load(f"{B}/slow_pred_hist_oos.npy"); R=np.load("probe_artifacts/pinned_probe.npz"); pts=R["ts"].astype(np.int64); P=R["pred"]; ROLL=np.load("probe_artifacts/slow_pred_rollq_splice.npy")
mrow={int(t):i for i,t in enumerate(E)}
def yr(t): return time.gmtime(int(t)).tm_year
ic={}; lr={}
for k,t in enumerate(pts):
    i=mrow.get(int(t))
    if i is None: continue
    m=mem[i]; y=y4[i,m]; ok=np.isfinite(y)
    if ok.sum()<50: continue
    for nm,arr in (("pinned",P[k,m]),("oos",SLOW[i,m]),("roll",ROLL[i,m])):
        v=arr.astype(float); o=ok&np.isfinite(v)
        if o.sum()<50: continue
        ic.setdefault((yr(t),nm),[]).append(spearmanr(v[o],y[o]).correlation)
        z=np.full(len(m),np.nan); z[o]=rankdata(v[o])/max(o.sum()-1,1)-0.5; z=np.where(o,z,0.0); z-=z[o].mean(); g=np.abs(z).sum()
        lr.setdefault((yr(t),nm),[]).append(float((z/g*np.expm1(np.nan_to_num(y,nan=0.0))).sum()*1e4) if g>0 else 0.0)
print("年 | king IC: pinned / 年折OOS / 季度滚动 | king 腿收益 bps/锚(LR 定义): pinned / OOS / 滚动 | pinned 覆盖锚数")
for y in (2022,2023,2024,2025,2026):
    f=lambda nm: f"{np.mean(ic[(y,nm)]):+.4f}" if (y,nm) in ic else "  —  "
    g=lambda nm: f"{np.mean(lr[(y,nm)]):+.2f}" if (y,nm) in lr else " — "
    print(f"{y} | {f('pinned')} / {f('oos')} / {f('roll')} | {g('pinned')} / {g('oos')} / {g('roll')} | {len(ic.get((y,'pinned'),[]))}")
print("PINNED_DONE")
