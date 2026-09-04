"""三腿(king/fund/rev24)+F10(若有预测) 在三口径下的腿收益: y4old=Σ简单(面板/bundle/生产者) · y4s=Π(1+r)−1(真简单=交易所记账) · expm1(y4old)(回放装置 CAL=simple)。逐年 + 末900窗 Sharpe/锚 + 偏差(expm1 − 真简单)。另核对面板 Y4 键 vs y4old。"""
import numpy as np, time, glob, os
FM=np.load("/workspace/data/wide_fea_v2ext_meta.npz",allow_pickle=True); FE_ts=FM["E_ts"].astype(np.int64); FMEM=FM["members"]
DT=np.load("/workspace/data/dlw_targets.npz",allow_pickle=True); DE=DT["E_ts"].astype(np.int64); Y4S=DT["y4s"]; Y4O=DT["y4old"]
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True); pts=PW["ts"].astype(np.int64); FUND=PW["f_fund_ema_v1"]; R24=PW["f_rev_24h"]; PY4=PW["Y4"]
PRED=np.load("/workspace/shadow_bundle_v3/slow_pred_pinned.npy")
f10=None
for c in glob.glob("/workspace/**/f10_V2MAIN_s42.npy",recursive=True):
    a=np.load(c); print("f10 candidate", c, a.shape); f10=(c,a) if a.shape[0] in (len(FE_ts),len(DE)) else f10
drow={int(t):i for i,t in enumerate(DE)}; prow={int(t):i for i,t in enumerate(pts)}
def xz(v):
    ok=np.isfinite(v); out=np.full(len(v),np.nan); n=ok.sum()
    if n>=10:
        r=np.empty(n); r[np.argsort(v[ok],kind="stable")]=np.arange(n); out[ok]=r/max(n-1,1)-0.5
    return out
def leg(pred,y):
    ok=np.isfinite(y)&np.isfinite(pred); z=np.nan_to_num(xz(np.where(ok,pred,np.nan))); z=np.where(ok,z,0.0); z-=z[ok].mean() if ok.sum() else 0; g=np.abs(z).sum()
    return float((z/g*np.nan_to_num(y,nan=0.0)).sum()*1e4) if g>1e-9 else np.nan
rows=[]; py4chk=[]
for i,t in enumerate(FE_ts):
    j=drow.get(int(t)); k=prow.get(int(t))
    if j is None or k is None: continue
    m=FMEM[i]; yo=Y4O[j,m].astype(np.float64); ys=Y4S[j,m].astype(np.float64)
    ok=np.isfinite(yo)&np.isfinite(ys)
    if ok.sum()<50: continue
    py4chk.append(np.nanmedian(np.abs(PY4[k,m].astype(np.float64)[ok]-yo[ok])))
    legs={"king":PRED[i,m], "fund":FUND[k,m], "rev24":-R24[k,m]}
    if f10 is not None:
        F=f10[1]; legs["f10"]=F[i,m] if F.shape[0]==len(FE_ts) else F[j,m]
    r=[time.gmtime(int(t)).tm_year,int(t)]
    for nm in ("king","fund","rev24","f10"):
        if nm in legs: p=legs[nm]; r+=[leg(p,yo),leg(p,ys),leg(p,np.expm1(yo))]
        else: r+=[np.nan]*3
    rows.append(r)
A=np.array(rows); print(f"n anchors {len(A)} | 面板 Y4 键 vs dlw y4old 同行中位|Δ| {np.median(py4chk):.2e}")
cal=("Σ简单","真简单","expm1(Σ简单)")
for li,nm in enumerate(("king","fund","rev24","f10")):
    c0=2+3*li
    if np.all(np.isnan(A[:,c0])): continue
    print(f"--- {nm} 腿 (bps/锚, 单位腿 gross)")
    for yv in (2024,2025,2026):
        s=A[:,0]==yv; print(f"  {yv}: "+" | ".join(f"{cal[c]} {np.nanmean(A[s,c0+c]):+.2f}" for c in range(3))+f" | 偏差 expm1−真简单 {np.nanmean(A[s,c0+2]-A[s,c0+1]):+.2f}")
    s=np.zeros(len(A),bool); s[-900:]=True
    print(f"  末900锚 Sharpe/锚: "+" | ".join(f"{cal[c]} {np.nanmean(A[s,c0+c])/np.nanstd(A[s,c0+c]):+.3f}" for c in range(3)))
print("ALLLEGS_DONE")
