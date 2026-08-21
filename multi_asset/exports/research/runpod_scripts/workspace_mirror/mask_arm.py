"""54ch = 53ch + metrics 存在掩码通道。E10 治疗② 的单变量实现。
设计五件套(简式, 机制自明):
 机制: 模型无法区分"信号为零"与"无数据"——2023-06 前 metrics 全零被当成真值学习;
       掩码把缺失变成可观测量, 让模型学会"这段别信 metrics 通道"。
 法证: 填充率 0.507→重建后应 ~0.77; 掩码=metrics_hourly X 第0列 isfinite。
 备选弃选: 逐列掩码(21列)——族内缺失同构, 1 列够; 纪元硬切——不可服务(实盘无"纪元"概念)。
 构造: mask=1.0 当该(t,n)的 metrics 有数, else 0; 因果(存在性在 t 时刻已知)。
 判据(预写): 全史折 Δ(54ch−rb32) 相比 −0.0143 至少收窄一半(→ >−0.007), 且纯有数折不劣化。"""
import numpy as np
R=np.load("/workspace/data/wide_dl_53ch.npz",allow_pickle=True)
M=np.load("/workspace/data/metrics_hourly.npz",allow_pickle=True)
mask=np.isfinite(M["X"][:,:,0]).astype(np.float32)[:,:,None]
CH=np.concatenate([R["CH"],mask],axis=2)
names=[str(x) for x in R["ch_names"]]+["metrics_present"]
d={k:R[k] for k in ("ts","symbols","MEMBER110","Y1","YR1","CL1","Y4","YR4","CL4","Y24","YR24","CL24","baseline_cols")}
d["CH"]=CH; d["ch_names"]=np.array(names,object)
np.savez("/workspace/data/wide_dl_54ch.npz",**d)
print(f"54ch 面板: {CH.shape}  掩码覆盖率 {mask.mean():.3f}")
