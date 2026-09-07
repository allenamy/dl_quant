"""(a) 重跑: interval 迁移自然实验, 只用两窗内 fn 与 iv 同时有限的行(排除上市前零行偏差); 按迁移年分组; 配对比。"""
import numpy as np, time
B="/mnt/storage/private/work_hsy/pod_backup_2026-08-21"
PW=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True); pts=PW["ts"].astype(np.int64)
FN=PW["f_fund_now"]; IV=PW["f_fund_iv"]; NW=FN.shape[1]; W=540
rows=[]
for k in range(NW):
    iv=IV[:,k]; fn=FN[:,k]; ok=np.isfinite(iv)&np.isfinite(fn)&(iv>0)
    idx=np.where(ok&(iv<8))[0]
    if not len(idx): continue
    i0=idx[0]; pre=np.arange(max(i0-W,0),i0); post=np.arange(i0,min(i0+W,len(pts)))
    pre=pre[ok[pre]]; post=post[ok[post]]
    if len(pre)<300 or len(post)<300: continue
    if (iv[pre]==8).mean()<0.95: continue
    a=np.abs(fn[pre]*(8.0/iv[pre])).mean()*1e4; b=np.abs(fn[post]*(8.0/iv[post])).mean()*1e4
    rows.append((time.gmtime(int(pts[i0])).tm_year, a, b, np.median(np.abs(fn[pre]*(8.0/iv[pre])))*1e4, np.median(np.abs(fn[post]*(8.0/iv[post])))*1e4))
R=np.array(rows)
print(f"(a2) 清晰迁移名(两窗各≥300有限行, 迁移前≥95%为8h): {len(R)}")
print(f"    归一化|fund| 均值 bp: 前 {R[:,1].mean():.2f} → 后 {R[:,2].mean():.2f} (配对比中位 ×{np.median(R[:,2]/np.maximum(R[:,1],1e-9)):.2f}); 中位数: 前 {R[:,3].mean():.2f} → 后 {R[:,4].mean():.2f}")
for y in sorted(set(R[:,0].astype(int))):
    s=R[R[:,0]==y]; print(f"    迁移年 {y}: n={len(s)} 前 {s[:,1].mean():.2f} → 后 {s[:,2].mean():.2f}")
# 对照: 同期未迁移名(全程 8h)在同一日历窗的 |fund| 变化 — 用每个迁移锚 i0 抽样对照名
ctrl=[]
allc=[k for k in range(NW) if np.isfinite(IV[:,k]).any() and np.nanmax(np.where(np.isfinite(IV[:,k]),IV[:,k],0))<=8 and (np.nanmin(np.where(np.isfinite(IV[:,k]),IV[:,k],8))>=8)]
print(f"    全程 8h 对照名: {len(allc)}")
for k in range(NW):
    iv=IV[:,k]; fn=FN[:,k]; ok=np.isfinite(iv)&np.isfinite(fn)&(iv>0); idx=np.where(ok&(iv<8))[0]
    if not len(idx): continue
    i0=idx[0]; pre=slice(max(i0-W,0),i0); post=slice(i0,min(i0+W,len(pts)))
    A=np.abs(np.nan_to_num(FN[pre][:,allc])); Bq=np.abs(np.nan_to_num(FN[post][:,allc]))
    A=A[A>0]; Bq=Bq[Bq>0]
    if len(A)>1000 and len(Bq)>1000: ctrl.append((A.mean()*1e4,Bq.mean()*1e4))
C=np.array(ctrl); print(f"    对照(全程8h名, 同日历窗): 前 {C[:,0].mean():.2f} → 后 {C[:,1].mean():.2f} bp (×{C[:,1].mean()/C[:,0].mean():.2f})")
print("MECHA2_DONE")
