import numpy as np, json, calendar, time
HOLE=set(json.load(open("/tmp/hole.json")))
z=np.load("/workspace/review_scratch/allweather_trackB/replay/dev_alt/probe_artifacts/w10_ablation_series_G_mE1cX7_R0_spl42.npz",allow_pickle=True)
syms=[str(s) for s in z["symbols"]]; W=z["d30_n2_c42_W"]; R=z["d30_n2_c42_rec"]
ts=R[:,0].astype(np.int64); gt=R[:,5]
idx={s:i for i,s in enumerate(syms)}
inpanel=[s for s in HOLE if s in idx]
print(f"回放面板 {len(syms)} 名 | 77 洞内币在面板里的: {len(inpanel)}")
if not inpanel: print("  ⇒ 洞内币不在回放面板 ⇒ 对本回放亦零暴露"); raise SystemExit
cols=[idx[s] for s in inpanel]
Wh=np.abs(W[:,cols]).sum(1)
T1=calendar.timegm((2026,8,11,0,0,0)); T2=calendar.timegm((2026,8,30,20,0,0))
m=(ts>=T1)&(ts<=T2)
frac=np.where(gt>0, Wh/np.maximum(gt,1e-12), 0.0)
print(f"\nAug11-30 窗({int(m.sum())} 锚):")
print(f"  洞内币在回放书里的 gross 占比: 均 {frac[m].mean()*100:.4f}%  max {frac[m].max()*100:.4f}%")
print(f"  非零锚数: {int((Wh[m]>1e-9).sum())}/{int(m.sum())}")
allm=ts>0
print(f"全样本: 均 {frac[allm].mean()*100:.4f}% | 非零锚 {int((Wh>1e-9).sum())}/{len(ts)}")
nz=[(s,float(np.abs(W[:,idx[s]]).sum())) for s in inpanel]
nz=[x for x in nz if x[1]>0]
print(f"\n有过非零权重的洞内币: {len(nz)}/{len(inpanel)}")
for s,v in sorted(nz,key=lambda x:-x[1])[:10]: print(f"   {s:16s} Σ|w| {v:.2f}")
