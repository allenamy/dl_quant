"""红队补测: ① 增量 Ridge 在【残差目标 YR24】上重打(含 basis) ② λ 敏感性(50/200/800)"""
import numpy as np, datetime as dt
R = np.load("/workspace/data/wide_dl_prodmask32.npz", allow_pickle=True)
M = np.load("/workspace/data/metrics_hourly.npz", allow_pickle=True)
B5 = np.load("/workspace/data/book5_hourly.npz", allow_pickle=True)
BA = np.load("/workspace/data/basis_hourly.npz", allow_pickle=True)
P = np.load("/workspace/data/panel_targets.npz", allow_pickle=True)
MEM = R["MEMBER110"]; YR = P["YR24"]; Y = P["Y4"]
TS = np.asarray(P["ts"]).astype(np.int64)
T, N = YR.shape
YEAR = np.array([dt.datetime.fromtimestamp(int(t)/1000, dt.timezone.utc).year for t in TS])
def zr(v):
    m = np.isfinite(v); o = np.full(len(v), np.nan)
    if m.sum() < 20: return o
    r = np.argsort(np.argsort(v[m])).astype(float)
    o[m] = (r - r.mean()) / (r.std() + 1e-12); return o
rows = np.array([i for i in range(24, T-30) if i % 4 == 0])
def run(tgt, extra, lam):
    ics = []
    for y in (2024, 2025, 2026):
        tr = rows[YEAR[rows] < y]; te = rows[YEAR[rows] == y]
        XS, YS = [], []
        for i in tr[::2]:
            m = MEM[i] & np.isfinite(tgt[i])
            if m.sum() < 25: continue
            c = [zr(np.where(m, R["CH"][i,:,k], np.nan)) for k in range(32)]
            if extra == "met": c += [zr(np.where(m, M["X"][i,:,k], np.nan)) for k in range(21)]
            if extra == "bas": c += [zr(np.where(m, BA["X"][i,:,k], np.nan)) for k in range(7)]
            if extra == "b5":  c += [zr(np.where(m, B5["X"][i,:,k], np.nan)) for k in range(22)]
            XS.append(np.nan_to_num(np.column_stack(c)[m])); YS.append(zr(np.where(m, tgt[i], np.nan))[m])
        A = np.vstack(XS); b = np.concatenate(YS)
        mu, sd = A.mean(0), A.std(0)+1e-9
        w = np.linalg.solve(((A-mu)/sd).T@((A-mu)/sd)+lam*np.eye(A.shape[1]), ((A-mu)/sd).T@b)
        per = []
        for i in te:
            m = MEM[i] & np.isfinite(tgt[i])
            if m.sum() < 25: continue
            c = [zr(np.where(m, R["CH"][i,:,k], np.nan)) for k in range(32)]
            if extra == "met": c += [zr(np.where(m, M["X"][i,:,k], np.nan)) for k in range(21)]
            if extra == "bas": c += [zr(np.where(m, BA["X"][i,:,k], np.nan)) for k in range(7)]
            if extra == "b5":  c += [zr(np.where(m, B5["X"][i,:,k], np.nan)) for k in range(22)]
            a = np.nan_to_num(np.column_stack(c)[m])
            p = zr((a-mu)/sd@w); t_ = zr(np.where(m, tgt[i], np.nan))[m]
            ok = np.isfinite(p)&np.isfinite(t_)
            if ok.sum() >= 20: per.append(float((p[ok]*t_[ok]).mean()))
        ics.append(float(np.mean(per)))
    return float(np.mean(ics))
print("== 残差目标 YR24 上的增量(λ=200) ==")
b0 = run(YR, None, 200)
for nm, ex in (("+metrics", "met"), ("+basis", "bas"), ("+book5", "b5")):
    print("  %-9s Δ %+0.4f  (基 %.4f)" % (nm, run(YR, ex, 200)-b0, b0))
print("== raw Y4, λ 敏感性(metrics) ==")
for lam in (50, 200, 800):
    b0r = run(Y, None, lam); bm = run(Y, "met", lam)
    print("  λ=%-4d 32ch %.4f  +metrics Δ %+0.4f" % (lam, b0r, bm-b0r))
print("== raw Y4 +basis(λ=200) ==")
b0r = run(Y, None, 200)
print("  +basis Δ %+0.4f (基 %.4f)" % (run(Y, "bas", 200)-b0r, b0r))
