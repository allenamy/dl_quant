import numpy as np, importlib.util, calendar, json
spec=importlib.util.spec_from_file_location("j","/workspace/uplift_2026-09-11/judgeD.py"); j=importlib.util.module_from_spec(spec); spec.loader.exec_module(j)
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
A0="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz"
A0b="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s2027.npz"
t0,g0,R0=j.load(A0,"d30_n2_c42_rec"); t0b,g0b,_=j.load(A0b,"d30_n2_c42_rec")
def get(tg): return j.load(f"/workspace/uplift_2026-09-11/trackD_v4/{tg}.npz","rec")
tags=["SL_f_amihud_24h__p","SL_D_SURP__m","SL_f_asz_24h__m","SL_LOBDEPTH__m"]
G={}
for tg in tags:
    ts,g,R=get(tg); idx=np.searchsorted(ts,t0); ok=(idx<len(ts)); G[tg]=np.where(ts[np.clip(idx,0,len(ts)-1)]==t0,g[np.clip(idx,0,len(ts)-1)],np.nan)
WIN={"full 2022->26-08-10":(T(2022,1,1),T(2026,8,10,20)+1),
     "frozen 2025-03->26-08-10":(T(2025,3,1),T(2026,8,10,20)+1),
     "EXT live-bleed 26-08-11->08-31":(T(2026,8,11),T(2026,8,31,20)+1),
     "2022":(T(2022,1,1),T(2023,1,1)),"2023":(T(2023,1,1),T(2024,1,1)),"2024":(T(2024,1,1),T(2025,1,1)),
     "2025":(T(2025,1,1),T(2026,1,1)),"2026->08-10":(T(2026,1,1),T(2026,8,10,20)+1)}
def st(v):
    v=v[np.isfinite(v)]
    if len(v)<3: return None
    c=np.concatenate([[0.0],np.cumsum(v)]); dd=float(np.max(np.maximum.accumulate(c)-c))
    return v.mean(), float(v.mean()/v.std(ddof=1)*np.sqrt(2190)), dd, len(v)
COMB={"A0 alone":g0,
      "A0 s2027 alone":None,
      "1/2 A0 + 1/4 amihud + 1/4 SURP":0.5*g0+0.25*G["SL_f_amihud_24h__p"]+0.25*G["SL_D_SURP__m"],
      "1/3 A0 + 1/3 amihud + 1/3 SURP (a-priori equal)":(g0+G["SL_f_amihud_24h__p"]+G["SL_D_SURP__m"])/3.0,
      "1/2 A0 + 1/4 asz + 1/4 SURP (family swap)":0.5*g0+0.25*G["SL_f_asz_24h__m"]+0.25*G["SL_D_SURP__m"],
      "1/2 A0 + 1/4 LOBDEPTH + 1/4 SURP (family swap)":0.5*g0+0.25*G["SL_LOBDEPTH__m"]+0.25*G["SL_D_SURP__m"]}
print(f"{'window':34s} "+" ".join(f"{k[:30]:>32s}" for k in COMB if k!="A0 s2027 alone"))
for w,(lo,hi) in WIN.items():
    m=(t0>=lo)&(t0<hi); row=[]
    for k,v in COMB.items():
        if k=="A0 s2027 alone": continue
        s=st(v[m]); row.append(f"{s[0]:+8.3f}/{s[1]:+6.2f}/dd{s[2]:6.0f}" if s else " "*30)
    print(f"{w:34s} "+" ".join(f"{r:>32s}" for r in row))
# s2027 robustness for the same combination
mb={}
for w,(lo,hi) in WIN.items():
    m=(t0b>=lo)&(t0b<hi)
    idx=np.searchsorted(t0,t0b); gg={k:np.where(t0[np.clip(idx,0,len(t0)-1)]==t0b, G[k][np.clip(idx,0,len(t0)-1)], np.nan) for k in G}
    v=0.5*g0b+0.25*gg["SL_f_amihud_24h__p"]+0.25*gg["SL_D_SURP__m"]
    s=st(v[m]); s0=st(g0b[m])
    if s: mb[w]=f"A0(s2027) {s0[0]:+.3f}/{s0[1]:+.2f}  ->  combo {s[0]:+.3f}/{s[1]:+.2f}"
print("\n--- second-seed A0 (s2027) robustness, same sleeves ---")
for k,v in mb.items(): print(f"  {k:34s} {v}")
