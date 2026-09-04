"""腿层快测(简单口径=交易所记账): king 腿在四种权重形态下的年度均值/夏普 — 基线 xz; 逆波动 xz/σ; 逆方差 xz/σ²; 空侧逆波动(只缩空头); 以及"空头 σ 顶 20% 置零". σ_i = 该名过去 42 个 4h 对数收益的 std(只用 t 之前已实现的行, 点时). 仅用 OOS 预测(年折 SLOW=复现装置 king; pinned=生产 king 2024+)."""
import numpy as np, time
from scipy.stats import rankdata
B="pod_backup_2026-08-21"; PD="probe_artifacts"
M=np.load(f"{B}/wide_fea_hist_meta.npz",allow_pickle=True); E=M["E_ts"].astype(np.int64); mem=M["members"]; y4=M["y4"]
R=np.load(f"{PD}/pinned_probe.npz"); pts=R["ts"].astype(np.int64); PIN=R["pred"]; prow={int(t):k for k,t in enumerate(pts)}
SLOW=np.load(f"{B}/slow_pred_hist_oos.npy")
def xz(v):
    ok=np.isfinite(v); out=np.full(len(v),np.nan)
    if ok.sum()>=10: out[ok]=rankdata(v[ok])/max(ok.sum()-1,1)-0.5
    return out
def book(z, ok, ys):
    z=np.where(ok&np.isfinite(z),z,0.0); z=z-(z[ok].mean() if ok.sum() else 0); g=np.abs(z).sum()
    return float((z/g*ys).sum()*1e4) if g>1e-9 else np.nan
WIN=42
out={}
for i,t in enumerate(E):
    if i<WIN+1: continue
    m=mem[i]; y=y4[i,m]; ok=np.isfinite(y)
    if ok.sum()<50: continue
    ys=np.expm1(np.nan_to_num(y,nan=0.0))
    hist=y4[i-WIN:i, m]            # 行 i-WIN..i-1 的 4h 收益, 在锚 i 时均已实现
    sig=np.nanstd(hist,axis=0); nfin=np.isfinite(hist).sum(0)
    sig=np.where(nfin>=20, sig, np.nan); sig=np.where(np.isfinite(sig)&(sig>1e-4), sig, np.nanmedian(sig))
    yr=time.gmtime(int(t)).tm_year
    for nm,P in (("OOS年折SLOW",SLOW[i,m]),("pinned生产king",(PIN[prow[int(t)],m] if int(t) in prow else None))):
        if P is None: continue
        z=xz(P); zs=np.nan_to_num(z)
        arms={"基线 xz":zs, "逆波动 xz/σ":zs/sig, "逆方差 xz/σ²":zs/sig**2,
              "空侧逆波动":np.where(zs<0, zs/sig*np.nanmedian(sig), zs),
              "空头σ顶20%置零":np.where((zs<0)&(sig>=np.nanpercentile(sig[zs<0],80)),0.0,zs) if (zs<0).sum()>10 else zs}
        for a,zz in arms.items():
            out.setdefault((nm,a),[]).append((yr, book(zz,ok,ys)))
for (nm,a),rows in out.items():
    A=np.array(rows); s=f"{nm:14s} {a:12s}:"
    for yv in (2022,2023,2024,2025,2026):
        v=A[A[:,0]==yv,1]; v=v[np.isfinite(v)]
        s+=f" {yv} {v.mean():+.2f}({v.mean()/v.std()*np.sqrt(2190):+.1f})" if len(v)>100 else f" {yv} —"
    print(s)
print("KVOL_LEG_DONE")
