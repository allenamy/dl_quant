"""逐年收益差归因 @jpline: NEW9 序列拆 腿贡献×w3×广度×截面波动×carry×cost, 并测 net~nsel 年内相关。"""
import numpy as np, time
PD = "/mnt/storage/private/work_hsy/probe_artifacts"
B = "/mnt/storage/private/work_hsy/pod_backup_2026-08-21"
MT = np.load(f"{B}/wide_fea_hist_meta.npz", allow_pickle=True)
mts = MT["E_ts"].astype(np.int64); y4 = MT["y4"]
mrow = {int(t): i for i, t in enumerate(mts)}
z = np.load(f"{PD}/w10_v2gate_s42_NEW9.npz", allow_pickle=True)
cols = [str(c) for c in z["cols"]]; rec = z["d30_n2_c42_rec"]
g = lambda k: rec[:, cols.index(k)].astype(np.float64)
ts = rec[:, cols.index("ts")].astype(np.int64)
yrs = np.array([time.gmtime(int(t)).tm_year for t in ts])
net = g("net_ex"); nsel = g("nsel"); carry = g("carry_ex"); cost = g("cost_ex")
lk, lr, lf = g("leg_king"), g("leg_rev24"), g("leg_fund")
wk, wf = g("w3_king"), g("w3_fund")
xv = np.full(len(ts), np.nan); disp = np.full(len(ts), np.nan)
for p, t in enumerate(ts):
    i = mrow.get(int(t))
    if i is None: continue
    v = y4[i]; v = v[np.isfinite(v)]
    if len(v) > 50: xv[p] = v.std(); disp[p] = np.subtract(*np.quantile(v, [0.9, 0.1]))
print("年 | 净ex | fund腿贡献 | king腿贡献 | w3_fund | nsel均 | 截面σ(bps) | 截面9-1分位差 | carry | cost")
for y in (2023, 2024, 2025, 2026):
    s = yrs == y
    fund_c = (lf * wf)[s].mean(); king_c = (lk * wk)[s].mean()
    print(f"{y} | {net[s].mean():+.2f} | {fund_c:+.2f} | {king_c:+.2f} | {wf[s].mean():.2f} | {nsel[s].mean():.0f} | {np.nanmean(xv[s])*1e4:.0f} | {np.nanmean(disp[s])*1e4:.0f} | {carry[s].mean():+.2f} | {cost[s].mean():.2f}")
    ok = s & np.isfinite(xv)
    c_n = np.corrcoef(net[ok], nsel[ok])[0, 1]; c_v = np.corrcoef(net[ok], xv[ok])[0, 1]
    print(f"     年内相关: net~nsel {c_n:+.2f} net~截面σ {c_v:+.2f}")
# 跨年归因: 2026 vs 2024 的 Δnet 分解(腿贡献差)
for a, b in ((2026, 2024),):
    sa, sb = yrs == a, yrs == b
    d_f = (lf * wf)[sa].mean() - (lf * wf)[sb].mean()
    d_k = (lk * wk)[sa].mean() - (lk * wk)[sb].mean()
    d_n = net[sa].mean() - net[sb].mean()
    print(f"Δ({a}-{b}) 净 {d_n:+.2f} = fund腿 {d_f:+.2f} + king腿 {d_k:+.2f} + 残差(成本/交互) {d_n-d_f-d_k:+.2f}")
print("ATTRIB_DONE")
