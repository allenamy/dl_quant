"""funding alpha 是独立状态量还是因子代理? B 面板逐锚截面残差化(2020-01..2026-08):
IC_raw vs IC_resid(持久率) / R² / 分组吸收 / 2020-26 逐年符号(reversal→continuation) / 状态持久性 / 多空半区 / 4h vs 24h。
产物: femat_resid_v1.npz(fe = 残差化 f_fund_ema_v1, 面板网格, 供 w10_fundleg.py 书层复判)。"""
import numpy as np, time, collections
from scipy.stats import spearmanr
B="/mnt/storage/private/work_hsy/pod_backup_2026-08-21"; PD="/mnt/storage/private/work_hsy/probe_artifacts"
z=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True)
ts=z["ts"].astype(np.int64); yrs=np.array([time.gmtime(int(t)).tm_year for t in ts])
S=z["f_fund_ema_v1"]; FN=z["f_fund_now"]; IV=z["f_fund_iv"]; Y4=z["Y4"]; Y24=z["Y24"]; EL=z["elig"].astype(bool)
ivn=np.where(np.isfinite(IV)&(IV>0),IV,8.0); FN8=FN*(8.0/ivn)
GROUPS={"mom":["f_mom_7d","f_mom_30d","f_rev_24h","f_rev_3d"],"liq":["f_amihud_24h","f_asz_24h","f_tbf_24h"],"vol":["f_vol_7d","f_range_24h","f_cpos_24h"]}
FAC={k:z[k] for g in GROUPS.values() for k in g}
def xz(v):
    v=v.astype(float); ok=np.isfinite(v)
    if ok.sum()<3: return np.full_like(v,np.nan)
    r=np.full_like(v,np.nan); q=np.argsort(np.argsort(v[ok])); r[ok]=(q+0.5)/ok.sum()
    from scipy.stats import norm
    return norm.ppf(np.clip(r,1e-3,1-1e-3))
def resid(y,X):
    A=np.column_stack([np.ones(len(y))]+[x for x in X]); ok=np.isfinite(A).all(1)&np.isfinite(y)
    if ok.sum()<40: return np.full_like(y,np.nan),np.nan
    b,*_=np.linalg.lstsq(A[ok],y[ok],rcond=None); f=A@b; r=y-f
    r2=1-np.nanvar(r[ok])/max(np.nanvar(y[ok]),1e-12); return r,r2
FE_RES=np.full(S.shape,np.nan,np.float32)
rows=collections.defaultdict(list)
for i in range(len(ts)):
    if i%2: continue
    ok=EL[i]&np.isfinite(S[i])&np.isfinite(Y4[i])
    for k in FAC: ok&=np.isfinite(FAC[k][i])
    if ok.sum()<60: continue
    s=xz(np.where(ok,S[i],np.nan)); y=Y4[i]; y24=Y24[i]
    X_all=[xz(np.where(ok,FAC[k][i],np.nan)) for g in GROUPS.values() for k in g]
    r_all,r2=resid(s,X_all)
    FE_RES[i,ok]=r_all[ok]
    rec={"ic_raw":spearmanr(s[ok],y[ok]).correlation,"ic_res":spearmanr(r_all[ok],y[ok]).correlation,"r2":r2,
         "ic_fit":spearmanr((s-r_all)[ok],y[ok]).correlation,
         "ic_raw24":spearmanr(s[ok],y24[ok]).correlation if np.isfinite(y24[ok]).sum()>40 else np.nan,
         "ic_res24":spearmanr(r_all[ok],y24[ok]).correlation if np.isfinite(y24[ok]).sum()>40 else np.nan,
         "ic_fn8":spearmanr(FN8[i][ok],y[ok]).correlation}
    for g,ks in GROUPS.items():
        rg,_=resid(s,[xz(np.where(ok,FAC[k][i],np.nan)) for k in ks]); rec[f"ic_res_{g}"]=spearmanr(rg[ok],y[ok]).correlation
    pos=ok&(FN8[i]>0); neg=ok&(FN8[i]<0)
    rec["ic_pos"]=spearmanr(s[pos],y[pos]).correlation if pos.sum()>30 else np.nan
    rec["ic_neg"]=spearmanr(s[neg],y[neg]).correlation if neg.sum()>30 else np.nan
    rec["ic_res_pos"]=spearmanr(r_all[pos],y[pos]).correlation if pos.sum()>30 else np.nan
    rec["ic_res_neg"]=spearmanr(r_all[neg],y[neg]).correlation if neg.sum()>30 else np.nan
    rec["n"]=int(ok.sum())
    for k,v in rec.items(): rows[(yrs[i],k)].append(v)
