"""king 腿角色澄清 @jpline: 未加权腿 alpha 逐年 / 腿间相关 / 方差压制测试(fund-only vs 加king)。"""
import numpy as np, time
PD = "/mnt/storage/private/work_hsy/probe_artifacts"
z = np.load(f"{PD}/w10_v2gate_s42_NEW9.npz", allow_pickle=True)
cols = [str(c) for c in z["cols"]]; rec = z["d30_n2_c42_rec"]
g = lambda k: rec[:, cols.index(k)].astype(np.float64)
ts = rec[:, cols.index("ts")].astype(np.int64)
yrs = np.array([time.gmtime(int(t)).tm_year for t in ts])
lk, lf = g("leg_king"), g("leg_fund"); wk, wf = g("w3_king"), g("w3_fund")
net = g("net_ex")
print("年 | king腿未加权净(bps) 夏普 | fund腿未加权 夏普 | corr(king,fund) | 回放w3_king均 |")
for y in (2023, 2024, 2025, 2026):
    s = yrs == y
    shk = lk[s].mean() / (lk[s].std() + 1e-12) * np.sqrt(6 * 365)
    shf = lf[s].mean() / (lf[s].std() + 1e-12) * np.sqrt(6 * 365)
    c = np.corrcoef(lk[s], lf[s])[0, 1]
    print(f"{y} | {lk[s].mean():+.2f} {shk:+.2f} | {lf[s].mean():+.2f} {shf:+.2f} | {c:+.2f} | {wk[s].mean():.2f}")
# 方差压制: 合成对比 — 纯fund腿收益序列 vs 0.2king+0.8fund(固定席位, 分数层近似)
for y in (2025, 2026):
    s = yrs == y
    pf = lf[s]
    mix = 0.2 * lk[s] + 0.8 * lf[s]
    for tag, r in (("纯fund", pf), ("0.2k+0.8f", mix)):
        print(f"{y} {tag}: 净{r.mean():+.2f} σ{r.std():.2f} 夏普{r.mean()/(r.std()+1e-12)*np.sqrt(6*365):+.2f}")
print("KING_ROLE_DONE")
