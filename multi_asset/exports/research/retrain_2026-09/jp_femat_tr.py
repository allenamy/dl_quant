"""第八批 FEMAT: fe_λ = cz(EMA_v1) − λ·(cz(now8h) − cz(EMA_v1)), λ∈{0.1,0.2,0.3}; 面板网格, elig∧有限名; 其余 NaN。"""
import numpy as np
B="/mnt/storage/private/work_hsy/pod_backup_2026-08-21"; PD="/mnt/storage/private/work_hsy/probe_artifacts"
z=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True); ts=z["ts"].astype(np.int64); syms=z["symbols"]
S=z["f_fund_ema_v1"]; FN=z["f_fund_now"]; IV=z["f_fund_iv"]; ivn=np.where(np.isfinite(IV)&(IV>0),IV,8.0); FN8=FN*(8.0/ivn)
def cz_row(v):
    ok=np.isfinite(v); r=np.full(v.shape,np.nan,np.float32)
    if ok.sum()<3: return r
    x=v[ok]; r[ok]=(x-x.mean())/(x.std()+1e-12); return r
E=np.full(S.shape,np.nan,np.float32); T=np.full(S.shape,np.nan,np.float32)
for i in range(len(ts)):
    ok=np.isfinite(S[i])&np.isfinite(FN8[i])
    if ok.sum()<3: continue
    e=cz_row(np.where(ok,S[i],np.nan)); f=cz_row(np.where(ok,FN8[i],np.nan)); E[i]=e; T[i]=f-e
for lam in (0.1,0.2,0.3):
    fe=E-np.float32(lam)*np.nan_to_num(T,nan=0.0); fe=np.where(np.isfinite(E),fe,np.nan).astype(np.float32)
    np.savez_compressed(f"{PD}/femat_tr_l{int(lam*10):02d}.npz", ts=ts, symbols=np.array(syms), fe=fe); print("saved",lam, np.isfinite(fe).mean())
print("FEMAT_TR_DONE")
