"""全史 alpha 衰减(执行时点)检验: 目标窗 (E, E+4h] vs 平移 +25min/+30min 的窗 (E+k·5m, E+4h+k·5m], 真简单收益 Π(1+r)−1, 用 5 分钟原生数据(dlnative)重算. 腿: king(pinned, 2024+ OOS) / fund / F10(s42); 书代理 0.21·xz(king)+0.79·xz(fund) (无 FTRIM/EMA/成本)."""
import numpy as np, time, glob, os
DT=np.load("/workspace/data/dlw_targets.npz",allow_pickle=True); DE=DT["E_ts"].astype(np.int64); ER=DT["E_row"].astype(np.int64); DMEM=DT["members"]
FM=np.load("/workspace/data/wide_fea_v2ext_meta.npz",allow_pickle=True); FE=FM["E_ts"].astype(np.int64); FMEM=FM["members"]; frow={int(t):i for i,t in enumerate(FE)}
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True); pts=PW["ts"].astype(np.int64); FUND=PW["f_fund_ema_v1"]; prow={int(t):i for i,t in enumerate(pts)}
PRED=np.load("/workspace/shadow_bundle_v3/slow_pred_pinned.npy"); F10=np.load("/workspace/f8_2026-08-22/preds/f10_V2MAIN_s42.npy")
cands=[p for p in glob.glob("/workspace/data/dlnative_5m_wide829_f16_*.npz")]; print("5m files:", cands)
Z=np.load(cands[0] if len(cands)==1 else [p for p in cands if "ext" in p][0], allow_pickle=True); print("5m keys:", Z.files)
D=Z["data"] if "data" in Z.files else Z[[k for k in Z.files if Z[k].ndim==3][0]]; print("5m data shape", D.shape, D.dtype)
r5=D[:,:,0].astype(np.float32); T=r5.shape[0]
fin=np.isfinite(r5); r5z=np.where(fin,r5,0).astype(np.float64)
CS_L=np.concatenate([np.zeros((1,r5.shape[1])), np.cumsum(np.log1p(r5z),0)]); CS_f=np.concatenate([np.zeros((1,r5.shape[1]),np.int32), np.cumsum(fin,0,dtype=np.int32)])
def y4s_shift(E,k):
    lo=E+1+k; hi=E+48+1+k
    if hi>T: return None
    y=np.expm1(CS_L[hi]-CS_L[lo]); n=CS_f[hi]-CS_f[lo]; y[n<46]=np.nan; return y
def xz(v):
    ok=np.isfinite(v); out=np.full(len(v),np.nan); n=ok.sum()
    if n>=10:
        r=np.empty(n); r[np.argsort(v[ok],kind="stable")]=np.arange(n); out[ok]=r/max(n-1,1)-0.5
    return out
def book(z,y):
    ok=np.isfinite(y)&np.isfinite(z); zz=np.where(ok,z,0.0); zz=zz-(zz[ok].mean() if ok.sum() else 0); g=np.abs(zz).sum()
    return float((zz/g*np.nan_to_num(y,nan=0.0)).sum()*1e4) if g>1e-9 else np.nan
SH=(0,5,6)
rows=[]
for j,t in enumerate(DE):
    i=frow.get(int(t)); k=prow.get(int(t))
    if i is None or k is None: continue
    m=FMEM[i]; E=ER[j]
    ys=[y4s_shift(E,s) for s in SH]
    if any(y is None for y in ys): continue
    zk=xz(PRED[i,m]); zf=xz(FUND[k,m]); z10=xz(F10[j,m]); zb=0.21*np.nan_to_num(zk)+0.79*np.nan_to_num(zf)
    r=[time.gmtime(int(t)).tm_year]
    for y in ys:
        yy=y[m]; r+=[book(zk,yy),book(zf,yy),book(z10,yy),book(zb,yy)]
    rows.append(r)
A=np.array(rows); print("n anchors", len(A))
names=("king","fund","F10","书代理0.21/0.79")
for yv in (2024,2025,2026):
    s=A[:,0]==yv
    for li,nm in enumerate(names):
        vals=[np.nanmean(A[s,1+4*si+li]) for si in range(len(SH))]
        print(f"{yv} {nm:14s}: 平移 0 {vals[0]:+.2f} | +25min {vals[1]:+.2f} | +30min {vals[2]:+.2f}   (保留比例 +25min {vals[1]/vals[0]*100 if abs(vals[0])>0.05 else float('nan'):.0f}%)")
print("ALPHA_DECAY_DONE")
