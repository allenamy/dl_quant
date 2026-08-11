"""多资产 · 5 年 · n≈10950 锚: "regime 条件化"存废的规模化检验。
动机(用户 2026-08-06): "regime 失败 4 次"全部测自【单资产 BTC】; 多资产从未在规模上测过。
判读先写死:
  某条件量为【真】 ⇔ 四分位 top−bottom 的模型 IC 差 |t| ≥ 3 且分位均值单调(容 1 处倒挂)。
  全部不过 ⇒ 单资产先验在多资产【坐实】(经验升级为本域实测);
  任一过   ⇒ 先验不迁移, 打开训练内条件化轨(E0 特征优先)。
条件量(全部严格因果, 用 ≤t−1 的信息):
  C1 风格 regime: 7d 反转因子 trailing 42 锚实现 IC 均值
  C2 alpha 动量:  模型自身 trailing 42 锚实现 IC 均值(T1 在 n=77 的 null 的规模化复检)
  C3 截面离散度:  |Y4| 截面均值的 trailing 42 锚均值
  C4 延续指数:    相邻 4h 收益截面相关的 trailing 42 锚均值
装置: ctrl 臂(现范式模型)五折 OOS 拼接; 全样本四分位边界(存在性检验口径, 已知二阶偏差, 如实登记)。"""
import numpy as np, glob, json
BASE="/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
P=np.load(f"{BASE}/wide_dl_full_corrfund_causal_0731.npz",allow_pickle=True)
Y4=P["Y4"]; MEM=P["MEMBER110"]; CL4=P["CL4"]
def zr(x):
    m=np.isfinite(x); out=np.full(len(x),np.nan)
    if m.sum()<3: return out
    r=np.argsort(np.argsort(x[m])).astype(float); out[m]=(r-r.mean())/(r.std()+1e-12); return out
def ic(a,b):
    m=np.isfinite(a)&np.isfinite(b)
    return float(np.nanmean(zr(np.where(m,a,np.nan))*zr(np.where(m,b,np.nan)))) if m.sum()>=10 else np.nan
rows_all=[]; ens_all=[]
for f in sorted(glob.glob(f"{BASE}/train/wideA_psmooth_ctrl/fold_*_head_scores.npz")):
    z=np.load(f,allow_pickle=True); S=z["scores"]; rows=z["te_rows"]
    for r in rows:
        mem=MEM[r]; hz=[]
        for h in range(S.shape[2]):
            v=np.where(mem,S[r,:,h],np.nan); s=np.nanstd(v)
            hz.append((v-np.nanmean(v))/s if s>0 else v*np.nan)
        rows_all.append(int(r)); ens_all.append(np.nanmean(hz,axis=0))
o=np.argsort(rows_all); rows=np.array(rows_all)[o]; ens=np.array(ens_all)[o]
n=len(rows); print(f"n_anchors={n}")
model_ic=np.full(n,np.nan); style_ic=np.full(n,np.nan); disp=np.full(n,np.nan); cont=np.full(n,np.nan)
style_prev=None; y_prev=None
for k,r in enumerate(rows):
    mask=MEM[r]&CL4[r]
    y=np.where(mask&np.isfinite(Y4[r]),Y4[r],np.nan)
    model_ic[k]=ic(ens[k],y)
    # trailing 168h 收益 = 过去 42 格 4h 收益复合(用 Y4 在 r-4k 行, 严格 ≤t)
    tr=np.zeros(Y4.shape[1]); okc=np.ones(Y4.shape[1],bool)
    for j in range(1,43):
        rr=r-4*j
        if rr<0: okc[:]=False; break
        v=Y4[rr]; okc&=np.isfinite(v); tr=tr+np.log1p(np.where(np.isfinite(v),np.clip(v,-0.5,0.5),0.0))
    style=np.where(mask&okc,-tr,np.nan)
    style_ic[k]=ic(style,y)
    disp[k]=float(np.nanstd(np.where(mask,Y4[r-4] if r>=4 else np.nan,np.nan)))  # 上一格实现离散度
    if y_prev is not None:
        cont[k]=ic(y_prev,np.where(mask,Y4[r-4],np.nan)) if r>=4 else np.nan
    y_prev=np.where(mask,Y4[r-4],np.nan) if r>=4 else None
def trail(x,k=42):
    out=np.full(len(x),np.nan)
    for i in range(k,len(x)): out[i]=np.nanmean(x[i-k:i])
    return out
conds={"C1_风格regime":trail(style_ic),"C2_alpha动量":trail(model_ic),
       "C3_离散度":trail(disp),"C4_延续指数":trail(cont)}
res={}
for nm,c in conds.items():
    m=np.isfinite(c)&np.isfinite(model_ic)
    q=np.nanquantile(c[m],[0.25,0.5,0.75])
    b=np.digitize(c[m],q); mi=model_ic[m]
    means=[float(np.nanmean(mi[b==i])) for i in range(4)]
    ns=[int((b==i).sum()) for i in range(4)]
    d=mi[b==3]; a=mi[b==0]
    t=float((d.mean()-a.mean())/np.sqrt(d.var(ddof=1)/len(d)+a.var(ddof=1)/len(a)))
    mono=all(means[i+1]>=means[i]-0.005 for i in range(3)) or all(means[i+1]<=means[i]+0.005 for i in range(3))
    res[nm]={"q_means":[round(x,4) for x in means],"n":ns,"t_top_bottom":round(t,2),"monotone":bool(mono)}
    print(f"{nm}: 分位均值={[round(x,4) for x in means]}  t={t:+.2f}  单调={mono}")
verdict=[nm for nm,r in res.items() if abs(r["t_top_bottom"])>=3 and r["monotone"]]
print(f"\n判决(|t|>=3 且单调): 通过 = {verdict or '无 — 单资产先验在多资产规模上坐实'}")
json.dump(res,open("/tmp/regime_scale.json","w"),indent=1)
