"""D2: 费率瞬时分量(fund_now8h − EMA_v1) vs 持久分量(EMA_v1) 的逐年 IC(y4/y24), 及正交化后各自 IC。"""
import numpy as np, time, collections
from scipy.stats import spearmanr
B="/mnt/storage/private/work_hsy/pod_backup_2026-08-21"
z=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True)
ts=z["ts"].astype(np.int64); yrs=np.array([time.gmtime(int(t)).tm_year for t in ts])
S=z["f_fund_ema_v1"]; FN=z["f_fund_now"]; IV=z["f_fund_iv"]; Y4=z["Y4"]; Y24=z["Y24"]; EL=z["elig"].astype(bool)
ivn=np.where(np.isfinite(IV)&(IV>0),IV,8.0); FN8=FN*(8.0/ivn)
# EMA_v1 与 fund_now 量纲: 先各自截面 z, 再差
def cz(v):
    ok=np.isfinite(v); r=np.full(v.shape,np.nan)
    if ok.sum()<3: return r
    x=v[ok]; r[ok]=(x-x.mean())/(x.std()+1e-12); return r
rows=collections.defaultdict(list)
for i in range(0,len(ts),2):
    ok=EL[i]&np.isfinite(S[i])&np.isfinite(FN8[i])&np.isfinite(Y4[i])
    if ok.sum()<60: continue
    e=cz(np.where(ok,S[i],np.nan)); f=cz(np.where(ok,FN8[i],np.nan)); tr=f-e   # 瞬时 = 当前费率超出持久水平的部分
    # 正交: tr ⟂ e
    b=np.nansum(tr[ok]*e[ok])/max(np.nansum(e[ok]**2),1e-12); tro=tr-b*e
    y=Y4[i]; y24=Y24[i]; ok24=ok&np.isfinite(y24)
    rows[(yrs[i],"ic_e4")].append(spearmanr(e[ok],y[ok]).correlation); rows[(yrs[i],"ic_tr4")].append(spearmanr(tr[ok],y[ok]).correlation); rows[(yrs[i],"ic_tro4")].append(spearmanr(tro[ok],y[ok]).correlation)
    if ok24.sum()>40:
        rows[(yrs[i],"ic_e24")].append(spearmanr(e[ok24],y24[ok24]).correlation); rows[(yrs[i],"ic_tr24")].append(spearmanr(tr[ok24],y24[ok24]).correlation); rows[(yrs[i],"ic_tro24")].append(spearmanr(tro[ok24],y24[ok24]).correlation)
    rows[(yrs[i],"corr_e_f")].append(spearmanr(e[ok],f[ok]).correlation)
def m(y,k): v=np.array(rows[(y,k)],float); v=v[np.isfinite(v)]; return (v.mean(), v.std()/np.sqrt(max(len(v),1))) if len(v) else (np.nan,np.nan)
print("D2) 年 | 持久 EMA→y4 | 瞬时(now−EMA)→y4 | 瞬时⟂EMA→y4 | 持久→y24 | 瞬时→y24 | 瞬时⟂→y24 | corr(EMA,now)")
for y in sorted(set(a for a,_ in rows)):
    print(f"  {y}: {m(y,'ic_e4')[0]:+.4f}±{m(y,'ic_e4')[1]:.4f} | {m(y,'ic_tr4')[0]:+.4f}±{m(y,'ic_tr4')[1]:.4f} | {m(y,'ic_tro4')[0]:+.4f} | {m(y,'ic_e24')[0]:+.4f} | {m(y,'ic_tr24')[0]:+.4f} | {m(y,'ic_tro24')[0]:+.4f} | {m(y,'corr_e_f')[0]:.2f}")
print("FUND_D2_DONE")
