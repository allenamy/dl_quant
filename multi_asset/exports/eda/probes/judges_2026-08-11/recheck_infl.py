"""重核有效 n 膨胀因子: 现用估计量(截断求和) vs 三个不带截断偏差的估计量。"""
import csv, os, sys
import numpy as np
MON = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/live/monitor"
path = os.path.join(MON, "ic_history_deployable_4leg.csv")
if not os.path.exists(path):
    path = os.path.join(MON, "ic_history.csv")
rows = list(csv.DictReader(open(path)))
ic = np.array([float(r["ic"]) for r in rows if r["ic"] not in ("", "None")])
n = len(ic); x = ic - ic.mean(); denom = (x * x).sum()
sd = ic.std(ddof=1); se_iid = sd / np.sqrt(n)
print(f"序列: {os.path.basename(path)}  n={n}  mean={ic.mean():+.5f}  sd={sd:.4f}  SE_iid={se_iid:.5f}")
rho = np.array([float((x[:-k] * x[k:]).sum() / denom) for k in range(1, 21)])
se_rho = 1 / np.sqrt(n)
print(f"\nρ_1..12: {np.round(rho[:12], 3).tolist()}")
print(f"SE(ρ) ≈ 1/√n = {se_rho:.3f}   ⇒ |ρ|>2SE={2*se_rho:.3f} 才算显著; 超出的滞后: "
      f"{[k+1 for k in range(12) if abs(rho[k]) > 2*se_rho] or '无'}")

# ① 现用估计量 (截断负值)
infl_clip = 1 + 2 * sum(max(r, 0.0) for r in rho[:12])
# ② 不截断求和 (同样 12 阶)
infl_raw = 1 + 2 * float(rho[:12].sum())
# ③ Bartlett / Newey-West 核 (线性降权, 不截断)
L = 12
w = 1 - np.arange(1, L + 1) / (L + 1)
infl_nw = 1 + 2 * float((w * rho[:L]).sum())
# ④ 重叠区块自助法: 直接估均值的方差
rng = np.random.default_rng(20260726)
def block_boot(a, bl, B=4000):
    m = len(a) - bl + 1
    starts = rng.integers(0, m, size=(B, int(np.ceil(len(a) / bl))))
    out = np.empty(B)
    for i in range(B):
        s = np.concatenate([a[j:j + bl] for j in starts[i]])[:len(a)]
        out[i] = s.mean()
    return out.std(ddof=1)
print("\n估计量对比:")
print(f"  ① 现用 (截断负值, 12 阶)      infl = {infl_clip:5.2f}   n_eff = {n/infl_clip:5.1f}")
print(f"  ② 不截断求和 (12 阶)          infl = {infl_raw:5.2f}   n_eff = {n/infl_raw:5.1f}")
print(f"  ③ Bartlett/NW 核 (L=12)       infl = {infl_nw:5.2f}   n_eff = {n/infl_nw:5.1f}")
for bl in (2, 4, 6, 12):
    se_b = block_boot(ic, bl)
    print(f"  ④ 重叠区块自助 (块长 {bl:2d})     infl = {(se_b/se_iid)**2:5.2f}   n_eff = {n/((se_b/se_iid)**2):5.1f}   (SE={se_b:.5f})")
# ⑤ Ljung-Box
def ljung_box(rho, n, h):
    q = n * (n + 2) * sum(rho[k] ** 2 / (n - k - 1) for k in range(h))
    return q
from math import erf, sqrt
for h in (6, 12):
    q = ljung_box(rho, n, h)
    # chi2 上尾近似 (Wilson-Hilferty)
    z = ((q / h) ** (1/3) - (1 - 2/(9*h))) / sqrt(2/(9*h))
    p = 0.5 * (1 - erf(z / sqrt(2)))
    print(f"\n⑤ Ljung-Box h={h}: Q={q:.2f}  (df={h})  p≈{p:.3f}  ⇒ "
          f"{'拒绝独立性' if p < 0.05 else '不能拒绝独立性 (ρ 与 0 不可区分)'}")
print("\n★ 现用估计量对纯噪声的偏差检验 (同长度白噪声, 1000 次):")
vals = [1 + 2*sum(max(v, 0.0) for v in
        [float((y[:-k]*y[k:]).sum()/ (y*y).sum()) for k in range(1, 13)])
        for y in (rng.standard_normal(n) - 0 for _ in range(400))
        for y in [y - y.mean()]]
print(f"   白噪声上 infl 的均值 = {np.mean(vals):.2f} (真值应为 1.00), 中位 {np.median(vals):.2f}")
