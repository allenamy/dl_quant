"""F-8 诊断(非预注册, 只读报告): 新 89 列对 82 列基线的线性冗余度 —— 逐列 R²(OLS on 82 列, 30 万行抽样, 训练/验证各半)与
对任一单个 82 列的最大 |Spearman|; 以及新列自身的 S1 单列秩 IC(逐锚 Spearman vs YR4s, 抽 1/5 锚)。产物 results/f8_redundancy.json"""
import json, numpy as np
from scipy.stats import spearmanr
ROOT = "/mnt/storage/private/work_hsy"; DLW = f"{ROOT}/dlw_2026-08-22"; OUT = f"{ROOT}/f8_2026-08-22"
TG = np.load(f"{DLW}/data/dlw_targets.npz", allow_pickle=True); YRZ = TG["YRZ"]; YR4s = TG["YR4s"]; yrs = TG["yrs"]
FE = np.load(f"{DLW}/data/dlw_fea82.npz", allow_pickle=True); X82 = FE["X"]; pa = FE["pair_a"].astype(np.int64); ps = FE["pair_s"].astype(np.int64); n82 = [str(n) for n in FE["names"]]
F9 = np.load(f"{OUT}/data/f8_fea89.npz", allow_pickle=True); X89 = F9["X"]; names = [str(n) for n in F9["names"]]
rng = np.random.default_rng(0); idx = rng.choice(len(pa), 300000, replace=False); idx.sort()
A = X82[idx].astype(np.float64); B = X89[idx].astype(np.float64)
mu = A.mean(0); sd = A.std(0) + 1e-9; A = np.clip((A - mu) / sd, -5, 5); A1 = np.concatenate([A, np.ones((len(A), 1))], 1)
tr = np.arange(len(idx)) < 150000; te = ~tr
G = A1[tr].T @ A1[tr] + 1e-3 * np.eye(A1.shape[1])
beta = np.linalg.solve(G, A1[tr].T @ B[tr])
pred = A1[te] @ beta
r2 = 1 - ((B[te] - pred) ** 2).sum(0) / np.maximum(((B[te] - B[te].mean(0)) ** 2).sum(0), 1e-12)
# 最大单列 |Spearman|(抽 5 万行)
sub = rng.choice(len(idx), 50000, replace=False)
maxs = []
for j in range(B.shape[1]):
    best = 0.0; bn = ""
    for k in range(A.shape[1]):
        c = spearmanr(B[sub, j], A[sub, k]).correlation
        if np.isfinite(c) and abs(c) > abs(best):
            best = c; bn = n82[k]
    maxs.append((best, bn))
# 单列秩 IC(逐锚, 测试年, 抽 1/5 锚)
nA = YRZ.shape[0]; st = np.searchsorted(pa, np.arange(nA + 1)); test_anchors = [i for i in range(nA) if yrs[i] >= 2023][::5]
ic = np.zeros(B.shape[1]); cnt = 0
for i in test_anchors:
    sl = slice(st[i], st[i + 1]); y = YR4s[pa[sl], ps[sl]]; ok = np.isfinite(y)
    if ok.sum() < 30:
        continue
    Xi = X89[sl][ok]
    for j in range(B.shape[1]):
        c = spearmanr(Xi[:, j], y[ok]).correlation
        ic[j] += 0 if not np.isfinite(c) else c
    cnt += 1
ic /= max(cnt, 1)
out = {"n_sample_rows": int(len(idx)), "n_anchors_ic": cnt, "cols": {names[j]: {"R2_on_82": float(r2[j]), "max_abs_spearman_82": float(maxs[j][0]), "max_partner": maxs[j][1], "single_col_rank_ic": float(ic[j])} for j in range(len(names))}}
fam = {}
for f in "ABCDEFGHIJ":
    js = [j for j, n in enumerate(names) if n.startswith(f + ":")]
    fam[f] = {"median_R2_on_82": float(np.median(r2[js])), "max_R2": float(np.max(r2[js])), "min_R2": float(np.min(r2[js])), "mean_abs_single_ic": float(np.mean(np.abs(ic[js]))), "max_abs_single_ic": float(np.max(np.abs(ic[js])))}
out["by_family"] = fam
json.dump(out, open(f"{OUT}/results/f8_redundancy.json", "w"), indent=1)
print(json.dumps(fam, indent=1))
for j in np.argsort(-np.abs(ic))[:15]:
    print(f"{names[j]:<18s} ic {ic[j]:+.4f}  R2_82 {r2[j]:.3f}  max|ρ| {maxs[j][0]:+.3f} ({maxs[j][1]})")
print("REDUNDANCY_DONE")
