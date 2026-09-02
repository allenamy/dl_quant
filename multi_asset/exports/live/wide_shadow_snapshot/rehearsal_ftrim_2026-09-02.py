import json, numpy as np, time
WS='/Users/haosiyu/wide_shadow'; HERE=f'{WS}/fea171'
a=json.load(open(f'{WS}/state/aux.json')); pr=a['prev_rec']; A=int(pr['anchor_ts']); pm=np.array(pr['members'],np.int64)
syms=[str(s) for s in np.load(f'{HERE}/xfer_ref.npz',allow_pickle=True)['symbols']]; NW=len(syms); col={s:j for j,s in enumerate(syms)}
legz={k:np.array(v,np.float64) for k,v in pr['legz'].items()}
sm=np.zeros(NW); sm[np.array(pr['sm_idx'],np.int64)]=np.array(pr['sm'],np.float64)
# w3: 最近 signal 事件
import glob
w3=None
for f in sorted(glob.glob(f'{WS}/shadow_log*.jsonl')):
    for l in open(f):
        if '"e": "signal"' in l and f'"anchor_ts": {A}' in l: w3=json.loads(l)['w3']
w3=np.array(w3); w3m=np.array([w3[0],0.0,w3[2]]); w3m=w3m/w3m.sum()
z_kc=w3m[0]*np.nan_to_num(legz['king'])+w3m[2]*np.nan_to_num(legz['fund'])
rn8=np.full(NW,np.nan)
for s_,rows_ in a['ledger_tail'].items():
    j=col.get(s_)
    if j is not None and rows_:
        r=rows_[-1]; iv=float(r[2]) if len(r)>2 and r[2] else 8.0; rn8[j]=float(r[1])*(8.0/(iv if iv>0 else 8.0))
rn8m=rn8[pm]; band=(z_kc<0)&np.isfinite(rn8m)&(rn8m<=-0.0010)
print(f"anchor {time.strftime('%m-%d %H:%MZ',time.gmtime(A))} members {len(pm)} w3m {np.round(w3m,4).tolist()} 费率覆盖 {np.isfinite(rn8m).mean():.3f}")
print(f"kc 频带集合: {band.sum()} 名 (z<0 名共 {(z_kc<0).sum()}, rn8≤−10bp 名共 {int((np.isfinite(rn8m)&(rn8m<=-0.0010)).sum())})")
g=np.abs(sm).sum(); idx=pm[band]
held=[(syms[j], round(rn8[j]*1e4,1), round(sm[j]/g*100,3)) for j in idx]
held.sort(key=lambda x:x[1])
print("名 / rn8(bp/8h) / 当前权重(%gross):", held[:40])
print(f"频带名当前 gross 占比 {sum(abs(sm[j]) for j in idx)/g*100:.2f}% ; 其中当前为空头持仓的 {sum(1 for j in idx if sm[j]<0)} 名, 未持仓 {sum(1 for j in idx if abs(sm[j])<1e-12)} 名")
# 深负分布(全部成员)
fin=rn8m[np.isfinite(rn8m)]; print("成员费率分布(bp/8h): ≤−30:", int((fin<=-0.003).sum()), " (−30,−10]:", int(((fin>-0.003)&(fin<=-0.001)).sum()), " (−10,0):", int(((fin>-0.001)&(fin<0)).sum()), " ≥0:", int((fin>=0).sum()))
