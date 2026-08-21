'''把 metrics 21 通道装成 wide_dl 格式, 供现有 harness 直接吃 —— 不改 harness 一行。

★ 归一化选 xsec rank-z (逐时刻跨币): 它【只用 t 时刻的横截面】⇒ 天然因果, 且尺度无关
  (原始 oi ~2e7, 直接喂网络会炸)。这也正是 §Metric Discipline 的口径。
★ 通道值域: rank-z 后天然 ~N(0,1), 无需裁剪常数。
'''
import numpy as np
P=np.load('/workspace/data/panel_targets.npz',allow_pickle=True)
M=np.load('/workspace/data/metrics_hourly.npz',allow_pickle=True)
X=M['X'].astype(np.float32); FEAT=[str(f) for f in M['feats']]
MEM=P['MEMBER110']; T,N,C=X.shape
print(f'原始 {X.shape}  填充 {np.isfinite(X[:,:,0]).mean():.3f}')
out=np.full_like(X,np.nan)
for t in range(T):
    m=MEM[t]
    if m.sum()<20: continue
    for c in range(C):
        v=X[t,:,c]; f=m&np.isfinite(v)
        k=f.sum()
        if k<20: continue
        r=np.argsort(np.argsort(v[f])).astype(np.float32)
        out[t,f,c]=(r-r.mean())/(r.std()+1e-9)
np.nan_to_num(out,copy=False,nan=0.0)
print(f'xsec rank-z 完成  值域 [{out.min():.2f},{out.max():.2f}]  sd {out.std():.3f}')
d={'CH':out,'ch_names':np.array(FEAT,object),
   'baseline_cols':np.array([f for f in FEAT if f.endswith('_mean')],object)}
for k in ('ts','symbols','MEMBER110','Y1','YR1','CL1','Y4','YR4','CL4','Y24','YR24','CL24'):
    d[k]=P[k]
np.savez('/workspace/data/wide_dl_metrics21.npz',**d)
print('saved /workspace/data/wide_dl_metrics21.npz')
