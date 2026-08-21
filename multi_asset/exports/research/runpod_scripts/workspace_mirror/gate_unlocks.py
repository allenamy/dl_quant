"""#64 解锁族 G1/G2/增量门。两个口径(覆盖率仅 25%, 必须分开报):
 (A) 仅覆盖币宇宙 —— "在有解锁日程的币里, 解锁能不能排序?"(族的机制是否真)
 (B) 全宇宙零填充 —— "接进现有书能不能加分?"(工程价值)
G1 前视签名: 每列 |IC vs 未来 24h| < 0.15 且 对过去相关 ≥ 对未来(时移不对称)
G2 走前: 2024/2025/2026 三折 Ridge, 均值 |IC| > 0.005 且无反号
增量: 32ch vs 32ch+6, Δ ≥ +0.003
"""
import numpy as np, datetime as dt
P=np.load("/workspace/data/wide_dl_pm32_hz.npz",allow_pickle=True)
U=np.load("/workspace/data/unlocks_hourly.npz",allow_pickle=True)
CH=P["CH"]; MEM=P["MEMBER110"]; Y4=P["Y4"]; CL4=P["CL4"]; ts=P["ts"].astype(np.int64)
X=U["X"]; F=[str(x) for x in U["feats"]]
YEAR=np.array([dt.datetime.fromtimestamp(int(t)/1000,dt.timezone.utc).year for t in ts])
T,N=Y4.shape
COV=np.isfinite(X).all(2)
def zr(v):
    m=np.isfinite(v); o=np.full(len(v),np.nan)
    if m.sum()<8: return o
    r=np.argsort(np.argsort(v[m])).astype(float); o[m]=(r-r.mean())/(r.std()+1e-12); return o
rows=np.array([i for i in range(24,T-30) if i%4==0])
print("== G1 前视签名(覆盖币宇宙) ==", flush=True)
for k,nm in enumerate(F):
    fu=[];pa=[]
    for i in rows[::6]:
        m=MEM[i]&COV[i]
        if m.sum()<12: continue
        a=zr(np.where(m,X[i,:,k],np.nan))
        for lag,acc in ((0,fu),(-24,pa)):
            j=i+ (0 if lag==0 else lag)
            if j<0 or j>=T: continue
            b=zr(np.where(m,Y4[j],np.nan))
            g=np.isfinite(a)&np.isfinite(b)
            if g.sum()>=10: acc.append(float((a[g]*b[g]).mean()))
    f_,p_=np.mean(fu) if fu else np.nan, np.mean(pa) if pa else np.nan
    print("  %-12s IC未来 %+.4f | IC过去 %+.4f  %s"%(nm,f_,p_,"★可疑" if abs(f_)>0.15 else ""), flush=True)
def ridge(use_unlock, cov_only):
    ics=[]
    for y in (2024,2025,2026):
        tr=rows[YEAR[rows]<y]; te=rows[YEAR[rows]==y]
        XS,YS=[],[]
        for i in tr[::2]:
            m=MEM[i]&CL4[i]&np.isfinite(Y4[i])
            if cov_only: m=m&COV[i]
            if m.sum()<(12 if cov_only else 25): continue
            c=[zr(np.where(m,CH[i,:,j],np.nan)) for j in range(32)]
            if use_unlock: c+=[zr(np.where(m&COV[i],X[i,:,j],np.nan)) for j in range(len(F))]
            XS.append(np.nan_to_num(np.column_stack(c)[m])); YS.append(zr(np.where(m,Y4[i],np.nan))[m])
        A=np.vstack(XS); b=np.concatenate(YS)
        mu,sd=A.mean(0),A.std(0)+1e-9
        w=np.linalg.solve(((A-mu)/sd).T@((A-mu)/sd)+200*np.eye(A.shape[1]),((A-mu)/sd).T@b)
        per=[]
        for i in te:
            m=MEM[i]&CL4[i]&np.isfinite(Y4[i])
            if cov_only: m=m&COV[i]
            if m.sum()<(12 if cov_only else 25): continue
            c=[zr(np.where(m,CH[i,:,j],np.nan)) for j in range(32)]
            if use_unlock: c+=[zr(np.where(m&COV[i],X[i,:,j],np.nan)) for j in range(len(F))]
            a=np.nan_to_num(np.column_stack(c)[m])
            p=zr((a-mu)/sd@w); t_=zr(np.where(m,Y4[i],np.nan))[m]
            g=np.isfinite(p)&np.isfinite(t_)
            if g.sum()>=10: per.append(float((p[g]*t_[g]).mean()))
        ics.append(float(np.mean(per)))
    return ics
print("\n== G2/增量 ==", flush=True)
for lbl,co in (("(A) 仅覆盖币宇宙",True),("(B) 全宇宙零填充",False)):
    b0=ridge(False,co); b1=ridge(True,co)
    print("  %s  32ch %s 均 %.4f"%(lbl,["%+.4f"%x for x in b0],np.mean(b0)), flush=True)
    print("  %s  +解锁 %s 均 %.4f  Δ %+.4f  %s"%(" "*len(lbl),["%+.4f"%x for x in b1],np.mean(b1),
          np.mean(b1)-np.mean(b0), "过门" if np.mean(b1)-np.mean(b0)>=0.003 else "不过门"), flush=True)
print("UNLOCK_GATE_DONE", flush=True)