def m(y,k): v=np.array(rows[(y,k)],float); v=v[np.isfinite(v)]; return v.mean() if len(v) else np.nan
def se(y,k): v=np.array(rows[(y,k)],float); v=v[np.isfinite(v)]; return v.std()/np.sqrt(max(len(v),1)) if len(v) else np.nan
Y=sorted(set(y for y,_ in rows))
print("A) 逐年: IC_raw(±se) | IC_resid(全因子) | 持久率 | R²(因子解释funding的比例) | IC_fit(被解释部分) | 锚数 | 名/锚")
for y in Y:
    n=len(rows[(y,'ic_raw')]); print(f"  {y}: {m(y,'ic_raw'):+.4f}±{se(y,'ic_raw'):.4f} | {m(y,'ic_res'):+.4f}±{se(y,'ic_res'):.4f} | {m(y,'ic_res')/m(y,'ic_raw') if abs(m(y,'ic_raw'))>1e-4 else float('nan'):5.2f} | {m(y,'r2'):.3f} | {m(y,'ic_fit'):+.4f} | {n} | {m(y,'n'):.0f}")
print("B) 分组吸收(只对该组残差化后的 IC): 年 | mom | liq | vol | 全组")
for y in Y: print(f"  {y}: {m(y,'ic_res_mom'):+.4f} | {m(y,'ic_res_liq'):+.4f} | {m(y,'ic_res_vol'):+.4f} | {m(y,'ic_res'):+.4f}")
print("C) reversal→continuation: 年 | IC(EMA→y4) | IC(fund_now 8h→y4) | IC(EMA→y24) | IC_resid(→y24)")
for y in Y: print(f"  {y}: {m(y,'ic_raw'):+.4f} | {m(y,'ic_fn8'):+.4f} | {m(y,'ic_raw24'):+.4f} | {m(y,'ic_res24'):+.4f}")
print("D) 多空半区(正费率名内 / 负费率名内): 年 | IC_pos | IC_neg | IC_res_pos | IC_res_neg")
for y in Y: print(f"  {y}: {m(y,'ic_pos'):+.4f} | {m(y,'ic_neg'):+.4f} | {m(y,'ic_res_pos'):+.4f} | {m(y,'ic_res_neg'):+.4f}")
print("E) 状态持久性: funding EMA 截面秩自相关 lag 6/42/180 锚(1d/1w/1m) vs 收益预测持久(IC)")
for y in Y:
    idx=np.where(yrs==y)[0][::6]; ac={}
    for L in (6,42,180):
        v=[]
        for i in idx:
            if i+L>=len(ts): continue
            ok=EL[i]&np.isfinite(S[i])&np.isfinite(S[i+L])
            if ok.sum()>60: v.append(spearmanr(S[i][ok],S[i+L][ok]).correlation)
        ac[L]=np.nanmean(v) if v else np.nan
    print(f"  {y}: ρ1d {ac[6]:.3f} ρ1w {ac[42]:.3f} ρ1m {ac[180]:.3f}")
np.savez_compressed(f"{PD}/femat_resid_v1.npz", fe=FE_RES, ts=ts, note="f_fund_ema_v1 residualized on mom/liq/vol (xz, per-anchor OLS), stride-2 anchors (odd anchors NaN)")
print("FUND_RESID_DONE")
