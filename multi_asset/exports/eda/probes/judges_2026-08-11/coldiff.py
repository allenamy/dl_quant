"""逐列判别: 自建 32ch(子采样) vs 生产 panel_0731(本机原件)。
每列报 corr + 分位数比 —— corr 高但尺度错也会伤 LayerNorm 前的投影, 两个都看。
预写判读: corr<0.99 = 构造差异列; 全列 >0.999 ⇒ 差距归训练环境/种子。"""
import numpy as np, os
S=np.load(os.path.expanduser("~/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad/rb32_sample.npz"),allow_pickle=True)
P=np.load(os.path.expanduser("~/lob_raw/panel_0731.npz"),allow_pickle=True)
rows=S["rows"]; A=S["CH"]                  # (r,140,32) 自建
B=P["CH"][rows]                            # 生产同行
names=[str(x) for x in S["ch_names"]]
pn=[str(x) for x in P["ch_names"]]
assert names==pn, "通道名不一致"
print(f"对照 {A.shape[0]} 行 × 140 币 × 32 通道\n")
print(f"{'通道':16s} {'corr':>8s} {'我sd':>10s} {'产sd':>10s} {'sd比':>7s}  判")
bad=[]
for k,nm in enumerate(names):
    a,b=A[:,:,k].ravel(),B[:,:,k].ravel()
    m=np.isfinite(a)&np.isfinite(b)&((a!=0)|(b!=0))
    if m.sum()<500: print(f"{nm:16s}  样本不足"); continue
    c=float(np.corrcoef(a[m],b[m])[0,1])
    sa,sb=a[m].std(),b[m].std()
    flag="" if c>0.999 else ("★ 构造差异" if c<0.99 else "≈")
    if c<0.999: bad.append((nm,c))
    print(f"{nm:16s} {c:8.4f} {sa:10.4g} {sb:10.4g} {sa/max(sb,1e-12):7.2f}  {flag}")
print(f"\n构造差异列: {bad if bad else '无 ⇒ 差距归训练环境/种子分布'}")
