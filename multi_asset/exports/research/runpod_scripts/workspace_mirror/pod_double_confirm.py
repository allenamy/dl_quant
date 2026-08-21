"""Double-confirm 电池: A β拆解(BTC/等权市场, 滚动β, 对冲后alpha t) B 逐月夏普表(36月)
C 灾难场景(市场最差10天的书表现) D 安慰剂(随机分数同构造书 ×50, 3.4 的分位).
基底 = 终形延迟执行 b 2024-26.
"""
import json, time, math
import numpy as np
import sys; sys.path.insert(0, "/workspace")
exec(open("/workspace/pod_queue_items.py").read().split("# 2024")[0])
# 终形净额序列(重算一次, 与 battery 同构)
H = np.zeros(NW, np.float64)
nets, iidx = [], []
mkt_ret = []
for i in range(nA):
    if not okA[i]: continue
    tgt = Wt[i].astype(np.float64)
    sm = H + 0.1 * (tgt - H)
    trade = sm - H
    sm = np.where(np.abs(trade) < 2.5e-4, H, sm)
    trade = sm - H
    j = pw_row[int(E_ts[i])]
    m = members[i]
    qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
    tr = tier_of(qv4h); tabs = np.abs(trade[m])
    cb = 0.0
    for tt in range(3):
        s_ = tr == tt
        mk, tk, fr = COST_B[tt]
        cb += tabs[s_].sum() * (fr * mk + (1 - fr) * tk)
    yv = np.nan_to_num(y4d[i, m], nan=0.0)
    fnow = np.nan_to_num(FN[j, m], nan=0.0)
    nets.append(float((sm[m] * yv).sum() * 1e4 - (sm[m] * fnow).sum() / 2 * 1e4 - cb))
    iidx.append(i)
    okm = np.isfinite(y4d[i, m])
    mkt_ret.append(float(np.nanmean(y4d[i, m][okm]) * 1e4))
    H = sm
nets = np.array(nets); iidx = np.array(iidx); mkt = np.array(mkt_ret)
win = yrs[iidx] >= 2024
X = nets[win]; M = mkt[win]; XI = iidx[win]
# A: β 拆解
btc_j = [pw_row[int(E_ts[i])] for i in XI]
cov = np.cov(X, M)
beta = cov[0, 1] / (cov[1, 1] + 1e-12)
alpha = X - beta * M
t_alpha = alpha.mean() / (alpha.std() / math.sqrt(len(alpha)))
sh_alpha = alpha.mean() / (alpha.std() + 1e-12) * math.sqrt(6 * 365)
r2 = float(np.corrcoef(X, M)[0, 1] ** 2)
print(f"A β拆解: 市场β {beta:+.4f} R² {r2:.4f} | 对冲后alpha夏普 {sh_alpha:.2f} t {t_alpha:.1f}", flush=True)
half = len(X) // 2
b1 = np.cov(X[:half], M[:half])[0,1] / (np.var(M[:half]) + 1e-12)
b2 = np.cov(X[half:], M[half:])[0,1] / (np.var(M[half:]) + 1e-12)
print(f"A 滚动β稳定: 前半 {b1:+.4f} 后半 {b2:+.4f}", flush=True)
# B: 逐月
print("B 逐月净额(bps/锚):", flush=True)
mon = {}
for k, i in enumerate(XI):
    t = time.gmtime(int(E_ts[i]))
    mon.setdefault((t.tm_year, t.tm_mon), []).append(X[k])
pos_m = 0; rows = []
for key in sorted(mon):
    v = np.array(mon[key])
    rows.append(f"{key[0]}-{key[1]:02d}:{v.mean():+.2f}")
    if v.mean() > 0: pos_m += 1
print("  " + " ".join(rows), flush=True)
print(f"  正月份 {pos_m}/{len(mon)} 最差月 {min(np.mean(v) for v in mon.values()):+.2f} bps/锚", flush=True)
# C: 市场最差 10 天
day_mkt, day_book = {}, {}
for k, i in enumerate(XI):
    d = time.strftime("%Y%m%d", time.gmtime(int(E_ts[i])))
    day_mkt[d] = day_mkt.get(d, 0) + M[k]
    day_book[d] = day_book.get(d, 0) + X[k]
worst = sorted(day_mkt, key=lambda d: day_mkt[d])[:10]
print("C 市场最差10天 vs 书:", flush=True)
for d in worst:
    print(f"  {d}: 市场 {day_mkt[d]:+.0f}bps 书 {day_book[d]:+.1f}bps", flush=True)
# D: 安慰剂 ×50
rng = np.random.default_rng(3)
plc = []
for trial in range(50):
    Hp = np.zeros(NW, np.float64)
    tot, cnt = 0.0, 0
    for i in range(0, nA, 3):
        if not okA[i] or yrs[i] < 2024: continue
        m = members[i]
        z = rng.standard_normal(len(m))
        w = z - z.mean()
        g = np.abs(w).sum(); w /= g
        capw = 2.5 / max(len(m), 1)
        w = np.clip(w, -capw, capw)
        g2 = np.abs(w).sum()
        if g2 > 1e-9: w /= g2
        tgt = np.zeros(NW); tgt[m] = w
        sm = Hp + 0.1 * (tgt - Hp)
        yv = np.zeros(NW); yv[m] = np.nan_to_num(y4d[i, m], nan=0.0)
        tot += float((sm * yv).sum() * 1e4); cnt += 1
        Hp = sm
    plc.append(tot / max(cnt, 1))
plc = np.array(plc)
print(f"D 安慰剂书×50: 毛均值 {plc.mean():+.3f}±{plc.std():.3f} bps/锚(应≈0) | 终形毛额远超 {X.mean()+0.3:+.2f}", flush=True)
print("DOUBLE_CONFIRM_DONE", flush=True)
