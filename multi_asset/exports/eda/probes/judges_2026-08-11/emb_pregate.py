"""asset-id embedding 两道 pre-gate:
P1 逐币截距跨年稳定性: 32ch Ridge 残差的逐币年均 rank, 年际相关 ⇒ 身份是否携带持久 alpha
P2 簇持久性: 相关聚类(k=6)成员年际保持率 ⇒ "sector"概念的稳定度"""
import numpy as np, pandas as pd, datetime as dt
R = np.load("/workspace/data/wide_dl_prodmask32.npz", allow_pickle=True)
P = np.load("/workspace/data/panel_targets.npz", allow_pickle=True)
CH = R["CH"]; MEM = R["MEMBER110"]; Y4 = P["Y4"]
TS = np.asarray(P["ts"]).astype(np.int64)
T, N = Y4.shape
YEAR = np.array([dt.datetime.fromtimestamp(int(t)/1000, dt.timezone.utc).year for t in TS])
names = [str(x) for x in R["ch_names"]]
def zr(v):
    m = np.isfinite(v); o = np.full(len(v), np.nan)
    if m.sum() < 20: return o
    r = np.argsort(np.argsort(v[m])).astype(float)
    o[m] = (r - r.mean()) / (r.std() + 1e-12); return o
rows = np.array([i for i in range(24, T-8) if i % 4 == 0])
# P1: 逐年内, 用前一年拟合 ridge, 记逐币残差年均
resmean = {}
for y in (2022, 2023, 2024, 2025, 2026):
    tr = rows[YEAR[rows] < y]; te = rows[YEAR[rows] == y]
    if len(tr) < 400 or len(te) < 200: continue
    XS, YS = [], []
    for i in tr[::3]:
        m = MEM[i] & np.isfinite(Y4[i])
        if m.sum() < 25: continue
        a = np.column_stack([zr(np.where(m, CH[i, :, k], np.nan)) for k in range(32)])[m]
        XS.append(np.nan_to_num(a)); YS.append(zr(np.where(m, Y4[i], np.nan))[m])
    A = np.vstack(XS); b = np.concatenate(YS)
    mu, sd = A.mean(0), A.std(0)+1e-9
    w = np.linalg.solve(((A-mu)/sd).T@((A-mu)/sd)+200*np.eye(32), ((A-mu)/sd).T@b)
    rs = np.full(N, 0.0); cnt = np.full(N, 0)
    for i in te:
        m = MEM[i] & np.isfinite(Y4[i])
        if m.sum() < 25: continue
        a = np.nan_to_num(np.column_stack([zr(np.where(m, CH[i,:,k], np.nan)) for k in range(32)])[m])
        p = (a-mu)/sd @ w
        t_ = zr(np.where(m, Y4[i], np.nan))[m]
        resid = t_ - p * (np.nanstd(t_)/max(np.nanstd(p),1e-9))
        idx = np.where(m)[0]
        rs[idx] += resid; cnt[idx] += 1
    resmean[y] = np.where(cnt > 100, rs/np.maximum(cnt,1), np.nan)
ys = sorted(resmean)
print("P1 逐币残差截距 年际 rank-corr:")
for a, b2 in zip(ys[:-1], ys[1:]):
    x, y2 = resmean[a], resmean[b2]
    m = np.isfinite(x) & np.isfinite(y2)
    c = float(pd.Series(x[m]).rank().corr(pd.Series(y2[m].astype(float)).rank())) if m.sum()>30 else np.nan
    print("  %d→%d: %+.3f (n=%d)" % (a, b2, c, m.sum()))
# P2: 相关聚类年际保持
ret1 = CH[:, :, names.index("ret_1h")].astype(np.float64); ret1[ret1==0]=np.nan
def clusters(yr):
    m = YEAR == yr
    r = pd.DataFrame(ret1[m]).dropna(axis=1, thresh=int(m.sum()*0.5))
    cols = r.columns.to_numpy()
    Cm = r.corr().fillna(0).values
    # 简易谱聚类: 前 5 特征向量 + kmeans(手写, 固定种子)
    w, V = np.linalg.eigh(Cm)
    E = V[:, -5:]
    rng = np.random.default_rng(11)
    cent = E[rng.choice(len(E), 6, replace=False)]
    for _ in range(25):
        d = ((E[:,None,:]-cent[None])**2).sum(-1); lab = d.argmin(1)
        for k in range(6):
            if (lab==k).any(): cent[k]=E[lab==k].mean(0)
    return dict(zip(cols, lab))
pairs = [(2023,2024),(2024,2025),(2025,2026)]
print("\nP2 簇成员年际保持率(同簇对的 Jaccard):")
for a,b2 in pairs:
    ca, cb = clusters(a), clusters(b2)
    common = [c for c in ca if c in cb]
    same_a = set(); same_b = set()
    for i in range(len(common)):
        for j in range(i+1, len(common)):
            x, y2 = common[i], common[j]
            if ca[x]==ca[y2]: same_a.add((x,y2))
            if cb[x]==cb[y2]: same_b.add((x,y2))
    jac = len(same_a & same_b)/max(len(same_a | same_b),1)
    print("  %d→%d: Jaccard %.3f (共同币 %d)" % (a,b2,jac,len(common)))
print("\n判读: P1≈0 ⇒ 身份无持久alpha(支持 attn-only 注入); P2>0.3 ⇒ sector 概念稳定")
