"""正典仪器复刻 @jpline: 把杠杆/回撤/regime 正典口径原样施于新代 NEW9 序列(文件口径 b, gross=1)。"""
import numpy as np, time
PD = "/mnt/storage/private/work_hsy/probe_artifacts"
z = np.load(f"{PD}/w10_v2gate_s42_NEW9.npz", allow_pickle=True)
cols = [str(c) for c in z["cols"]]; rec = z["d30_n2_c42_rec"]
ts = rec[:, cols.index("ts")].astype(np.int64)
net = rec[:, cols.index("net")].astype(np.float64) / 1e4
nsel = rec[:, cols.index("nsel")].astype(np.float64)
yrs = np.array([time.gmtime(int(t)).tm_year for t in ts])
n = len(ts); W = 2190
d0 = time.strftime("%F", time.gmtime(ts[0])); d1 = time.strftime("%F", time.gmtime(ts[-1]))
print(f"全史 n={n} {d0}..{d1}", flush=True)
lognav_base = np.log1p
for L in (2.0, 2.5, 3.0):
    r = net * L
    lognav = np.cumsum(np.log1p(r))
    starts = np.arange(0, n - W, 6)
    touch = np.zeros(len(starts), bool)
    for k, i0 in enumerate(starts):
        seg = lognav[i0:i0 + W] - (lognav[i0 - 1] if i0 else 0.0)
        nav = np.exp(seg); peak = np.maximum.accumulate(nav)
        touch[k] = (nav / peak <= 0.75).any()
    stat = {}
    for y in (2022, 2023, 2024, 2025):
        s = yrs[starts] == y
        if s.sum(): stat[y] = f"{touch[s].mean() * 100:.0f}%"
    print(f"[触线-25% 峰值相对 365d滚动窗] L={L}x 按起始年: {stat}", flush=True)
day = np.add.reduceat(net, np.arange(0, n // 6 * 6, 6)); nd = len(day)
for L in (2.0, 2.5, 3.0):
    c = int((day * L <= -0.04).sum())
    print(f"[-4%日] L={L}x: {c} 次 / {nd / 365:.1f} 年 = {c / (nd / 365):.1f}/年", flush=True)
q1, q2 = np.quantile(nsel, [1 / 3, 2 / 3])
for tag, s in (("窄档", nsel <= q1), ("中档", (nsel > q1) & (nsel < q2)), ("宽档", nsel >= q2)):
    print(f"[regime {tag}] n {int(s.sum())} 净 {net[s].mean() * 1e4:+.2f} bps/锚 (nsel分界 {q1:.0f}/{q2:.0f})", flush=True)
for L in (1.5, 2.0, 2.5, 3.0):
    nav = np.cumprod(1 + net * L); peak = np.maximum.accumulate(nav)
    print(f"[全史单路径] L={L}x 年化 {float(nav[-1] ** (2190 / n) - 1) * 100:+.1f}% 最大回撤 {float((1 - nav / peak).max()) * 100:.1f}%", flush=True)
for y in (2021, 2022, 2023, 2024, 2025, 2026):
    s = yrs == y; nav = np.cumprod(1 + net[s] * 2.0)
    print(f"[@2x 分年NAV] {y}: {float(nav[-1] - 1) * 100:+.1f}%  ({int(s.sum())}锚)", flush=True)
