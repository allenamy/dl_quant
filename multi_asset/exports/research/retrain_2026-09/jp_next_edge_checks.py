"""前沿方向数据体检(B 面板 + canon 回放 2023+):
(a) regime 状态可预测性: σ_fund 的 1周/2周/1月 持久性预测 vs AR(3) 技能; σ_fund 变化是否领先 fund IC(lead-lag);
(b) 映射状态(in-context): 60 锚滚动 IC 的自相关与符号翻转检出滞后(2022/2025 型);
(c) 有效广度 N_eff: canon 回放权重 × 180 锚滚动相关 ⇒ N_eff=(Σ|w|)²/(w'Σw) 逐锚(stride 6), 与后 30 锚净额/回撤的关系。"""
import numpy as np, time
PD="/mnt/storage/private/work_hsy/probe_artifacts"; B="/mnt/storage/private/work_hsy/pod_backup_2026-08-21"
H=np.load(f"{PD}/regime_hist.npz"); ts=H["ts"].astype(np.int64); sig=H["sig_fund"]; icf=H["ic_fund"]; ict=H["ic_tr"]
ok=np.isfinite(sig)&np.isfinite(icf); ts=ts[ok]; sig=sig[ok]; icf=icf[ok]; ict=ict[ok]
ls=np.log(np.maximum(sig,0.1))
print("(a) σ_fund 可预测性(log): 视界 | 持久性预测 RMSE | AR(3) RMSE | 技能增益 | 均值回归 RMSE")
for h in (42,84,180):
    y=ls[h:]; p=ls[:-h]
    X=np.column_stack([np.ones(len(ls)-h-3*42), ls[3*42:-h], ls[2*42:-h-42], ls[42:-h-2*42]]) ; yy=ls[3*42+h:]
    n=len(yy)//2; b,*_=np.linalg.lstsq(X[:n],yy[:n],rcond=None); pred=X[n:]@b
    rm_p=np.sqrt(np.mean((y[3*42:][n:]-p[3*42:][n:])**2)); rm_ar=np.sqrt(np.mean((yy[n:]-pred)**2)); rm_m=np.sqrt(np.mean((yy[n:]-ls[:n].mean())**2))
    print(f"  {h/6:.0f}天 | {rm_p:.3f} | {rm_ar:.3f} | {(1-rm_ar/rm_p)*100:+.1f}% | {rm_m:.3f}")
print("(a2) lead-lag corr(Δσ_fund(t, 42锚差) , IC_fund(t+h) − IC_fund(t)):")
d=ls[42:]-ls[:-42]; 
for h in (0,42,84,180,360):
    a=d[:len(d)-h] if h else d; b=(icf[42+h:]-icf[42:len(icf)-h]) if h else (icf[42:]-icf[:-42])
    m=min(len(a),len(b)); print(f"  h={h/6:.0f}天: {np.corrcoef(a[:m],b[:m])[0,1]:+.3f}")
print("(b) 映射状态: IC_fund(60锚滚动) 自相关 lag 42/180/360:", [round(float(np.corrcoef(icf[:-L],icf[L:])[0,1]),3) for L in (42,180,360)])
# 符号翻转检出: 以 360 锚(60天)滚动 IC 的符号 作为"当前映射"判断; 与 年度真值比
yrs=np.array([time.gmtime(int(t)).tm_year for t in ts])
for L in (180,360,900):
    roll=np.array([icf[max(0,i-L):i+1].mean() for i in range(len(icf))])
    for Y in (2024,2025,2026):
        s=yrs==Y; frac=(np.sign(roll[s])==np.sign(icf[s].mean())).mean()
        print(f"  L={L}: {Y} 年内滚动符号与全年符号一致占比 {frac*100:.0f}%(全年 IC 均 {icf[s].mean():+.4f})")
# (c) N_eff
z=np.load(f"{PD}/w10_canonpred_s42.npz",allow_pickle=True); cols=[str(c) for c in z["cols"]]; rec=z["d30_n2_c42_rec"]; W=z["d30_n2_c42_W"]
rts=rec[:,cols.index("ts")].astype(np.int64); net=rec[:,cols.index("net_ex")].astype(float)
PW=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True); pts=PW["ts"].astype(np.int64); prow={int(t):j for j,t in enumerate(pts)}; Y4=PW["Y4"]
neff=[]; neff_naive=[]; tt=[]; fwd=[]
for i in range(1200,len(rts),6):
    w=W[i].astype(float); nz=np.where(np.abs(w)>1e-9)[0]
    if len(nz)<30: continue
    j=prow.get(int(rts[i])); 
    if j is None or j<180: continue
    R=Y4[j-180:j][:,nz]; okc=np.isfinite(R).mean(0)>0.8; nz=nz[okc]; R=R[:,okc]; R=np.nan_to_num(R-np.nanmean(R,0))
    sd=R.std(0)+1e-12; C=(R/sd).T@(R/sd)/len(R); ww=w[nz]/np.abs(w[nz]).sum(); v=ww@C@ww
    neff.append(1.0/max(v,1e-9)); neff_naive.append(1.0/np.sum(ww**2)); tt.append(rts[i]); fwd.append(net[i:i+30].mean() if i+30<=len(net) else np.nan)
neff=np.array(neff); nn=np.array(neff_naive); tt=np.array(tt); fwd=np.array(fwd); yy=np.array([time.gmtime(int(t)).tm_year for t in tt])
print("(c) N_eff(相关调整) 逐年 均/最低 | 名义 N_eff 均:")
for Y in (2023,2024,2025,2026): s=yy==Y; print(f"  {Y}: {neff[s].mean():.0f} / {neff[s].min():.0f} | {nn[s].mean():.0f}")
q=np.nanquantile(neff,[0.2,0.8]); lo=neff<=q[0]; hi=neff>=q[1]; f=np.isfinite(fwd)
print(f"  N_eff 最低五分位锚 后30锚净 {np.nanmean(fwd[lo&f]):+.3f} vs 最高五分位 {np.nanmean(fwd[hi&f]):+.3f} bps/锚; corr(N_eff, 后30锚净) {np.corrcoef(neff[f],fwd[f])[0,1]:+.3f}")
mo=np.array([time.gmtime(int(t)).tm_year*100+time.gmtime(int(t)).tm_mon for t in tt]); print("  2026 逐月 N_eff:", {int(m)%100:int(neff[mo==m].mean()) for m in sorted(set(mo[yy==2026]))})
np.savez_compressed(f"{PD}/neff_series.npz", ts=tt, neff=neff, neff_naive=nn)
print("NEXT_EDGE_DONE")
