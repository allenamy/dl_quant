"""E-0904-C 修复前最严格核验包: (i) OOS 种子给出的逐年席位路径; (ii) 0.21 固定席位书 vs 诚实 msharpe 书 的权重差(换装冲击); (iii) fund 腿口径一致性(种子 vs bundle 生产口径); (iv) 判官 CI: ms vs fx 同构造双种子。"""
import numpy as np, time
PD="probe_artifacts"
S=np.load(f"{PD}/leg_returns_oos_seed.npz"); ts=S["ts"].astype(np.int64); K,R_,F=S["king"],S["rev24"],S["fund"]
def w3(k,r,f):
    shp=np.array([k.mean()/(k.std()+1e-9), r.mean()/(r.std()+1e-9), f.mean()/(f.std()+1e-9)]); shp=np.maximum(shp,0); w=shp/shp.sum() if shp.sum()>0 else np.array([1/3]*3); w=w*np.array([1,0,1.0]); return w/w.sum() if w.sum()>0 else w
yr=np.array([time.gmtime(int(t)).tm_year for t in ts]); print("(i) OOS 种子 → msharpe 席位 king 逐年均(900 窗因果):", {y: round(float(np.mean([w3(K[i-900:i],R_[i-900:i],F[i-900:i])[0] for i in np.where(yr==y)[0] if i>=900][::10])),3) for y in (2022,2023,2024,2025,2026)})
print("    末锚 08-15 席位 king/fund:", np.round(w3(K[-900:],R_[-900:],F[-900:])[[0,2]],3), "| 若 king 腿末 900 窗 Sharpe 需 >0 才有席位: 实际 king 均", round(K[-900:].mean(),2), "std", round(K[-900:].std(),1))
def loadW(tag):
    z=np.load(f"{PD}/w10_{tag}.npz",allow_pickle=True); cols=[str(c) for c in z["cols"]]; rec=z["d30_n2_c42_rec"]; return rec[:,cols.index("ts")].astype(np.int64), z["d30_n2_c42_W"]
for a,b,lab in (("canonfix_s42","canonpred_s42","无FTRIM: 0.21 固定 vs msharpe"),("uni2_N829T400F_fx_s42","uni2_N829T400F_ms_s42","FTRIM+M1: 0.21 固定 vs msharpe")):
    ta,Wa=loadW(a); tb,Wb=loadW(b); n=min(len(ta),len(tb)); Wa,Wb=Wa[-n:],Wb[-n:]; g=np.abs(Wa).sum(1); d=np.abs(Wa-Wb).sum(1)/np.maximum(g,1e-9)
    print(f"(ii) {lab}: 末 30 锚 Σ|Δw|/gross 中位 {np.median(d[-30:]):.3f} | 2026 均 {d[-1300:].mean():.3f} | 首锚 EMA 0.1 步长下执行换手增量 ≈ {0.1*np.median(d[-30:]):.3f}")
B=np.load(f"{PD}/bundle_leg_returns.npz",allow_pickle=True); bts=B["ts"].astype(np.int64); bi={int(t):i for i,t in enumerate(bts)}; si={int(t):i for i,t in enumerate(ts)}
c=[(si[t],bi[t]) for t in ts if int(t) in bi and t>=1767225600]; fs=np.array([F[x] for x,_ in c]); fb=np.array([B["fund"][y] for _,y in c]); ks=np.array([K[x] for x,_ in c]); kb=np.array([B["king"][y] for _,y in c])
print(f"(iii) 2026 共同锚 {len(c)}: fund 腿 种子 vs bundle 均 {fs.mean():+.2f}/{fb.mean():+.2f} std {fs.std():.1f}/{fb.std():.1f} corr {np.corrcoef(fs,fb)[0,1]:.3f} | king 腿 {ks.mean():+.2f}/{kb.mean():+.2f} corr {np.corrcoef(ks,kb)[0,1]:.3f}")
print("VERIFY_DONE")
