"""回答"为什么离线 Q4 只是小降, 而实盘坏窗 IC 直接为负"。
关键: 二者不是同一个对象。离线 Q4 = 最坏五分位【约 8000 个锚的平均】;
实盘坏窗 = 连续 ~30 个锚, 且是【因为它坏才被指认】(在结果上选择)。
正确的离线类比不是"Q4 的均值", 而是【滚动 30 锚窗均值的分布下尾】。
"""
import numpy as np, json, glob, datetime as dt
PAN="/workspace/data/wide_dl_pm32_hz.npz"
d=np.load(PAN,allow_pickle=True); MEM=d["MEMBER110"]; ts=d["ts"].astype(np.int64)
YR=d["YR4"]; CL=d["CL4"]
def zr(v):
    m=np.isfinite(v); o=np.full(len(v),np.nan)
    if m.sum()<20: return o
    r=np.argsort(np.argsort(v[m])).astype(float); o[m]=(r-r.mean())/(r.std()+1e-12); return o
def anchor_ic(tag):
    R,I=[],[]
    for f in sorted(glob.glob(f"/workspace/exports_train/{tag}/fold_*_head_scores.npz")):
        z=np.load(f); sc=z["scores"]; te=z["te_rows"]; ens=sc[te].mean(2)
        for j,i in enumerate(te):
            m=MEM[i]&CL[i]&np.isfinite(YR[i])
            if m.sum()<25: continue
            t_=zr(np.where(m,YR[i],np.nan))[m]; p=zr(np.where(m,ens[j],np.nan))[m]
            g=np.isfinite(t_)&np.isfinite(p)
            if g.sum()>=20: R.append(i); I.append(float((p[g]*t_[g]).mean()))
    o=np.argsort(R); return np.array(R)[o], np.array(I)[o]
print("%-22s %6s %8s | %8s %8s %8s | %8s %8s"%("臂","n锚","全期IC","滚30窗<0占比","5%分位","最小","连负最长","最差月"))
for tag in ("rb32_lam0_yr4_s42","rb32_lam0_yr4_s2027","rb32_lam0_yr4_s3037"):
    R,I=anchor_ic(tag)
    if len(I)<200: continue
    W=30
    roll=np.convolve(I,np.ones(W)/W,mode="valid")
    neg=(roll<0).mean()
    # 最长连负锚
    best=cur=0
    for x in I:
        cur=cur+1 if x<0 else 0; best=max(best,cur)
    mo={}
    for i,ic in zip(R,I):
        k=dt.datetime.fromtimestamp(int(ts[i])/1000,dt.timezone.utc).strftime("%Y-%m")
        mo.setdefault(k,[]).append(ic)
    mm={k:np.mean(v) for k,v in mo.items() if len(v)>=20}
    wm=min(mm,key=mm.get)
    print("%-22s %6d %8.4f | %12.3f %8.4f %8.4f | %8d %8s %.4f"%(
        tag,len(I),np.mean(I),neg,np.percentile(roll,5),roll.min(),best,wm,mm[wm]))
print()
print("参照: 实盘 08-01→08-06 约 30 个锚(4h 锚 ⇒ 6 天 = 36 锚)")
