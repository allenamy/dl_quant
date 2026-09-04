"""bundle leg_returns.npz king 列的取证: (a) 用 exporter 的逐字公式(成员全体, 原始 y4, xz 有限预测)从 slow_pred_pinned.npy 重算 king 腿收益, 与 bundle 列比; (b) 样本内签名: 各 king 腿收益序列与"完美预见腿"(rank(y4) 书)收益的相关系数。"""
import numpy as np, time
from scipy.stats import rankdata
B="pod_backup_2026-08-21"; PD="probe_artifacts"
M=np.load(f"{B}/wide_fea_hist_meta.npz",allow_pickle=True); E=M["E_ts"].astype(np.int64); mem=M["members"]; y4=M["y4"]
R=np.load(f"{PD}/pinned_probe.npz"); pts=R["ts"].astype(np.int64); PIN=R["pred"]; prow={int(t):k for k,t in enumerate(pts)}
SLOW=np.load(f"{B}/slow_pred_hist_oos.npy"); ROLL=np.load(f"{PD}/slow_pred_rollq_splice.npy")
BL=np.load(f"{PD}/bundle_leg_returns.npz"); bts=BL["ts"].astype(np.int64); bk=BL["king"]; brow={int(t):k for k,t in enumerate(bts)}
def xz(v):
    ok=np.isfinite(v); out=np.full(len(v),np.nan)
    if ok.sum()>=10: out[ok]=rankdata(v[ok])/max(ok.sum()-1,1)-0.5
    return out
def leg(pred, y, ok):
    z=np.nan_to_num(xz(pred)); z=np.where(ok,z,0.0); z-=z[ok].mean() if ok.sum() else 0; g=np.abs(z).sum()
    return float((z/g*np.nan_to_num(y,nan=0.0)).sum()*1e4) if g>1e-9 else 0.0
rows=[]
for i,t in enumerate(E):
    if t<1735689600: continue
    k=prow.get(int(t)); b=brow.get(int(t))
    if k is None or b is None: continue
    m=mem[i]; y=y4[i,m]; ok=np.isfinite(y)
    if ok.sum()<50: continue
    rows.append((time.gmtime(int(t)).tm_year, bk[b], leg(PIN[k,m],y,ok), leg(SLOW[i,m],y,ok), leg(ROLL[i,m],y,ok), leg(y,y,ok)))
A=np.array(rows)
for yv in (2025,2026):
    s=A[:,0]==yv; bkv,pin,oos,roll,perf=(A[s,c] for c in range(1,6))
    print(f"{yv} n={s.sum()}: bundle king 均 {bkv.mean():+.2f} | pinned 重算 {pin.mean():+.2f} | OOS 年折 {oos.mean():+.2f} | 滚动 {roll.mean():+.2f} | 完美预见腿 {perf.mean():+.1f}")
    print(f"     corr(bundle, pinned重算) {np.corrcoef(bkv,pin)[0,1]:.3f} | corr(bundle, 完美预见) {np.corrcoef(bkv,perf)[0,1]:.3f} | corr(pinned重算, 完美) {np.corrcoef(pin,perf)[0,1]:.3f} | corr(OOS, 完美) {np.corrcoef(oos,perf)[0,1]:.3f} | corr(滚动, 完美) {np.corrcoef(roll,perf)[0,1]:.3f}")
print("FORENSICS_DONE")
