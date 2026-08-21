'''和解实验: 早先持仓 NULL是现象为空, 还是【仪器】为空?

早版每小时只取一个快照(asof <=t-5min) ⇒ 小时内离散度/斜率结构性不可见。
本版保留 mean/std/slope。若把本版【削回只剩 mean】就退化到早版的信息量,
则早先的 NULL 是仪器的 NULL, 不是现象的 NULL —— 这是可证伪的, 不是辩解。

子集: mean(6) / std(6) / slope(6) / chg(3) / 全部(21)
同一套走前装置, 同一批锚点, 只换输入列。
'''
import numpy as np, datetime as dt
P=np.load('/workspace/data/panel_targets.npz',allow_pickle=True)
M=np.load('/workspace/data/metrics_hourly.npz',allow_pickle=True)
X=M['X']; FEAT=[str(f) for f in M['feats']]
Y4,MEM,TS=P['Y4'],P['MEMBER110'],np.asarray(P['ts']).astype(np.int64)
T,N=Y4.shape
YEAR=np.array([dt.datetime.fromtimestamp(int(t)/1000,dt.timezone.utc).year for t in TS])
def zr(v):
    m=np.isfinite(v); o=np.full(len(v),np.nan)
    if m.sum()<20: return o
    r=np.argsort(np.argsort(v[m])).astype(float)
    o[m]=(r-r.mean())/(r.std()+1e-12); return o
rows=np.array([i for i in range(24,T-8) if i%4==0])
SUBS={'mean 只(≈早版信息量)':[k for k,f in enumerate(FEAT) if f.endswith('_mean')],
      'std 只(早版结构性缺失)':[k for k,f in enumerate(FEAT) if f.endswith('_std')],
      'slope 只':[k for k,f in enumerate(FEAT) if f.endswith('_slope')],
      'chg 只':[k for k,f in enumerate(FEAT) if 'chg' in f],
      '全部 21':list(range(len(FEAT)))}
def run(cols):
    ics=[]
    for y in (2024,2025,2026):
        tr=rows[YEAR[rows]<y]; te=rows[YEAR[rows]==y]
        if len(tr)<500 or len(te)<100: continue
        def stack(idxs):
            XS,YS=[],[]
            for i in idxs:
                m=MEM[i]&np.isfinite(Y4[i])&np.isfinite(X[i][:,cols]).all(axis=1)
                if m.sum()<25: continue
                a=np.column_stack([zr(np.where(m,X[i,:,k],np.nan)) for k in cols])[m]
                XS.append(a); YS.append(zr(np.where(m,Y4[i],np.nan))[m])
            return (np.vstack(XS),np.concatenate(YS)) if XS else (None,None)
        Xtr,ytr=stack(tr)
        if Xtr is None: continue
        mu,sd=Xtr.mean(0),Xtr.std(0)+1e-9
        A=(Xtr-mu)/sd
        w=np.linalg.solve(A.T@A+200*np.eye(A.shape[1]),A.T@ytr)
        per=[]
        for i in te:
            m=MEM[i]&np.isfinite(Y4[i])&np.isfinite(X[i][:,cols]).all(axis=1)
            if m.sum()<25: continue
            a=np.column_stack([zr(np.where(m,X[i,:,k],np.nan)) for k in cols])[m]
            p=zr(((a-mu)/sd)@w); t_=zr(np.where(m,Y4[i],np.nan))[m]
            ok=np.isfinite(p)&np.isfinite(t_)
            if ok.sum()>=20: per.append(float((p[ok]*t_[ok]).mean()))
        if per: ics.append(np.mean(per))
    return ics
print(f"{'子集':>26s} {'2024':>9s} {'2025':>9s} {'2026':>9s} {'均值':>9s}")
for nm,cols in SUBS.items():
    ics=run(cols)
    print(f'{nm:>26s} '+' '.join(f'{v:>+9.4f}' for v in ics)+f' {np.mean(ics):>+9.4f}')
