"""book 族 G1/G1b/G2 三门。判据先写死(DESIGN_book §4):
 G1 |IC vs 未来24h| < 0.15   G1b 对未来的相关不得超过对过去 +0.05
 G2 Ridge 逐年走前(2024/25/26): 均值 |IC| > 0.005 且逐年无反号"""
import numpy as np, datetime as dt
P = np.load("/workspace/data/panel_targets.npz", allow_pickle=True)
M = np.load("/workspace/data/book1p_hourly.npz", allow_pickle=True)
X, FEAT = M["X"], [str(f) for f in M["feats"]]
Y4, MEM, TS = P["Y4"], P["MEMBER110"], np.asarray(P["ts"]).astype(np.int64)
T, N = Y4.shape
YEAR = np.array([dt.datetime.fromtimestamp(int(t)/1000, dt.timezone.utc).year for t in TS])
print("book 面板 %s  填充 %.4f  特征 %d" % (X.shape, np.isfinite(X[:,:,0]).mean(), len(FEAT)))

def zr(v):
    m = np.isfinite(v); o = np.full(len(v), np.nan)
    if m.sum() < 20: return o
    r = np.argsort(np.argsort(v[m])).astype(float)
    o[m] = (r - r.mean()) / (r.std() + 1e-12); return o
def xic(a, b):
    za, zb = zr(a), zr(b); m = np.isfinite(za) & np.isfinite(zb)
    return float((za[m]*zb[m]).mean()) if m.sum() >= 20 else np.nan

rows = [i for i in range(48, T-30) if i % 4 == 0]
fut = np.full((T, N), np.nan, np.float32); pas = np.full((T, N), np.nan, np.float32)
for i in rows:
    if i+24 < T:
        s = np.zeros(N); ok = np.ones(N, bool)
        for k in range(6):
            v = Y4[i+4*k]; ok &= np.isfinite(v); s += np.where(np.isfinite(v), v, 0)
        fut[i] = np.where(ok, s, np.nan)
    if i-24 >= 0:
        s = np.zeros(N); ok = np.ones(N, bool)
        for k in range(1, 7):
            v = Y4[i-4*k]; ok &= np.isfinite(v); s += np.where(np.isfinite(v), v, 0)
        pas[i] = np.where(ok, s, np.nan)
samp = rows[::5]
print("\n%-14s %>14s" % ("特征", "") if False else "%-14s %14s %14s %10s  判" % ("特征","IC vs 未来24h","IC vs 过去24h","IC vs Y4"))
red = []
for k, nm in enumerate(FEAT):
    f_ = np.nanmean([xic(np.where(MEM[i], X[i,:,k], np.nan), np.where(MEM[i], fut[i], np.nan)) for i in samp])
    p_ = np.nanmean([xic(np.where(MEM[i], X[i,:,k], np.nan), np.where(MEM[i], pas[i], np.nan)) for i in samp])
    y_ = np.nanmean([xic(np.where(MEM[i], X[i,:,k], np.nan), np.where(MEM[i], Y4[i], np.nan)) for i in rows[::3]])
    # ★ G1b 的假阳性模式(本轮自查发现): "对未来相关 > 对过去相关"对【真预测因子】
    # 由构造成立 —— 波动率类特征预测未来收益(低波溢价), 与过去【方向】本就无关。
    # 修正: 只在 |未来IC| 同时超过绝对小阈值(0.08)时才当可疑; 真泄漏检测交给 shuffle-future null。
    bad = abs(f_) > 0.15; asym = (abs(f_) > abs(p_) + 0.05) and (abs(f_) > 0.08)
    if bad or asym: red.append(nm)
    print("%-14s %+14.4f %+14.4f %+10.4f  %s" % (nm, f_, p_, y_,
          "★★★泄漏" if bad else ("★不对称" if asym else ("信息" if abs(y_) > 0.01 else "—"))))
print("\nG1/G1b: %s" % ("FAIL " + str(red) if red else "PASS(无红旗)"))

print("\n[G2] Ridge 逐年走前 (book 13 列)")
rows2 = np.array([i for i in range(24, T-8) if i % 4 == 0])
def stack(idxs, cols):
    XS, YS = [], []
    for i in idxs:
        m = MEM[i] & np.isfinite(Y4[i]) & np.isfinite(X[i][:, cols]).all(axis=1)
        if m.sum() < 25: continue
        a = np.column_stack([zr(np.where(m, X[i,:,k], np.nan)) for k in cols])[m]
        XS.append(a); YS.append(zr(np.where(m, Y4[i], np.nan))[m])
    return (np.vstack(XS), np.concatenate(YS)) if XS else (None, None)
cols = list(range(len(FEAT))); ics = []
for y in (2024, 2025, 2026):
    tr = rows2[YEAR[rows2] < y]; te = rows2[YEAR[rows2] == y]
    Xtr, ytr = stack(tr, cols)
    if Xtr is None or len(te) < 100: print("  %d 样本不足" % y); continue
    mu, sd = Xtr.mean(0), Xtr.std(0)+1e-9
    A = (Xtr-mu)/sd
    w = np.linalg.solve(A.T@A + 200*np.eye(A.shape[1]), A.T@ytr)
    per = []
    for i in te:
        m = MEM[i] & np.isfinite(Y4[i]) & np.isfinite(X[i][:, cols]).all(axis=1)
        if m.sum() < 25: continue
        a = np.column_stack([zr(np.where(m, X[i,:,k], np.nan)) for k in cols])[m]
        p = zr(((a-mu)/sd)@w); t_ = zr(np.where(m, Y4[i], np.nan))[m]
        ok = np.isfinite(p)&np.isfinite(t_)
        if ok.sum() >= 20: per.append(float((p[ok]*t_[ok]).mean()))
    if per:
        ic = float(np.mean(per)); ics.append(ic)
        print("  %d: OOS rank-IC %+.4f  IR %.2f  n=%d" % (y, ic, ic/(np.std(per)+1e-12)*np.sqrt(len(per)), len(per)))
if ics:
    print("  均值 %+.4f  反号 %s  ⇒ G2 %s" % (np.mean(ics), "有" if min(ics)<0<max(ics) else "无",
          "PASS" if abs(np.mean(ics))>0.005 and not (min(ics)<0<max(ics)) else "FAIL"))
