"""★ R1 执行成本轨 前置门 —— book 族退役备案里【唯一被允许的重启路径】。
判据在 DESIGN_book 附2-A 早已预写: book 特征预测 fill/adverse 必须【超过 rvol+turnover 基线】
AUC 增量 > 0.02, 否则只是波动率换皮。

真目标(可由 klines H/L 离线构造, 无需成交回执):
  maker 买单挂在 C(t)*(1-d) —— 下一小时成交当且仅当 LOW(t+1) < C(t)*(1-d)
  maker 卖单挂在 C(t)*(1+d) —— 下一小时成交当且仅当 HIGH(t+1) > C(t)*(1+d)
  d ∈ {5,10,20} bps
★ 买卖分开报: book 法证实测买侧变异 0.392 vs 卖侧 1.248(3.2x), 若侧不对称是真的,
  两侧的可预测性应当不同 —— 这同时是对那条法证的独立检验。
装置: 逐年走前 logistic(牛顿法), 训练用先前全部年份; AUC 用 Mann-Whitney。
纪律: 特征全部 <=t; 标签用 t+1 小时(标签用未来是合法的)。npz 全部先物化。
"""
import numpy as np, datetime as dt
G = np.load("/workspace/data/ohlcv_grid.npz", allow_pickle=True)
P = np.load("/workspace/data/wide_dl_pm32_hz.npz", allow_pickle=True)
B1 = np.load("/workspace/data/book1p_hourly.npz", allow_pickle=True)
B5 = np.load("/workspace/data/book5_hourly.npz", allow_pickle=True)
assert np.array_equal(G["ts"], P["ts"]), "ts 不一致"
C = G["CLOSE"].astype(np.float64); H = G["HIGH"].astype(np.float64); L = G["LOW"].astype(np.float64)
CH = P["CH"]; MEM = P["MEMBER110"]; ts = P["ts"].astype(np.int64)
nm = [str(v) for v in P["ch_names"]]
X1 = np.nan_to_num(B1["X"]); X5 = np.nan_to_num(B5["X"])
COV = np.isfinite(B1["X"]).all(2)
iv, il = nm.index("rvol_24h"), nm.index("size_dvol")
YEAR = np.array([dt.datetime.fromtimestamp(int(t)/1000, dt.timezone.utc).year for t in ts])
T, N = C.shape
rows = np.array([i for i in range(24, T-2) if i % 4 == 0 and YEAR[i] >= 2023])

def logit_fit(A, y, lam=1e-2, iters=40):
    w = np.zeros(A.shape[1]+1); Ab = np.column_stack([np.ones(len(A)), A])
    for _ in range(iters):
        p = 1/(1+np.exp(-np.clip(Ab@w, -30, 30)))
        g = Ab.T@(p-y) + lam*np.r_[0, w[1:]]
        Wd = np.clip(p*(1-p), 1e-6, None)
        Hm = (Ab*Wd[:, None]).T@Ab + lam*np.eye(len(w))
        w -= np.linalg.solve(Hm, g)
    return w

def auc(s, y):
    o = np.argsort(s); r = np.empty(len(s)); r[o] = np.arange(1, len(s)+1)
    n1 = y.sum(); n0 = len(y)-n1
    if n1 < 10 or n0 < 10: return np.nan
    return (r[y > 0.5].sum() - n1*(n1+1)/2) / (n1*n0)

def run(side, dbps, blocks):
    d = dbps/1e4
    res = {}
    for lbl, extra in blocks:
        aucs = []
        for y in (2024, 2025, 2026):
            tr = rows[YEAR[rows] < y]; te = rows[YEAR[rows] == y]
            def build(idx):
                Xs, Ys = [], []
                for i in idx:
                    m = MEM[i] & COV[i] & np.isfinite(C[i]) & np.isfinite(H[i+1]) & np.isfinite(L[i+1])
                    if m.sum() < 20: continue
                    lab = (L[i+1] < C[i]*(1-d)) if side == "buy" else (H[i+1] > C[i]*(1+d))
                    f = [np.log1p(np.abs(CH[i, :, iv])), CH[i, :, il]]
                    if extra == "b1": f += [X1[i, :, k] for k in range(X1.shape[2])]
                    if extra == "b5": f += [X5[i, :, k] for k in range(X5.shape[2])]
                    Xs.append(np.nan_to_num(np.column_stack(f))[m]); Ys.append(lab[m].astype(float))
                return np.vstack(Xs), np.concatenate(Ys)
            Atr, ytr = build(tr[::3]); Ate, yte = build(te)
            mu, sd = Atr.mean(0), Atr.std(0)+1e-9
            w = logit_fit((Atr-mu)/sd, ytr)
            s = np.column_stack([np.ones(len(Ate)), (Ate-mu)/sd])@w
            aucs.append(auc(s, yte))
        res[lbl] = float(np.nanmean(aucs))
    return res

print("%-6s %5s | %8s %8s %8s | %9s %9s" % ("侧", "δbps", "基线", "+book1p", "+book5", "Δb1p", "Δb5"), flush=True)
BLOCKS = [("base", None), ("b1", "b1"), ("b5", "b5")]
for side in ("buy", "sell"):
    for dbps in (5, 10, 20):
        r = run(side, dbps, BLOCKS)
        print("%-6s %5d | %8.4f %8.4f %8.4f | %+9.4f %+9.4f  %s" % (
            side, dbps, r["base"], r["b1"], r["b5"], r["b1"]-r["base"], r["b5"]-r["base"],
            "★过门" if max(r["b1"], r["b5"])-r["base"] > 0.02 else ""), flush=True)
print("判据: AUC 增量 > 0.02 (DESIGN_book 附2-A 预写)", flush=True)
print("R1_FILL_GATE_DONE", flush=True)
