"""metrics 族的 Ridge 走前验证(家规: Ridge 必须先于 DL)。

设计要点:
 · 逐年走前: 训练 = 该年之前的全部, 测试 = 该年。严格时序, 无未来数据。
 · 横截面: 每个 4h 锚点内, 特征与目标各自 rank-z 化(跨币可比), 与 §Metric Discipline 一致。
 · 判据(先写死): (a) 逐年 OOS rank-IC 【无一年反号】; (b) 均值 > 0.005。
   任一不过 = 该族单独不成立(仍可能有增量价值, 由 baseline+metrics 的增量测回答)。
 · 只报 OOS, 不报样本内。
"""
import sys
import numpy as np
import datetime as dt

P = np.load("/workspace/data/panel_targets.npz", allow_pickle=True)
M = np.load("/workspace/data/metrics_hourly.npz", allow_pickle=True)
X, FEAT = M["X"], [str(f) for f in M["feats"]]
Y4, MEM, TS = P["Y4"], P["MEMBER110"], np.asarray(P["ts"]).astype(np.int64)
T, N = Y4.shape
YEAR = np.array([dt.datetime.fromtimestamp(int(t)/1000, dt.timezone.utc).year for t in TS])

def zr(v):
    m = np.isfinite(v); o = np.full(len(v), np.nan)
    if m.sum() < 20: return o
    r = np.argsort(np.argsort(v[m])).astype(float)
    o[m] = (r - r.mean()) / (r.std() + 1e-12); return o

rows = np.array([i for i in range(24, T - 8) if i % 4 == 0])
def stack(idxs):
    XS, YS = [], []
    for i in idxs:
        m = MEM[i] & np.isfinite(Y4[i]) & np.isfinite(X[i]).all(axis=1)
        if m.sum() < 25: continue
        a = np.column_stack([zr(np.where(m, X[i, :, k], np.nan)) for k in range(X.shape[2])])[m]
        XS.append(a); YS.append(zr(np.where(m, Y4[i], np.nan))[m])
    return (np.vstack(XS), np.concatenate(YS)) if XS else (None, None)

print(f"特征 {len(FEAT)}  锚点 {len(rows):,}")
years = sorted(set(YEAR[rows]))
print(f"{'测试年':>8s} {'训练锚':>8s} {'测试锚':>8s} {'OOS rank-IC':>13s} {'IC-IR':>8s}")
ics = []
for y in years:
    tr = rows[YEAR[rows] < y]; te = rows[YEAR[rows] == y]
    if len(tr) < 500 or len(te) < 100:
        print(f"{y:>8d} {len(tr):>8,} {len(te):>8,}   (训练/测试样本不足, 跳过)"); continue
    Xtr, ytr = stack(tr); Xte, yte = stack(te)
    if Xtr is None or Xte is None:
        print(f"{y:>8d}   数据不足"); continue
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
    A = (Xtr - mu) / sd
    w = np.linalg.solve(A.T @ A + 200 * np.eye(A.shape[1]), A.T @ ytr)
    # 逐锚 OOS rank-IC
    per = []
    for i in te:
        m = MEM[i] & np.isfinite(Y4[i]) & np.isfinite(X[i]).all(axis=1)
        if m.sum() < 25: continue
        a = np.column_stack([zr(np.where(m, X[i, :, k], np.nan)) for k in range(X.shape[2])])[m]
        p = ((a - mu) / sd) @ w
        t_ = zr(np.where(m, Y4[i], np.nan))[m]
        pr = zr(p)
        ok = np.isfinite(pr) & np.isfinite(t_)
        if ok.sum() >= 20: per.append(float((pr[ok] * t_[ok]).mean()))
    ic = float(np.mean(per)); ir = ic / (np.std(per) + 1e-12) * np.sqrt(len(per))
    ics.append(ic)
    print(f"{y:>8d} {len(tr):>8,} {len(te):>8,} {ic:>+13.4f} {ir:>8.2f}")
if ics:
    print(f"\n均值 OOS rank-IC = {np.mean(ics):+.4f}   逐年反号? "
          f"{'★ 有' if (min(ics) < 0 < max(ics)) else '无'}")
    print(f"判据: 均值>0.005 {'PASS' if abs(np.mean(ics))>0.005 else 'FAIL'};  "
          f"无反号 {'PASS' if not (min(ics)<0<max(ics)) else 'FAIL'}")
