"""X2 FundMap-lite @jpline(PREREG_legs_factors_2026-09-04): 走前(逐月)条件映射打分矩阵。
每月 m: 用 ≤ m−1 的最近 6 个月成员横截面(标准化 rank 特征)拟合 OLS: r4h_rank ~ a·rE + b·rT + c·rE·H + d·rT·H(+截距), 其中 rE=rank(EMA), rT=rank(now−EMA), H=1[σ_fund_t > 其滚动 2 年中位](因果);
月 m 的每锚打分 = 拟合系数 × 当锚特征(只用 ≤t 数据)。输出 fundmap_lite.npz(ts, symbols, mat: 面板行 × 829, 非成员/缺失 NaN)。"""
import numpy as np, time
from scipy.stats import rankdata
B="pod_backup_2026-08-21"; PD="probe_artifacts"
M=np.load(f"{B}/wide_fea_hist_meta.npz",allow_pickle=True); E=M["E_ts"].astype(np.int64); y4=M["y4"]; mem=M["members"]
P=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True); pts=P["ts"].astype(np.int64); syms=[str(s) for s in P["symbols"]]; FN=P["f_fund_now"]; IV=P["f_fund_iv"]; FE=P["f_fund_ema_v1"]; prow={int(t):j for j,t in enumerate(pts)}
NW=len(syms); L=len(pts); mat=np.full((L,NW),np.nan)
def rk(v):
    ok=np.isfinite(v); out=np.full(len(v),np.nan)
    if ok.sum()>=10: out[ok]=rankdata(v[ok])/max(ok.sum()-1,1)-0.5
    return out
def ym(t): g=time.gmtime(int(t)); return g.tm_year*100+g.tm_mon
# 逐锚特征与 σ_fund
rows=[]  # (i, j, m, rE, rT, y_rank, sig)
sig=np.full(len(E),np.nan)
for i,t in enumerate(E):
    j=prow.get(int(t))
    if j is None: continue
    m=mem[i]; f=FN[j,m]; iv=IV[j,m]; ivf=np.where(np.isfinite(iv)&(iv>0),iv,8.0); rn=np.nan_to_num(f,nan=0.0)*(8.0/ivf); ok=np.isfinite(f)
    if ok.sum()<50: continue
    sig[i]=np.std(rn[ok])*1e4
    e=FE[j,m]; tr=rn-np.nan_to_num(e,nan=0.0); rE=rk(e); rT=rk(np.where(np.isfinite(e),tr,np.nan)); yr_=rk(y4[i,m])
    rows.append((i,j,m,rE,rT,yr_))
# 因果 H: σ_fund 相对其滚动 2 年中位
sref=np.array([np.nanmedian(sig[max(0,i-4380):i+1]) if i>=1000 else np.nan for i in range(len(E))]); H=np.where(np.isfinite(sig)&np.isfinite(sref),(sig>sref).astype(float),np.nan)
months=sorted(set(ym(E[r[0]]) for r in rows)); by_m={}
for r in rows: by_m.setdefault(ym(E[r[0]]),[]).append(r)
coefs={}
for k,mth in enumerate(months):
    prev=[mm for mm in months[:k] if mm>=months[max(0,k-6)]]
    if len(prev)<3: continue
    X=[]; Y=[]
    for mm in prev:
        for (i,j,m,rE,rT,yr_) in by_m[mm]:
            h=H[i]
            if not np.isfinite(h): continue
            ok=np.isfinite(rE)&np.isfinite(rT)&np.isfinite(yr_)
            X.append(np.column_stack([np.ones(ok.sum()),rE[ok],rT[ok],rE[ok]*h,rT[ok]*h])); Y.append(yr_[ok])
    if not X: continue
    X=np.vstack(X); Y=np.concatenate(Y); beta=np.linalg.lstsq(X,Y,rcond=None)[0]; coefs[mth]=beta
    for (i,j,m,rE,rT,yr_) in by_m[mth]:
        h=H[i]
        if not np.isfinite(h): continue
        s=beta[0]+beta[1]*rE+beta[2]*rT+beta[3]*rE*h+beta[4]*rT*h; mat[j,m]=np.where(np.isfinite(rE)&np.isfinite(rT),s,np.nan)
np.savez_compressed(f"{PD}/fundmap_lite.npz", ts=pts, symbols=np.array(syms), mat=mat)
print("系数(a rE, b rT, c rE·H, d rT·H)按年均:")
for y in (2022,2023,2024,2025,2026):
    cs=[v for k,v in coefs.items() if k//100==y]
    if cs: c=np.mean(cs,axis=0); print(f"  {y}: a {c[1]:+.4f} b {c[2]:+.4f} c {c[3]:+.4f} d {c[4]:+.4f} (n月 {len(cs)})")
print("FUNDMAP_LITE_DONE finite", np.isfinite(mat).mean())
