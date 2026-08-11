"""特征扩充的完整定量分解: PR(输入空间) + 增量 Ridge(信号空间), 同装置逐年走前。
回答: 正交特征的 IC 有多少在以 32ch 为条件后幸存?"""
import numpy as np, datetime as dt
R = np.load("/workspace/data/wide_dl_prodmask32.npz", allow_pickle=True)
Z = np.load("/workspace/data/wide_dl_55ch.npz", allow_pickle=True)
M = np.load("/workspace/data/metrics_hourly.npz", allow_pickle=True)
B = np.load("/workspace/data/book1p_hourly.npz", allow_pickle=True)
P = np.load("/workspace/data/panel_targets.npz", allow_pickle=True)
MEM = R["MEMBER110"]; Y4 = P["Y4"]
TS = np.asarray(P["ts"]).astype(np.int64)
T, N = Y4.shape
YEAR = np.array([dt.datetime.fromtimestamp(int(t)/1000, dt.timezone.utc).year for t in TS])
def zr(v):
    m = np.isfinite(v); o = np.full(len(v), np.nan)
    if m.sum() < 20: return o
    r = np.argsort(np.argsort(v[m])).astype(float)
    o[m] = (r - r.mean()) / (r.std() + 1e-12); return o
SETS = {
  "32ch(基线)":            [("R", k) for k in range(32)],
  "+zooV2(56ch)":          [("Z", k) for k in range(56)],
  "+metrics21(53)":        [("R", k) for k in range(32)] + [("M", k) for k in range(21)],
  "+book13(45)":           [("R", k) for k in range(32)] + [("B", k) for k in range(13)],
  "全部(90)":              [("Z", k) for k in range(56)] + [("M", k) for k in range(21)] + [("B", k) for k in range(13)],
  "metrics 单独":          [("M", k) for k in range(21)],
  "book 单独":             [("B", k) for k in range(13)],
}
SRC = {"R": R["CH"], "Z": Z["CH"], "M": M["X"], "B": B["X"]}
rows = np.array([i for i in range(24, T - 8) if i % 4 == 0])
def feat(i, cols, m):
    out = []
    for s, k in cols:
        v = SRC[s][i, :, k]
        out.append(zr(np.where(m & np.isfinite(v), v, np.nan)))
    return np.column_stack(out)
def run(cols):
    ics = []
    for y in (2024, 2025, 2026):
        tr = rows[YEAR[rows] < y]; te = rows[YEAR[rows] == y]
        XS, YS = [], []
        for i in tr[::2]:
            m = MEM[i] & np.isfinite(Y4[i])
            if m.sum() < 25: continue
            a = feat(i, cols, m)[m]
            XS.append(np.nan_to_num(a)); YS.append(zr(np.where(m, Y4[i], np.nan))[m])
        if not XS: return []
        A = np.vstack(XS); b = np.concatenate(YS)
        mu, sd = A.mean(0), A.std(0) + 1e-9
        w = np.linalg.solve(((A-mu)/sd).T @ ((A-mu)/sd) + 200*np.eye(A.shape[1]), ((A-mu)/sd).T @ b)
        per = []
        for i in te:
            m = MEM[i] & np.isfinite(Y4[i])
            if m.sum() < 25: continue
            a = np.nan_to_num(feat(i, cols, m)[m])
            p = zr((a-mu)/sd @ w); t_ = zr(np.where(m, Y4[i], np.nan))[m]
            ok = np.isfinite(p) & np.isfinite(t_)
            if ok.sum() >= 20: per.append(float((p[ok]*t_[ok]).mean()))
        if per: ics.append(float(np.mean(per)))
    return ics
def pr_of(cols):
    rs = rows[::12]
    mats = []
    for i in rs:
        m = MEM[i]
        if m.sum() < 50: continue
        a = np.nan_to_num(feat(i, cols, m)[m])
        mats.append(a)
    A = np.vstack(mats)
    C = np.corrcoef(A.T); C = np.where(np.isfinite(C), C, 0)
    w = np.clip(np.linalg.eigvalsh(C)[::-1], 0, None)
    return float((w.sum()**2) / (w**2).sum())
base = None
print("%-18s %8s %28s %8s" % ("集合", "PR", "逐年 OOS rank-IC", "vs 32ch"))
for nm, cols in SETS.items():
    ics = run(cols); pr = pr_of(cols)
    mean = np.mean(ics) if ics else float("nan")
    if nm.startswith("32ch"): base = mean
    d = "" if base is None or nm.startswith("32ch") else "%+.4f" % (mean - base)
    print("%-18s %8.1f %28s %8s" % (nm, pr, " ".join("%+.4f" % x for x in ics), d))
