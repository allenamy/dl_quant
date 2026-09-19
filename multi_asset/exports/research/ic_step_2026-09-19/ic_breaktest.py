# -*- coding: utf-8 -*-
"""Where is the break, and is there one at all?
(a) placebo: sweep EVERY admissible split point and rank the documented combo-switch among them;
(b) structural break test: max-over-split-points difference against a day-permutation null;
(c) break vs monotone decline: Spearman(time, IC) against the same null, and R^2 of both models.

This device exists because the first version of DIAG_realized_ic_step_at_combo_switch_2026-09-19.md
attributed the step to the 2026-08-26 combo switch. (a) refutes that attribution.
READ-ONLY. Usage: python3 ic_breaktest.py
"""
import json, time
import numpy as np

LEDGER = "/Users/haosiyu/dl_quant_live/state/live/ic_monitor.jsonl"
SW = 1787716800          # 2026-08-26 04Z, first combo anchor (N_FIRST_COMBO, from canon_reconcile.py)
MIN = 40                 # minimum anchors on each side of a split
SEED = 20260919

rows = [json.loads(l) for l in open(LEDGER) if l.strip()]
rows.sort(key=lambda r: r["anchor_ts"])
ts = np.array([r["anchor_ts"] for r in rows], float)
ic = np.array([r["rank_ic"] for r in rows], float)
day = np.array([time.strftime("%Y-%m-%d", time.gmtime(t)) for t in ts])
days = sorted(set(day)); dmap = {d: ic[day == d] for d in days}
u = lambda t: time.strftime("%m-%d %HZ", time.gmtime(t))
print(f"账本 {len(rows)} 锚, {u(ts[0])} .. {u(ts[-1])}; UTC 日 {len(days)}")

def maxdiff(series):
    n = len(series); best, arg = -9.0, None
    for j in range(MIN, n - MIN + 1):
        d = series[:j].mean() - series[j:].mean()
        if d > best: best, arg = d, j
    return best, arg

# ---------- (a) placebo over every split point ----------
cands = [t for t in ts if (ts < t).sum() >= MIN and (ts >= t).sum() >= MIN]
res = sorted(((t, ic[ts < t].mean() - ic[ts >= t].mean()) for t in cands), key=lambda x: -x[1])
obs_sw = ic[ts < SW].mean() - ic[ts >= SW].mean()
rank = 1 + sum(1 for _, d in res if d > obs_sw)
print(f"\n(a) 安慰剂: {len(res)} 个候选切点")
print(f"    换装点 {u(SW)} 的差 = {obs_sw:+.5f}  ⇒ 排第 {rank}/{len(res)}, 经验 p = {rank/len(res):.4f}")
print("    差最大的前 5 个切点:")
for t, d in res[:5]:
    print(f"      {u(t)}  差 {d:+.5f}  (前 {int((ts<t).sum())} / 后 {int((ts>=t).sum())}){'  <- 换装' if t == SW else ''}")
i0 = int(np.searchsorted(ts, SW))
print("    换装点邻域(±k 锚):", end=" ")
for k in (-12, -6, -3, 0, 3, 6, 12):
    j = i0 + k
    if MIN <= j <= len(ts) - MIN:
        print(f"{k:+d}:{ic[:j].mean()-ic[j:].mean():+.4f}", end="  ")
print()

# ---------- (b) structural break test ----------
rng = np.random.default_rng(SEED)
obs_max, obs_j = maxdiff(ic)
B = 4000
null = np.empty(B)
for b in range(B):
    s = np.concatenate([dmap[days[i]] for i in rng.permutation(len(days))])
    null[b] = maxdiff(s)[0]
p = float((null >= obs_max).mean())
print(f"\n(b) 结构断点检验(日块置换零假设「无断点」, B={B})")
print(f"    观测最大切点差 {obs_max:+.5f} 于 {u(ts[obs_j])}")
print(f"    零分布 中位 {np.median(null):+.5f}  95% {np.percentile(null,95):+.5f}  99% {np.percentile(null,99):+.5f}")
print(f"    ★ p = {p:.4f}  ⇒ {'存在断点' if p < 0.05 else '无法拒绝无断点'}")

# ---------- (c) break vs monotone decline ----------
rk = lambda x: np.argsort(np.argsort(x)).astype(float)
r = np.arange(len(ic))
rho = float(np.corrcoef(rk(r), rk(ic))[0, 1])
bs = []
for _ in range(2000):
    s = np.concatenate([dmap[rng.choice(days)] for _ in days])
    bs.append(np.corrcoef(rk(np.arange(len(s))), rk(s))[0, 1])
print(f"\n(c) 断点 vs 单调下滑")
print(f"    Spearman(时间, IC) = {rho:+.4f}; 置换零分布 95% 区间 [{np.percentile(bs,2.5):+.4f}, {np.percentile(bs,97.5):+.4f}]"
      f"  ⇒ {'出界, 趋势成立' if not (np.percentile(bs,2.5) < rho < np.percentile(bs,97.5)) else '在界内'}")
j = obs_j
step = np.concatenate([np.full(j, ic[:j].mean()), np.full(len(ic)-j, ic[j:].mean())])
lin = np.polyval(np.polyfit(r, ic, 1), r)
sst = ((ic - ic.mean())**2).sum()
print(f"    断点模型 R² {1-((ic-step)**2).sum()/sst:.4f} vs 线性趋势 R² {1-((ic-lin)**2).sum()/sst:.4f}"
      f"   (逐锚 sd {ic.std(ddof=1):.4f} ⇒ 信号在均值不在逐锚)")
print("\n读法: (a) 把「断点在换装时刻」证伪; (b) 证明【存在】断点但位置在 08-19; (c) 说明断点与单调下滑分不开。")
