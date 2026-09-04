"""口径分解: 同一预测、同一公式(exporter 逐字), 只换 y4 原始(对数口径) vs expm1(y4)(简单口径), 看 king 腿收益差多少; 附 2022-23 样本内签名与 900 锚窗 Sharpe/锚。"""
import numpy as np, time
from scipy.stats import rankdata
B="pod_backup_2026-08-21"; PD="probe_artifacts"
M=np.load(f"{B}/wide_fea_hist_meta.npz",allow_pickle=True); E=M["E_ts"].astype(np.int64); mem=M["members"]; y4=M["y4"]
R=np.load(f"{PD}/pinned_probe.npz"); pts=R["ts"].astype(np.int64); PIN=R["pred"]; prow={int(t):k for k,t in enumerate(pts)}
SLOW=np.load(f"{B}/slow_pred_hist_oos.npy"); ROLL=np.load(f"{PD}/slow_pred_rollq_splice.npy")
def xz(v):
    ok=np.isfinite(v); out=np.full(len(v),np.nan)
    if ok.sum()>=10: out[ok]=rankdata(v[ok])/max(ok.sum()-1,1)-0.5
    return out
def w(pred, ok):
    z=np.nan_to_num(xz(pred)); z=np.where(ok,z,0.0); z-=z[ok].mean() if ok.sum() else 0; g=np.abs(z).sum()
    return z/g if g>1e-9 else None
rows=[]
for i,t in enumerate(E):
    k=prow.get(int(t))
    if k is None: continue
    m=mem[i]; y=y4[i,m]; ok=np.isfinite(y)
    if ok.sum()<50: continue
    yl=np.nan_to_num(y,nan=0.0); ys=np.expm1(yl)
    r=[time.gmtime(int(t)).tm_year, int(t)]
    for P in (PIN[k,m], SLOW[i,m], ROLL[i,m]):
        ww=w(P,ok)
        if ww is None: r+= [np.nan]*4; continue
        lg=float((ww*yl).sum()*1e4); sp=float((ww*ys).sum()*1e4)
        # 凸性项拆到空头/多头
        conv=ws=float((ww*(ys-yl))[ww<0].sum()*1e4); convl=float((ww*(ys-yl))[ww>0].sum()*1e4)
        r+=[lg,sp,conv,convl]
    r.append(float((w(y,ok)*ys).sum()*1e4))
    rows.append(r)
A=np.array(rows); yr=A[:,0]
names=("pinned(生产king)","OOS年折SLOW","滚动季king")
for yv in (2022,2023,2024,2025,2026):
    s=yr==yv
    line=f"{yv} n={s.sum():4d}"
    for j,nm in enumerate(names):
        lg,sp,cs,cl=(A[s,2+4*j+c] for c in range(4))
        line+=f" | {nm}: 对数 {np.nanmean(lg):+.2f} 简单 {np.nanmean(sp):+.2f} (凸性 空头 {np.nanmean(cs):+.2f} 多头 {np.nanmean(cl):+.2f})"
    print(line)
# 900 锚窗(面板末 900 锚) Sharpe/锚
s=np.zeros(len(A),bool); s[-900:]=True
print(f"末900锚窗 {time.strftime('%m-%d',time.gmtime(A[s,1].min()))}→{time.strftime('%m-%d',time.gmtime(A[s,1].max()))}:")
for j,nm in enumerate(names):
    lg=A[s,2+4*j]; sp=A[s,3+4*j]
    print(f"   {nm}: 对数口径 均 {np.nanmean(lg):+.2f} Sharpe/锚 {np.nanmean(lg)/np.nanstd(lg):+.3f} | 简单口径 均 {np.nanmean(sp):+.2f} Sharpe/锚 {np.nanmean(sp)/np.nanstd(sp):+.3f}")
# 样本内签名: 与完美预见腿相关(2022-23 生产 booster 训练年 vs 2026 留出年)
perf=A[:,-1]
for yv in (2022,2023,2024,2025,2026):
    s=yr==yv
    print(f"corr(pinned简单, 完美预见) {yv}: {np.corrcoef(A[s,3],perf[s])[0,1]:.3f} | OOS年折 {np.corrcoef(A[s,7],perf[s])[0,1]:.3f}")
print("DECOMP_DONE")
