"""成本门终判: logistic(rvol+turn) vs +book5全特征, 逐年走前 AUC 增量。判据 ≥+0.02。"""
import numpy as np, datetime as dt
G = np.load("/workspace/data/ohlcv_grid.npz", allow_pickle=True)
B5 = np.load("/workspace/data/book5_hourly.npz", allow_pickle=True)
R = np.load("/workspace/data/wide_dl_prodmask32.npz", allow_pickle=True)
C = G["CLOSE"].astype(np.float64); L = G["LOW"].astype(np.float64)
MEM = R["MEMBER110"]; T, N = C.shape
TS = np.asarray(G["ts"]).astype(np.int64)
YEAR = np.array([dt.datetime.fromtimestamp(int(t)/1000, dt.timezone.utc).year for t in TS])
d = 2e-3
FILL = np.full((T, N), np.nan, np.float32)
FILL[:-1] = (L[1:] < C[:-1]*(1-d)).astype(np.float32)
FILL[:-1][~np.isfinite(L[1:]) | ~np.isfinite(C[:-1])] = np.nan
names32 = [str(x) for x in R["ch_names"]]
rvol = R["CH"][:, :, names32.index("rvol_6h")].astype(np.float64)
turn = R["CH"][:, :, names32.index("lturnover_24h")].astype(np.float64)
BX = B5["X"].astype(np.float64)
def sig(z): return 1/(1+np.exp(-np.clip(z, -30, 30)))
def logit_fit(A, y, it=200, lr=0.5):
    w = np.zeros(A.shape[1])
    for _ in range(it):
        p = sig(A @ w); w -= lr * (A.T @ (p - y)) / len(y) + 1e-4*w
    return w
def auc(x, y):
    r = np.argsort(np.argsort(x)).astype(float)+1
    n1 = (y > .5).sum(); n0 = len(y)-n1
    if n1 == 0 or n0 == 0: return np.nan
    return float((r[y > .5].sum()-n1*(n1+1)/2)/(n1*n0))
rows = [i for i in range(24, T-2)]
def collect(idxs, with_book):
    XA, YA = [], []
    for i in idxs:
        m = MEM[i] & np.isfinite(FILL[i]) & np.isfinite(rvol[i]) & (rvol[i] != 0)
        if with_book: m &= np.isfinite(BX[i]).all(axis=1)
        if m.sum() < 20: continue
        cols = [rvol[i][m], turn[i][m]]
        if with_book: cols += [BX[i, m, k] for k in range(BX.shape[2])]
        A = np.column_stack(cols)
        XA.append(A); YA.append(FILL[i][m])
    if not XA: return None, None
    return np.vstack(XA), np.concatenate(YA)
print("多变量增量 (δ=20bp, 逐年走前):")
incs = []
for y in (2024, 2025, 2026):
    tr = [i for i in rows if YEAR[i] < y][-40000:]
    te = [i for i in rows if YEAR[i] == y]
    a0 = []
    for wb in (False, True):
        Xtr, ytr = collect(tr[::7], wb); Xte, yte = collect(te[::5], wb)
        if Xtr is None or Xte is None: a0.append(np.nan); continue
        mu, sd = Xtr.mean(0), Xtr.std(0)+1e-9
        w = logit_fit((Xtr-mu)/sd, ytr)
        a0.append(auc((Xte-mu)/sd @ w, yte))
    print("  %d: 基线(rvol+turn) %.4f  +book5 %.4f  Δ %+0.4f" % (y, a0[0], a0[1], a0[1]-a0[0]))
    incs.append(a0[1]-a0[0])
print("均值 Δ = %+.4f  判据 ≥+0.02 ⇒ %s" % (np.mean(incs), "PASS" if np.mean(incs) >= 0.02 else "FAIL"))
