"""实盘席位种子核: bundle leg_returns(king 疑似样本内) vs 回放 OOS 腿收益(canonpred 的 leg_*) — 同一 msharpe 规则(LOOK 900, LEGS 101)在各锚给出的 w3_king 差。"""
import numpy as np, time
PD="probe_artifacts"; z=np.load(f"{PD}/w10_canonpred_s42.npz",allow_pickle=True); cols=[str(c) for c in z["cols"]]; rec=z["d30_n2_c42_rec"]
ts=rec[:,cols.index("ts")].astype(np.int64); g=lambda k: rec[:,cols.index(k)].astype(float); LK,LR,LF=g("leg_king"),g("leg_rev24"),g("leg_fund")
B=np.load(f"{PD}/bundle_leg_returns.npz",allow_pickle=True); bts=B["ts"].astype(np.int64); bk,br,bf=B["king"],B["rev24"],B["fund"]
def w3(k,r,f):
    shp=np.array([k.mean()/(k.std()+1e-9), r.mean()/(r.std()+1e-9), f.mean()/(f.std()+1e-9)]); shp=np.maximum(shp,0); w=shp/shp.sum() if shp.sum()>0 else np.array([1/3]*3)
    m=np.array([1,0,1.0]); w=w*m; return w/w.sum() if w.sum()>0 else w
common=sorted(set(ts.tolist())&set(bts.tolist())); print(f"共同锚 {len(common)} ({time.strftime('%Y-%m-%d',time.gmtime(common[0]))}→{time.strftime('%Y-%m-%d',time.gmtime(common[-1]))})")
mi={int(t):i for i,t in enumerate(ts)}; bi={int(t):i for i,t in enumerate(bts)}
print("锚 | 回放 OOS 腿 900 窗 w3_king | bundle 种子 900 窗 w3_king | king 腿 900 窗均: OOS / bundle | fund 腿: OOS / bundle")
for T in [common[-1], common[-600], common[-1200], common[-2400], common[-3600]]:
    i=mi[T]; j=bi[T]
    if i<900 or j<900: continue
    wo=w3(LK[i-900:i],LR[i-900:i],LF[i-900:i]); wb=w3(bk[j-900:j],br[j-900:j],bf[j-900:j])
    print(f"{time.strftime('%Y-%m-%d',time.gmtime(T))} | {wo[0]:.3f} | {wb[0]:.3f} | {LK[i-900:i].mean():+.2f} / {bk[j-900:j].mean():+.2f} | {LF[i-900:i].mean():+.2f} / {bf[j-900:j].mean():+.2f}")
# 同锚 fund 腿逐位一致性(应接近: 无模型)
c=[(mi[T],bi[T]) for T in common]; a=np.array([LF[x] for x,_ in c]); b=np.array([bf[y] for _,y in c]); print(f"fund 腿 回放 vs bundle: corr {np.corrcoef(a,b)[0,1]:.3f} 均 {a.mean():+.2f}/{b.mean():+.2f} | king 腿: corr {np.corrcoef(np.array([LK[x] for x,_ in c]),np.array([bk[y] for _,y in c]))[0,1]:.3f}")
print("SEED_GAP_DONE")
