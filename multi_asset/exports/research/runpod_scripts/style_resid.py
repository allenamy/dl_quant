"""★ 风格/残差分解仪器 —— 把实盘 08-06 归因用的镜头搬到离线, 逐臂逐视界打分。
实盘实测(STATE §0-octies): 在役分数 = 风格投影 + 正交残差; 风格 +0.085 活着,
残差全期 +0.091 但最近 6 锚 −0.008 ⇒ 亏的是【模型相对风格的增值】。
本仪器在【离线】重现这个镜头, 用来回答: y12 的 +0.0060 优势, 长在风格里还是长在残差里?
装置: 逐锚横截面, 把模型分数对 8 个 baseline 风格因子做最小二乘投影,
      分解 score = style_hat + resid; 分别报三者对 YR 的 rank-IC, 并按冻结健康分层拆开。
口径声明: 与 regime 记分卡同尺(头均 ensemble, member&CL 掩码, YR 目标)。
"""
import numpy as np, json, glob, os, sys
PAN="/workspace/data/wide_dl_pm32_hz.npz"
d=np.load(PAN, allow_pickle=True)
MEM=d["MEMBER110"]; CH=d["CH"]; nm=[str(x) for x in d["ch_names"]]
BC=[str(x) for x in d["baseline_cols"]]; BI=[nm.index(b) for b in BC]
YR={h:d[f"YR{h}"] for h in (4,8,12,24)}; CL={h:d[f"CL{h}"] for h in (4,8,12,24)}
S=np.load("/workspace/data/regime_strata.npz"); QUINT=S["quint"]
def zr(v):
    m=np.isfinite(v); o=np.full(len(v),np.nan)
    if m.sum()<20: return o
    r=np.argsort(np.argsort(v[m])).astype(float); o[m]=(r-r.mean())/(r.std()+1e-12); return o
def card(tag):
    fs=sorted(glob.glob(f"/workspace/exports_train/{tag}/fold_*_head_scores.npz"))
    if not fs: return None
    jf=f"/workspace/exports_train/wide_harness_{tag}.json"
    hz=json.load(open(jf))["target_horizon"] if os.path.exists(jf) else 4
    Y,C=YR[hz],CL[hz]
    rows=[]; tot=[]; sty=[]; res=[]; frac=[]
    for f in fs:
        z=np.load(f); sc=z["scores"]; te=z["te_rows"]
        # ★ 2026-08-09 修: 逐头先横截面 z-rank 再平均 —— 与 harness 的 ensemble 口径一致。
        # 原实现直接对【原始分数】取头均, 尺度最大的头会主导, 在头反号时给出虚高读数
        # (ls_icv05: 原口径 0.0431 vs harness 0.0073)。同号时两者无差, 异号时差 6 倍。
        for j,i in enumerate(te):
            m=MEM[i]&C[i]&np.isfinite(Y[i])
            if m.sum()<25: continue
            t_=zr(np.where(m,Y[i],np.nan))[m]
            _hs=np.column_stack([zr(np.where(m,sc[i,:,_k],np.nan)) for _k in range(sc.shape[2])])
            s_=zr(np.nanmean(_hs,axis=1))[m]
            X=np.column_stack([zr(np.where(m,CH[i,:,k],np.nan))[m] for k in BI])
            g=np.isfinite(t_)&np.isfinite(s_)&np.all(np.isfinite(X),axis=1)
            if g.sum()<20: continue
            t2,s2,X2=t_[g],s_[g],X[g]
            A=np.column_stack([np.ones(len(X2)),X2])
            beta,*_=np.linalg.lstsq(A,s2,rcond=None)
            sh=A@beta; rs=s2-sh
            ss=s2.std()+1e-12
            rows.append(i); tot.append(float((s2*t2).mean()/ (s2.std()*t2.std()+1e-12) * s2.std()*t2.std()/(s2.std()*t2.std()+1e-12)) if False else float(np.corrcoef(s2,t2)[0,1]))
            sty.append(float(np.corrcoef(sh,t2)[0,1]) if sh.std()>1e-9 else np.nan)
            res.append(float(np.corrcoef(rs,t2)[0,1]) if rs.std()>1e-9 else np.nan)
            frac.append(float(rs.std()/ss))
    R=np.array(rows); T=np.array(tot); St=np.array(sty); Rs=np.array(res); F=np.array(frac)
    q=QUINT[R]
    out={"tag":tag,"hz":hz,"n":len(R),"total":float(np.nanmean(T)),
         "style":float(np.nanmean(St)),"resid":float(np.nanmean(Rs)),
         "resid_share_of_var":float(np.nanmean(F**2))}
    for k in (0,4):
        sel=q==k
        out[f"total_Q{k}"]=float(np.nanmean(T[sel])) if sel.sum() else np.nan
        out[f"style_Q{k}"]=float(np.nanmean(St[sel])) if sel.sum() else np.nan
        out[f"resid_Q{k}"]=float(np.nanmean(Rs[sel])) if sel.sum() else np.nan
    return out
tags=sys.argv[1:]
print("%-24s %3s %6s | %7s %7s %7s | %6s | %7s %7s | %7s %7s"%(
  "臂","hz","n","总分IC","风格IC","残差IC","残差方差占比","总Q0","总Q4","残Q0","残Q4"),flush=True)
res=[]
for t in tags:
    try: r=card(t)
    except Exception as e: print("%-24s ERR %s"%(t,e),flush=True); continue
    if not r: continue
    res.append(r)
    print("%-24s %3d %6d | %7.4f %7.4f %7.4f | %6.3f | %7.4f %7.4f | %7.4f %7.4f"%(
      r["tag"],r["hz"],r["n"],r["total"],r["style"],r["resid"],r["resid_share_of_var"],
      r["total_Q0"],r["total_Q4"],r["resid_Q0"],r["resid_Q4"]),flush=True)
json.dump(res,open("/workspace/data/style_resid_cards.json","w"),indent=1)
print("STYLE_RESID_DONE",flush=True)
