"""波动目标 sidecar(--target_npz 格式: 键 YR4K + KMASK + ts)。
目标 = 未来 24 小时实现波动的【横截面高斯秩】—— 尺度无关, 与 IC 口径一致。
用途: 给 W3(档位空间塔)一个 DL 参照点。已知 32ch 线性 Ridge 在该目标上到 0.7208,
     本臂回答"同一冠军架构在波动目标上能到多少", 是后续 book 结构臂的对照基准。
纪律: 标签用未来数据是合法的(它就是标签); 输入仍严格 <=t。
"""
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
P="/workspace/data/wide_dl_pm32_hz.npz"
d=np.load(P,allow_pickle=True)
Y1=d["Y1"]; ts=d["ts"]; MEM=d["MEMBER110"]; CL=d["CL4"]
T,N=Y1.shape
FV=np.full((T,N),np.nan,np.float32)
sw=sliding_window_view(Y1,24,axis=0)
with np.errstate(all="ignore"):
    for s in range(0,sw.shape[0],4096):
        v=np.nanstd(sw[s:s+4096],axis=-1); FV[s:s+v.shape[0]]=v
def zr_row(v):
    m=np.isfinite(v); o=np.full(len(v),np.nan,np.float32)
    if m.sum()<20: return o
    r=np.argsort(np.argsort(v[m])).astype(np.float64)
    o[m]=((r-r.mean())/(r.std()+1e-12)).astype(np.float32); return o
Y=np.full((T,N),np.nan,np.float32)
for i in range(T):
    if np.isfinite(FV[i]).sum()>=20: Y[i]=zr_row(np.where(MEM[i],FV[i],np.nan))
K=np.isfinite(Y)&MEM&CL
print("波动目标: 有效格 %.4f | 逐锚有效名中位 %d"%(K.mean(), int(np.median(K.sum(1)))),flush=True)
np.savez("/workspace/data/target_volrank.npz", YR4K=np.nan_to_num(Y), KMASK=K, ts=ts)
print("VOLT_BUILD_DONE",flush=True)
