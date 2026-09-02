"""机制三问 @jpline(B面板+meta+canon preds): (a) interval迁移自然实验 (b) king腿多/空侧IC不对称 (c) 深负空头挤压频率。"""
import numpy as np, time, collections
from scipy.stats import spearmanr
B="/mnt/storage/private/work_hsy/pod_backup_2026-08-21"; PD="/mnt/storage/private/work_hsy/probe_artifacts"
PW=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True); pts=PW["ts"].astype(np.int64)
FN=PW["f_fund_now"]; IV=PW["f_fund_iv"]; FE=PW["f_fund_ema_v1"]; Y4=PW["Y4"]
yrs=np.array([time.gmtime(int(t)).tm_year for t in pts])
NW=FN.shape[1]
# (a) 迁移自然实验: 每名首次 iv<8 的锚; 迁移前后各 90 天(540 锚) |fn 归一化| 均值 与 fund IC
first_mig=np.full(NW,-1)
for k in range(NW):
    iv=IV[:,k]; ok=np.isfinite(iv)
    idx=np.where(ok&(iv<8))[0]
    if len(idx) and np.isfinite(iv[:idx[0]]).any() and (iv[:idx[0]][np.isfinite(iv[:idx[0]])]==8).mean()>0.9:
        first_mig[k]=idx[0]
mig=np.where(first_mig>0)[0]
print(f"(a) 迁移自然实验: 有清晰 8h→短周期迁移点的名 {len(mig)}")
pre=[];post=[];pre_ic=[];post_ic=[]
for k in mig:
    i0=first_mig[k]
    a=slice(max(i0-540,0),i0); b=slice(i0,min(i0+540,len(pts)))
    ivn=np.where(np.isfinite(IV[:,k])&(IV[:,k]>0),IV[:,k],8.0); fn=np.nan_to_num(FN[:,k])*(8.0/ivn)
    pre.append(np.nanmean(np.abs(fn[a]))*1e4); post.append(np.nanmean(np.abs(fn[b]))*1e4)
print(f"    归一化|fund|均值(bp): 迁移前90天 {np.nanmean(pre):.2f} → 迁移后90天 {np.nanmean(post):.2f} (×{np.nanmean(post)/max(np.nanmean(pre),1e-9):.2f}); 中位 {np.nanmedian(pre):.2f}→{np.nanmedian(post):.2f}")
# 迁移名 vs 未迁移名 2026 fund 腿 IC(截面内: 两组各自 spearman(FE, Y4))
s26=np.where(yrs==2026)[0][::3]
ic_m=[];ic_u=[]
migset=set(mig.tolist())
for j in s26:
    v=FE[j]; y=Y4[j]; ok=np.isfinite(v)&np.isfinite(y)
    m_=np.array([k in migset for k in range(NW)])&ok; u_=(~np.array([k in migset for k in range(NW)]))&ok
    if m_.sum()>40: ic_m.append(spearmanr(v[m_],y[m_]).correlation)
    if u_.sum()>40: ic_u.append(spearmanr(v[u_],y[u_]).correlation)
print(f"    2026 fund腿组内IC: 已迁移名 {np.nanmean(ic_m):+.4f}(n锚{len(ic_m)}) vs 仍8h名 {np.nanmean(ic_u):+.4f}(n{len(ic_u)})")
# (b) king 腿多/空侧 IC 不对称: canon PRED(meta grid) 与 y4: 上半 vs 下半 排名内 spearman
MT=np.load(f"{B}/wide_fea_hist_meta.npz",allow_pickle=True); mts=MT["E_ts"].astype(np.int64); y4=MT["y4"]; members=MT["members"]
KP=np.load(f"{B}/slow_pred_hist_oos.npy") if __import__("os").path.exists(f"{B}/slow_pred_hist_oos.npy") else None
if KP is not None:
    myrs=np.array([time.gmtime(int(t)).tm_year for t in mts])
    out=collections.defaultdict(lambda:[[],[],[]])
    for i in range(0,len(mts),3):
        m=members[i]; p=KP[i,m]; y=y4[i,m]; ok=np.isfinite(p)&np.isfinite(y)
        if ok.sum()<60: continue
        p=p[ok]; y=y[ok]; med=np.median(p)
        top=p>=med; bot=p<med
        out[myrs[i]][0].append(spearmanr(p,y).correlation)
        out[myrs[i]][1].append(spearmanr(p[top],y[top]).correlation)
        out[myrs[i]][2].append(spearmanr(p[bot],y[bot]).correlation)
    print("(b) king OOS 预测: 年 | 全截面IC | 多头半区内IC | 空头半区内IC")
    for y in sorted(out):
        a=out[y]; print(f"    {y}: {np.nanmean(a[0]):+.4f} | {np.nanmean(a[1]):+.4f} | {np.nanmean(a[2]):+.4f}")
# (c) 挤压频率: 深负(<-10bp 归一化)名 vs 其他名, 4h 收益 > +8% 的频率, 分年; 以及 >+15%
print("(c) 挤压尾: 年 | 深负名 P(y4>+8%) | 其他名 | 深负 P(>+15%) | 其他")
for y in (2023,2024,2025,2026):
    sel=np.where(yrs==y)[0][::2]
    d1=[];o1=[];d2=[];o2=[]
    for j in sel:
        ivn=np.where(np.isfinite(IV[j])&(IV[j]>0),IV[j],8.0); fn=np.nan_to_num(FN[j])*(8.0/ivn); yv=Y4[j]; ok=np.isfinite(yv)
        deep=ok&(fn<-0.0010); oth=ok&(fn>=-0.0010)
        if deep.sum()>3: d1.append((yv[deep]>0.08).mean()); d2.append((yv[deep]>0.15).mean())
        if oth.sum()>3: o1.append((yv[oth]>0.08).mean()); o2.append((yv[oth]>0.15).mean())
    print(f"    {y}: {np.mean(d1)*100:5.2f}% | {np.mean(o1)*100:5.2f}% | {np.mean(d2)*100:5.2f}% | {np.mean(o2)*100:5.2f}%")
print("MECH3_DONE")
