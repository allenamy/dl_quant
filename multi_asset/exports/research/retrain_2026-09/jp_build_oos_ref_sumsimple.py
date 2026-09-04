"""E-0904-C 修复备料 v2: 用装置 legs() 的逐字定义(xz 秩→去均值→单位 gross→expm1(y4))在正典成员上重算三腿**原始**腿收益(king=年折 OOS SLOW; rev24=−f_rev_24h; fund=f_fund_ema_v1),
并核对 rec 列 leg_* = w3 × 原始腿收益(席位加权贡献)。输出 leg_returns_oos_ref_sumsimple.npz(ts, king, rev24, fund) 与 bundle 同 schema。只备料。"""
import numpy as np, time, hashlib
from scipy.stats import rankdata
B="pod_backup_2026-08-21"; PD="probe_artifacts"
M=np.load(f"{B}/wide_fea_hist_meta.npz",allow_pickle=True); E=M["E_ts"].astype(np.int64); mem=M["members"]; y4=M["y4"]
P=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True); pts=P["ts"].astype(np.int64); prow={int(t):j for j,t in enumerate(pts)}; R24=P["f_rev_24h"]; FE=P["f_fund_ema_v1"]
SLOW=np.load(f"{B}/slow_pred_hist_oos.npy")
def xz(v):
    ok=np.isfinite(v); out=np.full(len(v),np.nan)
    if ok.sum()>=10: out[ok]=rankdata(v[ok])/max(ok.sum()-1,1)-0.5
    return out
ts=[]; LR={"king":[],"rev24":[],"fund":[]}
for i,t in enumerate(E):
    j=prow.get(int(t))
    if j is None: continue
    m=mem[i]; sc={"king":SLOW[i,m],"rev24":-R24[j,m],"fund":FE[j,m]}; ok=np.isfinite(y4[i,m])
    if ok.sum()<10: continue
    yy=np.nan_to_num(y4[i,m],nan=0.0)   # 无偏口径: 面板 y4 = Σ 5m 简单收益, 不做 expm1 (E-0904-F); row={}
    for leg in LR:
        z=np.nan_to_num(xz(sc[leg])); z=np.where(ok,z,0.0); z-=z[ok].mean() if ok.sum() else 0; g=np.abs(z).sum()
        row[leg]=float((z/g*yy).sum()*1e4) if g>1e-9 else 0.0
    ts.append(int(t)); [LR[k].append(row[k]) for k in LR]
ts=np.array(ts); K=np.array(LR["king"]); R_=np.array(LR["rev24"]); F=np.array(LR["fund"])
# 核对: rec leg_king ≈ w3_king × 原始
z=np.load(f"{PD}/w10_canonpred_s42.npz",allow_pickle=True); cols=[str(c) for c in z["cols"]]; rec=z["d30_n2_c42_rec"]; rts=rec[:,cols.index("ts")].astype(np.int64); lk=rec[:,cols.index("leg_king")].astype(float); wk=rec[:,cols.index("w3_king")].astype(float); lf=rec[:,cols.index("leg_fund")].astype(float); wf=rec[:,cols.index("w3_fund")].astype(float)
mi={int(t):i for i,t in enumerate(ts)}; a=[];b=[];c=[];d=[]
for p,t in enumerate(rts):
    i=mi.get(int(t))
    if i is None or wk[p]<0.05: continue
    a.append(lk[p]); b.append(wk[p]*K[i]); c.append(lf[p]); d.append(wf[p]*F[i])
a,b,c,d=map(np.array,(a,b,c,d)); print(f"核对 rec.leg_king vs w3_king×原始king: corr {np.corrcoef(a,b)[0,1]:.4f} 比值中位 {np.median(a/np.where(np.abs(b)>1e-6,b,np.nan)):.3f} (n{len(a)}) | fund: corr {np.corrcoef(c,d)[0,1]:.4f} 比值 {np.median(c/np.where(np.abs(d)>1e-6,d,np.nan)):.3f}")
yr=np.array([time.gmtime(int(t)).tm_year for t in ts])
print("原始腿收益 均 bps/锚(king OOS / rev24 / fund):", {y:(round(K[yr==y].mean(),2),round(R_[yr==y].mean(),2),round(F[yr==y].mean(),2)) for y in (2022,2023,2024,2025,2026)})
print("原始 king 腿 std:", {y:round(K[yr==y].std(),1) for y in (2024,2025,2026)})
np.savez_compressed(f"{PD}/leg_returns_oos_ref_sumsimple.npz", ts=ts, king=K, rev24=R_, fund=F)
k=K[-900:]; r=R_[-900:]; f=F[-900:]; shp=np.maximum([k.mean()/(k.std()+1e-9), r.mean()/(r.std()+1e-9), f.mean()/(f.std()+1e-9)],0); w=shp/shp.sum(); w=w*np.array([1,0,1.0]); w=w/w.sum()
print(f"OOS seed {len(ts)} 锚 → {time.strftime('%Y-%m-%d %HZ',time.gmtime(int(ts[-1])))} | 末 900 锚 msharpe 席位 king/fund = {w[0]:.3f}/{w[2]:.3f} | sha {hashlib.sha256(open(f'{PD}/leg_returns_oos_ref_sumsimple.npz','rb').read()).hexdigest()[:12]}")
print("SEED_BUILT")
