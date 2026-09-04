"""最终判定: king/fund 腿收益在三种口径下 — y4old(=面板 y4 = Σ 5m 简单收益), y4s(=Π(1+r)−1 真简单收益 = 交易所记账), expm1(y4old)(=回放装置 CAL=simple 的做法), log1p(y4s)(=对数收益)。预测 = bundle 的 slow_pred_pinned(生产 king, 2024+ OOS)。"""
import numpy as np, time, json, os
FM=np.load("/workspace/data/wide_fea_v2ext_meta.npz",allow_pickle=True); FE=FM["E_ts"].astype(np.int64); FMEM=FM["members"]; FY4=FM["y4"]
DT=np.load("/workspace/data/dlw_targets.npz",allow_pickle=True); DE=DT["E_ts"].astype(np.int64); Y4S=DT["y4s"]; Y4O=DT["y4old"]; DMEM=DT["members"]
print("fea meta:", FE.shape, FY4.shape, "| dlw targets:", DE.shape, Y4S.shape, "y4old" in DT.files)
PRED=np.load("/workspace/shadow_bundle_v3/slow_pred_pinned.npy"); print("pinned:", PRED.shape)
drow={int(t):i for i,t in enumerate(DE)}
def xz(v):
    ok=np.isfinite(v); out=np.full(len(v),np.nan); n=ok.sum()
    if n>=10:
        r=np.empty(n); r[np.argsort(v[ok],kind="stable")]=np.arange(n); out[ok]=r/max(n-1,1)-0.5
    return out
def leg(pred,y):
    ok=np.isfinite(y); z=np.nan_to_num(xz(pred)); z=np.where(ok,z,0.0); z-=z[ok].mean() if ok.sum() else 0; g=np.abs(z).sum()
    return float((z/g*np.nan_to_num(y,nan=0.0)).sum()*1e4) if g>1e-9 else np.nan
rows=[]; chk=[]
for i,t in enumerate(FE):
    j=drow.get(int(t))
    if j is None: continue
    m=FMEM[i]
    yo=Y4O[j,m].astype(np.float64); ys=Y4S[j,m].astype(np.float64); yf=FY4[i,m].astype(np.float64)
    ok=np.isfinite(yo)&np.isfinite(ys)&np.isfinite(yf)
    if ok.sum()<50: continue
    chk.append((np.nanmedian(np.abs(yf[ok]-yo[ok])), np.mean((ys-yo)[ok]), np.mean((np.expm1(yo)-ys)[ok])))
    p=PRED[i,m]
    rows.append((time.gmtime(int(t)).tm_year, int(t), leg(p,yo), leg(p,ys), leg(p,np.expm1(yo)), leg(p,np.log1p(ys))))
A=np.array(rows); C=np.array(chk)
print(f"对账: 面板 y4 vs dlw y4old 同行中位|Δ| {np.median(C[:,0]):.2e} | mean(y4s−y4old) {np.mean(C[:,1]):+.2e} | mean(expm1(y4old)−y4s) {np.mean(C[:,2]):+.2e}  (每名每 4h, 1e-4=1bp)")
names=("Σ简单 y4old(面板/bundle/生产者)","真简单 y4s(交易所记账)","expm1(Σ简单)(回放装置 simple)","对数 log1p(y4s)")
for yv in (2024,2025,2026):
    s=A[:,0]==yv; print(f"{yv} n={s.sum()}: "+" | ".join(f"{nm}: {np.nanmean(A[s,2+k]):+.2f}" for k,nm in enumerate(names)))
s=np.zeros(len(A),bool); s[-900:]=True
print(f"末900锚 {time.strftime('%m-%d',time.gmtime(A[s,1].min()))}→{time.strftime('%m-%d',time.gmtime(A[s,1].max()))} king 腿 Sharpe/锚: "+" | ".join(f"{nm}: {np.nanmean(A[s,2+k])/np.nanstd(A[s,2+k]):+.3f} (均 {np.nanmean(A[s,2+k]):+.2f})" for k,nm in enumerate(names)))
# 差值分解: 真简单 − Σ简单 (交叉项, 应≈0) 与 expm1(Σ简单) − 真简单 (伪凸性)
d1=A[:,3]-A[:,2]; d2=A[:,4]-A[:,3]
print(f"king 腿 每锚: mean(真简单−Σ简单) {np.nanmean(d1):+.3f} bps (std {np.nanstd(d1):.2f}) | mean(expm1(Σ简单)−真简单) {np.nanmean(d2):+.3f} bps (2026: {np.nanmean(d2[A[:,0]==2026]):+.3f})")
print("TRUTH_DONE")
