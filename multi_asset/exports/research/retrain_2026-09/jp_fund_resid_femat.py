"""D1 书层复判用: 全锚(stride 1)残差化 f_fund_ema_v1 → femat_resid_v1.npz(ts, symbols, fe; 与 pod_femat_build 同格式)。"""
import numpy as np
from scipy.stats import norm
B="/mnt/storage/private/work_hsy/pod_backup_2026-08-21"; PD="/mnt/storage/private/work_hsy/probe_artifacts"
z=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True)
ts=z["ts"].astype(np.int64); syms=z["symbols"]; S=z["f_fund_ema_v1"]; EL=z["elig"].astype(bool)
KEYS=["f_mom_7d","f_mom_30d","f_rev_24h","f_rev_3d","f_amihud_24h","f_asz_24h","f_tbf_24h","f_vol_7d","f_range_24h","f_cpos_24h"]
FAC=[z[k] for k in KEYS]
def xz(v):
    ok=np.isfinite(v); r=np.full(v.shape,np.nan)
    if ok.sum()<3: return r
    q=np.argsort(np.argsort(v[ok])); r[ok]=norm.ppf(np.clip((q+0.5)/ok.sum(),1e-3,1-1e-3)); return r
FE=np.full(S.shape,np.nan,np.float32); nfit=0
for i in range(len(ts)):
    ok=EL[i]&np.isfinite(S[i])
    for f in FAC: ok&=np.isfinite(f[i])
    if ok.sum()<40:   # 因子不齐的早期锚: 保留原分数(不残差化)以免腿消失; 标记
        FE[i]=np.where(np.isfinite(S[i]),S[i],np.nan); continue
    s=xz(np.where(ok,S[i],np.nan).astype(float)); A=np.column_stack([np.ones(ok.sum())]+[xz(np.where(ok,f[i],np.nan).astype(float))[ok] for f in FAC])
    b,*_=np.linalg.lstsq(A,s[ok],rcond=None); r=np.full(S.shape[1],np.nan,np.float32); r[ok]=(s[ok]-A@b); FE[i]=r; nfit+=1
print(f"femat resid: anchors {len(ts)} fitted {nfit} finite {np.isfinite(FE).mean():.3f}")
np.savez_compressed(f"{PD}/femat_resid_v1.npz", ts=ts, symbols=np.array(syms), fe=FE)
print("FEMAT_RESID_DONE")
