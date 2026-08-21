"""机制验证: lead-lag 在 4h/24h 视界上存不存在方向性?

★ 为什么要先量: 现有 MultiRelXAttn 注入的关系偏置是 torch.bmm(rn, rn.T) —— 【对称】的
  Pearson 相关矩阵。B[i,j] == B[j,i] ⇒ 它在数学上【无法表达"i 领先 j"】。
  如果 lead-lag 真的存在, 这就是一个可指认的结构缺陷; 如果不存在, 就不该建这个模块。
  项目家规: 机制 > 堆叠, 每个模块先答"机理是什么" + 过定量门。

判据(先写死):
  L1 方向性存在: 平均 |corr(r_i[t-l], r_j[t]) - corr(r_j[t-l], r_i[t])| 显著 > 0
     (对称零假设下该差应为 0; 用逐锚 bootstrap 的 t 统计量)
  L2 有用: 领先者的滞后收益对跟随者的【未来】收益有增量 —— 用 xsec rank-IC 直接量
  L3 稳定: 领先关系在不同年份是否一致(否则是噪声)
"""
import numpy as np
import datetime as dt

P = np.load("/workspace/data/panel_targets.npz", allow_pickle=True)
Y1, Y4, MEM = P["Y1"], P["Y4"], P["MEMBER110"]
SYMS = [str(s) for s in P["symbols"]]
TS = np.asarray(P["ts"]).astype(np.int64)
T, N = Y1.shape
YEAR = np.array([dt.datetime.fromtimestamp(int(t)/1000, dt.timezone.utc).year for t in TS])
print(f"面板 {T:,}×{N}")

# 过去 1h 收益: past1[t] = Y1[t-1] (t-1 到 t 的实现收益) —— 严格 ≤t
past1 = np.full_like(Y1, np.nan); past1[1:] = Y1[:-1]

# 选常驻成员(整段可用率高的), 避免成员变动污染相关结构
avail = (MEM & np.isfinite(Y1)).mean(axis=0)
core = np.argsort(-avail)[:60]
print(f"常驻 60 名, 最低可用率 {avail[core].min():.2f}")

def lagged_corr(rows, lag):
    """C[i,j] = corr(过去收益_i 在 t-lag, 收益_j 在 t)。★ 非对称。"""
    A, B = [], []
    for t in rows:
        if t - lag < 1 or t >= T: continue
        a = past1[t - lag, core]; b = Y1[t, core]
        if np.isfinite(a).sum() < 50 or np.isfinite(b).sum() < 50: continue
        A.append(a); B.append(b)
    A, B = np.array(A), np.array(B)
    ok = np.isfinite(A).all(0) & np.isfinite(B).all(0)
    A, B = A[:, ok], B[:, ok]
    A = (A - A.mean(0)) / (A.std(0) + 1e-12); B = (B - B.mean(0)) / (B.std(0) + 1e-12)
    return (A.T @ B) / len(A), ok      # C[i,j]: i 的过去 vs j 的现在

rows = np.arange(200, T - 200, 4)
print(f"\n[L1] 方向性: |C[i,j] - C[j,i]| 的规模 vs 对称零假设")
print(f"{'滞后':>6s} {'均值|C|':>10s} {'均值|C-Cᵀ|':>12s} {'比值':>8s} {'最强有向对':>28s}")
for lag in (1, 2, 4, 8, 24):
    C, ok = lagged_corr(rows, lag)
    D = C - C.T
    names = [SYMS[core[k]] for k in range(len(core)) if ok[k]]
    iu = np.triu_indices_from(D, 1)
    k = np.argmax(np.abs(D[iu]))
    i, j = iu[0][k], iu[1][k]
    lead, foll = (names[i], names[j]) if D[i, j] > 0 else (names[j], names[i])
    print(f"{lag:>6d} {np.abs(C).mean():>10.4f} {np.abs(D).mean():>12.4f} "
          f"{np.abs(D).mean()/np.abs(C).mean():>8.2f} {lead+'→'+foll:>28s} ({abs(D[i,j]):.3f})")

print(f"\n[L3] 稳定性: 同一有向结构在不同年是否一致 (滞后=4h)")
mats = {}
for y in sorted(set(YEAR)):
    r = rows[(YEAR[rows] == y)]
    if len(r) < 300: continue
    C, ok = lagged_corr(r, 4)
    mats[y] = (C - C.T)[np.triu_indices(C.shape[0], 1)]
ys = sorted(mats)
print("      " + "".join(f"{y:>8d}" for y in ys))
for a in ys:
    row = "".join(f"{np.corrcoef(mats[a], mats[b])[0,1]:>8.3f}"
                  if mats[a].shape == mats[b].shape else f"{'—':>8s}" for b in ys)
    print(f"{a:>6d}" + row)
print("\n判读: 对角外的相关 = 有向结构的跨年一致性。>0.3 ⇒ 结构真实且持久; ~0 ⇒ 噪声, 不建该模块。")
