import numpy as np, json, calendar, time
hole=set(json.load(open("/tmp/hole.json")))
A=np.load("/workspace/dlw_ext/data/dlw_targets.npz",allow_pickle=True)
E=A["E_ts"].astype(np.int64); Y=A["y4s"]
z=np.load("/workspace/review_scratch/allweather_trackB/replay/dev_alt/probe_artifacts/w10_ablation_series_G_mE1cX7_R0_spl42.npz",allow_pickle=True)
syms=[str(s) for s in z["symbols"]]; W=z["d30_n2_c42_W"]; R=z["d30_n2_c42_rec"]
ts=R[:,0].astype(np.int64); gt=R[:,5]; n=len(ts)
off=int(np.searchsorted(E,ts[0]))
idx={s:i for i,s in enumerate(syms)}; ecols=np.array([idx[s] for s in hole if s in idx])
meq=np.zeros(len(syms),bool); meq[ecols]=True
def reshape(w,g0,pop=None):
    w2=w.copy()
    if pop is not None: w2[pop]=0.0
    nz=np.abs(w2)>0
    if nz.sum()<2: return None
    w2[nz]-=w2[nz].mean(); s=np.abs(w2).sum()
    if s<=0: return None
    return w2*(g0/s)
pb=np.zeros(n); pp=np.zeros(n); eqw=np.zeros(n)
for i in range(n):
    w=W[i].astype(np.float64); y=np.nan_to_num(Y[off+i]).astype(np.float64); g0=np.abs(w).sum()
    if g0<=0: continue
    eqw[i]=np.abs(w[meq]).sum()/g0
    a=reshape(w,g0); b=reshape(w,g0,meq)
    if a is None or b is None: continue
    pb[i]=float((a*y).sum())*1e4; pp[i]=float((b*y).sum())*1e4
yr=np.array([time.gmtime(int(t)).tm_year for t in ts])
CUT=calendar.timegm((2026,8,10,20,0,0)); T2503=calendar.timegm((2025,3,1,0,0,0)); T24=calendar.timegm((2024,1,1,0,0,0))
gb=np.where(gt>0,pb/np.maximum(gt,1e-12),0); gp=np.where(gt>0,pp/np.maximum(gt,1e-12),0)
def sh(x): return float(x.mean()/x.std(ddof=1)*np.sqrt(2190)) if len(x)>2 and x.std(ddof=1)>0 else float("nan")
print(f"{'窗':>20s} {'n':>5s} {'股票占gross':>11s} {'基线(同变换)':>13s} {'剔除股票':>10s} {'Δ':>8s} {'ΔSharpe':>8s}")
def row(lab,m):
    if m.sum()<20: return
    a,b=gb[m],gp[m]
    print(f"{lab:>20s} {int(m.sum()):>5d} {eqw[m].mean()*100:>10.3f}% {a.mean():>+13.4f} {b.mean():>+10.4f} {b.mean()-a.mean():>+8.4f} {sh(b)-sh(a):>+8.3f}")
for y in (2024,2025,2026): row(f"{y} 全年",(yr==y)&(ts<=CUT))
row("2024→26 ≤cut",(ts>=T24)&(ts<=CUT))
row("★冻结 2025-03→cut",(ts>=T2503)&(ts<=CUT))
row("全史 ≤cut",ts<=CUT)
print("\n★ 基线与处理臂做完全相同的 re-demean+re-scale, 只差 pop 一步 ⇒ 2024(股票占比 0)的 Δ 应为 0, 用作装置自检")
