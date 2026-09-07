"""Regime 仪表盘历史基准(B 面板 2023-01..2026-08, 逐锚): σ_fund8h(bp) / 短周期名占比 / 深负名占比(≤−10bp) / 浅负占比 / 正费率占比 / fund IC(EMA→y4) 60锚滚动 / 瞬时IC(now−EMA→y4) 60锚滚动 / σ(y4) bp / 市场中位 y4 bp / 合格名数。产物: regime_hist.npz + 百分位 json。"""
import numpy as np, time, json
from scipy.stats import spearmanr, norm
B="/mnt/storage/private/work_hsy/pod_backup_2026-08-21"; PD="/mnt/storage/private/work_hsy/probe_artifacts"
z=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True); ts=z["ts"].astype(np.int64); yrs=np.array([time.gmtime(int(t)).tm_year for t in ts])
S=z["f_fund_ema_v1"]; FN=z["f_fund_now"]; IV=z["f_fund_iv"]; Y4=z["Y4"]; EL=z["elig"].astype(bool)
ivn=np.where(np.isfinite(IV)&(IV>0),IV,8.0); FN8=FN*(8.0/ivn)
sel=np.where(yrs>=2023)[0]; out={k:np.full(len(sel),np.nan) for k in ("sig_fund","short_iv_share","deepneg_share","shallowneg_share","pos_share","ic_fund","ic_tr","sig_y4","mkt_y4","n_elig")}
ic_f=np.full(len(ts),np.nan); ic_t=np.full(len(ts),np.nan)
def cz(v):
    ok=np.isfinite(v); r=np.full(v.shape,np.nan)
    if ok.sum()<3: return r
    x=v[ok]; r[ok]=(x-x.mean())/(x.std()+1e-12); return r
for i in range(len(ts)):
    if yrs[i]<2022: continue
    ok=EL[i]&np.isfinite(FN8[i])&np.isfinite(S[i])&np.isfinite(Y4[i])
    if ok.sum()>=60:
        e=cz(np.where(ok,S[i],np.nan)); f=cz(np.where(ok,FN8[i],np.nan)); tr=f-e
        ic_f[i]=spearmanr(S[i][ok],Y4[i][ok]).correlation; ic_t[i]=spearmanr(tr[ok],Y4[i][ok]).correlation
for k,i in enumerate(sel):
    ok=EL[i]&np.isfinite(FN8[i]); f=FN8[i][ok]; iv=ivn[i][ok]
    if ok.sum()<30: continue
    out["n_elig"][k]=ok.sum(); out["sig_fund"][k]=np.std(f)*1e4; out["short_iv_share"][k]=(iv<8).mean()
    out["deepneg_share"][k]=(f<=-0.0010).mean(); out["shallowneg_share"][k]=((f>-0.0010)&(f<0)).mean(); out["pos_share"][k]=(f>=0).mean()
    y=Y4[i][EL[i]&np.isfinite(Y4[i])]
    if len(y)>50: out["sig_y4"][k]=np.std(y)*1e4; out["mkt_y4"][k]=np.median(y)*1e4
    w=ic_f[max(0,i-59):i+1]; w=w[np.isfinite(w)]; out["ic_fund"][k]=w.mean() if len(w)>=20 else np.nan
    w=ic_t[max(0,i-59):i+1]; w=w[np.isfinite(w)]; out["ic_tr"][k]=w.mean() if len(w)>=20 else np.nan
np.savez_compressed(f"{PD}/regime_hist.npz", ts=ts[sel], **out)
pct={}
for k,v in out.items():
    v=v[np.isfinite(v)]; pct[k]={"p5":float(np.percentile(v,5)),"p25":float(np.percentile(v,25)),"p50":float(np.percentile(v,50)),"p75":float(np.percentile(v,75)),"p95":float(np.percentile(v,95)),"last90d_mean":float(v[-540:].mean()),"n":int(len(v))}
    yy=yrs[sel]; pct[k]["by_year"]={int(Y):float(np.nanmean(out[k][yy==Y])) for Y in (2023,2024,2025,2026)}
json.dump(pct, open(f"{PD}/regime_hist_pct.json","w"), indent=1)
print(json.dumps({k:{"p50":round(v["p50"],4),"2024":round(v["by_year"][2024],4),"2026":round(v["by_year"][2026],4)} for k,v in pct.items()}, indent=0)[:1500])
print("REGIME_HIST_DONE")
