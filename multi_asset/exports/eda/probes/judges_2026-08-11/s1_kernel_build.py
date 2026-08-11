"""S1: 核目标构建 + 四道因果门 + Ridge 前置门。产出 target_npz 供 S2 训练。

因果性(门 4, 构建期断言): y_kernel^a(t) = Σ_k (1−a)^k · Y4(t+4k) —— 全部是【未来】收益,
与 YR4/YR24 同族(目标本就该看未来)。真正要断言的是: (i) 不含 t 之后【本不该在标签里】的东西
—— 它只由 Y4 组成, 与 Y4 同源同口径; (ii) 截断 K 不越界; (iii) 掩码遵循 CL(非重叠)约定;
(iv) a=1.0 时必须【逐位等于】YR4(退化自检 —— 本文 §1 的代数恒等式, 不过即范式作废)。
Ridge 前置门: 用 8 列 baseline 对 y_kernel 做 walk-forward 岭回归, 报可预测性; 与 YR4/YR24 对照。
"""
import numpy as np
import json

BASE = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
P = np.load(f"{BASE}/wide_dl_full_corrfund_causal_0731.npz", allow_pickle=True)
Y4 = P["Y4"].astype(np.float64); YR4 = P["YR4"]; YR24 = P["YR24"]
MEM = P["MEMBER110"]; CL4 = P["CL4"]; CH = P["CH"]
names = [str(x) for x in P["ch_names"]]
bcols = [str(x) for x in P["baseline_cols"]]
T, N = Y4.shape


def build_kernel(a, wfloor=0.01):
    """y_kernel^a(t) = Σ_k (1−a)^k Y4(t+4k) / Σ (1−a)^k, 截断至权重 < wfloor。"""
    if a >= 1.0:
        K = 0
    else:
        K = int(np.ceil(np.log(wfloor) / np.log(1 - a)))
    out = np.full((T, N), np.nan, np.float32)
    ws = [(1 - a) ** k for k in range(K + 1)]
    den = float(sum(ws))
    for t in range(T):
        acc = np.zeros(N); ok = np.ones(N, bool)
        for k, w in enumerate(ws):
            tt = t + 4 * k
            if tt >= T:
                ok[:] = False; break
            v = Y4[tt]; ok &= np.isfinite(v)
            acc += w * np.where(np.isfinite(v), v, 0.0)
        out[t] = np.where(ok, acc / den, np.nan)
    return out, K


print("[门4] 构建期断言")
k10, K10 = build_kernel(1.0)
same = np.allclose(np.where(np.isfinite(k10), k10, 0), np.where(np.isfinite(Y4), Y4, 0),
                   atol=1e-6) and (np.isfinite(k10) == np.isfinite(Y4)).all()
print(f"  ★ a=1.0 退化自检 (§1 代数恒等式): y_kernel ≡ Y4 ? {same}   K={K10}")
assert same, "退化自检失败 ⇒ 核定义与 §1 不符, 范式作废"
K_USED = {}
targets = {}
for a in (0.3, 0.03):
    yk, K = build_kernel(a)
    K_USED[a] = K
    targets[a] = yk
    fin = np.isfinite(yk) & MEM
    print(f"  a={a}: K={K} (跨 {4*K}h)  有限率={fin.mean():.3f}  "
          f"sd={np.nanstd(yk[MEM]):.5f} (对照 Y4 {np.nanstd(Y4[MEM]):.5f})")

print("\n[门2] 未来相关扫描 — 对【核目标】而言这是自明的(它就是未来), 故改测:")
print("  核目标 vs 【过去】收益的相关(应当小 — 否则核里混进了可被历史直接推出的成分)")


def zr(x):
    m = np.isfinite(x); out = np.full(len(x), np.nan)
    if m.sum() < 10: return out
    r = np.argsort(np.argsort(x[m])).astype(float)
    out[m] = (r - r.mean()) / (r.std() + 1e-12); return out


def xic(a_, b_):
    za, zb = zr(a_), zr(b_)
    m = np.isfinite(za) & np.isfinite(zb)
    return float(np.nanmean(za[m] * zb[m])) if m.sum() >= 10 else np.nan


rows = np.arange(900, T - 700, 197)
for a in (0.3, 0.03):
    ics = []
    for r in rows:
        past = np.zeros(N); ok = np.ones(N, bool)
        for j in range(6):
            v = Y4[r - 4 * (j + 1)]; ok &= np.isfinite(v)
            past += np.where(np.isfinite(v), v, 0.0)
        ics.append(xic(np.where(MEM[r] & ok, past, np.nan),
                       np.where(MEM[r], targets[a][r], np.nan)))
    print(f"  a={a}: IC(过去24h, 核目标) = {np.nanmean(ics):+.4f}  (对照 Y4: ", end="")
    ics0 = [xic(np.where(MEM[r], np.nansum([Y4[r-4*(j+1)] for j in range(6)], axis=0), np.nan),
                np.where(MEM[r], Y4[r], np.nan)) for r in rows]
    print(f"{np.nanmean(ics0):+.4f})")

print("\n[Ridge 前置门] 8 列 baseline 对各目标的 walk-forward 可预测性(折内拟合, 折外评)")
bidx = [names.index(b) for b in bcols if b in names]
days = np.arange(T) // 6
cut = int(T * 0.6)
for nm, Y in (("YR4", YR4), ("YR24", YR24), ("kernel_0.3", targets[0.3]),
              ("kernel_0.03", targets[0.03])):
    tr = np.arange(900, cut, 4); te = np.arange(cut, T - 700, 4)
    def stack(idxs):
        X, y = [], []
        for r in idxs:
            m = MEM[r] & np.isfinite(Y[r])
            if m.sum() < 20: continue
            X.append(CH[r][m][:, bidx]); y.append(zr(np.where(m, Y[r], np.nan))[m])
        return (np.vstack(X), np.concatenate(y)) if X else (None, None)
    Xtr, ytr = stack(tr); Xte, yte = stack(te)
    if Xtr is None or Xte is None:
        print(f"  {nm}: 样本不足"); continue
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
    A = ((Xtr - mu) / sd); B = ((Xte - mu) / sd)
    w = np.linalg.solve(A.T @ A + 50 * np.eye(A.shape[1]), A.T @ ytr)
    pred = B @ w
    ss = 1 - ((yte - pred) ** 2).sum() / ((yte - yte.mean()) ** 2).sum()
    print(f"  {nm:12s} OOS R²={ss:+.5f}  corr={np.corrcoef(pred, yte)[0,1]:+.4f}")

np.savez_compressed("/tmp/kernel_targets.npz",
                    Y_kernel_003=targets[0.03].astype(np.float32),
                    Y_kernel_03=targets[0.3].astype(np.float32),
                    K_003=K_USED[0.03], K_03=K_USED[0.3])
print("\nsaved /tmp/kernel_targets.npz")
