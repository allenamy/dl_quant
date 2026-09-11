import numpy as np, importlib.util, calendar
spec=importlib.util.spec_from_file_location("j","/workspace/uplift_2026-09-11/judgeD.py"); j=importlib.util.module_from_spec(spec); spec.loader.exec_module(j)
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
def load0(p): return j.load(p,"d30_n2_c42_rec")
HC="/workspace/review_scratch/health_check/dev_v4/probe_artifacts"
t0,g0,R0=load0(f"{HC}/w10_ablation_series_V4_A0_dyn_s42.npz")
t0b,g0b,_=load0(f"{HC}/w10_ablation_series_V4_A0_dyn_s2027.npz")
def get(tg):
    ts,g,R=j.load(f"/workspace/uplift_2026-09-11/trackD_v4/{tg}.npz","rec")
    idx=np.clip(np.searchsorted(ts,t0),0,len(ts)-1)
    return np.where(ts[idx]==t0,g[idx],np.nan), R[idx,17]
LIQ,tL=get("SL_ORTH_f_amihud_24h__p"); SUR,tS=get("SL_ORTH_D_SURP__m"); TBF,tT=get("SL_f_tbf_24h__p")
WIN={"full 2022->26-08-10":(T(2022,1,1),T(2026,8,10,20)+1),"frozen 25-03->26-08-10":(T(2025,3,1),T(2026,8,10,20)+1),
     "EXT live-bleed 08-11->08-31":(T(2026,8,11),T(2026,8,31,20)+1),
     "2022":(T(2022,1,1),T(2023,1,1)),"2023":(T(2023,1,1),T(2024,1,1)),"2024":(T(2024,1,1),T(2025,1,1)),
     "2025":(T(2025,1,1),T(2026,1,1)),"2026->08-10":(T(2026,1,1),T(2026,8,10,20)+1)}
COMB={"A0 alone":g0,
 "1/2 A0 +1/4 ORTH_LIQ +1/4 ORTH_SURP":0.5*g0+0.25*LIQ+0.25*SUR,
 "1/3 each A0/ORTH_LIQ/ORTH_SURP":(g0+LIQ+SUR)/3.0,
 "1/4 each +TBF (4 books)":0.25*(g0+LIQ+SUR+TBF)}
def st(v,m):
    x=v[m]; x=x[np.isfinite(x)]
    if len(x)<3: return None
    c=np.concatenate([[0.0],np.cumsum(x)])
    return x.mean(), float(x.mean()/x.std(ddof=1)*np.sqrt(2190)), float(np.max(np.maximum.accumulate(c)-c))
print(f"{'window':30s} "+" ".join(f"{k[:34]:>26s}" for k in COMB))
for w,(lo,hi) in WIN.items():
    m=(t0>=lo)&(t0<hi); row=[]
    for k,v in COMB.items():
        s=st(v,m); row.append(f"{s[0]:+7.3f}/{s[1]:+6.2f}/dd{s[2]:5.0f}" if s else "")
    print(f"{w:30s} "+" ".join(f"{r:>26s}" for r in row))
print("\nturnover/anchor: A0 %.4f | ORTH_LIQ %.4f | ORTH_SURP %.4f | TBF %.4f"%(R0[:,17].mean(),np.nanmean(tL),np.nanmean(tS),np.nanmean(tT)))
# second seed
idx=np.clip(np.searchsorted(t0,t0b),0,len(t0)-1); ok=t0[idx]==t0b
L2=np.where(ok,LIQ[idx],np.nan); S2=np.where(ok,SUR[idx],np.nan)
print("\n--- second-seed A0 (s2027), same sleeves, 1/3 each ---")
for w,(lo,hi) in WIN.items():
    m=(t0b>=lo)&(t0b<hi)
    a=st(g0b,m); b=st((g0b+L2+S2)/3.0,m)
    if a and b: print(f"  {w:30s} A0 {a[0]:+.3f}/{a[1]:+.2f}  ->  combo {b[0]:+.3f}/{b[1]:+.2f}")
